from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class Client(models.Model):
    """Law firm client"""
    CLIENT_TYPE_CHOICES = [
        ('individual', 'Individual'),
        ('business', 'Business'),
        ('nonprofit', 'Non-Profit'),
    ]

    client_number = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    client_type = models.CharField(max_length=20, choices=CLIENT_TYPE_CHOICES)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    tax_id = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_date = models.DateField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.client_number} - {self.name}"


class PracticeArea(models.Model):
    """Legal practice areas"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Attorney(models.Model):
    """Attorneys working at the firm"""
    LEVEL_CHOICES = [
        ('partner', 'Partner'),
        ('senior', 'Senior Associate'),
        ('associate', 'Associate'),
        ('junior', 'Junior Associate'),
    ]

    employee_id = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    bar_number = models.CharField(max_length=50)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    practice_areas = models.ManyToManyField(PracticeArea, related_name='attorneys')
    hire_date = models.DateField()
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Matter(models.Model):
    """Legal matters/cases"""
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('pending', 'Pending'),
        ('closed', 'Closed'),
        ('on_hold', 'On Hold'),
    ]

    BILLING_TYPE_CHOICES = [
        ('hourly', 'Hourly'),
        ('flat_fee', 'Flat Fee'),
        ('contingency', 'Contingency'),
        ('retainer', 'Retainer'),
    ]

    matter_number = models.CharField(max_length=30, unique=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='matters')
    title = models.CharField(max_length=200)
    description = models.TextField()
    practice_area = models.ForeignKey(PracticeArea, on_delete=models.PROTECT, related_name='matters')
    lead_attorney = models.ForeignKey(Attorney, on_delete=models.PROTECT, related_name='lead_matters')
    assigned_attorneys = models.ManyToManyField(Attorney, related_name='assigned_matters')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    billing_type = models.CharField(max_length=20, choices=BILLING_TYPE_CHOICES, default='hourly')
    flat_fee_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    contingency_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    opened_date = models.DateField()
    closed_date = models.DateField(null=True, blank=True)
    estimated_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ['-opened_date']

    def __str__(self):
        return f"{self.matter_number} - {self.title}"


class Service(models.Model):
    """Billable services"""
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField()
    default_rate = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.code} - {self.name}"


class TimeEntry(models.Model):
    """Time entries for billing"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('billed', 'Billed'),
    ]

    matter = models.ForeignKey(Matter, on_delete=models.PROTECT, related_name='time_entries')
    attorney = models.ForeignKey(Attorney, on_delete=models.PROTECT, related_name='time_entries')
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name='time_entries')
    date = models.DateField()
    hours = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.attorney} - {self.matter} - {self.date}"

    @property
    def total_amount(self):
        return self.hours * self.hourly_rate


class Expense(models.Model):
    """Expenses related to matters"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('billed', 'Billed'),
        ('reimbursed', 'Reimbursed'),
    ]

    matter = models.ForeignKey(Matter, on_delete=models.PROTECT, related_name='expenses')
    attorney = models.ForeignKey(Attorney, on_delete=models.PROTECT, related_name='expenses')
    date = models.DateField()
    category = models.CharField(max_length=100)
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    is_billable = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    receipt_number = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.category} - {self.matter} - ${self.amount}"


class Invoice(models.Model):
    """Client invoices"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]

    invoice_number = models.CharField(max_length=30, unique=True)
    matter = models.ForeignKey(Matter, on_delete=models.PROTECT, related_name='invoices')
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='invoices')
    invoice_date = models.DateField()
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-invoice_date']

    def __str__(self):
        return f"{self.invoice_number} - {self.client}"

    @property
    def balance_due(self):
        return self.total_amount - self.paid_amount


class InvoiceLineItem(models.Model):
    """Line items on invoices"""
    ITEM_TYPE_CHOICES = [
        ('time', 'Time Entry'),
        ('expense', 'Expense'),
        ('adjustment', 'Adjustment'),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='line_items')
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES)
    time_entry = models.ForeignKey(TimeEntry, on_delete=models.PROTECT, null=True, blank=True, related_name='invoice_items')
    expense = models.ForeignKey(Expense, on_delete=models.PROTECT, null=True, blank=True, related_name='invoice_items')
    description = models.TextField()
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    rate = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.invoice} - {self.description}"


class Document(models.Model):
    """Documents related to matters"""
    DOCUMENT_TYPE_CHOICES = [
        ('contract', 'Contract'),
        ('brief', 'Brief'),
        ('motion', 'Motion'),
        ('correspondence', 'Correspondence'),
        ('evidence', 'Evidence'),
        ('other', 'Other'),
    ]

    matter = models.ForeignKey(Matter, on_delete=models.PROTECT, related_name='documents')
    title = models.CharField(max_length=200)
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPE_CHOICES)
    description = models.TextField(blank=True)
    file_path = models.CharField(max_length=500)
    uploaded_by = models.ForeignKey(Attorney, on_delete=models.PROTECT, related_name='uploaded_documents')
    uploaded_date = models.DateTimeField(auto_now_add=True)
    is_confidential = models.BooleanField(default=False)

    class Meta:
        ordering = ['-uploaded_date']

    def __str__(self):
        return f"{self.title} - {self.matter}"


class Payment(models.Model):
    """Payments from clients"""
    PAYMENT_METHOD_CHOICES = [
        ('check', 'Check'),
        ('wire', 'Wire Transfer'),
        ('credit_card', 'Credit Card'),
        ('ach', 'ACH'),
        ('cash', 'Cash'),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='payments')
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='payments')
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-payment_date']

    def __str__(self):
        return f"{self.client} - ${self.amount} - {self.payment_date}"


# Import models
from .import_models import (
    ImportJob, ImportFile, ImportQuestion,
    ImportLog, ImportMapping, ImportedRecord
)
