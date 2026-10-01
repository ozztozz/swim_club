from datetime import datetime

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from datetime import date
from django.db.models import Sum, Count,Q
from teams.models import Team
from finance.models import PaymentRecord, TeamFeeHistory,Expense
from django.utils import timezone
from athletes.models import Athlete


def _get_teams_subscription_price(period=None):
    if period:
        year, month = map(int, period.split("-"))
        date_control = timezone.localdate().replace(
            year=year,
            month=month,
            day=1
        )
    else:
        date_control = timezone.localdate().replace(day=1)

    return {
        row["team_id"]: row["monthly_fee"]
        for row in TeamFeeHistory.objects.filter(
            start_date__lte=date_control,
        ).filter(
            Q(end_date__gte=date_control) |
            Q(end_date__isnull=True)
        ).values(
            "team_id",
            "monthly_fee"
        )
    }

def _get_admin_dashboard_context():
    """
    Admin dashboard için gerekli finansal ve operasyonel verileri hazırlar.
    financial_summary.total_income
    financial_summary.total_expense
    financial_summary.pending_income
    financial_summary.net_balance
    payment_counts.paid
    payment_counts.pending
    """

    today = timezone.localdate()
    current_period = today.strftime("%Y-%m")
    financial_summary = {}
    payment_counts = {}

    # =========================================================
    # TAHSİLATLAR
    # =========================================================

    payment_records_total = (
        PaymentRecord.objects
        .filter(
            period=current_period,
            status="paid",
        )

    )

    total_income= payment_records_total.filter(
      
    ).aggregate(
        total=Sum("amount")
    )["total"] or 0


    # =========================================================
    # HARCAMALAR
    # =========================================================

    total_expense = (
        Expense.objects
        .filter(
            period=current_period,
            is_active=True,
            status="paid",
        )
        .aggregate(
            total=Sum("amount")
        )["total"]
        or 0
    )

    # =========================================================
    # NET DURUM
    # =========================================================

    net_balance = (
        total_income - total_expense
    )
    # =========================================================
    # SON HARCAMALAR
    # =========================================================

    

    # =========================================================
    # BEKLEYEN TAHSİLAT SAYISI
    # =========================================================

    teams_subscription_price = _get_teams_subscription_price(period=current_period)
    athlete_payments = payment_records_total.filter(
        payment_type="fee"
    ).values("athlete").annotate(total_amount=Sum("amount"))
    active_athletes = Athlete.objects.filter(is_active=True).all().values("id", "custom_fee", "team_id")

    for payment in athlete_payments:
        athlete=active_athletes.get(id=payment["athlete"])
        if athlete["custom_fee"] and athlete["custom_fee"] > 0:
            expected_amount = athlete["custom_fee"]
        else:
            expected_amount = teams_subscription_price.get(athlete["team_id"], 0)
        athlete_payment = next((item for item in athlete_payments if item["athlete"] == athlete["id"]), None)
        athlete_payment = athlete_payment["total_amount"] if athlete_payment else 0

        if athlete_payment >= expected_amount:
            payment_counts["paid"] = payment_counts.get("paid", 0) + 1
        else:
            payment_counts["pending"] = payment_counts.get("pending", 0) + 1
    nan_paid_athletes = active_athletes.exclude(id__in=[payment["athlete"] for payment in athlete_payments])

    payment_counts["pending"] = payment_counts.get("pending", 0) + nan_paid_athletes.count()
    

    


    # =========================================================
    # GECİKMİŞ TAHSİLAT SAYISI
    # =========================================================

  

    return {
        "current_period": current_period,

        # Finansal özet
        "financial_summary": {
            "total_income": total_income,
            "total_expense": total_expense,
            
            "net_balance": net_balance,
        },
        "payment_counts": payment_counts,

    }



@login_required
def payment_list(request,payment_status):

    teams_subscription_price = _get_teams_subscription_price()

    period = request.GET.get('period', date.today().strftime('%Y-%m'))
    team_id = request.GET.get('team', '')
    payment_status = payment_status
    period_start = datetime.strptime(period + "-01", "%Y-%m-%d").date()
    monthly_payments = PaymentRecord.objects.filter(period=period,status='paid')
    if team_id:
        monthly_payments = monthly_payments.filter(athlete__team_id=team_id)
   # Toplam ödemeleri ve sporcu sayısını hesaplamak için her sporcunun toplam ödemesini alıyoruz.
    athletes_monthly_total = monthly_payments.filter(payment_type='fee').values('athlete',
                                                                                'athlete__team__name',
                                                                                'athlete__custom_fee',
                                                                                'athlete__team',
                                                                                'athlete__first_name',
                                                                                'athlete__last_name').annotate(
                                                                                    athlete_total_amount=Sum('amount'))
    
    
    # Her sporcunun toplam ödemesini ve detaylarını bir sözlükte saklıyoruz.
    athlete_payments_list = []
    if payment_status == 'paid':
        for athlete_total in athletes_monthly_total:
            athlete_payments = {}
            athlete_payments['athlete_id'] = athlete_total['athlete']
            athlete_payments['total_payment'] = athlete_total['athlete_total_amount']
            athlete_payments['last_payment_date'] = monthly_payments.filter(athlete=athlete_total['athlete']).order_by('-paid_at').first().paid_at if monthly_payments.filter(athlete=athlete_total['athlete']).exists() else None
            athlete_payments['team'] = athlete_total['athlete__team__name']
            athlete_payments['name'] = f"{athlete_total['athlete__first_name']} {athlete_total['athlete__last_name']}"
            team_subscription_price = teams_subscription_price.get(athlete_total['athlete__team'], 0)
            if athlete_total['athlete__custom_fee'] is not None:
                team_subscription_price = athlete_total['athlete__custom_fee']
            amount_due = max(team_subscription_price - athlete_payments['total_payment'], 0)
            athlete_payments['amount_due'] = amount_due
            athlete_payments['team_subscription_price'] = team_subscription_price
            for payment in monthly_payments.filter(athlete=athlete_total['athlete']).order_by('-paid_at'):
                        
                athlete_payments.setdefault('details', []).append({
                    'amount': payment.amount,
                    'date': payment.paid_at,
                    'payment_type': payment.get_payment_type_display(),
                    
                })
            athlete_payments_list.append(athlete_payments)
        athlete_payments_list.sort(key=lambda x: x['last_payment_date'] , reverse=True)
        

    else:
        active_athletes = Athlete.objects.filter(is_active=True, joined_date__lte=period_start)
        if team_id:
            active_athletes = active_athletes.filter(team_id=team_id)
        for athlete in active_athletes:
            athlete_payments = {}
            athlete_monthly_total=athletes_monthly_total.filter(athlete=athlete).order_by('athlete_total_amount').first()
            athlete_payments['athlete_id'] = athlete.id

            athlete_payments['total_payment'] = athlete_monthly_total['athlete_total_amount'] if athlete_monthly_total is not None else 0
      
            athlete_payments['name'] = f"{athlete.first_name} {athlete.last_name}"
            team_subscription_price = teams_subscription_price.get(athlete.team_id, 0)
            if athlete.custom_fee is not None:
                team_subscription_price = athlete.custom_fee
            amount_due = max(team_subscription_price - athlete_payments['total_payment'], 0)
            athlete_payments['amount_due'] = amount_due
            athlete_payments['team_subscription_price'] = team_subscription_price
            if amount_due > 0:
                athlete_payments_list.append(athlete_payments)
    teams = Team.objects.filter(is_active=True)
    team = Team.objects.filter(id=team_id).first() if team_id else None
    total_amount = athletes_monthly_total.aggregate(total=Sum('athlete_total_amount'))['total'] or 0
    athlete_count = athletes_monthly_total.aggregate(count=Count('athlete', distinct=True))['count'] or 0
    context = {
        'period': period,
        'selected_team': team_id,
        'athlete_payments_list': athlete_payments_list,
        'total_amount': total_amount,
        'athlete_count': athlete_count,
        'teams': teams,
        'team': team,
    }
    return render(request, 'dashboard/payment_status_list.html', context)

  

    return render(request, 'dashboard/payment_status_list.html', {
        'athlete_payments_list': athlete_payments_list,
        'period': period,
        'team_id': team_id,
        'team': team,
        'total_amount': total_amount,
        'athlete_count': athlete_count,
        'status_label': 'Ödeyen sporcular',
        'teams': teams,
    })

