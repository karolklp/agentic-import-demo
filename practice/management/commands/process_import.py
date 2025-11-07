"""
Autonomous import worker using Claude for intelligent data import.
This script runs as a standalone process (locally or on Render.com)
and uses Claude to analyze, clean, and import messy data files.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
import csv
import json
import os
import sys
from datetime import datetime
from decimal import Decimal
import re

# Import Django models
from practice.models import (
    ImportJob, ImportFile, ImportQuestion, ImportLog,
    Client, Attorney, PracticeArea, Matter, Service,
    TimeEntry, Expense, Invoice, Payment
)


class ImportWorker:
    """Handles the autonomous import process with Claude assistance"""

    def __init__(self, job_id, base_url='http://127.0.0.1:8000'):
        self.job_id = job_id
        self.base_url = base_url
        self.job = ImportJob.objects.get(id=job_id)

    def log(self, message, level='INFO', metadata=None):
        """Add a log entry"""
        print(f"[{level}] {message}")
        self.job.add_log(message, level, metadata)

    def ask_question(self, question_text, question_type='text', context='', options=None):
        """Ask a question and wait for answer"""
        self.log(f"Asking question: {question_text}", 'DECISION')

        question = ImportQuestion.objects.create(
            job=self.job,
            question_type=question_type,
            question_text=question_text,
            context=context,
            options=options
        )

        self.job.status = 'waiting_input'
        self.job.save()

        # Poll for answer (in production, this would be more sophisticated)
        import time
        max_wait = 300  # 5 minutes
        waited = 0
        while waited < max_wait:
            time.sleep(2)
            waited += 2
            question.refresh_from_db()

            if question.status == 'answered':
                self.job.status = 'processing'
                self.job.save()
                return question.answer

        return None

    def normalize_date(self, date_str):
        """Parse various date formats"""
        if not date_str:
            return None

        date_str = str(date_str).strip()

        # Try various formats
        formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%d-%m-%Y',
            '%Y/%m/%d',
            '%d/%m/%Y',
            '%B %d %Y',
            '%b %d %Y',
            '%B %d, %Y',
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except:
                continue

        self.log(f"Could not parse date: {date_str}", 'WARNING')
        return None

    def fuzzy_match_client(self, name, tax_id=None):
        """Find client by fuzzy name matching"""
        name_clean = name.upper().strip()

        # Remove common suffixes
        name_clean = re.sub(r'\s+(LLC|INC|CORP|CORPORATION|LTD)\.?$', '', name_clean)

        clients = Client.objects.all()
        for client in clients:
            client_name = client.name.upper().strip()
            client_name = re.sub(r'\s+(LLC|INC|CORP|CORPORATION|LTD)\.?$', '', client_name)

            if client_name == name_clean:
                return client

            # Check tax ID if provided
            if tax_id and client.tax_id == tax_id:
                return client

        return None

    def process(self):
        """Main import process"""
        try:
            self.job.status = 'processing'
            self.job.started_at = timezone.now()
            self.job.save()

            self.log("=" * 60, 'INFO')
            self.log("AUTONOMOUS IMPORT STARTED", 'INFO')
            self.log("=" * 60, 'INFO')

            # Phase 1: Analysis
            self.log("\n>>> PHASE 1: Analyzing uploaded files...", 'THINKING')
            files_data = self.analyze_files()

            # Phase 2: Dependency Resolution
            self.log("\n>>> PHASE 2: Determining import order...", 'THINKING')
            import_order = self.determine_import_order(files_data)

            # Phase 3: Import Execution
            self.log("\n>>> PHASE 3: Importing data...", 'THINKING')
            self.execute_imports(import_order, files_data)

            # Complete
            self.job.status = 'completed'
            self.job.completed_at = timezone.now()
            self.job.save()

            self.log("=" * 60, 'SUCCESS')
            self.log("IMPORT COMPLETED SUCCESSFULLY", 'SUCCESS')
            self.log("=" * 60, 'SUCCESS')
            self.log(f"Total imported: {self.job.records_imported}", 'SUCCESS')
            self.log(f"Total skipped: {self.job.records_skipped}", 'SUCCESS')
            self.log(f"Total errors: {self.job.errors_count}", 'SUCCESS')

        except Exception as e:
            self.log(f"Import failed with error: {str(e)}", 'ERROR')
            self.job.status = 'failed'
            self.job.error_details = str(e)
            self.job.completed_at = timezone.now()
            self.job.save()
            raise

    def analyze_files(self):
        """Analyze all uploaded files"""
        files_data = {}

        for import_file in self.job.files.all():
            self.log(f"Analyzing: {import_file.filename}", 'INFO')

            file_path = import_file.file.path

            if import_file.file_type == 'csv':
                data = self.analyze_csv(file_path)
            elif import_file.file_type == 'json':
                data = self.analyze_json(file_path)
            else:
                self.log(f"Unsupported file type: {import_file.file_type}", 'WARNING')
                continue

            files_data[import_file.id] = {
                'file': import_file,
                'data': data,
                'detected_type': self.detect_entity_type(import_file.filename, data)
            }

            self.log(f"  Detected type: {files_data[import_file.id]['detected_type']}", 'INFO')
            self.log(f"  Records found: {len(data)}", 'INFO')

        return files_data

    def analyze_csv(self, file_path):
        """Read and analyze CSV file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)

    def analyze_json(self, file_path):
        """Read and analyze JSON file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Handle nested structures
            if isinstance(data, dict):
                # Flatten nested lists
                result = []
                for key, value in data.items():
                    if isinstance(value, list):
                        result.extend(value)
                return result
            return data if isinstance(data, list) else [data]

    def detect_entity_type(self, filename, data):
        """Detect what type of entity this file contains"""
        filename_lower = filename.lower()

        if 'client' in filename_lower:
            return 'clients'
        elif 'attorney' in filename_lower or 'lawyer' in filename_lower:
            return 'attorneys'
        elif 'matter' in filename_lower or 'case' in filename_lower:
            return 'matters'
        elif 'time' in filename_lower or 'hour' in filename_lower:
            return 'time_entries'
        elif 'billing' in filename_lower or 'invoice' in filename_lower:
            return 'invoices'
        elif 'payment' in filename_lower:
            return 'payments'

        # Analyze column names if available
        if data and len(data) > 0:
            columns = set(str(k).lower() for k in data[0].keys())

            if 'client_number' in columns or 'clientid' in columns:
                return 'clients'
            elif 'employeeid' in columns or 'bar' in columns:
                return 'attorneys'
            elif 'matternumber' in columns or 'matter_number' in columns:
                return 'matters'
            elif 'hours' in columns or 'time_spent' in columns:
                return 'time_entries'

        return 'unknown'

    def determine_import_order(self, files_data):
        """Determine correct order for importing files"""
        # Dependency graph
        order = {
            'clients': 1,
            'attorneys': 2,
            'matters': 3,
            'time_entries': 4,
            'invoices': 5,
            'payments': 6
        }

        sorted_files = sorted(
            files_data.items(),
            key=lambda x: order.get(x[1]['detected_type'], 99)
        )

        self.log("Import order determined:", 'DECISION')
        for file_id, file_info in sorted_files:
            self.log(f"  {file_info['file'].filename} -> {file_info['detected_type']}", 'INFO')

        return sorted_files

    def execute_imports(self, import_order, files_data):
        """Execute imports in correct order"""
        for file_id, file_info in import_order:
            entity_type = file_info['detected_type']
            data = file_info['data']
            file_obj = file_info['file']

            self.log(f"\nImporting {entity_type} from {file_obj.filename}...", 'INFO')

            if entity_type == 'clients':
                self.import_clients(data, file_obj)
            elif entity_type == 'attorneys':
                self.import_attorneys(data, file_obj)
            elif entity_type == 'matters':
                self.import_matters(data, file_obj)
            elif entity_type == 'time_entries':
                self.import_time_entries(data, file_obj)
            elif entity_type == 'invoices':
                self.import_invoices(data, file_obj)
            else:
                self.log(f"Skipping unknown entity type: {entity_type}", 'WARNING')

    def import_clients(self, data, file_obj):
        """Import clients with duplicate detection"""
        for idx, row in enumerate(data):
            try:
                # Extract fields with various column name variations
                client_number = row.get('Client Number') or row.get('ClientNumber') or row.get('client_number')
                name = row.get('Client Name') or row.get('Name') or row.get('name')
                client_type = (row.get('Type') or row.get('client_type') or 'individual').lower()
                email = row.get('Email Address') or row.get('Email') or row.get('email')
                phone = row.get('Phone') or row.get('phone')
                address = row.get('Address') or row.get('address')
                tax_id = row.get('Tax ID') or row.get('TaxID') or row.get('tax_id') or ''
                status_str = (row.get('Status') or 'active').lower()
                is_active = status_str == 'active'
                joined_date = self.normalize_date(row.get('Joined Date') or row.get('created_date'))

                # Check for duplicate
                existing = self.fuzzy_match_client(name, tax_id)
                if existing:
                    answer = self.ask_question(
                        f"Found similar client: '{existing.name}' (#{existing.client_number}). Is this the same as '{name}'?",
                        question_type='yes_no',
                        context=f"Existing: {existing.name} | Tax ID: {existing.tax_id}\nNew: {name} | Tax ID: {tax_id}"
                    )

                    if answer and answer.lower() == 'yes':
                        self.log(f"Skipping duplicate client: {name}", 'INFO')
                        self.job.records_skipped += 1
                        self.job.save()
                        continue

                # Create client
                with transaction.atomic():
                    client = Client.objects.create(
                        client_number=client_number,
                        name=name,
                        client_type=client_type,
                        email=email,
                        phone=phone,
                        address=address,
                        tax_id=tax_id,
                        is_active=is_active
                    )

                    self.log(f"  Created client: {client.name} ({client.client_number})", 'SUCCESS')
                    self.job.records_imported += 1
                    self.job.records_processed += 1
                    self.job.save()

            except Exception as e:
                self.log(f"  Error importing client row {idx}: {str(e)}", 'ERROR')
                self.job.errors_count += 1
                self.job.save()

    def import_attorneys(self, data, file_obj):
        """Import attorneys"""
        for idx, row in enumerate(data):
            try:
                employee_id = row.get('EmployeeID') or row.get('employee_id')
                first_name = row.get('FirstName') or row.get('first_name')
                last_name = row.get('LastName') or row.get('last_name')
                email = row.get('email') or row.get('Email')
                bar_number = row.get('Bar #') or row.get('BarNumber') or row.get('bar_number')
                level = (row.get('Level') or row.get('level') or 'associate').lower()
                hire_date = self.normalize_date(row.get('HireDate') or row.get('hire_date'))
                rate = Decimal(str(row.get('Rate') or row.get('hourly_rate') or '250.00'))

                # Check if already exists
                if Attorney.objects.filter(employee_id=employee_id).exists():
                    self.log(f"  Skipping duplicate attorney: {employee_id}", 'INFO')
                    self.job.records_skipped += 1
                    self.job.save()
                    continue

                with transaction.atomic():
                    attorney = Attorney.objects.create(
                        employee_id=employee_id,
                        first_name=first_name,
                        last_name=last_name,
                        email=email,
                        bar_number=bar_number,
                        level=level,
                        hire_date=hire_date or timezone.now().date(),
                        hourly_rate=rate
                    )

                    self.log(f"  Created attorney: {attorney.full_name} ({attorney.employee_id})", 'SUCCESS')
                    self.job.records_imported += 1
                    self.job.records_processed += 1
                    self.job.save()

            except Exception as e:
                self.log(f"  Error importing attorney row {idx}: {str(e)}", 'ERROR')
                self.job.errors_count += 1
                self.job.save()

    def import_matters(self, data, file_obj):
        """Import matters with FK resolution"""
        for idx, row in enumerate(data):
            try:
                matter_number = row.get('MatterNumber') or row.get('matter_number')
                client_id = row.get('ClientID') or row.get('client_id')
                title = row.get('Title') or row.get('title')
                description = row.get('Description') or row.get('description') or ''
                practice_area_name = row.get('Practice Area') or row.get('practice_area')
                lead_attorney_id = row.get('LeadAttorney') or row.get('lead_attorney')
                status = (row.get('Status') or 'open').lower()
                billing_type = (row.get('BillingType') or 'hourly').lower().replace(' ', '_')
                opened_date = self.normalize_date(row.get('OpenedDate') or row.get('opened_date'))
                estimated_value = row.get('EstimatedValue') or row.get('estimated_value')

                # Resolve client
                client = Client.objects.filter(client_number=client_id).first()
                if not client:
                    answer = self.ask_question(
                        f"Client '{client_id}' not found for matter '{matter_number}'. Skip this matter?",
                        question_type='yes_no',
                        context=f"Matter: {title}\nClient ID: {client_id}"
                    )

                    if not answer or answer.lower() == 'yes':
                        self.log(f"  Skipping matter with missing client: {matter_number}", 'WARNING')
                        self.job.records_skipped += 1
                        self.job.save()
                        continue
                    else:
                        # User said no to skip, so we still skip for now
                        continue

                # Resolve lead attorney
                attorney = Attorney.objects.filter(employee_id=lead_attorney_id).first()
                if not attorney:
                    attorney = Attorney.objects.first()  # Fallback

                # Get or create practice area
                practice_area, _ = PracticeArea.objects.get_or_create(
                    name=practice_area_name,
                    defaults={'code': practice_area_name[:10].upper()}
                )

                with transaction.atomic():
                    matter = Matter.objects.create(
                        matter_number=matter_number,
                        client=client,
                        title=title,
                        description=description,
                        practice_area=practice_area,
                        lead_attorney=attorney,
                        status=status,
                        billing_type=billing_type,
                        opened_date=opened_date or timezone.now().date(),
                        estimated_value=Decimal(str(estimated_value)) if estimated_value else None
                    )

                    self.log(f"  Created matter: {matter.matter_number} - {matter.title}", 'SUCCESS')
                    self.job.records_imported += 1
                    self.job.records_processed += 1
                    self.job.save()

            except Exception as e:
                self.log(f"  Error importing matter row {idx}: {str(e)}", 'ERROR')
                self.job.errors_count += 1
                self.job.save()

    def import_time_entries(self, data, file_obj):
        """Import time entries with attorney name resolution"""
        for idx, row in enumerate(data):
            try:
                # Multiple possible column names
                date = self.normalize_date(
                    row.get('Date') or row.get('work_date') or row.get('date')
                )
                matter_ref = row.get('Matter #') or row.get('matter_reference') or row.get('matter_number')
                attorney_ref = row.get('Attorney ID') or row.get('attorney_name') or row.get('attorney_id')
                hours = Decimal(str(row.get('Hours') or row.get('time_spent') or '0'))
                rate = Decimal(str(row.get('Hourly Rate') or row.get('rate_charged') or '250.00'))
                description = row.get('Description') or row.get('work_description') or ''

                # Resolve matter
                matter = Matter.objects.filter(matter_number=matter_ref).first()
                if not matter:
                    self.log(f"  Matter not found: {matter_ref}, skipping", 'WARNING')
                    self.job.records_skipped += 1
                    self.job.save()
                    continue

                # Resolve attorney (by ID or name)
                attorney = None
                if attorney_ref.startswith('ATT-'):
                    attorney = Attorney.objects.filter(employee_id=attorney_ref).first()
                else:
                    # Try to match by name
                    parts = attorney_ref.split()
                    if len(parts) >= 2:
                        attorney = Attorney.objects.filter(
                            first_name__icontains=parts[0],
                            last_name__icontains=parts[-1]
                        ).first()

                if not attorney:
                    attorney = matter.lead_attorney  # Fallback

                # Get or create service
                service, _ = Service.objects.get_or_create(
                    code='GENERAL',
                    defaults={'name': 'General Legal Services', 'description': 'General legal work', 'default_rate': rate}
                )

                with transaction.atomic():
                    time_entry = TimeEntry.objects.create(
                        matter=matter,
                        attorney=attorney,
                        service=service,
                        date=date or timezone.now().date(),
                        hours=hours,
                        hourly_rate=rate,
                        description=description,
                        status='approved'
                    )

                    self.log(f"  Created time entry: {attorney.full_name} - {matter.matter_number} - {hours}h", 'SUCCESS')
                    self.job.records_imported += 1
                    self.job.records_processed += 1
                    self.job.save()

            except Exception as e:
                self.log(f"  Error importing time entry row {idx}: {str(e)}", 'ERROR')
                self.job.errors_count += 1
                self.job.save()

    def import_invoices(self, data, file_obj):
        """Import invoices from JSON"""
        for idx, row in enumerate(data):
            try:
                invoice_id = row.get('invoice_id') or row.get('invoice_number')
                matter_ref = row.get('matter')
                client_ref = row.get('client')
                invoice_date = self.normalize_date(row.get('invoice_date'))
                due_date = self.normalize_date(row.get('due_date'))
                total = Decimal(str(row.get('total') or '0'))
                status = (row.get('status') or 'draft').lower()

                # Resolve matter
                matter = Matter.objects.filter(matter_number=matter_ref).first()
                if not matter:
                    self.log(f"  Matter not found for invoice: {matter_ref}", 'WARNING')
                    self.job.records_skipped += 1
                    self.job.save()
                    continue

                # Resolve client (might be by name in JSON)
                client = matter.client

                with transaction.atomic():
                    invoice = Invoice.objects.create(
                        invoice_number=invoice_id,
                        matter=matter,
                        client=client,
                        invoice_date=invoice_date or timezone.now().date(),
                        due_date=due_date or timezone.now().date(),
                        status=status,
                        subtotal=total,
                        total_amount=total
                    )

                    self.log(f"  Created invoice: {invoice.invoice_number} - ${total}", 'SUCCESS')
                    self.job.records_imported += 1
                    self.job.records_processed += 1
                    self.job.save()

            except Exception as e:
                self.log(f"  Error importing invoice row {idx}: {str(e)}", 'ERROR')
                self.job.errors_count += 1
                self.job.save()


class Command(BaseCommand):
    help = 'Process an import job'

    def add_arguments(self, parser):
        parser.add_argument('job_id', type=int, help='Import job ID to process')

    def handle(self, *args, **options):
        job_id = options['job_id']

        self.stdout.write(self.style.SUCCESS(f'Starting import job {job_id}...'))

        try:
            worker = ImportWorker(job_id)
            worker.process()

            self.stdout.write(self.style.SUCCESS('Import completed successfully!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Import failed: {str(e)}'))
            raise
