"""
Management command to reset/clean imported data.
Useful for testing the import process multiple times.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from practice.models import (
    Client, Attorney, Matter, TimeEntry, Expense,
    Invoice, InvoiceLineItem, Payment, Document,
    ImportJob, ImportFile, ImportQuestion, ImportLog,
    ImportMapping, ImportedRecord
)


class Command(BaseCommand):
    help = 'Reset imported data - useful for testing imports multiple times'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Delete ALL data including original sample data',
        )
        parser.add_argument(
            '--imported-only',
            action='store_true',
            help='Delete only data from imports (default)',
        )
        parser.add_argument(
            '--jobs',
            action='store_true',
            help='Delete only import jobs and logs',
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Skip confirmation prompt',
        )

    def handle(self, *args, **options):
        delete_all = options['all']
        imported_only = options['imported_only'] or (not delete_all and not options['jobs'])
        jobs_only = options['jobs']
        confirm = options['confirm']

        self.stdout.write(self.style.WARNING('\n' + '=' * 60))
        self.stdout.write(self.style.WARNING('DATA DELETION TOOL'))
        self.stdout.write(self.style.WARNING('=' * 60 + '\n'))

        # Show what will be deleted
        if delete_all:
            self.stdout.write(self.style.ERROR('⚠️  Will delete ALL DATA including original samples!'))
            self.stdout.write('This includes:')
            self.stdout.write(f'  - All {Client.objects.count()} clients')
            self.stdout.write(f'  - All {Attorney.objects.count()} attorneys')
            self.stdout.write(f'  - All {Matter.objects.count()} matters')
            self.stdout.write(f'  - All {TimeEntry.objects.count()} time entries')
            self.stdout.write(f'  - All {Invoice.objects.count()} invoices')
            self.stdout.write(f'  - All {ImportJob.objects.count()} import jobs')

        elif jobs_only:
            self.stdout.write(self.style.WARNING('Will delete import jobs and logs only'))
            self.stdout.write('This includes:')
            self.stdout.write(f'  - {ImportJob.objects.count()} import jobs')
            self.stdout.write(f'  - {ImportLog.objects.count()} import logs')
            self.stdout.write(f'  - {ImportQuestion.objects.count()} import questions')
            self.stdout.write('\nData (clients, matters, etc.) will NOT be touched')

        else:  # imported_only
            # Count data that was imported via import system
            imported_records = ImportedRecord.objects.all()
            if imported_records.exists():
                self.stdout.write(self.style.WARNING('Will delete data from imports only'))
                self.stdout.write('This includes:')

                # Group by model
                from collections import Counter
                model_counts = Counter(ir.model_name for ir in imported_records)
                for model_name, count in model_counts.items():
                    self.stdout.write(f'  - {count} imported {model_name}(s)')

                self.stdout.write(f'\nTotal: {imported_records.count()} imported records')
                self.stdout.write('Original sample data will NOT be touched')
            else:
                self.stdout.write(self.style.SUCCESS('No imported data found - nothing to delete'))
                return

        # Confirmation
        if not confirm:
            self.stdout.write('')
            response = input('Are you sure? Type "yes" to confirm: ')
            if response.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Cancelled'))
                return

        # Perform deletion
        self.stdout.write('\nDeleting...')

        try:
            with transaction.atomic():
                if delete_all:
                    self._delete_all()
                elif jobs_only:
                    self._delete_jobs_only()
                else:
                    self._delete_imported_only()

            self.stdout.write(self.style.SUCCESS('\n✓ Deletion complete!'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ Error during deletion: {str(e)}'))
            raise

    def _delete_all(self):
        """Delete everything - nuclear option"""
        # Delete in reverse dependency order
        Payment.objects.all().delete()
        self.stdout.write('  ✓ Deleted payments')

        InvoiceLineItem.objects.all().delete()
        self.stdout.write('  ✓ Deleted invoice line items')

        Invoice.objects.all().delete()
        self.stdout.write('  ✓ Deleted invoices')

        Document.objects.all().delete()
        self.stdout.write('  ✓ Deleted documents')

        Expense.objects.all().delete()
        self.stdout.write('  ✓ Deleted expenses')

        TimeEntry.objects.all().delete()
        self.stdout.write('  ✓ Deleted time entries')

        Matter.objects.all().delete()
        self.stdout.write('  ✓ Deleted matters')

        Attorney.objects.all().delete()
        self.stdout.write('  ✓ Deleted attorneys')

        Client.objects.all().delete()
        self.stdout.write('  ✓ Deleted clients')

        # Delete import system data
        self._delete_jobs_only()

    def _delete_jobs_only(self):
        """Delete only import jobs and related records"""
        ImportedRecord.objects.all().delete()
        self.stdout.write('  ✓ Deleted imported records tracking')

        ImportMapping.objects.all().delete()
        self.stdout.write('  ✓ Deleted import mappings')

        ImportLog.objects.all().delete()
        self.stdout.write('  ✓ Deleted import logs')

        ImportQuestion.objects.all().delete()
        self.stdout.write('  ✓ Deleted import questions')

        ImportFile.objects.all().delete()
        self.stdout.write('  ✓ Deleted import files')

        ImportJob.objects.all().delete()
        self.stdout.write('  ✓ Deleted import jobs')

    def _delete_imported_only(self):
        """Delete only data that was imported (tracked in ImportedRecord)"""
        imported_records = ImportedRecord.objects.select_related('job').all()

        if not imported_records.exists():
            self.stdout.write('  No imported data to delete')
            return

        # Group by model and delete
        from collections import defaultdict
        records_by_model = defaultdict(list)

        for record in imported_records:
            records_by_model[record.model_name].append(record.record_id)

        # Delete in dependency order
        deletion_order = [
            ('Payment', Payment),
            ('InvoiceLineItem', InvoiceLineItem),
            ('Invoice', Invoice),
            ('Document', Document),
            ('Expense', Expense),
            ('TimeEntry', TimeEntry),
            ('Matter', Matter),
            ('Attorney', Attorney),
            ('Client', Client),
        ]

        for model_name, model_class in deletion_order:
            if model_name in records_by_model:
                ids = records_by_model[model_name]
                deleted_count = model_class.objects.filter(id__in=ids).delete()[0]
                self.stdout.write(f'  ✓ Deleted {deleted_count} imported {model_name}(s)')

        # Clean up tracking records and jobs
        self._delete_jobs_only()
