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
    Belirtilen dönem (örn: '2026-08') için onaylı sporcuların 
    AİDAT ('fee') borç kayıtlarını dinamik kontrol eder ve getirir.
    """
    if not period_str:
        period_str = date.today().strftime('%Y-%m')

    year, month = map(int, period_str.split('-'))
    target_period_date = date(year, month, 1)

    approved_athletes = Athlete.objects.filter(
        status='approved', 
        is_active=True,
        joined_date__lte=target_period_date
    )
    
    # Sadece 'fee' türündeki kayıtların sporcu ID'lerini çekiyoruz
    existing_athlete_ids = set(
        PaymentRecord.objects.filter(
            period=period_str,
            payment_type='fee'
        ).values_list('athlete_id', flat=True)
    )

    new_records = []
    default_due_date = date(year, month, 15)

    for athlete in approved_athletes:
        if athlete.id not in existing_athlete_ids:
            # GÜNCELLEME: Anlık sabit fee yerine o döneme ait dinamik fiyatı çağırıyoruz
            fee = get_athlete_fee_for_period(athlete, period_str)
            
            if fee > 0:
                new_records.append(PaymentRecord(
                    athlete=athlete,
                    payment_type='fee',  # Varsayılan olarak Aidat borcu
                    period=period_str,
                    amount=fee,          # O aydaki geçerli tutar yazılır
                    status='pending',
                    due_date=default_due_date
                ))

    if new_records:
        PaymentRecord.objects.bulk_create(new_records)

    return PaymentRecord.objects.filter(period=period_str).select_related('athlete', 'athlete__parent', 'athlete__team')

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