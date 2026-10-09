
from io import BytesIO

from django.db.models import Sum, Q
from openpyxl import Workbook
from openpyxl.styles import Font
from teams.models import Team
from finance.models import PaymentRecord, TeamFeeHistory, Expense, ExpenseCategory
from finance.views import (
    get_expense_summary,
    get_expenses_for_period,
    get_regular_expense_summary,
)
from django.utils import timezone
from athletes.models import Athlete
from datetime import datetime

from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from datetime import date


def _normalize_period(period):
    fallback_period = timezone.localdate().strftime("%Y-%m")
    if not period:
        return fallback_period

    try:
        return datetime.strptime(period, "%Y-%m").strftime("%Y-%m")
    except (TypeError, ValueError):
        return fallback_period

def _get_active_athletes(period):
    period = _normalize_period(period)
    period_start = datetime.strptime(period + "-01", "%Y-%m-%d").date()
    active_athletes = Athlete.objects.filter(
        is_active=True, joined_date__lte=period_start
    )
    return active_athletes


def _get_teams_subscription_price(period=None):
    period = _normalize_period(period)
    year, month = map(int, period.split("-"))
    date_control = timezone.localdate().replace(year=year, month=month, day=1)

    return {
                row["team_id"]: row["monthly_fee"]
                for row in TeamFeeHistory.objects.filter(
                    start_date__lte=date_control,
                )
                .filter(Q(end_date__gte=date_control) | Q(end_date__isnull=True))
                .values("team_id", "monthly_fee")
            }


def _get_financial_context(current_period, payment_records_total):
    total_income = (
        payment_records_total.filter().aggregate(total=Sum("amount"))["total"] or 0
    )

    # =========================================================
    # HARCAMALAR
    # =========================================================
    expense_totals = Expense.objects.filter(
    period=current_period,
    is_active=True,
    ).aggregate(
        paid=Sum("amount", filter=Q(status="paid")),
        pending=Sum("amount", filter=Q(status="pending")),
    )

    total_expense = expense_totals["paid"] or 0
    pending_expense = expense_totals["pending"] or 0

    net_balance = total_income - total_expense

    return {
        "financial_summary": {
            "total_income": total_income,
            "total_expense": total_expense,
            "pending_expense": pending_expense,
            "net_balance": net_balance,
        },
    }


def _period_label(period):
    month_names = (
        "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
        "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
    )
    year, month = period.split("-")
    return f"{month_names[int(month) - 1]} {year}"


def _get_period_financial_summary():
    collected_by_period = {
        row["period"]: row["total"] or 0
        for row in PaymentRecord.objects.filter(status="paid")
        .values("period")
        .annotate(total=Sum("amount"))
    }
    expense_by_period = {
        row["period"]: row
        for row in Expense.objects.filter(
            is_active=True,
            status__in=("paid", "pending"),
        )
        .values("period")
        .annotate(
            paid=Sum("amount", filter=Q(status="paid")),
            pending=Sum("amount", filter=Q(status="pending")),
        )
    }

    periods = sorted(
        set(collected_by_period) | set(expense_by_period),
        reverse=True,
    )
    rows = []
    totals = {
        "collected": 0,
        "paid": 0,
        "pending": 0,
    }

    for period in periods:
        expenses = expense_by_period.get(period, {})
        collected = collected_by_period.get(period, 0)
        paid = expenses.get("paid") or 0
        pending = expenses.get("pending") or 0
        net = collected - paid
        totals["collected"] += collected
        totals["paid"] += paid
        totals["pending"] += pending
        rows.append({
            "period": period,
            "label": _period_label(period),
            "collected": collected,
            "paid": paid,
            "pending": pending,
            "net": net,
            "net_class": "ui-text-success" if net >= 0 else "ui-text-danger",
            "net_prefix": "+" if net >= 0 else "",
        })

    totals["net"] = totals["collected"] - totals["paid"]
    totals["net_class"] = "ui-text-success" if totals["net"] >= 0 else "ui-text-danger"
    totals["net_prefix"] = "+" if totals["net"] >= 0 else ""
    return {
        "period_financial_rows": rows,
        "period_financial_totals": totals,
    }


def _get_payment_counts(current_period, payment_records_total):
    payment_counts = {}

    teams_subscription_price = _get_teams_subscription_price(period=current_period)
    athlete_payments = (
        payment_records_total.filter(payment_type="fee")
        .values("athlete")
        .annotate(total_amount=Sum("amount"))
    )
    active_athletes = {
        athlete["id"]: athlete
        for athlete in _get_active_athletes(
            period=current_period
        ).values("id", "custom_fee", "team_id")
    }

    for payment in athlete_payments:
        athlete = active_athletes.get(payment["athlete"])
        if athlete is None:
            continue
        if athlete["custom_fee"] and athlete["custom_fee"] > 0:
            expected_amount = athlete["custom_fee"]
        else:
            expected_amount = teams_subscription_price.get(athlete["team_id"], 0)
        athlete_payment = next(
            (item for item in athlete_payments if item["athlete"] == athlete["id"]),
            None,
        )
        athlete_payment = athlete_payment["total_amount"] if athlete_payment else 0

        if athlete_payment >= expected_amount:
            payment_counts["paid"] = payment_counts.get("paid", 0) + 1

        else:
            payment_counts["pending"] = payment_counts.get("pending", 0) + 1
    paid_athlete_ids = {payment["athlete"] for payment in athlete_payments}
    unpaid_athlete_count = len(set(active_athletes) - paid_athlete_ids)

    payment_counts["pending"] = (
        payment_counts.get("pending", 0) + unpaid_athlete_count
    )

    return {"payment_counts": payment_counts}


def _get_admin_dashboard_context(period=None):
    """Admin dashboard için finans ve ödeme context'ini birleştirir."""

    current_period = _normalize_period(period)
    payment_records_total = PaymentRecord.objects.filter(
        period=current_period,
        status="paid",
    )

    context = {
        "current_period": current_period,
    }
    context.update(_get_financial_context(current_period, payment_records_total))
    context.update(_get_payment_counts(current_period, payment_records_total))
    context.update(_get_period_financial_summary())
    return context


@login_required
def payment_list(request, payment_status):

    teams_subscription_price = _get_teams_subscription_price()

    period = _normalize_period(request.GET.get("period"))
    team_id = request.GET.get("team", "")
    payment_status = payment_status
    monthly_payments = PaymentRecord.objects.filter(period=period, status="paid")
    if team_id:
        monthly_payments = monthly_payments.filter(athlete__team_id=team_id)
    # Toplam ödemeleri ve sporcu sayısını hesaplamak için her sporcunun toplam ödemesini alıyoruz.
    athletes_monthly_total = (
        monthly_payments.filter(payment_type="fee")
        .values(
            "athlete",
            "athlete__team__name",
            "athlete__custom_fee",
            "athlete__team",
            "athlete__first_name",
            "athlete__last_name",
        )
        .annotate(athlete_total_amount=Sum("amount"))
    )

    # Her sporcunun toplam ödemesini ve detaylarını bir sözlükte saklıyoruz.
    athlete_payments_list = []
    if payment_status == "paid":
        for athlete_total in athletes_monthly_total:
            athlete_payments = {}
            athlete_payments["athlete_id"] = athlete_total["athlete"]
            athlete_payments["total_payment"] = athlete_total["athlete_total_amount"]
            athlete_payments["last_payment_date"] = (
                monthly_payments.filter(athlete=athlete_total["athlete"])
                .order_by("-paid_at")
                .first()
                .paid_at
                if monthly_payments.filter(athlete=athlete_total["athlete"]).exists()
                else None
            )
            athlete_payments["team"] = athlete_total["athlete__team__name"]
            athlete_payments[
                "name"
            ] = f"{athlete_total['athlete__first_name']} {athlete_total['athlete__last_name']}"
            team_subscription_price = teams_subscription_price.get(
                athlete_total["athlete__team"], 0
            )
            if athlete_total["athlete__custom_fee"] is not None:
                team_subscription_price = athlete_total["athlete__custom_fee"]
            amount_due = max(
                team_subscription_price - athlete_payments["total_payment"], 0
            )
            athlete_payments["amount_due"] = amount_due
            athlete_payments["team_subscription_price"] = team_subscription_price
            for payment in monthly_payments.filter(
                athlete=athlete_total["athlete"]
            ).order_by("-paid_at"):

                athlete_payments.setdefault("details", []).append(
                    {
                        "amount": payment.amount,
                        "date": payment.paid_at,
                        "payment_type": payment.get_payment_type_display(),
                    }
                )
            athlete_payments_list.append(athlete_payments)
        athlete_payments_list.sort(key=lambda x: x["last_payment_date"], reverse=True)
        total_amount = (
            athletes_monthly_total.aggregate(total=Sum("athlete_total_amount"))["total"]
            or 0
        )

    else:
        active_athletes = _get_active_athletes(period)
        if team_id:
            active_athletes = active_athletes.filter(team_id=team_id)
        for athlete in active_athletes:
            athlete_payments = {}
            athlete_monthly_total = (
                athletes_monthly_total.filter(athlete=athlete)
                .order_by("athlete_total_amount")
                .first()
            )
            athlete_payments["athlete_id"] = athlete.id
            athlete_payments["regular_payment_day"] = date.today().replace(day=athlete.regular_payment_day if athlete.regular_payment_day is not None else 1)
            athlete_payments["is_overdue"] = (
                athlete_payments["regular_payment_day"] < date.today()
            )
            athlete_payments["team"] = athlete.team if athlete.team is not None else None
            if athlete.team is None:
                athlete_payments["team"] = None
            else:
                athlete_payments["team"] = athlete.team
            athlete_payments["total_payment"] = (
                athlete_monthly_total["athlete_total_amount"]
                if athlete_monthly_total is not None
                else 0
            )

            athlete_payments["name"] = f"{athlete.first_name} {athlete.last_name}"
            team_subscription_price = teams_subscription_price.get(athlete.team_id, 0)
            if athlete.custom_fee is not None:
                team_subscription_price = athlete.custom_fee
            if athlete.private_lesson_fee is not None:
                team_subscription_price = athlete.private_lesson_fee
            amount_due = max(team_subscription_price - athlete_payments["total_payment"], 0)
            athlete_payments["amount_due"] = amount_due
            athlete_payments["team_subscription_price"] = team_subscription_price
            for payment in monthly_payments.filter(athlete=athlete).order_by(
                "-paid_at"
            ):

                athlete_payments.setdefault("details", []).append(
                    {
                        "amount": payment.amount,
                        "date": payment.paid_at,
                        "payment_type": payment.get_payment_type_display(),
                    }
                )
            if amount_due > 0:
                athlete_payments_list.append(athlete_payments)
        athlete_payments_list.sort(key=lambda x: (x["regular_payment_day"] is None, x["regular_payment_day"] or 0))
        total_amount = sum(
            [
                athlete_payments["amount_due"]
                for athlete_payments in athlete_payments_list
            ]
        )
    teams = Team.objects.filter(is_active=True)
    team = Team.objects.filter(id=team_id).first() if team_id else None
    #skipped_athletes = [athlete for athlete in active_athletes if athlete.id not in [a["athlete_id"] for a in athlete_payments_list]]
    athlete_count = len(athlete_payments_list)
    context = {
        "period": period,
        "payment_status": payment_status,
        "status_label": "Ödenenler" if payment_status == "paid" else "Bekleyenler",
        "selected_team": team_id,
        "athlete_payments_list": athlete_payments_list,
        "total_amount": total_amount,
        "athlete_count": athlete_count,
        "teams": teams,
        "team": team,
        #"skipped_athletes": skipped_athletes,
    }
    return render(request, "dashboard/payment_status_list.html", context)


@login_required
def payment_list_export(request, payment_status):
    period = _normalize_period(request.GET.get("period"))
    team_id = request.GET.get("team", "")
    monthly_payments = PaymentRecord.objects.filter(period=period, status="paid")
    if team_id:
        monthly_payments = monthly_payments.filter(athlete__team_id=team_id)

    rows = []
    if payment_status == "paid":
        paid_by_athlete = (
            monthly_payments.filter(payment_type="fee")
            .values(
                "athlete_id",
                "athlete__first_name",
                "athlete__last_name",
                "athlete__team__name",
            )
            .annotate(total=Sum("amount"))
        )
        for payment in paid_by_athlete:
            last_payment = monthly_payments.filter(
                athlete_id=payment["athlete_id"]
            ).order_by("-paid_at").first()
            rows.append([
                period,
                "Ödendi",
                f'{payment["athlete__first_name"]} {payment["athlete__last_name"]}',
                payment["athlete__team__name"] or "Takımsız",
                payment["total"],
                last_payment.paid_at.strftime("%d.%m.%Y") if last_payment and last_payment.paid_at else "",
            ])
    else:
        prices = _get_teams_subscription_price()
        active_athletes = _get_active_athletes(period)
        if team_id:
            active_athletes = active_athletes.filter(team_id=team_id)
        for athlete in active_athletes:
            paid = monthly_payments.filter(
                athlete=athlete,
                payment_type="fee",
            ).aggregate(total=Sum("amount"))["total"] or 0
            amount_due = prices.get(athlete.team_id, 0)
            if athlete.custom_fee is not None:
                amount_due = athlete.custom_fee
            if athlete.private_lesson_fee is not None:
                amount_due = athlete.private_lesson_fee
            amount_due = max(amount_due - paid, 0)
            if amount_due:
                rows.append([
                    period,
                    "Bekliyor",
                    athlete.get_full_name(),
                    athlete.team.name if athlete.team else "Takımsız",
                    amount_due,
                    "",
                ])

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Ödemeler"
    worksheet.append(["Period", "Durum", "Sporcu", "Takım", "Tutar", "Son ödeme"])
    for cell in worksheet[1]:
        cell.font = Font(bold=True)
    for row in rows:
        worksheet.append(row)
    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = worksheet.dimensions
    worksheet.column_dimensions["A"].width = 12
    worksheet.column_dimensions["B"].width = 14
    worksheet.column_dimensions["C"].width = 28
    worksheet.column_dimensions["D"].width = 22
    worksheet.column_dimensions["E"].width = 14
    worksheet.column_dimensions["F"].width = 14

    output = BytesIO()
    workbook.save(output)
    status_filename = "odenen" if payment_status == "paid" else "bekleyen"
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="odemeler-{status_filename}-{period}.xlsx"'
    )
    return response


@login_required(login_url="user-login")
def admin_finance(request):
    period = _normalize_period(request.GET.get("period"))
    return render(
        request,
        "dashboard/admin_finance.html",
        _get_admin_dashboard_context(period=period),
    )


@login_required(login_url="user-login")
def finance_dashboard(request):
    period = _normalize_period(request.GET.get("period"))
    category_id = request.GET.get("category", "")
    query = request.GET.get("q", "").strip()
    expenses = get_expenses_for_period(period, category_id, query)

    return render(request, "dashboard/finance.html", {
        "period": period,
        "expenses": expenses,
        "categories": ExpenseCategory.objects.all().order_by("name"),
        "selected_category": category_id,
        "query": query,
        "expense_summary": get_expense_summary(period),
        "regular_expense_summary": get_regular_expense_summary(period),
        "today": date.today(),
    })
