"""
Classic (non-agentic) import - demonstrates traditional import failures.
This is the "old way" that fails on messy data without intelligent handling.
"""
import csv
import json
from datetime import datetime
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from practice.models import ImportJob, Client, Attorney, Matter, TimeEntry, Invoice, Payment


class Command(BaseCommand):
    help = 'Run classic (non-agentic) import that fails on messy data'

    def add_arguments(self, parser):
        parser.add_argument('job_id', type=int, help='Import job ID')

    def handle(self, *args, **options):
        job_id = options['job_id']

        try:
            job = ImportJob.objects.get(id=job_id)
        except ImportJob.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ Import job {job_id} not found'))
            return

        self.stdout.write(self.style.SUCCESS(f'\n📁 Classic Import for Job #{job_id}'))
        self.stdout.write(self.style.WARNING('⚠️  This is the OLD WAY - rigid, fragile, no intelligence'))
        self.stdout.write('=' * 60)

        # Update job status
        job.status = 'processing'
        job.save()
        job.add_log('📁 Classic import started', 'INFO')

        # Get uploaded files
        files = job.files.all()
        if not files.exists():
            self.stdout.write(self.style.ERROR('❌ No files uploaded for this job'))
            job.status = 'failed'
            job.save()
            return

        total_errors = 0
        total_imported = 0
        total_skipped = 0

        # Process each file
        for import_file in files:
            file_path = Path(import_file.file.path)
            self.stdout.write(f'\n📄 Processing: {import_file.filename}')
            job.add_log(f'Processing {import_file.filename}', 'INFO')

            try:
                if 'client' in import_file.filename.lower():
                    imported, errors, skipped = self._import_clients(file_path, job)
                elif 'attorney' in import_file.filename.lower():
                    imported, errors, skipped = self._import_attorneys(file_path, job)
                elif 'matter' in import_file.filename.lower():
                    imported, errors, skipped = self._import_matters(file_path, job)
                elif 'time' in import_file.filename.lower():
                    imported, errors, skipped = self._import_time_entries(file_path, job)
                elif 'invoice' in import_file.filename.lower():
                    imported, errors, skipped = self._import_invoices(file_path, job)
                else:
                    self.stdout.write(self.style.WARNING(f'⚠️  Unknown file type, skipping'))
                    job.add_log(f'Unknown file type: {import_file.filename}', 'WARNING')
                    continue

                total_imported += imported
                total_errors += errors
                total_skipped += skipped

            except Exception as e:
                error_msg = f'❌ Fatal error processing {import_file.filename}: {str(e)}'
                self.stdout.write(self.style.ERROR(error_msg))
                job.add_log(error_msg, 'ERROR')
                total_errors += 1

        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('\n📊 Classic Import Summary:'))
        self.stdout.write(f'  ✅ Imported: {total_imported}')
        self.stdout.write(self.style.WARNING(f'  ⏭️  Skipped: {total_skipped}'))
        self.stdout.write(self.style.ERROR(f'  ❌ Errors: {total_errors}'))

        job.add_log(f'Classic import completed: {total_imported} imported, {total_skipped} skipped, {total_errors} errors', 'INFO')

        if total_errors > 0:
            job.status = 'failed'
            self.stdout.write(self.style.ERROR('\n❌ Import FAILED due to errors'))
            job.add_log('Import failed due to errors', 'ERROR')
        else:
            job.status = 'completed'
            self.stdout.write(self.style.SUCCESS('\n✅ Import completed'))
            job.add_log('Import completed', 'SUCCESS')

        job.save()

    def _import_clients(self, file_path, job):
        """Import clients - classic rigid approach"""
        imported = 0
        errors = 0
        skipped = 0

        self.stdout.write('  Importing clients...')

        with open(file_path) as f:
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=2):
                try:
                    # Rigid date parsing - only accepts one format!
                    onboarding_date = None
                    if row.get('onboarding_date'):
                        try:
                            # Only tries ONE date format - will fail on others!
                            onboarding_date = datetime.strptime(row['onboarding_date'], '%Y-%m-%d').date()
                        except ValueError as e:
                            error_msg = f"❌ Row {row_num}: Invalid date format '{row['onboarding_date']}' (expected YYYY-MM-DD)"
                            self.stdout.write(self.style.ERROR(f'    {error_msg}'))
                            job.add_log(error_msg, 'ERROR')
                            errors += 1
                            continue

                    # No duplicate checking - will crash on duplicate client_number!
                    try:
                        client = Client.objects.create(
                            client_number=row['client_number'],
                            name=row['name'],
                            client_type=row.get('client_type', 'individual'),
                            contact_email=row.get('email', ''),
                            contact_phone=row.get('phone', ''),
                            tax_id=row.get('tax_id', ''),
                            onboarding_date=onboarding_date,
                            status='active'
                        )
                        imported += 1
                        self.stdout.write(self.style.SUCCESS(f'    ✓ Imported: {client.name}'))
                        job.add_log(f'Imported client: {client.name}', 'SUCCESS')

                    except Exception as e:
                        error_msg = f"❌ Row {row_num}: Database error for '{row.get('name', 'Unknown')}': {str(e)}"
                        self.stdout.write(self.style.ERROR(f'    {error_msg}'))
                        job.add_log(error_msg, 'ERROR')
                        errors += 1

                except KeyError as e:
                    error_msg = f"❌ Row {row_num}: Missing required column {str(e)}"
                    self.stdout.write(self.style.ERROR(f'    {error_msg}'))
                    job.add_log(error_msg, 'ERROR')
                    errors += 1

        return imported, errors, skipped

    def _import_attorneys(self, file_path, job):
        """Import attorneys - classic rigid approach"""
        imported = 0
        errors = 0
        skipped = 0

        self.stdout.write('  Importing attorneys...')

        with open(file_path) as f:
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=2):
                try:
                    # Rigid date parsing
                    hire_date = None
                    if row.get('hire_date'):
                        try:
                            hire_date = datetime.strptime(row['hire_date'], '%Y-%m-%d').date()
                        except ValueError:
                            error_msg = f"❌ Row {row_num}: Invalid date format '{row['hire_date']}'"
                            self.stdout.write(self.style.ERROR(f'    {error_msg}'))
                            job.add_log(error_msg, 'ERROR')
                            errors += 1
                            continue

                    # No duplicate checking
                    try:
                        attorney = Attorney.objects.create(
                            employee_id=row['employee_id'],
                            first_name=row['first_name'],
                            last_name=row['last_name'],
                            email=row['email'],
                            phone=row.get('phone', ''),
                            bar_number=row.get('bar_number', ''),
                            bar_state=row.get('bar_state', ''),
                            hire_date=hire_date,
                            status='active'
                        )
                        imported += 1
                        self.stdout.write(self.style.SUCCESS(f'    ✓ Imported: {attorney.first_name} {attorney.last_name}'))
                        job.add_log(f'Imported attorney: {attorney.first_name} {attorney.last_name}', 'SUCCESS')

                    except Exception as e:
                        error_msg = f"❌ Row {row_num}: Database error: {str(e)}"
                        self.stdout.write(self.style.ERROR(f'    {error_msg}'))
                        job.add_log(error_msg, 'ERROR')
                        errors += 1

                except KeyError as e:
                    error_msg = f"❌ Row {row_num}: Missing required column {str(e)}"
                    self.stdout.write(self.style.ERROR(f'    {error_msg}'))
                    job.add_log(error_msg, 'ERROR')
                    errors += 1

        return imported, errors, skipped

    def _import_matters(self, file_path, job):
        """Import matters - classic rigid approach"""
        imported = 0
        errors = 0
        skipped = 0

        self.stdout.write('  Importing matters...')

        with open(file_path) as f:
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=2):
                try:
                    # Rigid date parsing
                    opened_date = None
                    if row.get('opened_date'):
                        try:
                            opened_date = datetime.strptime(row['opened_date'], '%Y-%m-%d').date()
                        except ValueError:
                            error_msg = f"❌ Row {row_num}: Invalid date format '{row['opened_date']}'"
                            self.stdout.write(self.style.ERROR(f'    {error_msg}'))
                            job.add_log(error_msg, 'ERROR')
                            errors += 1
                            continue

                    # Rigid FK lookup - fails if not found!
                    try:
                        client = Client.objects.get(client_number=row['client_number'])
                    except Client.DoesNotExist:
                        error_msg = f"❌ Row {row_num}: Client '{row['client_number']}' not found"
                        self.stdout.write(self.style.ERROR(f'    {error_msg}'))
                        job.add_log(error_msg, 'ERROR')
                        errors += 1
                        continue

                    try:
                        attorney = Attorney.objects.get(employee_id=row['responsible_attorney'])
                    except Attorney.DoesNotExist:
                        error_msg = f"❌ Row {row_num}: Attorney '{row['responsible_attorney']}' not found"
                        self.stdout.write(self.style.ERROR(f'    {error_msg}'))
                        job.add_log(error_msg, 'ERROR')
                        errors += 1
                        continue

                    # No duplicate checking
                    try:
                        matter = Matter.objects.create(
                            matter_number=row['matter_number'],
                            client=client,
                            title=row['title'],
                            responsible_attorney=attorney,
                            opened_date=opened_date,
                            status='open',
                            billing_rate=row.get('billing_rate', 0)
                        )
                        imported += 1
                        self.stdout.write(self.style.SUCCESS(f'    ✓ Imported: {matter.matter_number}'))
                        job.add_log(f'Imported matter: {matter.matter_number}', 'SUCCESS')

                    except Exception as e:
                        error_msg = f"❌ Row {row_num}: Database error: {str(e)}"
                        self.stdout.write(self.style.ERROR(f'    {error_msg}'))
                        job.add_log(error_msg, 'ERROR')
                        errors += 1

                except KeyError as e:
                    error_msg = f"❌ Row {row_num}: Missing required column {str(e)}"
                    self.stdout.write(self.style.ERROR(f'    {error_msg}'))
                    job.add_log(error_msg, 'ERROR')
                    errors += 1

        return imported, errors, skipped

    def _import_time_entries(self, file_path, job):
        """Import time entries - classic rigid approach"""
        imported = 0
        errors = 0
        skipped = 0

        self.stdout.write('  Importing time entries...')
        error_msg = "❌ Classic import doesn't handle time entries - too complex!"
        self.stdout.write(self.style.ERROR(f'    {error_msg}'))
        job.add_log(error_msg, 'ERROR')
        errors += 1

        return imported, errors, skipped

    def _import_invoices(self, file_path, job):
        """Import invoices - classic rigid approach"""
        imported = 0
        errors = 0
        skipped = 0

        self.stdout.write('  Importing invoices...')
        error_msg = "❌ Classic import doesn't handle invoices - too complex!"
        self.stdout.write(self.style.ERROR(f'    {error_msg}'))
        job.add_log(error_msg, 'ERROR')
        errors += 1

        return imported, errors, skipped
