import json
import calendar

from django.shortcuts import render

# Create your views here.
# finance/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, F, Prefetch, Q, Sum
from django.urls import reverse
from django.utils import timezone
from .models import PaymentRecord
from .forms import EquipmentForm, ExpenseCategoryForm, ExpenseForm, ProcessPaymentForm, RegularExpenseForm
from .services import get_equipment_central_stock, get_equipment_coach_stock, get_or_create_monthly_payments, get_financial_summary
from athletes.models import Team, Athlete
from .models import Equipment, EquipmentSaleItem, EquipmentStockMovement, Expense, ExpenseCategory, RegularExpense, TeamFeeHistory
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, date


@login_required
def equipment_list(request):
    return render(request, 'finance/equipment_list.html', {
        'equipments': Equipment.objects.all(),
        'form': EquipmentForm(),
    })


@login_required
def equipment_create(request):
    if request.method == 'POST':
        form = EquipmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Malzeme eklendi.')
            return redirect('equipment-list')
    else:
        form = EquipmentForm()
    return render(request, 'finance/equipment_form.html', {'form': form, 'title': 'Malzeme ekle'})


@login_required
def equipment_update(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    if request.method == 'POST':
        active_state = equipment.is_active
        form = EquipmentForm(request.POST, instance=equipment)
        if form.is_valid():
            equipment = form.save(commit=False)
            if 'is_active' not in request.POST:
                equipment.is_active = active_state
            equipment.save()
            messages.success(request, 'Malzeme güncellendi.')
            return redirect('equipment-list')
    else:
        form = EquipmentForm(instance=equipment)
    return render(request, 'finance/equipment_form.html', {
        'form': form,
        'title': 'Malzeme düzenle',
        'equipment': equipment,
    })


@login_required
def equipment_toggle_active(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    if request.method == 'POST':
        equipment.is_active = not equipment.is_active
        equipment.save(update_fields=('is_active',))
    return redirect('equipment-list')


@login_required
def equipment_stock(request):
    equipments = list(Equipment.objects.filter(is_active=True).order_by('name'))
    coaches = [request.user] if request.user.is_coach else list(
        request.user.__class__.objects.filter(role='coach', is_active=True).order_by('first_name', 'last_name')
    )
    athletes = list(Athlete.objects.filter(is_active=True).order_by('first_name', 'last_name'))
    error = None

    if request.method == 'POST':
        action = request.POST.get('action')
        equipment = get_object_or_404(Equipment, pk=request.POST.get('equipment'), is_active=True)
        try:
            quantity = int(request.POST.get('quantity', '0'))
            if quantity < 1:
                raise ValueError
        except (TypeError, ValueError):
            error = 'Adet en az 1 olmalıdır.'
        else:
            coach = request.user if request.user.is_coach else (
                get_object_or_404(request.user.__class__, pk=request.POST.get('coach'))
                if request.POST.get('coach') else None
            )
            athlete = get_object_or_404(Athlete, pk=request.POST.get('athlete'), is_active=True) if request.POST.get('athlete') else None
            if action in {'coach_transfer', 'coach_return', 'athlete_distribution'} and coach is None:
                error = 'Antrenör seçilmelidir.'
            elif action == 'athlete_distribution' and athlete is None:
                error = 'Sporcu seçilmelidir.'
            elif action == 'coach_transfer' and quantity > get_equipment_central_stock(equipment):
                error = 'Merkez stokta yeterli adet yok.'
            elif action in {'coach_return', 'athlete_distribution'} and quantity > get_equipment_coach_stock(equipment, coach):
                error = 'Antrenör stoğunda yeterli adet yok.'
            elif action not in {'stock_in', 'coach_transfer', 'coach_return', 'athlete_distribution'}:
                error = 'Geçersiz stok işlemi.'
            else:
                with transaction.atomic():
                    payment = None
                    if action == 'athlete_distribution':
                        payment = PaymentRecord.objects.create(
                            athlete=athlete,
                            payment_type='equipment_sale',
                            payment_method='cash',
                            period=date.today().strftime('%Y-%m'),
                            amount=equipment.price * quantity,
                            status='pending',
                            due_date=date.today(),
                            notes=f'Stoktan dağıtım: {equipment.name} x{quantity}',
                        )
                        sale_item = EquipmentSaleItem.objects.create(
                            payment=payment,
                            equipment=equipment,
                            quantity=quantity,
                            unit_price=equipment.price,
                        )
                    EquipmentStockMovement.objects.create(
                        equipment=equipment,
                        movement_type=action,
                        quantity=quantity,
                        coach=coach,
                        athlete=athlete,
                        payment=payment,
                        sale_item=sale_item if action == 'athlete_distribution' else None,
                        created_by=request.user,
                        notes=request.POST.get('notes', '').strip(),
                    )
                messages.success(request, 'Stok işlemi kaydedildi.')
                if request.headers.get('HX-Request') == 'true':
                    response = redirect('equipment-stock')
                    response['HX-Redirect'] = reverse('equipment-stock')
                    return response
                return redirect('equipment-stock')

    coach_stock_rows = []
    for coach in coaches:
        coach_items = []
        for equipment in equipments:
            quantity = get_equipment_coach_stock(equipment, coach)
            if quantity:
                coach_items.append({'equipment': equipment, 'quantity': quantity})
        coach_stock_rows.append({'coach': coach, 'items': coach_items})

    for equipment in equipments:
        equipment.central_stock = get_equipment_central_stock(equipment)
    movements = EquipmentStockMovement.objects.select_related(
        'equipment', 'coach', 'athlete', 'created_by',
    ).order_by('-created_at', '-pk')[:20]
    return render(request, 'finance/equipment_stock.html', {
        'equipments': equipments,
        'coaches': coaches,
        'athletes': athletes,
        'coach_stock_rows': coach_stock_rows,
        'movements': movements,
        'error': error,
    })


@login_required
def equipment_stock_modal(request):
    equipments = Equipment.objects.filter(is_active=True).order_by('name')
    coaches = [request.user] if request.user.is_coach else request.user.__class__.objects.filter(
        role='coach', is_active=True,
    ).order_by('first_name', 'last_name')
    athletes = Athlete.objects.filter(is_active=True).order_by('first_name', 'last_name')
    return render(request, 'finance/modals/_equipment_stock_modal.html', {
        'equipments': equipments,
        'coaches': coaches,
        'athletes': athletes,
        'selected_action': request.GET.get('action', 'stock_in'),
    })

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
    financial_summary = get_financial_summary(period, monthly_payments=monthly_payments)
    expense_summary = get_expense_summary(period)
    collection_summary = get_collection_summary(period)
    
    context = {
        'period': period,
        'payment_counts': payment_counts,
        'expense_summary': expense_summary,
        'collection_summary': collection_summary,
        'financial_summary': financial_summary,
    }
    return render(request, 'finance/dashboard.html', context)


@login_required
def payment_status_list(request, payment_status):
    if payment_status not in {'paid', 'pending'}:
        return redirect('finance-dashboard')

    period = request.GET.get('period', date.today().strftime('%Y-%m'))
    team_id = request.GET.get('team', '')
    monthly_payments = get_or_create_monthly_payments(period)
    payments = [
        athlete for athlete in monthly_payments
        if athlete.payment_status == payment_status
        and (not team_id or str(athlete.team_id) == team_id)
    ]
    teams = Team.objects.filter(is_active=True).order_by('name')

    return render(request, 'finance/payment_status_list.html', {
        'period': period,
        'payments': payments,
        'payment_status': payment_status,
        'status_label': 'Ödeyen sporcular' if payment_status == 'paid' else 'Bekleyen sporcular',
        'teams': teams,
        'selected_team': team_id,
    })


def get_expense_summary(period):
    active_expenses = Expense.objects.filter(
        period=period,
        is_active=True,
        status__in=('paid', 'pending'),
    )
    category_totals = active_expenses.values('category__name').annotate(
        total=Sum('amount')
    ).order_by('-total')
    regular_expense_summary = get_regular_expense_summary(period)
    return {
        'total_expense': active_expenses.aggregate(total=Sum('amount'))['total'] or 0,
        'expense_count': active_expenses.count(),
        'paid_expense_total': active_expenses.filter(status='paid').aggregate(total=Sum('amount'))['total'] or 0,
        'pending_expense_total': active_expenses.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0,
        **get_regular_expense_summary(period),
        'category_totals': [
            {
                'name': item['category__name'] or 'Kategorisiz',
                'total': item['total'],
            }
            for item in category_totals
        ],
    }


def get_collection_summary(period):
    paid_collections = PaymentRecord.objects.filter(
        period=period,
        status='paid',
        athlete__is_active=True,
    )
    payment_type_totals = paid_collections.values('payment_type').annotate(
        total=Sum('amount'),
        count=Count('id'),
    ).order_by('-total')
    payment_type_labels = dict(PaymentRecord.PAYMENT_TYPE_CHOICES)

    return {
        'payment_type_totals': [
            {
                'name': payment_type_labels.get(item['payment_type'], item['payment_type']),
                'total': item['total'],
                'count': item['count'],
            }
            for item in payment_type_totals
        ],
    }


def get_expenses_for_period(period, category_id='', query=''):
    period_start, period_end = get_period_bounds(period)
    expense_queryset = Expense.objects.select_related(
        'category',
        'regular_expense',
    ).filter(
        period=period,
        is_active=True,
    ).exclude(
        status='cancelled',
    )

    if category_id:
        expense_queryset = expense_queryset.filter(category_id=category_id)
    if query:
        expense_queryset = expense_queryset.filter(
            Q(reciever__icontains=query)
            | Q(notes__icontains=query)
            | Q(category__name__icontains=query)
        )

    expenses = list(expense_queryset)
    paid_regular_ids = [
        expense.regular_expense_id
        for expense in expenses
        if expense.regular_expense_id
    ]

    regular_queryset = RegularExpense.objects.select_related('category').filter(
        start_date__lte=period_end
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=period_start)
    )
    if paid_regular_ids:
        regular_queryset = regular_queryset.exclude(pk__in=paid_regular_ids)
    if category_id:
        regular_queryset = regular_queryset.filter(category_id=category_id)
    if query:
        regular_queryset = regular_queryset.filter(
            Q(reciever__icontains=query)
            | Q(notes__icontains=query)
            | Q(category__name__icontains=query)
        )

    regular_expenses = list(regular_queryset)
    for expense in regular_expenses:
        expense.is_regular_source = True
        payment_day = expense.paymentDay or 1
        last_day = calendar.monthrange(period_start.year, period_start.month)[1]
        payment_day = min(payment_day, last_day)
        expense.expense_date = date(period_start.year, period_start.month, payment_day)


    expenses.extend(regular_expenses)
    expenses.sort(key=lambda expense: -expense.expense_date.toordinal())
    return expenses


@login_required
def expense_list(request):
    period = request.GET.get('period', date.today().strftime('%Y-%m'))
    category_id = request.GET.get('category', '')
    query = request.GET.get('q', '').strip()
    expenses = get_expenses_for_period(period, category_id, query)
    expense_summary = get_expense_summary(period)
    regular_expense_summary = get_regular_expense_summary(period)
    context = {
        'period': period,
        'expenses': expenses,
        'categories': ExpenseCategory.objects.all().order_by('name'),
        'selected_category': category_id,
        'query': query,
        'expense_summary': expense_summary,
        'regular_expense_summary': regular_expense_summary,
        'today': date.today(),
    }
    return render(request, 'finance/expenses.html', context)


@login_required
def expense_summary_htmx(request):
    period = request.GET.get('period', date.today().strftime('%Y-%m'))
    summary = get_expense_summary(period)
    return render(request, 'finance/partials/_expense_summary.html', {
        'period': period,
        'expense_summary': summary,
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
    paid_expenses = Expense.objects.filter(
        regular_expense__in=active_expenses,
        is_active=True,
        status='paid',
        period=period,
    )
    regular_total = active_expenses.aggregate(total=Sum('amount'))['total'] or 0
    paid_total = paid_expenses.aggregate(total=Sum('amount'))['total'] or 0

    return {
        'regular_total': regular_total,
        'regular_paid_total': paid_total,
        'regular_pending_total': regular_total - paid_total,

    }


@login_required
def regular_expense_list(request):
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '')
    status = request.GET.get('status', 'active')
    expenses = RegularExpense.objects.select_related('category', 'created_by').order_by(
        F('paymentDay').asc(nulls_last=True), '-start_date'
    )

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
    expenses = RegularExpense.objects.select_related('category', 'created_by').order_by(
        F('paymentDay').asc(nulls_last=True), '-start_date'
    )
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
        form_data = request.POST.copy()
        form_data['status'] = 'paid'
        form = ExpenseForm(form_data)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.regular_expense = regular_expense
            expense.status = 'paid'
            expense.created_by = request.user
            expense.save()
            if source == 'expenses':
                period = request.POST.get('period') or expense.period
                expenses = get_expenses_for_period(period, category_id, query)
                response = render(request, 'finance/partials/_expense_list_response.html', {
                    'expenses': expenses,
                    'period': period,
                    'expense_summary': get_expense_summary(period),
                    'regular_expense_summary': get_regular_expense_summary(period),
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
    dashboard_mode = request.GET.get('dashboard') == '1'
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.created_by = request.user
            expense.save()
            summary = get_expense_summary(period)
            if dashboard_mode:
                response = render(request, 'finance/partials/_expense_row.html', {
                    'expense': expense,
                })
                response['HX-Trigger'] = json.dumps({'closeExpenseModal': {}})
                return response
            expenses = get_expenses_for_period(period, category_id, query)
            response = render(request, 'finance/partials/_expense_list_response.html', {
                'expenses': expenses,
                'period': period,
                'expense_summary': summary,
                'regular_expense_summary': get_regular_expense_summary(period),
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
        'dashboard_mode': dashboard_mode,
    })
    if request.method == 'POST':
        response['HX-Retarget'] = '#modal-container'
        response['HX-Reswap'] = 'innerHTML'
    return response


@login_required
def update_expense_htmx(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    period = request.GET.get('period') or request.POST.get('period') or expense.period
    category_id = request.GET.get('category', '') or request.POST.get('category_filter', '')
    query = request.GET.get('q', '') or request.POST.get('query_filter', '')

    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            updated_expense = form.save(commit=False)
            if request.POST.get('cancel_expense') == '1':
                updated_expense.is_active = False
                updated_expense.status = 'cancelled'
            updated_expense.save()
            expense_summary = get_expense_summary(period)
            expenses = get_expenses_for_period(period, category_id, query)
            response = render(request, 'finance/partials/_expense_list_response.html', {
                'expenses': expenses,
                'period': period,
                'selected_category': category_id,
                'query': query,
                'expense_summary': expense_summary,
                'regular_expense_summary': get_regular_expense_summary(period),
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
    teams = Team.objects.annotate(athlete_count=Count('athletes')).prefetch_related('fee_histories')
    athletes = Athlete.objects.filter(is_active=True, custom_fee__isnull=False).select_related('team')

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



