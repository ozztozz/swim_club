# athletes/views.py
from calendar import monthrange
from datetime import date
from decimal import Decimal
import json
import re
from collections import OrderedDict

from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db import models
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from django.db.models import Sum
from .forms import AthleteForm, AthletePaymentCreateForm, AthletePaymentEditForm, EquipmentSaleForm
from .models import Athlete
from teams.models import TeamTrainingAttendance, TeamTrainingSchedule
from .serializers import AthleteSerializer
from finance.models import Equipment, EquipmentSaleItem, EquipmentStockMovement, PaymentRecord
from finance.services import get_equipment_central_stock, get_equipment_coach_stock

MONTH_NAMES = (
    'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
    'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık',
)
WEEKDAY_NAMES = (
    'Pazartesi', 'Salı', 'Çarşamba', 'Perşembe',
    'Cuma', 'Cumartesi', 'Pazar',
)


def _athlete_queryset(request):
    queryset = Athlete.objects.select_related('team').order_by('-is_active', 'team__name', 'first_name', 'last_name')
    if request.user.is_coach:
        return queryset.filter(team__coaches=request.user)
    if request.user.is_parent:
        return queryset.filter(parent_email=request.user.email)
    return queryset


def _athlete_context(request):
    query = request.GET.get('q', '').strip()
    has_search = len(query) >= 3
    show_coach_roster = request.user.is_coach and not query
    athletes = _athlete_queryset(request).none()
    if show_coach_roster:
        athletes = _athlete_queryset(request)
        has_search = True
    if has_search:
        athletes = _athlete_queryset(request).filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(parent__icontains=query) |
            Q(parent_email__icontains=query) |
            Q(parent_phone__icontains=query)
        )
    return {
        'athletes': athletes,
        'query': query,
        'athlete_list_loaded': has_search,
    }


@login_required
def athlete_list(request):
    context = _athlete_context(request)
    if request.headers.get('HX-Request') == 'true':
        return render(request, 'athlete/partials/athlete_table.html', context)
    return render(request, 'athlete/athlete_list.html', context)


@login_required
def athlete_detail(request, pk):
    from finance.services import get_athlete_fee_for_period

    athlete = get_object_or_404(_athlete_queryset(request), pk=pk)
    first_month = athlete.joined_date.replace(day=1)
    current_month = date.today().replace(day=1)
    attendance_first_month = current_month.replace(month=1)
    payments_records = PaymentRecord.objects.filter(
        athlete=athlete,
        payment_type='fee',
    ).order_by('-due_date', '-paid_at', '-created_at', '-pk')
    equipment_sales = PaymentRecord.objects.filter(
        athlete=athlete,
        payment_type='equipment_sale',
    ).order_by('-due_date', '-paid_at', '-created_at', '-pk')
    other_payments = PaymentRecord.objects.filter(
        athlete=athlete,
    ).exclude(payment_type__in=('fee', 'equipment_sale')).order_by(
        '-due_date', '-paid_at', '-created_at', '-pk'
    )
    attendance_records = TeamTrainingAttendance.objects.filter(
        athlete=athlete,
    ).select_related('schedule').order_by(
        '-training_date', '-schedule__start_time', '-pk'
    )

    def payment_item(payment):
        return {
            'period': payment.period,
            'label': f'{MONTH_NAMES[int(payment.period[5:]) - 1]} {payment.period[:4]}',
            'amount': payment.amount,
            'payment': payment,
            'paid_amount': payment.amount if payment.status == 'paid' else Decimal('0.00'),
            'payment_type': payment.payment_type,
            'payment_type_display': payment.get_payment_type_display(),
            'equipment_items': _equipment_sale_items(payment) if payment.payment_type == 'equipment_sale' else [],
            'is_paid': payment.status == 'paid',
            'status': payment.status,
        }

    equipment_sale_items = [payment_item(payment) for payment in equipment_sales]
    other_payment_items = [payment_item(payment) for payment in other_payments]


    monthly_payments = []
    payments_by_period = {}
    for payment in payments_records:
        payments_by_period.setdefault(payment.period, []).append(payment)

    payment_periods = [
        date.fromisoformat(f'{period}-01')
        for period in payments_by_period
    ]
    period_month = max([current_month, *payment_periods])
    earliest_period = min([first_month, *payment_periods])
    while period_month >= earliest_period:
        period = period_month.strftime('%Y-%m')
        period_payments = payments_by_period.get(period, [])
        if not period_payments:
            monthly_payments.append({
                'period': period,
                'label': f'{MONTH_NAMES[period_month.month - 1]} {period_month.year}',
                'amount': get_athlete_fee_for_period(athlete, period),
                'payment': None,
                'paid_amount': Decimal('0.00'),
                'payment_type': 'fee',
                'payment_type_display': 'Aidat',
                'is_paid': False,
                'status': 'pending',
            })
        else:
            for payment in period_payments:
                fee_amount = get_athlete_fee_for_period(athlete, period)
                monthly_payments.append({
                    'period': period,
                    'label': f'{MONTH_NAMES[period_month.month - 1]} {period_month.year}',
                    'amount': fee_amount,
                    'payment': payment,
                    'paid_amount': (
                        payment.amount or fee_amount
                        if payment.status == 'paid'
                        else Decimal('0.00')
                    ),
                    'payment_type': 'fee',
                    'payment_type_display': payment.get_payment_type_display(),
                    'is_paid': payment.status == 'paid',
                    'status': payment.status,
                })
        if period_month.month == 1:
            period_month = period_month.replace(year=period_month.year - 1, month=12)
        else:
            period_month = period_month.replace(month=period_month.month - 1)

    def payment_date(item):
        if item['payment'] is not None:
            payment = item['payment']
            return (
                payment.due_date,
                payment.paid_at.timestamp() if payment.paid_at else float('-inf'),
                payment.created_at.timestamp() if payment.created_at else float('-inf'),
                payment.pk,
            )
        return (date.fromisoformat(f"{item['period']}-15"), float('-inf'), float('-inf'), 0)

    monthly_payments.sort(key=payment_date, reverse=True)

    monthly_payment_groups = OrderedDict()
    for item in monthly_payments:
        group = monthly_payment_groups.setdefault(item['period'], {
            'period': item['period'],
            'label': item['label'],
            'fee_amount': item['amount'],
            'total_paid': Decimal('0.00'),
            'items': [],
        })
        group['items'].append(item)
        group['total_paid'] += item['paid_amount']

    for group in monthly_payment_groups.values():
        group['is_paid_sufficient'] = group['total_paid'] >= group['fee_amount']
    monthly_payment_groups = OrderedDict(
        sorted(
            monthly_payment_groups.items(),
            key=lambda item: item[0],
            reverse=True,
        )
    )

    attendance_months = OrderedDict()
    for record in attendance_records:
        period = record.training_date.strftime('%Y-%m')
        if period not in attendance_months:
            attendance_months[period] = {
                'label': f'{MONTH_NAMES[record.training_date.month - 1]} {record.training_date.year}',
                'weekdays': OrderedDict(),
            }
        weekdays = attendance_months[period]['weekdays']
        weekday = record.training_date.weekday()
        if weekday not in weekdays:
            weekdays[weekday] = {
                'label': WEEKDAY_NAMES[weekday],
                'days': OrderedDict(),
            }
        days = weekdays[weekday]['days']
        day = record.training_date.day
        day_record = days.setdefault(day, {
            'sessions': {},
        })
        session_label = 'S' if record.schedule.start_time.hour < 12 else 'A'
        day_record['sessions'][session_label] = {
            'status': record.status,
            'is_makeup': record.notes == 'Telafi',
        }

    period_month = current_month
    while period_month >= attendance_first_month:
        period = period_month.strftime('%Y-%m')
        attendance_months.setdefault(period, {
            'label': f'{MONTH_NAMES[period_month.month - 1]} {period_month.year}',
            'weekdays': OrderedDict(),
        })
        if period_month.month == 1:
            period_month = period_month.replace(year=period_month.year - 1, month=12)
        else:
            period_month = period_month.replace(month=period_month.month - 1)

    attendance_total = attendance_records.count()
    attendance_absent = attendance_records.filter(
        status=TeamTrainingAttendance.Status.ABSENT,
    ).count()
    attendance_swimming = attendance_records.filter(
        schedule__training_type=TeamTrainingSchedule.TrainingType.SWIMMING,
    ).count()
    attendance_land = attendance_records.filter(
        schedule__training_type=TeamTrainingSchedule.TrainingType.LAND,
    ).count()
    attendance_absent_swimming = attendance_records.filter(
        schedule__training_type=TeamTrainingSchedule.TrainingType.SWIMMING,
        status=TeamTrainingAttendance.Status.ABSENT,
    ).count()
    attendance_absent_land = attendance_records.filter(
        schedule__training_type=TeamTrainingSchedule.TrainingType.LAND,
        status=TeamTrainingAttendance.Status.ABSENT,
    ).count()
    for month in attendance_months.values():
        month_records = [
            status
            for weekday in month['weekdays'].values()
            for day_record in weekday['days'].values()
            for status in day_record['sessions'].values()
        ]
        month['total_count'] = len(month_records)
        month['absent_count'] = sum(
            record['status'] == TeamTrainingAttendance.Status.ABSENT
            for record in month_records
        )

    for period, month in attendance_months.items():
        year, month_number = map(int, period.split('-'))
        days_in_month = monthrange(year, month_number)[1]
        first_weekday = date(year, month_number, 1).weekday()
        calendar_days = [None] * first_weekday

        for day_number in range(1, days_in_month + 1):
            weekday = month['weekdays'].get(date(year, month_number, day_number).weekday())
            day_record = weekday['days'].get(day_number) if weekday else None
            calendar_days.append(
                {
                    'number': day_number,
                    'sessions': [
                        {
                            'label': session,
                            **session_data,
                        }
                        for session, session_data in sorted(
                            (day_record or {'sessions': {}})['sessions'].items(),
                            key=lambda item: 0 if item[0] == 'S' else 1,
                        )
                    ],
                }
            )

        calendar_days.extend([None] * (-len(calendar_days) % 7))
        month['calendar_weeks'] = [
            calendar_days[index:index + 7]
            for index in range(0, len(calendar_days), 7)
        ]
        month['weekdays'] = [
            {'label': WEEKDAY_NAMES[weekday]}
            for weekday in range(7)
        ]

    attendance_periods = sorted(attendance_months.keys(), reverse=True)
    requested_period = request.GET.get('attendance_month')
    selected_period = (
        requested_period
        if requested_period in attendance_months
        else attendance_periods[0] if attendance_periods else None
    )
    selected_month = attendance_months.get(selected_period) if selected_period else None
    selected_months = [selected_month] if selected_month else []
    selected_index = attendance_periods.index(selected_period) if selected_period else -1
    selected_attendance_records = attendance_records
    if selected_period:
        selected_year, selected_month_number = map(int, selected_period.split('-'))
        selected_attendance_records = attendance_records.filter(
            training_date__year=selected_year,
            training_date__month=selected_month_number,
        )
    attendance_total = selected_attendance_records.count()
    attendance_absent = selected_attendance_records.filter(
        status=TeamTrainingAttendance.Status.ABSENT,
    ).count()
    attendance_swimming = selected_attendance_records.filter(
        schedule__training_type=TeamTrainingSchedule.TrainingType.SWIMMING,
    ).count()
    attendance_land = selected_attendance_records.filter(
        schedule__training_type=TeamTrainingSchedule.TrainingType.LAND,
    ).count()
    attendance_absent_swimming = selected_attendance_records.filter(
        schedule__training_type=TeamTrainingSchedule.TrainingType.SWIMMING,
        status=TeamTrainingAttendance.Status.ABSENT,
    ).count()
    attendance_absent_land = selected_attendance_records.filter(
        schedule__training_type=TeamTrainingSchedule.TrainingType.LAND,
        status=TeamTrainingAttendance.Status.ABSENT,
    ).count()

    return render(request, 'athlete/athlete_detail.html', {
        'athlete': athlete,
        'monthly_payments': monthly_payments,
        'monthly_payment_groups': monthly_payment_groups.values(),
        'equipment_sales': equipment_sale_items,
        'other_payments': other_payment_items,
        'attendance_months': selected_months,
        'attendance_period': selected_period,
        'attendance_previous_period': (
            attendance_periods[selected_index + 1]
            if selected_index >= 0 and selected_index < len(attendance_periods) - 1 else None
        ),
        'attendance_next_period': (
            attendance_periods[selected_index - 1]
            if selected_index > 0 else None
        ),
        'attendance_total': attendance_total,
        'attendance_absent': attendance_absent,
        'attendance_swimming': attendance_swimming,
        'attendance_land': attendance_land,
        'attendance_absent_swimming': attendance_absent_swimming,
        'attendance_absent_land': attendance_absent_land,
    })


@login_required
def athlete_make_payment(request, athlete_id, period=None, payment_id=None):
    from finance.services import get_athlete_fee_for_period

    athlete = get_object_or_404(_athlete_queryset(request), pk=athlete_id)
    dashboard_mode = request.GET.get('dashboard') == '1'
    if payment_id is not None:
        payment = get_object_or_404(
            PaymentRecord,
            pk=payment_id,
            athlete=athlete,
        )
        period = payment.period
        year, month = map(int, period.split('-'))
    else:
        try:
            year, month = map(int, period.split('-'))
            period_date = date(year, month, 1)
        except (TypeError, ValueError):
            return render(request, 'athlete/partials/athlete_payment_modal.html', {'mode': 'pay'}, status=400)

        payment = None

    private_lesson_fee = athlete.private_lesson_fee or 0
    is_private_lesson = private_lesson_fee > 0
    fee_amount = private_lesson_fee if is_private_lesson else get_athlete_fee_for_period(athlete, period)
    paid_amount = PaymentRecord.objects.filter(athlete=athlete, period=period, payment_type='fee', status='paid').aggregate(total_paid=Sum('amount'))['total_paid'] or Decimal('0.00')

    lesson_count = 1
    if is_private_lesson and payment and fee_amount:
        lesson_count = max(1, int(payment.amount or fee_amount) // int(fee_amount))

    if payment:
        amount = payment.amount or fee_amount
    else:
        amount = fee_amount
    if not is_private_lesson and fee_amount:
        amount = max(fee_amount - paid_amount, Decimal('0.00'))

    item = {
        'period': period,
        'label': f'{MONTH_NAMES[month - 1]} {year}',
        'fee_amount': fee_amount,
        'private_lesson_fee': private_lesson_fee,
        'is_private_lesson': is_private_lesson,
        'lesson_count': lesson_count,
        'amount': amount,
        'payment': payment,
        'paid_amount': paid_amount,
        'payment_type': payment.payment_type if payment else 'fee',
        'payment_type_display': payment.get_payment_type_display() if payment else 'Aidat',
        'is_paid': payment is not None and payment.status == 'paid',
        'status': payment.status if payment else 'pending',
    }

    if request.method == 'GET':
        return render(request, 'athlete/partials/athlete_payment_modal.html', {
            'athlete': athlete,
            'item': item,
            'mode': 'pay',
            'dashboard_mode': dashboard_mode,
        })
    if request.method != 'POST':
        return render(request, 'athlete/partials/athlete_payment_modal.html', {
            'athlete': athlete,
            'item': item,
            'mode': 'pay',
            'dashboard_mode': dashboard_mode,
        }, status=405)

    try:
        if is_private_lesson:
            raw_lesson_count = request.POST.get('lesson_count', '').strip()
            if not raw_lesson_count.isdigit() or int(raw_lesson_count) < 1:
                raise ValueError
            lesson_count = int(raw_lesson_count)
            amount = private_lesson_fee * lesson_count
            item['lesson_count'] = lesson_count
            item['amount'] = amount
        else:
            raw_amount = request.POST.get('amount', '').strip()
            normalized_amount = raw_amount.replace(',', '').replace('.', '').replace(' ', '')
            if not normalized_amount.isdigit():
                raise ValueError
            amount = int(normalized_amount)
            if amount < 0:
                raise ValueError
    except (TypeError, ValueError):
        item['amount_error'] = 'Geçerli bir ders sayısı veya tutar girin.'
        return render(request, 'athlete/partials/athlete_payment_modal.html', {
            'athlete': athlete,
            'item': item,
            'mode': 'pay',
            'dashboard_mode': dashboard_mode,
        }, status=400)

    if payment is None:
        payment = PaymentRecord.objects.create(
            athlete=athlete,
            period=period,
            payment_type='fee',
            amount=amount,
            payment_method='cash',
            status='pending',
            due_date=period_date.replace(day=15),
        )
    payment.amount = amount
    payment.status = 'paid'
    payment.paid_at = timezone.now()
    payment.collected_by = request.user
    payment.save(update_fields=('amount', 'status', 'paid_at', 'collected_by'))

    item['payment'] = payment
    item['is_paid'] = True
    item['status'] = payment.status
    if dashboard_mode:
        response = render(request, 'dashboard/_recent_payment_row.html', {
            'payment': payment,
        })
    else:
        response = render(request, 'athlete/partials/athlete_payment_row.html', {
            'athlete': athlete,
            'item': item,
        })
    response['HX-Trigger'] = 'closeAthletePaymentModal'
    return response


@login_required
def athlete_create_payment(request, pk):
    athlete = get_object_or_404(_athlete_queryset(request), pk=pk)
    if request.method == 'POST':
        form = AthletePaymentCreateForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.athlete = athlete
            if payment.status == 'paid':
                payment.paid_at = payment.paid_at or timezone.now()
                payment.collected_by = request.user
            else:
                payment.paid_at = None
                payment.collected_by = None
            payment.save()
            response = HttpResponse(status=204)
            response['HX-Redirect'] = request.build_absolute_uri(
                reverse('athlete-manage-detail', args=[athlete.pk])
            )
            return response
    else:
        form = AthletePaymentCreateForm(initial={
            'period': date.today().strftime('%Y-%m'),
            'due_date': date.today().replace(day=15),
            'payment_method': 'cash',
            'status': 'paid',
        })

    return render(request, 'athlete/partials/athlete_payment_modal.html', {
        'athlete': athlete,
        'form': form,
        'mode': 'create',
    })


@login_required
def athlete_create_equipment_sale(request, pk):
    if not (
        request.user.is_superuser
        or request.user.is_coach
        or request.user.is_club_admin
        or request.user.is_finance
    ):
        raise PermissionDenied
    athlete = get_object_or_404(_athlete_queryset(request), pk=pk)
    coach_queryset = get_user_model().objects.filter(role='coach', is_active=True).order_by('first_name', 'last_name')
    if request.user.is_coach:
        coach_queryset = get_user_model().objects.filter(pk=request.user.pk)
    if request.method == 'POST':
        form = EquipmentSaleForm(request.POST, coach_queryset=coach_queryset)
        if form.is_valid():
            distribution_mode = request.POST.get('distribution_mode') == '1'
            stock_source = request.POST.get('stock_source', 'coach')
            if request.user.is_coach and not distribution_mode:
                raise PermissionDenied
            if request.user.is_coach:
                stock_source = 'coach'
            coach = form.cleaned_data['coach']
            if distribution_mode and stock_source == 'coach' and coach is None:
                form.add_error('coach', 'Dağıtım için antrenör seçilmelidir.')
                sale_data = None
            else:
                sale_data = _equipment_sale_data(form, request.user)
            if sale_data:
                insufficient = []
                if distribution_mode and stock_source == 'coach':
                    insufficient = [
                        f'{equipment.name}: mevcut {get_equipment_coach_stock(equipment, coach)}, istenen {quantity}'
                        for equipment, quantity, _, _, _ in sale_data['items']
                        if quantity > get_equipment_coach_stock(equipment, coach)
                    ]
                elif distribution_mode and stock_source == 'central':
                    insufficient = [
                        f'{equipment.name}: merkezde mevcut {get_equipment_central_stock(equipment)}, istenen {quantity}'
                        for equipment, quantity, _, _, _ in sale_data['items']
                        if quantity > get_equipment_central_stock(equipment)
                    ]
                if insufficient:
                    form.add_error(None, f'Antrenör stoğu yetersiz: {", ".join(insufficient)}')
                    sale_data = None
            if sale_data:
                with transaction.atomic():
                    payment = PaymentRecord.objects.create(
                        athlete=athlete,
                        payment_type='equipment_sale',
                        payment_method=form.cleaned_data['payment_method'],
                        period=date.today().strftime('%Y-%m'),
                        amount=sale_data['amount'],
                        status='pending' if distribution_mode else sale_data['status'],
                        due_date=date.today(),
                        paid_at=sale_data['paid_at'],
                        collected_by=sale_data['collected_by'],
                        notes=sale_data['notes'],
                    )
                    for equipment, quantity, unit_price, color, size in sale_data['items']:
                        sale_item = EquipmentSaleItem.objects.create(
                            payment=payment,
                            equipment=equipment,
                            quantity=quantity,
                            unit_price=unit_price,
                            selected_color=color,
                            selected_size=size,
                        )
                        if distribution_mode:
                            EquipmentStockMovement.objects.create(
                                equipment=equipment,
                                movement_type='athlete_distribution',
                                quantity=quantity,
                                coach=coach if stock_source == 'coach' else None,
                                athlete=athlete,
                                payment=payment,
                                sale_item=sale_item,
                                selected_color=color,
                                selected_size=size,
                                created_by=request.user,
                                notes='Sporcuya dağıtım',
                            )
                response = HttpResponse(status=204)
                response['HX-Redirect'] = request.build_absolute_uri(
                    reverse('athlete-manage-detail', args=[athlete.pk])
                )
                return response
    else:
        form = EquipmentSaleForm(coach_queryset=coach_queryset)

    return render(request, 'athlete/partials/athlete_equipment_sale_modal.html', {
        'athlete': athlete,
        'form': form,
        'distribution_mode': True,
        'sale_url': reverse('athlete-manage-equipment-sale-create', args=[athlete.pk]),
    })


@login_required
def athlete_edit_equipment_sale(request, pk, payment_id):
    athlete = get_object_or_404(_athlete_queryset(request), pk=pk)
    payment = get_object_or_404(
        PaymentRecord,
        pk=payment_id,
        athlete=athlete,
        payment_type='equipment_sale',
    )
    existing_items = list(payment.equipment_sale_items.all())
    initial_quantities = (
        {equipment_id: sum(item.quantity for item in existing_items if item.equipment_id == equipment_id)
         for equipment_id in {item.equipment_id for item in existing_items}}
        if existing_items else _equipment_sale_quantities(payment.notes)
    )
    unit_prices = {item.equipment_id: item.unit_price for item in existing_items}
    initial_variants = {}
    for item in existing_items:
        initial_variants.setdefault(item.equipment_id, []).append({
            'color': item.selected_color,
            'size': item.selected_size,
            'quantity': item.quantity,
        })
    initial = {
        **initial_quantities,
        'payment_method': payment.payment_method,
        'status': payment.status,
        'notes': _equipment_sale_extra_notes(payment.notes),
    }
    form_data = request.POST or None
    if request.method == 'POST' and existing_items:
        form_data = request.POST.copy()
        for equipment_id, variants in initial_variants.items():
            field_name = f'equipment_{equipment_id}_variants'
            if not form_data.get(field_name):
                legacy_quantity = form_data.get(f'equipment_{equipment_id}')
                legacy_variants = [dict(variant) for variant in variants]
                if legacy_quantity is not None and legacy_variants:
                    legacy_variants[0]['quantity'] = int(legacy_quantity or 0)
                    for variant in legacy_variants[1:]:
                        variant['quantity'] = 0
                form_data[field_name] = json.dumps(legacy_variants, ensure_ascii=False)
    form = EquipmentSaleForm(
        form_data,
        initial_quantities=initial_quantities,
        initial_variants=initial_variants,
        initial=initial,
    )
    if request.method == 'POST' and form.is_valid():
        sale_data = _equipment_sale_data(form, request.user, unit_prices=unit_prices)
        if sale_data:
            payment.amount = sale_data['amount']
            payment.payment_method = form.cleaned_data['payment_method']
            payment.status = sale_data['status']
            payment.paid_at = sale_data['paid_at']
            payment.collected_by = sale_data['collected_by']
            payment.notes = sale_data['notes']
            payment.save(update_fields=(
                'amount', 'payment_method', 'status', 'paid_at', 'collected_by', 'notes',
            ))
            payment.equipment_sale_items.all().delete()
            EquipmentSaleItem.objects.bulk_create([
                EquipmentSaleItem(
                    payment=payment,
                    equipment=equipment,
                    quantity=quantity,
                    unit_price=unit_price,
                    selected_color=color,
                    selected_size=size,
                )
                for equipment, quantity, unit_price, color, size in sale_data['items']
            ])
            response = HttpResponse(status=204)
            response['HX-Redirect'] = request.build_absolute_uri(
                reverse('athlete-manage-detail', args=[athlete.pk])
            )
            return response

    return render(request, 'athlete/partials/athlete_equipment_sale_modal.html', {
        'athlete': athlete,
        'form': form,
        'payment': payment,
        'sale_url': reverse('athlete-manage-equipment-sale-edit', args=[athlete.pk, payment.pk]),
    })


def _equipment_sale_data(form, user, unit_prices=None):
    selected_equipment = form.selected_equipment()
    if form.errors:
        return None
    if not selected_equipment:
        form.add_error(None, 'En az bir malzeme için adet girin.')
        return None
    unit_prices = unit_prices or {}
    total_amount = sum(
        (unit_prices.get(equipment.pk, equipment.price) * quantity for equipment, quantity, _, _ in selected_equipment),
        Decimal('0.00'),
    )
    sale_items = ', '.join(
        f'{equipment.display_name}{f" ({color} / {size})" if color or size else ""} x{quantity}'
        for equipment, quantity, color, size in selected_equipment
    )
    sale_status = form.cleaned_data['status']
    notes = f'Malzemeler: {sale_items}'
    if form.cleaned_data['notes']:
        notes = f'{notes}\n{form.cleaned_data["notes"]}'
    return {
        'amount': total_amount,
        'items': [
            (equipment, quantity, unit_prices.get(equipment.pk, equipment.price), color, size)
            for equipment, quantity, color, size in selected_equipment
        ],
        'status': sale_status,
        'paid_at': timezone.now() if sale_status == 'paid' else None,
        'collected_by': user if sale_status == 'paid' else None,
        'notes': notes,
    }


def _equipment_sale_quantities(notes):
    quantities = {}
    first_line = (notes or '').splitlines()[0] if notes else ''
    for equipment in Equipment.objects.filter(is_active=True):
        match = re.search(rf'(?:^|,\s*){re.escape(equipment.display_name)}\s+x(\d+)(?:,|$)', first_line.removeprefix('Malzemeler: '))
        if match:
            quantities[equipment.pk] = int(match.group(1))
    return quantities


def _equipment_sale_items(payment):
    sale_items = list(payment.equipment_sale_items.select_related('equipment').all())
    if sale_items:
        return [
            {
                'name': item.equipment.display_name,
                'color': item.selected_color,
                'size': item.selected_size,
                'price': item.unit_price,
                'quantity': item.quantity,
                'total': item.line_total,
            }
            for item in sale_items
        ]

    notes = payment.notes
    first_line = (notes or '').splitlines()[0] if notes else ''
    if not first_line.startswith('Malzemeler: '):
        return []

    items = []
    sale_items = first_line.removeprefix('Malzemeler: ')
    for equipment in Equipment.objects.filter(is_active=True):
        match = re.search(
            rf'(?:^|,\s*){re.escape(equipment.display_name)}\s+x(\d+)(?:,|$)',
            sale_items,
        )
        if match:
            quantity = int(match.group(1))
            items.append({
                'name': equipment.display_name,
                'color': '',
                'size': '',
                'price': equipment.price,
                'quantity': quantity,
                'total': equipment.price * quantity,
            })
    return items


def _equipment_sale_extra_notes(notes):
    lines = (notes or '').splitlines()
    return '\n'.join(lines[1:])


@login_required
def athlete_edit_payment(request, pk, payment_id):
    athlete = get_object_or_404(_athlete_queryset(request), pk=pk)
    payment = get_object_or_404(PaymentRecord, pk=payment_id, athlete=athlete)
    if request.method == 'POST':
        form = AthletePaymentEditForm(request.POST, instance=payment)
        if form.is_valid():
            payment = form.save(commit=False)
            if payment.status == 'paid':
                payment.paid_at = payment.paid_at or timezone.now()
                payment.collected_by = payment.collected_by or request.user
            else:
                payment.paid_at = None
                payment.collected_by = None
            payment.save()
            return _athlete_payment_row_response(request, athlete, payment)
    else:
        form = AthletePaymentEditForm(instance=payment)

    return render(request, 'athlete/partials/athlete_payment_modal.html', {
        'athlete': athlete,
        'period': payment.period,
        'form': form,
        'payment': payment,
        'payment_label': _payment_period_label(payment.period),
        'mode': 'edit',
    })


def _payment_period_label(period):
    year, month = map(int, period.split('-'))
    return f'{MONTH_NAMES[month - 1]} {year}'


def _athlete_payment_row_response(request, athlete, payment):
    from finance.services import get_athlete_fee_for_period

    fee_amount = get_athlete_fee_for_period(athlete, payment.period)
    item = {
        'period': payment.period,
        'label': _payment_period_label(payment.period),
        'amount': payment.amount if payment.payment_type == 'equipment_sale' else fee_amount,
        'payment': payment,
        'paid_amount': (
            payment.amount or fee_amount
            if payment.status == 'paid' and payment.payment_type == 'fee'
            else payment.amount if payment.status == 'paid' else Decimal('0.00')
        ),
        'payment_type': payment.payment_type,
        'payment_type_display': payment.get_payment_type_display(),
        'is_paid': payment.status == 'paid',
        'status': payment.status,
    }
    response = render(request, 'athlete/partials/athlete_payment_row.html', {
        'athlete': athlete,
        'item': item,
    })
    response['HX-Trigger'] = 'closeAthletePaymentModal'
    return response


@login_required
def athlete_toggle_active(request, pk):
    athlete = get_object_or_404(_athlete_queryset(request), pk=pk)
    if request.method == 'GET':
        return render(request, 'athlete/partials/athlete_status_modal.html', {'athlete': athlete})
    if request.method != 'POST':
        return render(request, 'athlete/partials/athlete_status_modal.html', {'athlete': athlete}, status=405)
    athlete.is_active = not athlete.is_active
    athlete.save(update_fields=('is_active',))
    response = render(request, 'athlete/partials/athlete_status.html', {'athlete': athlete})
    response['HX-Trigger'] = 'closeAthleteStatusModal'
    return response


@login_required
def athlete_create(request):
    form = AthleteForm(request.POST or None, request.FILES or None)
    if request.user.is_parent:
        form.fields['parent'].initial = request.user.get_full_name()
        form.fields['parent_phone'].initial = request.user.phone_number
        form.fields['parent_email'].initial = request.user.email
        form.fields['is_active'].disabled = True
    if request.method == 'POST' and form.is_valid():
        athlete = form.save(commit=False)
        if request.user.is_parent:
            athlete.parent = request.user.get_full_name()
            athlete.parent_phone = request.user.phone_number
            athlete.parent_email = request.user.email
            athlete.is_active = False
        athlete.save()
        response = render(request, 'athlete/partials/athlete_table.html', _athlete_context(request))
        response['HX-Trigger'] = 'closeAthleteModal'
        return response
    return render(request, 'athlete/partials/athlete_form_modal.html', {
        'form': form, 'modal_title': 'Yeni sporcu ekle', 'submit_label': 'Sporcuyu kaydet',
    })


@login_required
def athlete_update(request, pk):
    athlete = get_object_or_404(_athlete_queryset(request), pk=pk)
    form = AthleteForm(request.POST or None, request.FILES or None, instance=athlete)
    if request.user.is_parent:
        form.fields['parent'].disabled = True
        form.fields['parent_phone'].disabled = True
        form.fields['parent_email'].disabled = True
        form.fields['is_active'].disabled = True
    if request.method == 'POST' and form.is_valid():
        form.save()
        if request.POST.get('return_to_detail'):
            response = render(request, 'athlete/athlete_detail.html', {'athlete': athlete})
            response['HX-Redirect'] = request.build_absolute_uri(
                reverse('athlete-manage-detail', args=[athlete.pk])
            )
            return response
        response = render(request, 'athlete/partials/athlete_table.html', _athlete_context(request))
        response['HX-Trigger'] = 'closeAthleteModal'
        return response
    return render(request, 'athlete/partials/athlete_form_modal.html', {
        'form': form, 'athlete': athlete, 'modal_title': 'Sporcuyu düzenle',
        'submit_label': 'Değişiklikleri kaydet',
        'return_to_detail': request.GET.get('return_to_detail'),
    })


class AthleteViewSet(viewsets.ModelViewSet):
    serializer_class = AthleteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_club_admin or user.is_coach or user.is_finance:
            return Athlete.objects.all()
        if user.is_parent:
            return Athlete.objects.filter(parent_email=user.email)
        return Athlete.objects.none()

    def perform_create(self, serializer):
        # Veli oluşturuyorsa kayıt pasif ve onay bekliyor.
        if self.request.user.is_parent:
            serializer.save(
                parent=self.request.user.get_full_name(),
                parent_phone=self.request.user.phone_number or '',
                parent_email=self.request.user.email or '',
                is_active=False,
            )
        else:
            # Yönetici ekliyorsa: Doğrudan onaylı ve aktif
            parent_name = self.request.data.get('parent') or self.request.user.get_full_name()
            serializer.save(
                parent=parent_name,
                parent_phone=self.request.data.get('parent_phone') or '',
                parent_email=self.request.data.get('parent_email') or '',
                is_active=True,
            )

    # --- YÖNETİCİ ONAY AKSİYONLARI ---

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def approve(self, request, pk=None):
        """Yöneticinin sporcuyu onaylama endpoint'i: /api/athletes/{id}/approve/"""
        if not (request.user.is_club_admin or request.user.is_coach):
            return Response({'detail': 'Bu işlem için yetkiniz yok.'}, status=status.HTTP_403_FORBIDDEN)
        
        athlete = self.get_object()
        athlete.is_active = True
        athlete.save()
        return Response({'status': 'Sporcu onaylandı ve aktif edildi.'})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def reject(self, request, pk=None):
        """Yöneticinin sporcuyu reddetme endpoint'i: /api/athletes/{id}/reject/"""
        if not (request.user.is_club_admin or request.user.is_coach):
            return Response({'detail': 'Bu işlem için yetkiniz yok.'}, status=status.HTTP_403_FORBIDDEN)
        
        athlete = self.get_object()
        athlete.is_active = False
        athlete.save()
        return Response({'status': 'Sporcu kaydı reddedildi.'})