from django.db import models
from django.contrib.auth.models import User
import json


class ImportJob(models.Model):
    """Tracks an import session"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('uploading', 'Uploading Files'),
        ('queued', 'Queued for Processing'),
        ('processing', 'Processing'),
        ('waiting_input', 'Waiting for User Input'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='import_jobs')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Render.com job tracking
    render_job_id = models.CharField(max_length=100, blank=True)
    render_service_id = models.CharField(max_length=100, blank=True)

    # Statistics
    files_uploaded = models.IntegerField(default=0)
    records_processed = models.IntegerField(default=0)
    records_imported = models.IntegerField(default=0)
    records_skipped = models.IntegerField(default=0)
    errors_count = models.IntegerField(default=0)

    # Summary
    summary = models.TextField(blank=True)
    error_details = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Import Job {self.id} - {self.status} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    def add_log(self, message, level='INFO', metadata=None):
        """Helper to add a log entry"""
        ImportLog.objects.create(
            job=self,
            message=message,
            level=level,
            metadata=json.dumps(metadata) if metadata else ''
        )


class ImportFile(models.Model):
    """Uploaded files for import"""
    job = models.ForeignKey(ImportJob, on_delete=models.CASCADE, related_name='files')
    filename = models.CharField(max_length=255)
    file = models.FileField(upload_to='import_files/%Y/%m/%d/')
    file_type = models.CharField(max_length=10)  # csv, json, xlsx
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_size = models.IntegerField(default=0)  # bytes

    # Processing status
    processed = models.BooleanField(default=False)
    records_found = models.IntegerField(default=0)

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f"{self.filename} ({self.file_type})"


class ImportQuestion(models.Model):
    """Questions Claude asks during import that need user input"""
    QUESTION_TYPE_CHOICES = [
        ('yes_no', 'Yes/No'),
        ('choice', 'Multiple Choice'),
        ('text', 'Text Input'),
        ('skip_continue', 'Skip or Continue'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('answered', 'Answered'),
        ('skipped', 'Skipped'),
    ]

    job = models.ForeignKey(ImportJob, on_delete=models.CASCADE, related_name='questions')
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES)
    question_text = models.TextField()
    context = models.TextField(blank=True)  # Additional context for the question
    options = models.JSONField(null=True, blank=True)  # For choice questions

    # Answer
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    answer = models.TextField(blank=True)
    answered_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    related_entity = models.CharField(max_length=50, blank=True)  # e.g., "Client", "Matter"
    related_data = models.JSONField(null=True, blank=True)  # The conflicting data

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Question {self.id}: {self.question_text[:50]}..."


class ImportLog(models.Model):
    """Real-time logs from the import process"""
    LEVEL_CHOICES = [
        ('DEBUG', 'Debug'),
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('SUCCESS', 'Success'),
        ('THINKING', 'Claude Thinking'),
        ('DECISION', 'Claude Decision'),
    ]

    job = models.ForeignKey(ImportJob, on_delete=models.CASCADE, related_name='logs')
    timestamp = models.DateTimeField(auto_now_add=True)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='INFO')
    message = models.TextField()
    metadata = models.TextField(blank=True)  # JSON string for additional data

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"[{self.level}] {self.timestamp.strftime('%H:%M:%S')} - {self.message[:50]}"

    @property
    def metadata_dict(self):
        """Parse metadata JSON"""
        if self.metadata:
            try:
                return json.loads(self.metadata)
            except:
                return {}
        return {}


class ImportMapping(models.Model):
    """Stores column mappings detected by Claude"""
    job = models.ForeignKey(ImportJob, on_delete=models.CASCADE, related_name='mappings')
    file = models.ForeignKey(ImportFile, on_delete=models.CASCADE, related_name='mappings')

    source_column = models.CharField(max_length=100)
    target_model = models.CharField(max_length=50)  # e.g., "Client", "Matter"
    target_field = models.CharField(max_length=50)  # e.g., "client_number", "name"

    # Transformation info
    requires_transformation = models.BooleanField(default=False)
    transformation_type = models.CharField(max_length=50, blank=True)  # e.g., "date_format", "name_lookup"
    transformation_details = models.JSONField(null=True, blank=True)

    confidence = models.FloatField(default=1.0)  # Claude's confidence in the mapping

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['file', 'source_column']
        unique_together = ['file', 'source_column']

    def __str__(self):
        return f"{self.file.filename}: {self.source_column} → {self.target_model}.{self.target_field}"


class ImportedRecord(models.Model):
    """Track which records were created during import for rollback purposes"""
    job = models.ForeignKey(ImportJob, on_delete=models.CASCADE, related_name='imported_records')
    model_name = models.CharField(max_length=50)  # e.g., "Client", "Matter"
    record_id = models.IntegerField()  # The ID of the created record
    source_file = models.ForeignKey(ImportFile, on_delete=models.CASCADE, related_name='created_records')
    source_row = models.IntegerField(null=True, blank=True)  # Row number in source file
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['model_name', 'record_id']),
        ]

    def __str__(self):
        return f"{self.model_name} #{self.record_id} from {self.source_file.filename}"
