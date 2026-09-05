# finance/services.py
from datetime import date
from django.db.models import Sum
from athletes.models import Athlete
from decimal import Decimal
from django.db.models import Q
from .models import AthleteFeeHistory, TeamFeeHistory,PaymentRecord, Expense

def get_athlete_fee_for_period(athlete, period_str):
    """
    Belirtilen dönem (örn: '2026-08') tarihindeki geçerli aidat tutarını belirler.
    Öncelik Sırası:
    1. Sporcuya özel tanımlanmış tarihli fiyat geçmişi
    2. Takıma özel tanımlanmış tarihli fiyat geçmişi
    3. Sporcunun üzerindeki anlık 'current_monthly_fee' varsayılan değeri
    """
    year, month = map(int, period_str.split('-'))
    target_date = date(year, month, 1)  # İlgili ayın 1. günü itibarıyla geçerli fiyat

    # 1. Sporcuya özel geçerli fiyat var mı?
    athlete_fee = AthleteFeeHistory.objects.filter(
        athlete=athlete,
        start_date__lte=target_date
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=target_date)
    ).first()

    if athlete_fee:
        return athlete_fee.monthly_fee

    # 2. Takımın o tarihte geçerli fiyatı var mı?
    if athlete.team:
        team_fee = TeamFeeHistory.objects.filter(
            team=athlete.team,
            start_date__lte=target_date
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=target_date)
        ).first()

        if team_fee:
            return team_fee.monthly_fee

    # 3. Geçmiş kaydı bulunamadıysa varsayılan alan
    return athlete.current_monthly_fee or Decimal('0.00')

def get_or_create_monthly_payments(period_str=None):
    """
    Belirtilen dönem (örn: '2026-08') için onaylı sporcuları 
    dönem aidatı ile birlikte döndürür.
    """
    if not period_str:
        period_str = date.today().strftime('%Y-%m')

    year, month = map(int, period_str.split('-'))
    target_period_date = date(year, month, 1)

    approved_athletes = list(Athlete.objects.filter(
        status='approved', 
        is_active=True,
        joined_date__lte=target_period_date
    ).select_related('team'))

    default_due_date = date(year, month, 15)

    existing_payments = PaymentRecord.objects.filter(
        period=period_str,
        payment_type='fee',
        athlete__in=approved_athletes
    ).select_related('athlete', 'athlete__team')
    existing_payments_by_athlete_id = {
        payment.athlete_id: payment for payment in existing_payments
    }

    annotated_athletes = []

    for athlete in approved_athletes:
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

    # Tahsil edilen aidatlar
    total_income = PaymentRecord.objects.filter(
        period=period_str, 
        status='paid'
    ).aggregate(total=Sum('amount'))['total'] or 0.00

    # Bekleyen / Gecikmiş aidat alacakları
    pending_income = PaymentRecord.objects.filter(
        period=period_str, 
        status='pending'
    ).aggregate(total=Sum('amount'))['total'] or 0.00

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