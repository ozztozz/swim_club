from collections import defaultdict
from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from athletes.models import Athlete
from finance.models import PaymentRecord
from teams.models import TeamTrainingAttendance, TeamTrainingSchedule


def _next_session(schedules, now):
    """Haftalık programdan bir sonraki antrenmanı (tarih + program) döner."""
    best = None
    for schedule in schedules:
        days_ahead = (schedule.weekday - now.weekday()) % 7
        if days_ahead == 0 and schedule.end_time <= now.time():
            days_ahead = 7
        session_date = now.date() + timedelta(days=days_ahead)
        key = (session_date, schedule.start_time)
        if best is None or key < best[0]:
            best = (key, schedule, session_date)
    if best is None:
        return None
    return {
        "schedule": best[1],
        "date": best[2],
        "is_today": best[2] == now.date(),
    }


def _get_parent_dashboard_context(user):
    now = timezone.localtime()
    today = now.date()
    since = today - timedelta(days=30)

    children = list(
        Athlete.objects.for_parent(user)
        .select_related("team")
        .order_by("-is_active", "first_name", "last_name")
    )
    child_ids = [child.pk for child in children]
    team_ids = {child.team_id for child in children if child.team_id}

    schedules_by_team = defaultdict(list)
    for schedule in TeamTrainingSchedule.objects.filter(team_id__in=team_ids):
        schedules_by_team[schedule.team_id].append(schedule)

    attendance = {
        row["athlete_id"]: row
        for row in TeamTrainingAttendance.objects.filter(
            athlete_id__in=child_ids, training_date__gte=since, training_date__lte=today
        )
        .values("athlete_id")
        .annotate(
            present=Count("id", filter=Q(status=TeamTrainingAttendance.Status.ATTENDED)),
            total=Count("id"),
        )
    }

    pending_by_athlete = defaultdict(list)
    for payment in PaymentRecord.objects.filter(
        athlete_id__in=child_ids, status="pending"
    ).order_by("due_date"):
        pending_by_athlete[payment.athlete_id].append(payment)

    total_due = 0
    overdue_count = 0
    cards = []
    for child in children:
        pending = pending_by_athlete.get(child.pk, [])
        due = sum(p.amount for p in pending)
        overdue = sum(1 for p in pending if p.due_date < today)
        total_due += due
        overdue_count += overdue

        row = attendance.get(child.pk)
        rate = round(row["present"] * 100 / row["total"]) if row and row["total"] else None

        cards.append({
            "athlete": child,
            "next_session": _next_session(schedules_by_team.get(child.team_id, []), now),
            "attendance_rate": rate,
            "attendance_total": row["total"] if row else 0,
            "pending_payments": pending[:3],
            "pending_count": len(pending),
            "due_amount": due,
            "overdue_count": overdue,
        })

    return {
        "parent_today": today,
        "parent_children": cards,
        "parent_child_count": len(cards),
        "parent_total_due": total_due,
        "parent_overdue_count": overdue_count,
    }
