# athletes/views.py
from datetime import date
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .forms import AthleteForm, AthletePaymentCreateForm, AthletePaymentEditForm
from .models import Athlete
from .serializers import AthleteSerializer
from finance.models import PaymentRecord

MONTH_NAMES = (
    'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
    'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık',
)


def _athlete_queryset(request):
    queryset = Athlete.objects.select_related('team').order_by('-is_active', 'team__name', 'first_name', 'last_name')
    if request.user.is_parent:
        return queryset.filter(parent_email=request.user.email)
    return queryset


def _athlete_context(request):
    query = request.GET.get('q', '').strip()
    has_search = len(query) >= 3
    athletes = _athlete_queryset(request).none()
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
    payments_records = PaymentRecord.objects.filter(
        athlete=athlete,
        payment_type='fee',
    )
    other_payments = PaymentRecord.objects.filter(
        athlete=athlete,
    ).exclude(payment_type='fee')
    other_payment_items = [
        {
            'period': payment.period,
            'label': f'{MONTH_NAMES[int(payment.period[5:]) - 1]} {payment.period[:4]}',
            'amount': payment.amount,
            'payment': payment,
            'paid_amount': payment.amount if payment.status == 'paid' else Decimal('0.00'),
            'payment_type': payment.payment_type,
            'payment_type_display': payment.get_payment_type_display(),
            'is_paid': payment.status == 'paid',
            'status': payment.status,
        }
        for payment in other_payments
    ]


    monthly_payments = []
    period_month = current_month
    displayed_months = 0
    while period_month >= first_month and displayed_months < 10:
        period = period_month.strftime('%Y-%m')
        payments_by_period = payments_records.filter(period=period)
        if not payments_by_period.exists():
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
            for payment in payments_by_period:
                monthly_payments.append({
                    'period': period,
                    'label': f'{MONTH_NAMES[period_month.month - 1]} {period_month.year}',
                    'amount': get_athlete_fee_for_period(athlete, period),
                    'payment': payment,
                    'paid_amount': payment.amount if payment.status == 'paid' else Decimal('0.00'),
                    'payment_type': 'fee',
                    'payment_type_display': payment.get_payment_type_display(),
                    'is_paid': payment.status == 'paid',
                    'status': payment.status,
                })
        displayed_months += 1
        if period_month.month == 1:
            period_month = period_month.replace(year=period_month.year - 1, month=12)
        else:
            period_month = period_month.replace(month=period_month.month - 1)

    return render(request, 'athlete/athlete_detail.html', {
        'athlete': athlete,
        'monthly_payments': monthly_payments,
        'other_payments': other_payment_items,
    })


@login_required
def athlete_make_payment(request, pk, period):
    from finance.services import get_athlete_fee_for_period

    athlete = get_object_or_404(_athlete_queryset(request), pk=pk)
    try:
        year, month = map(int, period.split('-'))
        period_date = date(year, month, 1)
    except (TypeError, ValueError):
        return render(request, 'athlete/partials/athlete_payment_modal.html', {}, status=400)

    payment = PaymentRecord.objects.filter(
        athlete=athlete,
        period=period,
        payment_type='fee',
    ).first()
    amount = payment.amount if payment else get_athlete_fee_for_period(athlete, period)
    item = {
        'period': period,
        'label': f'{MONTH_NAMES[month - 1]} {year}',
        'amount': amount,
        'payment': payment,
        'paid_amount': payment.amount if payment and payment.status == 'paid' else Decimal('0.00'),
        'payment_type': payment.payment_type if payment else 'fee',
        'payment_type_display': payment.get_payment_type_display() if payment else 'Aidat',
        'is_paid': payment is not None and payment.status == 'paid',
        'status': payment.status if payment else 'pending',
    }

    if request.method == 'GET':
        return render(request, 'athlete/partials/athlete_payment_modal.html', {
            'athlete': athlete,
            'item': item,
        })
    if request.method != 'POST':
        return render(request, 'athlete/partials/athlete_payment_modal.html', {
            'athlete': athlete,
            'item': item,
        }, status=405)

    payment, _ = PaymentRecord.objects.get_or_create(
        athlete=athlete,
        period=period,
        payment_type='fee',
        defaults={
            'amount': amount,
            'payment_method': 'cash',
            'status': 'pending',
            'due_date': period_date.replace(day=15),
        },
    )
    if not payment.amount:
        payment.amount = amount
    payment.status = 'paid'
    payment.paid_at = timezone.now()
    payment.collected_by = request.user
    payment.save(update_fields=('amount', 'status', 'paid_at', 'collected_by'))

    item['payment'] = payment
    item['is_paid'] = True
    item['status'] = payment.status
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

    return render(request, 'athlete/partials/athlete_payment_create_modal.html', {
        'athlete': athlete,
        'form': form,
    })


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

    return render(request, 'athlete/partials/athlete_payment_edit_modal.html', {
        'athlete': athlete,
        'period': payment.period,
        'form': form,
        'payment': payment,
        'payment_label': _payment_period_label(payment.period),
    })


def _payment_period_label(period):
    year, month = map(int, period.split('-'))
    return f'{MONTH_NAMES[month - 1]} {year}'


def _athlete_payment_row_response(request, athlete, payment):
    from finance.services import get_athlete_fee_for_period

    item = {
        'period': payment.period,
        'label': _payment_period_label(payment.period),
        'amount': get_athlete_fee_for_period(athlete, payment.period),
        'payment': payment,
        'paid_amount': payment.amount if payment.status == 'paid' else Decimal('0.00'),
        'payment_type': payment.payment_type,
        'payment_type_display': payment.get_payment_type_display(),
        'is_paid': payment.status == 'paid',
        'status': payment.status,
    }
    response = render(request, 'athlete/partials/athlete_payment_row.html', {
        'athlete': athlete,
        'item': item,
    })
    response['HX-Trigger'] = 'closeAthletePaymentEditModal'
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