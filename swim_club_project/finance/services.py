# finance/services.py
from datetime import date
from django.db.models import Sum
from athletes.models import Athlete
from .models import PaymentRecord, Expense

def get_or_create_monthly_payments(period_str=None):
    """
    Belirtilen dönem (örn: '2026-08') için onaylı sporcuların 
    aidat borç kayıtlarını dinamik kontrol eder ve getirir.
    """
    if not period_str:
        period_str = date.today().strftime('%Y-%m')

    approved_athletes = Athlete.objects.filter(status='approved')
    existing_athlete_ids = set(
        PaymentRecord.objects.filter(period=period_str).values_list('athlete_id', flat=True)
    )

    new_records = []
    year, month = map(int, period_str.split('-'))
    default_due_date = date(year, month, 15)

    for athlete in approved_athletes:
        fee = athlete.current_monthly_fee
        if athlete.id not in existing_athlete_ids and fee > 0:
            new_records.append(PaymentRecord(
                athlete=athlete,
                period=period_str,
                amount=fee,
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