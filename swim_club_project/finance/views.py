import json
import calendar

from django.shortcuts import render

# Create your views here.
# finance/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch, Q, Sum
from django.utils import timezone
from .models import PaymentRecord
from .forms import ExpenseCategoryForm, ExpenseForm, ProcessPaymentForm, RegularExpenseForm
from .services import get_or_create_monthly_payments, get_financial_summary
from athletes.models import Team, Athlete
from .models import Expense, ExpenseCategory, RegularExpense, TeamFeeHistory, AthleteFeeHistory
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, date

@login_required
def finance_dashboard(request):
    # Seçilen veya varsayılan dönem (YYYY-MM)
    period = request.GET.get('period', date.today().strftime('%Y-%m'))
    
    # 1. Dönem ödeme durumlarını kişi bazında özetle
    monthly_payments = get_or_create_monthly_payments(period)
    paid_payment_count = PaymentRecord.objects.filter(
        period=period,
        payment_type='fee',
        status='paid',
        athlete__is_active=True,
    ).values('athlete_id').distinct().count()
    payment_counts = {
        'paid': paid_payment_count,
        'pending': sum(payment.payment_status == 'pending' for payment in monthly_payments),
    }
    
    # 2. Özet veriler (Gelir, Bekleyen, Harcama, Net)
    financial_summary = get_financial_summary(period)
    expense_summary = get_expense_summary(period)
    
    context = {
        'period': period,
        'payment_counts': payment_counts,
        'expense_summary': expense_summary,
        'financial_summary': financial_summary,
    }
    return render(request, 'finance/dashboard.html', context)


def get_expense_summary(period):
    active_expenses = Expense.objects.filter(period=period, is_active=True)
    category_totals = active_expenses.values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')
    return {
        'total_expense': active_expenses.aggregate(total=Sum('amount'))['total'] or 0,
        'expense_count': active_expenses.count(),
        **get_regular_expense_summary(period),
        'category_totals': [
            {
                'name': item['category__name'] or 'Kategorisiz',
                'total': item['total'],
            }
            for item in category_totals
        ],
    }


@login_required
def expense_list(request):
    period = request.GET.get('period', date.today().strftime('%Y-%m'))
    category_id = request.GET.get('category', '')
    query = request.GET.get('q', '').strip()

    expenses = Expense.objects.filter(period=period).select_related('category', 'created_by', 'regular_expense').order_by('updated_at')
    if category_id:
        expenses = expenses.filter(category_id=category_id)
    if query:
        expenses = expenses.filter(reciever__icontains=query)

    period_start, period_end = get_period_bounds(period)
    regular_expenses = RegularExpense.objects.filter(
        start_date__lte=period_end
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=period_start)
    ).select_related('category').prefetch_related(
        Prefetch(
            'generated_expenses',
            queryset=Expense.objects.filter(
                is_active=True,
                period=period,
            ).order_by('-expense_date'),
        )
    ).order_by('-start_date')[:5]
    summary = get_expense_summary(period)
    context = {
        'period': period,
        'expenses': expenses,
        'regular_expenses': regular_expenses,
        'categories': ExpenseCategory.objects.all().order_by('name'),
        'selected_category': category_id,
        'query': query,
        **summary,
        'today': date.today(),
    }
    return render(request, 'finance/expenses.html', context)


@login_required
def expense_summary_htmx(request):
    period = request.GET.get('period', date.today().strftime('%Y-%m'))
    summary = get_expense_summary(period)
    return render(request, 'finance/partials/_expense_summary.html', {
        'period': period,
        **summary,
    })


def get_period_bounds(period):
    try:
        period_start = datetime.strptime(period, '%Y-%m').date()
    except (TypeError, ValueError):
        period_start = date.today().replace(day=1)
    period_end = period_start.replace(
        day=calendar.monthrange(period_start.year, period_start.month)[1]
    )
    return period_start, period_end


def get_regular_expense_summary(period=None):
    period = period or date.today().strftime('%Y-%m')
    period_start, period_end = get_period_bounds(period)
    active_expenses = RegularExpense.objects.filter(
        start_date__lte=period_end
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=period_start)
    )
    paid_count = Expense.objects.filter(
        regular_expense__in=active_expenses,
        is_active=True,
        period=period,
    ).values('regular_expense').distinct().count()
    paid_total = Expense.objects.filter(
        regular_expense__in=active_expenses,
        is_active=True,
        period=period,
    ).aggregate(total=Sum('amount'))['total'] or 0
    pending_total = active_expenses.aggregate(total=Sum('amount'))['total'] or 0
    return {
        'regular_expense_count': active_expenses.count(),
        'regular_paid_count': paid_count,
        'regular_pending_count': active_expenses.count() - paid_count,
        'regular_paid_total': paid_total,
        'regular_pending_total': pending_total - paid_total,
        'regular_expense_total': pending_total,
        'regular_category_count': active_expenses.values('category_id').distinct().count(),
    }


@login_required
def regular_expense_list(request):
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '')
    status = request.GET.get('status', 'active')
    expenses = RegularExpense.objects.select_related('category', 'created_by').order_by('-start_date')

    if query:
        expenses = expenses.filter(reciever__icontains=query)
    if category_id:
        expenses = expenses.filter(category_id=category_id)
    if status == 'active':
        expenses = expenses.filter(Q(end_date__isnull=True) | Q(end_date__gte=date.today()))
    elif status == 'expired':
        expenses = expenses.filter(end_date__lt=date.today())

    return render(request, 'finance/regular_expenses.html', {
        'regular_expenses': expenses,
        'categories': ExpenseCategory.objects.all().order_by('name'),
        'query': query,
        'selected_category': category_id,
        'status': status,
        'today': date.today(),
        **get_regular_expense_summary(),
    })


def _regular_expense_response(request, query='', category_id='', status='active', period=None):
    expenses = RegularExpense.objects.select_related('category', 'created_by').order_by('-start_date')
    if query:
        expenses = expenses.filter(reciever__icontains=query)
    if category_id:
        expenses = expenses.filter(category_id=category_id)
    if status == 'active':
        expenses = expenses.filter(Q(end_date__isnull=True) | Q(end_date__gte=date.today()))
    elif status == 'expired':
        expenses = expenses.filter(end_date__lt=date.today())
    return render(request, 'finance/partials/_regular_expense_list_response.html', {
        'regular_expenses': expenses,
        'today': date.today(),
        'selected_category': category_id,
        'query': query,
        'status': status,
        'include_summary': True,
        **get_regular_expense_summary(),
    })


@login_required
def create_regular_expense_htmx(request):
    query = request.GET.get('q', '') or request.POST.get('query_filter', '')
    category_id = request.GET.get('category', '') or request.POST.get('category_filter', '')
    status = request.GET.get('status', 'active') or request.POST.get('status_filter', 'active')
    if request.method == 'POST':
        form = RegularExpenseForm(request.POST)
        if form.is_valid():
            regular_expense = form.save(commit=False)
            regular_expense.created_by = request.user
            regular_expense.save()
            response = _regular_expense_response(request, query, category_id, status)
            response['HX-Trigger'] = json.dumps({'closeRegularExpenseModal': {}})
            return response
    else:
        form = RegularExpenseForm(initial={'start_date': date.today()})

    response = render(request, 'finance/modals/_regular_expense_modal.html', {
        'form': form,
        'query_filter': query,
        'category_filter': category_id,
        'status_filter': status,
        'form_action': 'regular-expense-create',
        'modal_title': 'Yeni düzenli harcama',
        'submit_label': 'Düzenli harcamayı kaydet',
    })
    if request.method == 'POST':
        response['HX-Retarget'] = '#regular-expense-modal-container'
        response['HX-Reswap'] = 'innerHTML'
    return response


@login_required
def update_regular_expense_htmx(request, pk):
    regular_expense = get_object_or_404(RegularExpense, pk=pk)
    query = request.GET.get('q', '') or request.POST.get('query_filter', '')
    category_id = request.GET.get('category', '') or request.POST.get('category_filter', '')
    status = request.GET.get('status', 'active') or request.POST.get('status_filter', 'active')
    if request.method == 'POST':
        form = RegularExpenseForm(request.POST, instance=regular_expense)
        if form.is_valid():
            updated_expense = form.save(commit=False)
            updated_expense.save()
            response = _regular_expense_response(request, query, category_id, status)
            response['HX-Trigger'] = json.dumps({'closeRegularExpenseModal': {}})
            return response
    else:
        form = RegularExpenseForm(instance=regular_expense)

    response = render(request, 'finance/modals/_regular_expense_modal.html', {
        'form': form,
        'query_filter': query,
        'category_filter': category_id,
        'status_filter': status,
        'form_action': 'regular-expense-update',
        'regular_expense_id': regular_expense.pk,
        'modal_title': 'Düzenli harcamayı güncelle',
        'submit_label': 'Değişiklikleri kaydet',
    })
    if request.method == 'POST':
        response['HX-Retarget'] = '#regular-expense-modal-container'
        response['HX-Reswap'] = 'innerHTML'
    return response


@login_required
def convert_regular_expense_htmx(request, pk):
    regular_expense = get_object_or_404(RegularExpense, pk=pk)
    query = request.GET.get('q', '') or request.POST.get('query_filter', '')
    category_id = request.GET.get('category', '') or request.POST.get('category_filter', '')
    status = request.GET.get('status', 'active') or request.POST.get('status_filter', 'active')
    source = request.GET.get('source', '') or request.POST.get('conversion_source', '')
    conversion_target = '#expense-list' if source == 'expenses' else '#regular-expense-list'

    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.regular_expense = regular_expense
            expense.created_by = request.user
            expense.save()
            if source == 'expenses':
                period = request.POST.get('period') or expense.period
                expenses = Expense.objects.filter(
                    period=period
                ).select_related('category', 'created_by', 'regular_expense').order_by('-updated_at')
                if category_id:
                    expenses = expenses.filter(category_id=category_id)
                if query:
                    expenses = expenses.filter(reciever__icontains=query)
                response = render(request, 'finance/partials/_expense_list_response.html', {
                    'expenses': expenses,
                    'period': period,
                    **get_expense_summary(period),
                })
                response['HX-Trigger'] = json.dumps({
                    'closeExpenseModal': {},
                    'closeRegularExpenseModal': {},
                })
                return response
            period = request.POST.get('period') or request.GET.get('period') or date.today().strftime('%Y-%m')
            response = _regular_expense_response(request, query, category_id, status, period)
            response['HX-Trigger'] = json.dumps({'closeRegularExpenseModal': {}})
            return response
    else:
        form = ExpenseForm(initial={
            'category': regular_expense.category_id,
            'amount': regular_expense.amount,
            'reciever': regular_expense.reciever,
            'expense_date': date.today(),
            'notes': regular_expense.notes,
        })

    response = render(request, 'finance/modals/_regular_expense_convert_modal.html', {
        'form': form,
        'regular_expense': regular_expense,
        'period': request.GET.get('period', '') or request.POST.get('period', ''),
        'query_filter': query,
        'category_filter': category_id,
        'status_filter': status,
        'conversion_source': source,
        'conversion_target': conversion_target,
    })
    if request.method == 'POST':
        response['HX-Retarget'] = '#regular-expense-modal-container'
        response['HX-Reswap'] = 'innerHTML'
    return response


@login_required
def create_expense_htmx(request):
    period = request.GET.get('period') or request.POST.get('period') or date.today().strftime('%Y-%m')
    category_id = request.GET.get('category', '') or request.POST.get('category_filter', '')
    query = request.GET.get('q', '') or request.POST.get('query_filter', '')
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.created_by = request.user
            expense.save()
            summary = get_expense_summary(period)
            expenses = Expense.objects.filter(period=period).select_related('category', 'created_by', 'regular_expense').order_by('-updated_at')
            if category_id:
                expenses = expenses.filter(category_id=category_id)
            if query:
                expenses = expenses.filter(reciever__icontains=query)
            response = render(request, 'finance/partials/_expense_list_response.html', {
                'expenses': expenses,
                'period': period,
                **summary,
            })
            response['HX-Trigger'] = json.dumps({
                'closeExpenseModal': {},
                'expenseCreated': {
                    'total': f"{summary['total_expense']:.2f}",
                    'count': summary['expense_count'],
                },
            })
            return response
    else:
        form = ExpenseForm(initial={'expense_date': date.today()})

    response = render(request, 'finance/modals/_expense_modal.html', {
        'form': form,
        'period': period,
        'category_filter': category_id,
        'query_filter': query,
        'form_action': 'expense-create',
        'modal_title': 'Yeni harcama',
        'submit_label': 'Harcamayı kaydet',
        'record_user': request.user,
    })
    if request.method == 'POST':
        response['HX-Retarget'] = '#modal-container'
        response['HX-Reswap'] = 'innerHTML'
    return response


@login_required
def update_expense_htmx(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    period = expense.period
    category_id = request.GET.get('category', '') or request.POST.get('category_filter', '')
    query = request.GET.get('q', '') or request.POST.get('query_filter', '')

    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            updated_expense = form.save(commit=False)
            if request.POST.get('cancel_expense') == '1':
                updated_expense.is_active = False
            updated_expense.save()
            summary = get_expense_summary(period)
            expenses = Expense.objects.filter(period=period).select_related('category', 'created_by', 'regular_expense').order_by('-updated_at')
            if category_id:
                expenses = expenses.filter(category_id=category_id)
            if query:
                expenses = expenses.filter(reciever__icontains=query)
            response = render(request, 'finance/partials/_expense_list_response.html', {
                'expenses': expenses,
                'period': period,
                **summary,
            })
            response['HX-Trigger'] = json.dumps({'closeExpenseModal': {}})
            return response
    else:
        form = ExpenseForm(instance=expense)

    response = render(request, 'finance/modals/_expense_modal.html', {
        'form': form,
        'period': period,
        'category_filter': category_id,
        'query_filter': query,
        'form_action': 'expense-update',
        'expense_id': expense.pk,
        'modal_title': 'Harcamayı güncelle',
        'submit_label': 'Değişiklikleri kaydet',
        'show_cancel': expense.is_active,
        'record_user': expense.created_by,
    })
    if request.method == 'POST':
        response['HX-Retarget'] = '#modal-container'
        response['HX-Reswap'] = 'innerHTML'
    return response


@login_required
def create_expense_category_htmx(request):
    if request.method == 'GET' and request.GET.get('cancel'):
        return render(request, 'finance/partials/_expense_category_field.html', {
            'form': ExpenseForm(),
        })

    if request.method == 'POST':
        form = ExpenseCategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            expense_form = ExpenseForm(initial={'category': category.pk})
            return render(request, 'finance/partials/_expense_category_field.html', {
                'form': expense_form,
            })
    else:
        form = ExpenseCategoryForm()

    return render(request, 'finance/partials/_expense_category_form.html', {
        'form': form,
    })

@login_required
def mark_payment_paid_htmx(request, pk):
    payment = get_object_or_404(PaymentRecord, pk=pk)

    if request.method == 'POST':
        form = ProcessPaymentForm(request.POST, instance=payment)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.status = 'paid'
            payment.paid_at = timezone.now()
            payment.collected_by = request.user
            payment.save()

            
            # Güncellenmiş ödeme satırını ve trigger başlığını döndür
            period = payment.period
            financial_summary = get_financial_summary(period)
            response = render(request, 'finance/partials/_payment_row.html', {
                'payment': payment,
                'financial_summary': financial_summary,
                'period': period
            })
            response['HX-Trigger'] = 'closeModal, updateFinancialSummary'
            return response
    else:
        form = ProcessPaymentForm(instance=payment)

    return render(request, 'finance/modals/_mark_paid_modal.html', {
        'payment': payment,
        'form': form
    })



@login_required
def fee_management(request):
    """Takım ve Sporcu Ücret Yönetim Ana Sayfası"""
    teams = Team.objects.all().prefetch_related('fee_histories')
    athletes = Athlete.objects.filter(status='approved', is_active=True).prefetch_related('fee_histories')

    context = {
        'teams': teams,
        'athletes': athletes,
        'today': date.today(),
    }
    return render(request, 'finance/fee_management.html', context)


@login_required
def update_team_fee(request, team_id):
    """Takım Aidat Güncelleme (Eski kaydı kapatır, yeni kaydı başlatır)"""
    if request.method == 'POST':
        team = get_object_or_404(Team, id=team_id)
        new_fee = request.POST.get('monthly_fee')
        start_date_str = request.POST.get('start_date')

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else date.today()

        # 1. Takımın mevcut açık (end_date'i null olan) tarifesinin end_date'ini güncelle
        active_fee = TeamFeeHistory.objects.filter(team=team, end_date__isnull=True).first()
        if active_fee:
            # Yeni başlangıç tarihinden 1 gün öncesini bitiş tarihi yapıyoruz
            active_fee.end_date = start_date
            active_fee.save()

        # 2. Yeni tarife kaydı oluştur
        TeamFeeHistory.objects.create(
            team=team,
            monthly_fee=new_fee,
            start_date=start_date
        )

        messages.success(request, f"{team.name} için yeni aidat tarifesi kaydedildi.")
        return redirect('fee-management')


@login_required
def add_athlete_custom_fee(request, athlete_id):
    """Sporcuya Özel Fiyat/İndirim Ekleme"""
    if request.method == 'POST':
        athlete = get_object_or_404(Athlete, id=athlete_id)
        new_fee = request.POST.get('monthly_fee')
        start_date_str = request.POST.get('start_date')

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else date.today()

        # Aktif özel fiyat varsa kapat
        active_fee = AthleteFeeHistory.objects.filter(athlete=athlete, end_date__isnull=True).first()
        if active_fee:
            active_fee.end_date = start_date
            active_fee.save()

        AthleteFeeHistory.objects.create(
            athlete=athlete,
            monthly_fee=new_fee,
            start_date=start_date
        )

        messages.success(request, f"{athlete.get_full_name()} için özel fiyat tanımlandı.")
        return redirect('fee-management')