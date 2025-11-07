from django.shortcuts import render, get_object_or_404
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from ..models import (
    Client, Matter, Attorney, TimeEntry, Invoice,
    Expense, Payment, PracticeArea
)


def dashboard(request):
    """Main dashboard view"""
    # Get key metrics
    total_clients = Client.objects.filter(is_active=True).count()
    open_matters = Matter.objects.filter(status='open').count()
    active_attorneys = Attorney.objects.filter(is_active=True).count()

    # Recent invoices
    recent_invoices = Invoice.objects.select_related('client', 'matter').order_by('-invoice_date')[:10]

    # Outstanding invoices
    outstanding_invoices = Invoice.objects.filter(
        status__in=['sent', 'overdue']
    ).select_related('client')

    outstanding_amount = sum(inv.balance_due for inv in outstanding_invoices)

    # Recent matters
    recent_matters = Matter.objects.select_related(
        'client', 'practice_area', 'lead_attorney'
    ).order_by('-opened_date')[:10]

    context = {
        'total_clients': total_clients,
        'open_matters': open_matters,
        'active_attorneys': active_attorneys,
        'recent_invoices': recent_invoices,
        'outstanding_amount': outstanding_amount,
        'recent_matters': recent_matters,
    }

    return render(request, 'practice/dashboard.html', context)


def client_list(request):
    """List all clients"""
    clients = Client.objects.all().order_by('name')

    # Add matter count for each client
    for client in clients:
        client.matter_count = client.matters.count()
        client.open_matter_count = client.matters.filter(status='open').count()

    context = {
        'clients': clients,
    }

    return render(request, 'practice/client_list.html', context)


def client_detail(request, client_id):
    """Client detail view"""
    client = get_object_or_404(Client, id=client_id)
    matters = client.matters.select_related('practice_area', 'lead_attorney').order_by('-opened_date')
    invoices = client.invoices.order_by('-invoice_date')[:10]
    payments = client.payments.order_by('-payment_date')[:10]

    total_billed = sum(inv.total_amount for inv in client.invoices.all())
    total_paid = sum(pay.amount for pay in client.payments.all())

    context = {
        'client': client,
        'matters': matters,
        'invoices': invoices,
        'payments': payments,
        'total_billed': total_billed,
        'total_paid': total_paid,
    }

    return render(request, 'practice/client_detail.html', context)


def matter_list(request):
    """List all matters"""
    status_filter = request.GET.get('status', '')

    matters = Matter.objects.select_related(
        'client', 'practice_area', 'lead_attorney'
    ).order_by('-opened_date')

    if status_filter:
        matters = matters.filter(status=status_filter)

    context = {
        'matters': matters,
        'status_filter': status_filter,
    }

    return render(request, 'practice/matter_list.html', context)


def matter_detail(request, matter_id):
    """Matter detail view"""
    matter = get_object_or_404(
        Matter.objects.select_related('client', 'practice_area', 'lead_attorney'),
        id=matter_id
    )

    time_entries = matter.time_entries.select_related('attorney', 'service').order_by('-date')
    expenses = matter.expenses.select_related('attorney').order_by('-date')
    invoices = matter.invoices.order_by('-invoice_date')
    documents = matter.documents.select_related('uploaded_by').order_by('-uploaded_date')

    # Calculate totals
    total_hours = time_entries.aggregate(Sum('hours'))['hours__sum'] or 0
    total_time_value = sum(te.total_amount for te in time_entries)
    total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or 0

    context = {
        'matter': matter,
        'time_entries': time_entries,
        'expenses': expenses,
        'invoices': invoices,
        'documents': documents,
        'total_hours': total_hours,
        'total_time_value': total_time_value,
        'total_expenses': total_expenses,
    }

    return render(request, 'practice/matter_detail.html', context)


def attorney_list(request):
    """List all attorneys"""
    attorneys = Attorney.objects.prefetch_related('practice_areas').order_by('last_name', 'first_name')

    # Add matter counts
    for attorney in attorneys:
        attorney.lead_matter_count = attorney.lead_matters.filter(status='open').count()
        attorney.total_matters = attorney.assigned_matters.count()

    context = {
        'attorneys': attorneys,
    }

    return render(request, 'practice/attorney_list.html', context)


def attorney_detail(request, attorney_id):
    """Attorney detail view"""
    attorney = get_object_or_404(
        Attorney.objects.prefetch_related('practice_areas'),
        id=attorney_id
    )

    lead_matters = attorney.lead_matters.select_related('client', 'practice_area').order_by('-opened_date')[:20]
    time_entries = attorney.time_entries.select_related('matter', 'service').order_by('-date')[:50]
    expenses = attorney.expenses.select_related('matter').order_by('-date')[:20]

    # Calculate stats
    total_hours = time_entries.aggregate(Sum('hours'))['hours__sum'] or 0
    total_billed = sum(te.total_amount for te in attorney.time_entries.filter(status='billed'))

    context = {
        'attorney': attorney,
        'lead_matters': lead_matters,
        'time_entries': time_entries,
        'expenses': expenses,
        'total_hours': total_hours,
        'total_billed': total_billed,
    }

    return render(request, 'practice/attorney_detail.html', context)


def invoice_list(request):
    """List all invoices"""
    status_filter = request.GET.get('status', '')

    invoices = Invoice.objects.select_related('client', 'matter').order_by('-invoice_date')

    if status_filter:
        invoices = invoices.filter(status=status_filter)

    context = {
        'invoices': invoices,
        'status_filter': status_filter,
    }

    return render(request, 'practice/invoice_list.html', context)


def invoice_detail(request, invoice_id):
    """Invoice detail view"""
    invoice = get_object_or_404(
        Invoice.objects.select_related('client', 'matter'),
        id=invoice_id
    )

    line_items = invoice.line_items.select_related('time_entry', 'expense').order_by('id')
    payments = invoice.payments.order_by('-payment_date')

    context = {
        'invoice': invoice,
        'line_items': line_items,
        'payments': payments,
    }

    return render(request, 'practice/invoice_detail.html', context)
from django.shortcuts import redirect
from django.contrib import messages
from django.core.management import call_command

def reset_data(request):
    """Reset all data via web interface"""
    try:
        call_command("reset_import_data", "--all", "--confirm")
        messages.success(request, "✅ All data deleted successfully!")
    except Exception as e:
        messages.error(request, f"❌ Error: {str(e)}")
    return redirect("dashboard")

