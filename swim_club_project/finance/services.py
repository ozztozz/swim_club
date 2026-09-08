# finance/services.py
from datetime import date
from django.db.models import Sum
from athletes.models import Athlete
from decimal import Decimal
from django.db.models import Q
from .models import TeamFeeHistory, PaymentRecord, Expense

def get_athlete_fee_for_period(athlete, period_str):
    """
    Belirtilen dönem (örn: '2026-08') tarihindeki geçerli aidat tutarını belirler.
    Öncelik Sırası:
    1. Sporcunun güncel özel ücreti
    2. Takıma özel tanımlanmış tarihli fiyat geçmişi
    3. Geçerli ücret bulunamazsa sıfır
    """
    year, month = map(int, period_str.split('-'))
    target_date = date(year, month, 1)  # İlgili ayın 1. günü itibarıyla geçerli fiyat

    if athlete.custom_fee is not None:
        return athlete.custom_fee

    # 3. Takımın o tarihte geçerli fiyatı var mı?
    if athlete.team:
        team_fee = TeamFeeHistory.objects.filter(
            team=athlete.team,
            start_date__lte=target_date
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=target_date)
        ).first()

        if team_fee:
            return team_fee.monthly_fee

    return Decimal('0.00')

def get_or_create_monthly_payments(period_str=None):
    """
    Belirtilen dönem (örn: '2026-08') için onaylı sporcuları 
    dönem aidatı ile birlikte döndürür.
    """
    if not period_str:
        period_str = date.today().strftime('%Y-%m')

    year, month = map(int, period_str.split('-'))
    target_period_date = date(year, month, 1)

    active_athletes = list(Athlete.objects.filter(
        is_active=True,
        joined_date__lte=target_period_date
    ).select_related('team'))

    default_due_date = date(year, month, 15)

    existing_payments = PaymentRecord.objects.filter(
        period=period_str,
        payment_type='fee',
        athlete__in=active_athletes
    ).select_related('athlete', 'athlete__team')
    existing_payments_by_athlete_id = {
        payment.athlete_id: payment for payment in existing_payments
    }

    annotated_athletes = []

    for athlete in active_athletes:
        fee = get_athlete_fee_for_period(athlete, period_str)

        if fee <= 0:
            continue

        payment_record = existing_payments_by_athlete_id.get(athlete.id)
        athlete.period = period_str
        athlete.amount = fee
        athlete.due_date = payment_record.due_date if payment_record else default_due_date
        athlete.payment_record = payment_record
        athlete.payment_status = payment_record.status if payment_record else 'pending'
        athlete.paid_at = payment_record.paid_at if payment_record else None
        athlete.collected_by = payment_record.collected_by if payment_record else None
        annotated_athletes.append(athlete)

    return annotated_athletes

def get_financial_summary(period_str=None):
    """
    Seçilen döneme ait Tahsil Edilen Aidat, Bekleyen Alacak, 
    Toplam Harcama ve Net Bakiye özetini hesaplar.
    """
    if not period_str:
        period_str = date.today().strftime('%Y-%m')

    monthly_payments = get_or_create_monthly_payments(period_str)

    # Tahsilat yalnızca aktif sporcuların gerçek ödeme kayıtlarından hesaplanır.
    total_income = PaymentRecord.objects.filter(
        period=period_str,
        payment_type='fee',
        status='paid',
        athlete__is_active=True,
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    pending_income = sum(
        (payment.amount for payment in monthly_payments if payment.payment_status != 'paid'),
        Decimal('0.00'),
    )

    # Gerçekleşen harcamalar
    total_expense = Expense.objects.filter(
        period=period_str
    ).aggregate(total=Sum('amount'))['total'] or 0.00

    net_balance = float(total_income) - float(total_expense)

    return {
        'period': period_str,
        'total_income': total_income,
        'pending_income': pending_income,
        'total_expense': total_expense,
        'net_balance': net_balance,
    }