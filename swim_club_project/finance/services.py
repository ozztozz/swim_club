# finance/services.py
from datetime import date, datetime, timezone
from django.db.models import Sum
from athletes.models import Athlete
from decimal import Decimal
from django.db.models import Q
from .models import EquipmentStockMovement, TeamFeeHistory, PaymentRecord, Expense


def get_equipment_central_stock(equipment):
    movements = EquipmentStockMovement.objects.filter(equipment=equipment)
    stock_in = movements.filter(movement_type='stock_in').aggregate(total=Sum('quantity'))['total'] or 0
    returns = movements.filter(movement_type='coach_return').aggregate(total=Sum('quantity'))['total'] or 0
    transfers = movements.filter(movement_type='coach_transfer').aggregate(total=Sum('quantity'))['total'] or 0
    direct_distributions = movements.filter(
        movement_type='athlete_distribution',
        coach__isnull=True,
    ).aggregate(total=Sum('quantity'))['total'] or 0
    return stock_in + returns - transfers - direct_distributions


def get_equipment_coach_stock(equipment, coach):
    movements = EquipmentStockMovement.objects.filter(equipment=equipment, coach=coach)
    received = movements.filter(movement_type='coach_transfer').aggregate(total=Sum('quantity'))['total'] or 0
    distributed = movements.filter(movement_type='athlete_distribution').aggregate(total=Sum('quantity'))['total'] or 0
    returned = movements.filter(movement_type='coach_return').aggregate(total=Sum('quantity'))['total'] or 0
    return received - distributed - returned

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
    Belirtilen dönem (örn: '2026-08') için ödeme durumlarını hesaplar ve döndürür:
    
    1. Sorgu (Mevcut Ödemeler): Bu dönemde 'paid' (ödendi) durumundaki ödeme kayıtları.
    2. Sorgu (Bekleyenler): İlk listede olmayan ancak bu dönem için ödeme yapması gereken aktif sporcular.
    
    Sonrasında bu iki liste birleştirilir.
    """
    if not period_str:
        period_str = date.today().strftime('%Y-%m')

    year, month = map(int, period_str.split('-'))
    default_due_date = date(year, month, 15)

    # 1. SORGU: Bu dönemde 'paid' (ödendi) olan mevcut ödeme kayıtları
    paid_payments = PaymentRecord.objects.filter(
        period=period_str,
        status='paid'
    ).select_related('athlete', 'athlete__team')

    paid_athletes = []
    paid_athlete_ids = set()

    for payment in paid_payments:
        if not payment.athlete_id:
            continue
        athlete = payment.athlete
        paid_athlete_ids.add(athlete.id)

        expected_fee = Decimal(get_athlete_fee_for_period(athlete, period_str))
        payment_amount = Decimal(payment.amount)

        athlete.period = period_str
        athlete.fee_type = payment.payment_type
        athlete.fee_type_display = payment.get_payment_type_display()
        athlete.amount = expected_fee if expected_fee > 0 else payment_amount
        athlete.paid_amount = payment_amount
        athlete.paid_by = athlete.get_full_name()
        athlete.due_date = payment.due_date
        athlete.payment_record = payment
        athlete.payment_status = 'paid'
        athlete.paid_at = payment.paid_at
        athlete.collected_by = payment.collected_by
        paid_athletes.append(athlete)

    # 2. SORGU: Önceki listede olmayan ancak bu dönem için ödemesi gereken aktif sporcular
    unpaid_athletes_qs = Athlete.objects.filter(
        is_active=True
    ).exclude(
        id__in=paid_athlete_ids
    ).select_related('team')

    # Bu sporcular için varsa mevcut bekleyen ödeme kayıtları
    pending_payments = PaymentRecord.objects.filter(
        period=period_str,
        athlete_id__in=[a.id for a in unpaid_athletes_qs]
    ).select_related('athlete', 'athlete__team')
    pending_payments_by_athlete_id = {
        p.athlete_id: p for p in pending_payments if p.athlete_id
    }

    unpaid_athletes = []
    for athlete in unpaid_athletes_qs:
        payment_record = pending_payments_by_athlete_id.get(athlete.id)
        fee = Decimal(get_athlete_fee_for_period(athlete, period_str))
        if fee <= 0 and payment_record and payment_record.amount > 0:
            fee = Decimal(payment_record.amount)

        if fee <= 0:
            continue

        athlete.period = period_str
        athlete.fee_type = payment_record.payment_type if payment_record else 'fee'
        athlete.fee_type_display = payment_record.get_payment_type_display() if payment_record else 'Aidat'
        athlete.amount = fee
        athlete.paid_amount = Decimal('0.00')
        athlete.paid_by = athlete.get_full_name()
        athlete.due_date = payment_record.due_date if payment_record else default_due_date
        athlete.payment_record = payment_record
        athlete.payment_status = payment_record.status if payment_record else 'pending'
        athlete.paid_at = payment_record.paid_at if payment_record else None
        athlete.collected_by = payment_record.collected_by if payment_record else None
        unpaid_athletes.append(athlete)

    # İki sorgunun birleştirilmesi
    return paid_athletes + unpaid_athletes

def get_financial_summary(period_str=None, monthly_payments=None):
    """
    Seçilen döneme ait Tahsil Edilen Aidat, Bekleyen Alacak, 
    Toplam Harcama ve Net Bakiye özetini hesaplar.
    """
    if not period_str:
        period_str = date.today().strftime('%Y-%m')

    if monthly_payments is None:
        monthly_payments = get_or_create_monthly_payments(period_str)

    # Tahsilat yalnızca aktif sporcuların gerçek ödeme kayıtlarından hesaplanır.
    total_income = PaymentRecord.objects.filter(
        period=period_str,
        status='paid',
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    pending_income = sum(
        (payment.amount for payment in monthly_payments if payment.payment_status != 'paid'),
        Decimal('0.00'),
    )

    # Gerçekleşen harcamalar
    total_expense = Expense.objects.filter(
        period=period_str,
        is_active=True,
        status__in=('paid', 'pending'),
    ).aggregate(total=Sum('amount'))['total'] or 0.00

    net_balance = float(total_income) - float(total_expense)

    return {
        'period': period_str,
        'total_income': total_income,
        'pending_income': pending_income,
        'total_expense': total_expense,
        'net_balance': net_balance,
    }