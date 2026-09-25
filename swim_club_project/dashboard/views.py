# dashboard/views.py

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db.models.aggregates import Count
from django.shortcuts import render
from django.utils import timezone

from finance.models import Expense, PaymentRecord, TeamFeeHistory
from athletes.models import Athlete
from teams.models import Team
from users.models import User

def _get_teams_subscription_price(period=None):

    if period:
        year=int(period.split("-")[0])
        month=int(period.split("-")[1])
        date_control = timezone.localdate().replace(year=year, month=month, day=1)
    else:
        date_control = timezone.localdate().replace(day=1)

    teams_subscription_price = TeamFeeHistory.objects.filter(start_date__lte=date_control, 
                                                             end_date__gte=date_control).values("team_id", "monthly_fee")
    teams_subscription_price = {item["team_id"]: item["monthly_fee"] for item in teams_subscription_price}

    return teams_subscription_price



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
    active_athletes = Athlete.objects.filter(is_active=True).all()
    for athlete in active_athletes:
        if athlete.custom_fee and athlete.custom_fee > 0:
            expected_amount = athlete.custom_fee
        else:
            expected_amount = teams_subscription_price.get(athlete.team_id, 0)
        athlete_payment = next((item for item in athlete_payments if item["athlete"] == athlete.id), None)
        athlete_payment = athlete_payment["total_amount"] if athlete_payment else 0

        if athlete_payment >= expected_amount:
            payment_counts["paid"] = payment_counts.get("paid", 0) + 1
        else:
            payment_counts["pending"] = payment_counts.get("pending", 0) + 1

    

    


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


@login_required(login_url="user-login")
def dashboard(request):
    """
    Tüm kullanıcıların giriş sonrası geldiği merkezi dashboard.
    Dashboard içeriği kullanıcının rolüne göre belirlenir.
    """

    role = request.user.role

    context = {
        "dashboard_role": role,
    }

    if role == User.Role.ADMIN:
        template = "dashboard/admin.html"

        context.update(
            _get_admin_dashboard_context()
        )

    elif role == User.Role.COACH:
        template = "dashboard/coach.html"

    elif role == User.Role.FINANCE:
        template = "dashboard/finance.html"

    elif role == User.Role.PARENT:
        template = "dashboard/parent.html"

    else:
        template = "dashboard/unknown.html"

    return render(
        request,
        template,
        context,
    )

