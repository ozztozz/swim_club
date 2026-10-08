from datetime import timedelta

from django.conf.locale import te
from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone

from teams.models import Team, TeamTrainingAttendance, TeamTrainingSchedule



def _get_coach_dashboard_context(user):
    now = timezone.localtime()
    today = now.date()

    teams = list(
        Team.objects.filter( is_active=True)
        .annotate(
            athlete_count=Count("athletes", filter=Q(athletes__is_active=True), distinct=True)
        )
        .order_by("-athlete_count")
    )
    if not user.Role.ADMIN:
        teams = [team for team in teams if user in team.coaches.all()]

    team_ids = [team.pk for team in teams]

    schedules = list(
        TeamTrainingSchedule.objects.filter(team_id__in=team_ids)
        .select_related("team")
        .order_by("weekday", "start_time")
    )
    taken_ids = set(
        TeamTrainingAttendance.objects.filter(
            schedule__team_id__in=team_ids, training_date=today
        ).values_list("schedule_id", flat=True)
    )
    counts = {
        row["schedule_id"]: row
        for row in TeamTrainingAttendance.objects.filter(
            schedule__team_id__in=team_ids, training_date=today
        )
        .values("schedule_id")
        .annotate(
            present=Count("id", filter=Q(status=TeamTrainingAttendance.Status.ATTENDED)),
            absent=Count("id", filter=Q(status=TeamTrainingAttendance.Status.ABSENT)),
        )
    }

    today_sessions = []
    for schedule in schedules:
        if schedule.weekday != today.weekday():
            continue
        stats = counts.get(schedule.pk, {})
        today_sessions.append(
            {
                "schedule": schedule,
                "is_taken": schedule.pk in taken_ids,
                "is_past": schedule.end_time < now.time(),
                "is_now": schedule.start_time <= now.time() <= schedule.end_time,
                "present": stats.get("present", 0),
                "absent": stats.get("absent", 0),
            }
        )

    tomorrow = today + timedelta(days=1)
    tomorrow_sessions = [s for s in schedules if s.weekday == tomorrow.weekday()]
    week_attendance = TeamTrainingAttendance.objects.filter(
        schedule__team_id__in=team_ids,
        training_date__gte=today - timedelta(days=6),
        training_date__lte=today,
    ).aggregate(
        present=Count("id", filter=Q(status=TeamTrainingAttendance.Status.ATTENDED)),
        total=Count("id"),
    )
    per_team = {
        row["schedule__team_id"]: row
        for row in TeamTrainingAttendance.objects.filter(
            schedule__team_id__in=team_ids,
            training_date__gte=today - timedelta(days=6),
            training_date__lte=today,
        )
        .values("schedule__team_id")
        .annotate(
            present=Count("id", filter=Q(status=TeamTrainingAttendance.Status.ATTENDED)),
            total=Count("id"),
        )
    }
    for team in teams:
        row = per_team.get(team.pk)
        team.attendance_rate = (
            round(row["present"] * 100 / row["total"]) if row and row["total"] else None
        )

    total = week_attendance["total"]

    rate = round(week_attendance["present"] * 100 / total) if total else None

    return {
        "coach_teams": teams,
        "coach_today": today,
        "coach_today_sessions": today_sessions,
        "coach_pending_count": sum(
            1 for s in today_sessions if s["is_past"] and not s["is_taken"]
        ),
        "coach_tomorrow": tomorrow,
        "coach_tomorrow_sessions": tomorrow_sessions,
        "coach_team_count": len(teams),
        "coach_athlete_count": sum(t.athlete_count for t in teams),
        "coach_week_session_count": len(schedules),
        "coach_attendance_rate": rate,
        "coach_attendance_url": reverse("training-attendance"),
    }