from django.contrib import admin
from .models import (
    Client, PracticeArea, Attorney, Matter, Service,
    TimeEntry, Expense, Invoice, InvoiceLineItem, Document, Payment,
    ImportJob, ImportFile, ImportQuestion, ImportLog, ImportMapping, ImportedRecord
)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['client_number', 'name', 'client_type', 'email', 'is_active', 'created_date']
    list_filter = ['client_type', 'is_active', 'created_date']
    search_fields = ['client_number', 'name', 'email', 'phone']
    readonly_fields = ['created_date']


@admin.register(PracticeArea)
class PracticeAreaAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code']


@admin.register(Attorney)
class AttorneyAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'full_name', 'level', 'email', 'hourly_rate', 'is_active']
    list_filter = ['level', 'is_active', 'hire_date']
    search_fields = ['employee_id', 'first_name', 'last_name', 'email', 'bar_number']
    filter_horizontal = ['practice_areas']
    readonly_fields = ['full_name']


@admin.register(Matter)
class MatterAdmin(admin.ModelAdmin):
    list_display = ['matter_number', 'title', 'client', 'practice_area', 'lead_attorney', 'status', 'billing_type', 'opened_date']
    list_filter = ['status', 'billing_type', 'practice_area', 'opened_date']
    search_fields = ['matter_number', 'title', 'description']
    filter_horizontal = ['assigned_attorneys']
    readonly_fields = ['opened_date']


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'default_rate', 'is_active']
    list_filter = ['is_active']
    search_fields = ['code', 'name']


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ['date', 'attorney', 'matter', 'service', 'hours', 'hourly_rate', 'total_amount', 'status']
    list_filter = ['status', 'date', 'attorney', 'service']
    search_fields = ['description', 'matter__matter_number', 'attorney__last_name']
    readonly_fields = ['total_amount', 'created_at', 'updated_at']


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['date', 'category', 'matter', 'attorney', 'amount', 'is_billable', 'status']
    list_filter = ['status', 'is_billable', 'category', 'date']
    search_fields = ['description', 'category', 'receipt_number', 'matter__matter_number']
    readonly_fields = ['created_at']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'client', 'matter', 'invoice_date', 'due_date', 'total_amount', 'paid_amount', 'balance_due', 'status']
    list_filter = ['status', 'invoice_date', 'due_date']
    search_fields = ['invoice_number', 'client__name', 'matter__matter_number']
    readonly_fields = ['balance_due', 'created_at']


@admin.register(InvoiceLineItem)
class InvoiceLineItemAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'item_type', 'description', 'quantity', 'rate', 'amount']
    list_filter = ['item_type']
    search_fields = ['description', 'invoice__invoice_number']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'matter', 'document_type', 'uploaded_by', 'uploaded_date', 'is_confidential']
    list_filter = ['document_type', 'is_confidential', 'uploaded_date']
    search_fields = ['title', 'description', 'matter__matter_number']
    readonly_fields = ['uploaded_date']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_date', 'client', 'invoice', 'amount', 'payment_method', 'reference_number']
    list_filter = ['payment_method', 'payment_date']
    search_fields = ['client__name', 'invoice__invoice_number', 'reference_number']
    readonly_fields = ['created_at']


# Import system admin

@admin.register(ImportJob)
class ImportJobAdmin(admin.ModelAdmin):
    list_display = ['id', 'status', 'created_at', 'files_uploaded', 'records_imported', 'records_skipped', 'errors_count']
    list_filter = ['status', 'created_at']
    search_fields = ['id', 'render_job_id']
    readonly_fields = ['created_at', 'started_at', 'completed_at', 'render_job_id']

    fieldsets = (
        ('Job Info', {
            'fields': ('created_by', 'status', 'created_at', 'started_at', 'completed_at')
        }),
        ('Render Integration', {
            'fields': ('render_job_id', 'render_service_id')
        }),
        ('Statistics', {
            'fields': ('files_uploaded', 'records_processed', 'records_imported', 'records_skipped', 'errors_count')
        }),
        ('Details', {
            'fields': ('summary', 'error_details')
        }),
    )


@admin.register(ImportFile)
class ImportFileAdmin(admin.ModelAdmin):
    list_display = ['filename', 'job', 'file_type', 'uploaded_at', 'file_size', 'processed', 'records_found']
    list_filter = ['file_type', 'processed', 'uploaded_at']
    search_fields = ['filename', 'job__id']
    readonly_fields = ['uploaded_at', 'file_size']


@admin.register(ImportQuestion)
class ImportQuestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'job', 'question_type', 'status', 'created_at', 'answered_at']
    list_filter = ['question_type', 'status', 'created_at']
    search_fields = ['question_text', 'answer', 'job__id']
    readonly_fields = ['created_at', 'answered_at']

    fieldsets = (
        ('Question', {
            'fields': ('job', 'question_type', 'question_text', 'context', 'options')
        }),
        ('Answer', {
            'fields': ('status', 'answer', 'answered_at')
        }),
        ('Metadata', {
            'fields': ('related_entity', 'related_data')
        }),
    )


@admin.register(ImportLog)
class ImportLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'job', 'level', 'message_preview']
    list_filter = ['level', 'timestamp']
    search_fields = ['message', 'job__id']
    readonly_fields = ['timestamp']

    def message_preview(self, obj):
        return obj.message[:100] + '...' if len(obj.message) > 100 else obj.message
    message_preview.short_description = 'Message'


@admin.register(ImportMapping)
class ImportMappingAdmin(admin.ModelAdmin):
    list_display = ['file', 'source_column', 'target_model', 'target_field', 'requires_transformation', 'confidence']
    list_filter = ['target_model', 'requires_transformation', 'file']
    search_fields = ['source_column', 'target_field']


@admin.register(ImportedRecord)
class ImportedRecordAdmin(admin.ModelAdmin):
    list_display = ['job', 'model_name', 'record_id', 'source_file', 'source_row', 'created_at']
    list_filter = ['model_name', 'created_at']
    search_fields = ['job__id', 'model_name', 'record_id']
    readonly_fields = ['created_at']
