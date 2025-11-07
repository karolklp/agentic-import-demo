from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import random

from practice.models import (
    Client, PracticeArea, Attorney, Matter, Service,
    TimeEntry, Expense, Invoice, InvoiceLineItem, Document, Payment
)


class Command(BaseCommand):
    help = 'Generate sample data for the law firm practice management system'

    def handle(self, *args, **kwargs):
        self.stdout.write('Clearing existing data...')
        # Clear in reverse order of dependencies
        Payment.objects.all().delete()
        InvoiceLineItem.objects.all().delete()
        Invoice.objects.all().delete()
        Document.objects.all().delete()
        Expense.objects.all().delete()
        TimeEntry.objects.all().delete()
        Matter.objects.all().delete()
        Attorney.objects.all().delete()
        Service.objects.all().delete()
        PracticeArea.objects.all().delete()
        Client.objects.all().delete()

        self.stdout.write('Generating practice areas...')
        practice_areas = self.create_practice_areas()

        self.stdout.write('Generating attorneys...')
        attorneys = self.create_attorneys(practice_areas)

        self.stdout.write('Generating clients...')
        clients = self.create_clients()

        self.stdout.write('Generating services...')
        services = self.create_services()

        self.stdout.write('Generating matters...')
        matters = self.create_matters(clients, attorneys, practice_areas)

        self.stdout.write('Generating time entries...')
        time_entries = self.create_time_entries(matters, attorneys, services)

        self.stdout.write('Generating expenses...')
        expenses = self.create_expenses(matters, attorneys)

        self.stdout.write('Generating invoices...')
        invoices = self.create_invoices(matters, time_entries, expenses)

        self.stdout.write('Generating payments...')
        self.create_payments(invoices)

        self.stdout.write('Generating documents...')
        self.create_documents(matters, attorneys)

        self.stdout.write(self.style.SUCCESS('Successfully generated sample data!'))

    def create_practice_areas(self):
        areas_data = [
            ('CORP', 'Corporate Law', 'Business formations, mergers, acquisitions'),
            ('LIT', 'Litigation', 'Civil and commercial litigation'),
            ('IP', 'Intellectual Property', 'Patents, trademarks, copyrights'),
            ('RE', 'Real Estate', 'Property transactions and disputes'),
            ('LABOR', 'Labor & Employment', 'Employment law and workplace issues'),
            ('TAX', 'Tax Law', 'Tax planning and disputes'),
            ('ESTATE', 'Estate Planning', 'Wills, trusts, and estate administration'),
        ]

        areas = []
        for code, name, desc in areas_data:
            area = PracticeArea.objects.create(
                code=code,
                name=name,
                description=desc
            )
            areas.append(area)

        return areas

    def create_attorneys(self, practice_areas):
        attorneys_data = [
            ('ATT001', 'Sarah', 'Mitchell', 'sarah.mitchell@lawfirm.com', 'NY-12345', 'partner', 450.00),
            ('ATT002', 'James', 'Rodriguez', 'james.rodriguez@lawfirm.com', 'NY-23456', 'partner', 425.00),
            ('ATT003', 'Emily', 'Chen', 'emily.chen@lawfirm.com', 'NY-34567', 'senior', 350.00),
            ('ATT004', 'Michael', 'Thompson', 'michael.thompson@lawfirm.com', 'NY-45678', 'senior', 325.00),
            ('ATT005', 'Jessica', 'Williams', 'jessica.williams@lawfirm.com', 'NY-56789', 'associate', 275.00),
            ('ATT006', 'David', 'Lee', 'david.lee@lawfirm.com', 'NY-67890', 'associate', 250.00),
            ('ATT007', 'Amanda', 'Brown', 'amanda.brown@lawfirm.com', 'NY-78901', 'junior', 200.00),
        ]

        attorneys = []
        hire_date = datetime(2015, 1, 1).date()

        for emp_id, first, last, email, bar, level, rate in attorneys_data:
            attorney = Attorney.objects.create(
                employee_id=emp_id,
                first_name=first,
                last_name=last,
                email=email,
                bar_number=bar,
                level=level,
                hire_date=hire_date,
                hourly_rate=Decimal(str(rate))
            )
            # Assign random practice areas
            attorney.practice_areas.set(random.sample(practice_areas, k=random.randint(2, 4)))
            attorneys.append(attorney)
            hire_date += timedelta(days=365)

        return attorneys

    def create_clients(self):
        clients_data = [
            ('CL001', 'Acme Corporation', 'business', 'contact@acmecorp.com', '555-0101', '123 Business St, NY', '12-3456789'),
            ('CL002', 'TechStart Inc', 'business', 'info@techstart.com', '555-0102', '456 Innovation Ave, NY', '23-4567890'),
            ('CL003', 'John Anderson', 'individual', 'john.anderson@email.com', '555-0103', '789 Residential Ln, NY', ''),
            ('CL004', 'Global Retail LLC', 'business', 'legal@globalretail.com', '555-0104', '321 Commerce Blvd, NY', '34-5678901'),
            ('CL005', 'Maria Garcia', 'individual', 'maria.garcia@email.com', '555-0105', '654 Oak Street, NY', ''),
            ('CL006', 'Property Holdings Trust', 'business', 'trustees@propholdings.com', '555-0106', '987 Investment Dr, NY', '45-6789012'),
            ('CL007', 'Sarah Johnson', 'individual', 'sarah.j@email.com', '555-0107', '147 Maple Ave, NY', ''),
            ('CL008', 'Manufacturing Co', 'business', 'legal@mfgco.com', '555-0108', '258 Industrial Way, NY', '56-7890123'),
            ('CL009', 'Community Foundation', 'nonprofit', 'director@commfound.org', '555-0109', '369 Charity St, NY', '67-8901234'),
            ('CL010', 'Robert Chen', 'individual', 'robert.chen@email.com', '555-0110', '741 Pine Rd, NY', ''),
        ]

        clients = []
        for num, name, c_type, email, phone, addr, tax_id in clients_data:
            client = Client.objects.create(
                client_number=num,
                name=name,
                client_type=c_type,
                email=email,
                phone=phone,
                address=addr,
                tax_id=tax_id
            )
            clients.append(client)

        return clients

    def create_services(self):
        services_data = [
            ('CONSULT', 'Legal Consultation', 'General legal advice and consultation', 250.00),
            ('RESEARCH', 'Legal Research', 'Case law and statute research', 200.00),
            ('DRAFT', 'Document Drafting', 'Drafting legal documents', 275.00),
            ('REVIEW', 'Document Review', 'Review and analysis of documents', 225.00),
            ('COURT', 'Court Appearance', 'Representation in court proceedings', 400.00),
            ('DEPO', 'Deposition', 'Taking or defending depositions', 375.00),
            ('NEGO', 'Negotiation', 'Settlement negotiations', 325.00),
            ('FILING', 'Court Filing', 'Preparation and filing of court documents', 150.00),
        ]

        services = []
        for code, name, desc, rate in services_data:
            service = Service.objects.create(
                code=code,
                name=name,
                description=desc,
                default_rate=Decimal(str(rate))
            )
            services.append(service)

        return services

    def create_matters(self, clients, attorneys, practice_areas):
        matter_types = {
            'Corporate Law': [
                'Business Formation and Structuring',
                'Merger and Acquisition',
                'Corporate Governance Review',
                'Commercial Contract Negotiation',
            ],
            'Litigation': [
                'Contract Dispute',
                'Employment Discrimination Case',
                'Breach of Fiduciary Duty',
                'Commercial Litigation',
            ],
            'Intellectual Property': [
                'Trademark Registration',
                'Patent Application',
                'Copyright Infringement',
                'Trade Secret Protection',
            ],
            'Real Estate': [
                'Commercial Property Purchase',
                'Lease Agreement Dispute',
                'Property Development',
                'Zoning Variance Application',
            ],
            'Estate Planning': [
                'Will and Trust Preparation',
                'Estate Administration',
                'Probate Matter',
                'Trust Amendment',
            ],
        }

        matters = []
        matter_num = 1
        start_date = datetime(2024, 1, 1).date()

        # Create 25-30 matters
        for _ in range(28):
            client = random.choice(clients)
            practice_area = random.choice(practice_areas[:5])  # Use first 5 areas
            lead_attorney = random.choice(attorneys[:4])  # Partners and seniors as leads

            if practice_area.name in matter_types:
                title = random.choice(matter_types[practice_area.name])
            else:
                title = f"{practice_area.name} Matter"

            status_weights = [('open', 0.6), ('pending', 0.15), ('closed', 0.2), ('on_hold', 0.05)]
            status = random.choices([s[0] for s in status_weights], weights=[s[1] for s in status_weights])[0]

            billing_type = random.choice(['hourly', 'flat_fee', 'contingency', 'retainer'])

            opened_date = start_date + timedelta(days=random.randint(0, 300))
            closed_date = None
            if status == 'closed':
                closed_date = opened_date + timedelta(days=random.randint(30, 180))

            matter = Matter.objects.create(
                matter_number=f'MAT-2024-{matter_num:04d}',
                client=client,
                title=title,
                description=f'Legal matter regarding {title.lower()} for {client.name}',
                practice_area=practice_area,
                lead_attorney=lead_attorney,
                status=status,
                billing_type=billing_type,
                opened_date=opened_date,
                closed_date=closed_date,
                estimated_value=Decimal(str(random.randint(5000, 500000)))
            )

            # Assign additional attorneys
            assigned = random.sample(attorneys, k=random.randint(1, 3))
            matter.assigned_attorneys.set(assigned)

            matters.append(matter)
            matter_num += 1

        return matters

    def create_time_entries(self, matters, attorneys, services):
        time_entries = []

        for matter in matters:
            # Create 5-20 time entries per matter
            num_entries = random.randint(5, 20)

            assigned_attorneys = list(matter.assigned_attorneys.all())
            if matter.lead_attorney not in assigned_attorneys:
                assigned_attorneys.append(matter.lead_attorney)

            for _ in range(num_entries):
                attorney = random.choice(assigned_attorneys)
                service = random.choice(services)

                # Date between matter opened and now (or closed date)
                end_date = matter.closed_date if matter.closed_date else datetime.now().date()
                days_range = (end_date - matter.opened_date).days
                if days_range > 0:
                    entry_date = matter.opened_date + timedelta(days=random.randint(0, days_range))
                else:
                    entry_date = matter.opened_date

                hours = Decimal(str(random.choice([0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0, 8.0])))

                status_weights = [('draft', 0.1), ('submitted', 0.15), ('approved', 0.25), ('billed', 0.5)]
                status = random.choices([s[0] for s in status_weights], weights=[s[1] for s in status_weights])[0]

                descriptions = [
                    'Client consultation regarding case strategy',
                    'Research relevant case law and statutes',
                    'Draft motion for summary judgment',
                    'Review and analyze discovery documents',
                    'Attend court hearing',
                    'Conference call with opposing counsel',
                    'Prepare for deposition',
                    'Review and revise contract terms',
                    'Legal analysis of liability issues',
                    'Correspondence with client',
                ]

                entry = TimeEntry.objects.create(
                    matter=matter,
                    attorney=attorney,
                    service=service,
                    date=entry_date,
                    hours=hours,
                    hourly_rate=attorney.hourly_rate,
                    description=random.choice(descriptions),
                    status=status
                )
                time_entries.append(entry)

        return time_entries

    def create_expenses(self, matters, attorneys):
        expenses = []

        # Create expenses for about 60% of matters
        for matter in random.sample(matters, k=int(len(matters) * 0.6)):
            num_expenses = random.randint(1, 5)

            for _ in range(num_expenses):
                attorney = random.choice(list(matter.assigned_attorneys.all()))

                categories = [
                    ('Filing Fees', 150, 500),
                    ('Court Reporter', 300, 800),
                    ('Expert Witness', 1000, 5000),
                    ('Travel', 200, 1500),
                    ('Photocopying', 50, 300),
                    ('Research Database', 100, 400),
                    ('Messenger Service', 25, 100),
                ]

                category, min_amt, max_amt = random.choice(categories)

                end_date = matter.closed_date if matter.closed_date else datetime.now().date()
                days_range = (end_date - matter.opened_date).days
                if days_range > 0:
                    expense_date = matter.opened_date + timedelta(days=random.randint(0, days_range))
                else:
                    expense_date = matter.opened_date

                status_weights = [('pending', 0.15), ('approved', 0.3), ('billed', 0.5), ('reimbursed', 0.05)]
                status = random.choices([s[0] for s in status_weights], weights=[s[1] for s in status_weights])[0]

                expense = Expense.objects.create(
                    matter=matter,
                    attorney=attorney,
                    date=expense_date,
                    category=category,
                    description=f'{category} for {matter.title}',
                    amount=Decimal(str(random.randint(min_amt, max_amt))),
                    is_billable=random.choice([True, True, True, False]),  # 75% billable
                    status=status,
                    receipt_number=f'RCP-{random.randint(10000, 99999)}'
                )
                expenses.append(expense)

        return expenses

    def create_invoices(self, matters, time_entries, expenses):
        invoices = []
        invoice_num = 1

        # Create invoices for closed matters and some open matters
        invoice_matters = [m for m in matters if m.status == 'closed']
        invoice_matters.extend(random.sample([m for m in matters if m.status == 'open'], k=int(len(matters) * 0.3)))

        for matter in invoice_matters:
            # Create 1-3 invoices per matter
            num_invoices = random.randint(1, 3)

            matter_time_entries = [te for te in time_entries if te.matter == matter and te.status == 'billed']
            matter_expenses = [e for e in expenses if e.matter == matter and e.status == 'billed' and e.is_billable]

            if not matter_time_entries:
                continue

            for inv_idx in range(num_invoices):
                # Split time entries among invoices
                entries_per_invoice = len(matter_time_entries) // num_invoices
                if inv_idx == num_invoices - 1:
                    invoice_entries = matter_time_entries[inv_idx * entries_per_invoice:]
                else:
                    invoice_entries = matter_time_entries[inv_idx * entries_per_invoice:(inv_idx + 1) * entries_per_invoice]

                if not invoice_entries:
                    continue

                # Date after last time entry
                last_entry_date = max(te.date for te in invoice_entries)
                invoice_date = last_entry_date + timedelta(days=random.randint(1, 15))
                due_date = invoice_date + timedelta(days=30)

                status_weights = [('draft', 0.05), ('sent', 0.25), ('paid', 0.6), ('overdue', 0.1)]
                status = random.choices([s[0] for s in status_weights], weights=[s[1] for s in status_weights])[0]

                invoice = Invoice.objects.create(
                    invoice_number=f'INV-2024-{invoice_num:05d}',
                    matter=matter,
                    client=matter.client,
                    invoice_date=invoice_date,
                    due_date=due_date,
                    status=status
                )

                # Add time entry line items
                subtotal = Decimal('0.00')
                for te in invoice_entries:
                    amount = te.hours * te.hourly_rate
                    InvoiceLineItem.objects.create(
                        invoice=invoice,
                        item_type='time',
                        time_entry=te,
                        description=f'{te.service.name} - {te.attorney.full_name} ({te.hours} hrs @ ${te.hourly_rate})',
                        quantity=te.hours,
                        rate=te.hourly_rate,
                        amount=amount
                    )
                    subtotal += amount

                # Add some expenses to this invoice
                invoice_expenses = random.sample(matter_expenses, k=min(len(matter_expenses), random.randint(0, 3)))
                for exp in invoice_expenses:
                    InvoiceLineItem.objects.create(
                        invoice=invoice,
                        item_type='expense',
                        expense=exp,
                        description=f'{exp.category} - {exp.description}',
                        quantity=Decimal('1.00'),
                        rate=exp.amount,
                        amount=exp.amount
                    )
                    subtotal += exp.amount

                tax_amount = subtotal * Decimal('0.08')  # 8% tax
                total_amount = subtotal + tax_amount

                # Calculate paid amount based on status
                if status == 'paid':
                    paid_amount = total_amount
                elif status == 'sent':
                    paid_amount = Decimal('0.00') if random.random() > 0.3 else total_amount * Decimal(str(random.uniform(0.2, 0.8)))
                else:
                    paid_amount = Decimal('0.00')

                invoice.subtotal = subtotal
                invoice.tax_amount = tax_amount
                invoice.total_amount = total_amount
                invoice.paid_amount = paid_amount
                invoice.save()

                invoices.append(invoice)
                invoice_num += 1

        return invoices

    def create_payments(self, invoices):
        payments = []

        for invoice in invoices:
            if invoice.paid_amount > 0:
                # Create 1-2 payments per invoice
                if invoice.paid_amount == invoice.total_amount:
                    # Full payment
                    payment_date = invoice.invoice_date + timedelta(days=random.randint(5, 45))
                    payment_method = random.choice(['check', 'wire', 'credit_card', 'ach'])

                    payment = Payment.objects.create(
                        invoice=invoice,
                        client=invoice.client,
                        payment_date=payment_date,
                        amount=invoice.paid_amount,
                        payment_method=payment_method,
                        reference_number=f'{payment_method.upper()}-{random.randint(100000, 999999)}'
                    )
                    payments.append(payment)
                else:
                    # Partial payment
                    payment_date = invoice.invoice_date + timedelta(days=random.randint(5, 30))
                    payment_method = random.choice(['check', 'wire', 'credit_card', 'ach'])

                    payment = Payment.objects.create(
                        invoice=invoice,
                        client=invoice.client,
                        payment_date=payment_date,
                        amount=invoice.paid_amount,
                        payment_method=payment_method,
                        reference_number=f'{payment_method.upper()}-{random.randint(100000, 999999)}',
                        notes='Partial payment'
                    )
                    payments.append(payment)

        return payments

    def create_documents(self, matters, attorneys):
        documents = []

        # Create 2-5 documents per matter
        for matter in matters:
            num_docs = random.randint(2, 5)

            doc_types = [
                ('contract', 'Service Agreement'),
                ('brief', 'Memorandum of Law'),
                ('motion', 'Motion to Dismiss'),
                ('correspondence', 'Client Letter'),
                ('evidence', 'Exhibit A - Email Chain'),
                ('other', 'Case Notes'),
            ]

            for _ in range(num_docs):
                doc_type, title_template = random.choice(doc_types)
                title = f'{title_template} - {matter.matter_number}'

                uploaded_by = random.choice(list(matter.assigned_attorneys.all()))

                days_since_opened = (datetime.now().date() - matter.opened_date).days
                if days_since_opened > 0:
                    upload_date_offset = random.randint(0, days_since_opened)
                else:
                    upload_date_offset = 0

                upload_date = datetime.combine(
                    matter.opened_date + timedelta(days=upload_date_offset),
                    datetime.min.time()
                )

                document = Document.objects.create(
                    matter=matter,
                    title=title,
                    document_type=doc_type,
                    description=f'Document related to {matter.title}',
                    file_path=f'/documents/{matter.matter_number}/{title.replace(" ", "_")}.pdf',
                    uploaded_by=uploaded_by,
                    uploaded_date=upload_date,
                    is_confidential=random.choice([True, False])
                )
                documents.append(document)

        return documents
