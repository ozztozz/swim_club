from django.contrib.auth.decorators import login_required
from datetime import datetime, time, timedelta
from django.db import transaction
from django.db.models import Count, Q
from django.utils.dateparse import parse_date
from django.utils import timezone
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse

from athletes.models import Athlete

from .forms import TeamForm, TeamTrainingScheduleForm
from .models import Team, TeamTrainingAttendance, TeamTrainingSchedule


def _team_context(request):
	query = request.GET.get('q', '').strip()
	status = request.GET.get('status', 'active')
	teams = Team.objects.prefetch_related('coaches').order_by('name')
	if request.user.is_coach:
		teams = teams.filter(coaches=request.user)

	if query:
		teams = teams.filter(name__icontains=query)
	if status == 'active':
		teams = teams.filter(is_active=True)
	elif status == 'inactive':
		teams = teams.filter(is_active=False)

	return {
		'teams': teams,
		'query': query,
		'status': status,
	}


@login_required
def team_list(request):
	return render(request, 'team/team_list.html', _team_context(request))


@login_required
def team_detail(request, pk):
	teams = Team.objects.prefetch_related('coaches', 'athletes', 'fee_histories')
	if request.user.is_coach:
		teams = teams.filter(coaches=request.user)
	team = get_object_or_404(teams, pk=pk)
	return render(request, 'team/team_detail.html', {'team': team})


def _weekly_schedule_context(team):
	schedules = team.training_schedules.all()
	schedules_by_day = {}
	for schedule in schedules:
		schedules_by_day.setdefault(schedule.weekday, []).append(schedule)
	durations = [
		datetime.combine(datetime.min, schedule.end_time)
		- datetime.combine(datetime.min, schedule.start_time)
		for schedule in schedules
	]
	total_duration = sum(durations, timedelta())
	total_minutes = int(total_duration.total_seconds() // 60)
	training_type_minutes = {}
	for training_type in TeamTrainingSchedule.TrainingType.values:
		type_durations = [
			datetime.combine(datetime.min, schedule.end_time)
			- datetime.combine(datetime.min, schedule.start_time)
			for schedule in schedules
			if schedule.training_type == training_type
		]
		duration = sum(type_durations, timedelta())
		training_type_minutes[training_type] = int(duration.total_seconds() // 60)
	swimming_minutes = training_type_minutes[TeamTrainingSchedule.TrainingType.SWIMMING]
	land_minutes = training_type_minutes[TeamTrainingSchedule.TrainingType.LAND]
	return {
		'team': team,
		'scheduled_day_count': len(schedules_by_day),
		'swimming_count': sum(
			1 for schedule in schedules
			if schedule.training_type == TeamTrainingSchedule.TrainingType.SWIMMING
		),
		'land_count': sum(
			1 for schedule in schedules
			if schedule.training_type == TeamTrainingSchedule.TrainingType.LAND
		),
		'total_training_hours': total_minutes // 60,
		'total_training_minutes': total_minutes % 60,
		'swimming_training_hours': swimming_minutes // 60,
		'swimming_training_minutes': swimming_minutes % 60,
		'land_training_hours': land_minutes // 60,
		'land_training_minutes': land_minutes % 60,
		'weekly_days': [
			{
				'value': weekday,
				'label': label,
				'schedules': schedules_by_day.get(weekday, []),
				'morning_schedules': [
					schedule for schedule in schedules_by_day.get(weekday, [])
					if schedule.start_time < time(12, 0)
				],
				'evening_schedules': [
					schedule for schedule in schedules_by_day.get(weekday, [])
					if schedule.start_time >= time(12, 0)
				],
			}
			for weekday, label in TeamTrainingSchedule.Weekday.choices
		],
	}


def _schedule_teams(request):
	teams = Team.objects.order_by('name')
	if request.user.is_coach:
		teams = teams.filter(coaches=request.user)
	return teams


@login_required
def team_schedule_home(request):
	teams = _schedule_teams(request)
	team = teams.filter(pk=request.GET.get('team')).first() or teams.first()
	context = _weekly_schedule_context(team) if team else {
		'team': None,
		'weekly_days': [],
		'scheduled_day_count': 0,
	}
	context['schedule_teams'] = teams
	return render(request, 'team/weekly_schedule.html', context)


@login_required
def team_schedule(request, pk):
	teams = _schedule_teams(request)
	team = get_object_or_404(teams, pk=pk)
	context = _weekly_schedule_context(team)
	context['schedule_teams'] = teams
	return render(request, 'team/weekly_schedule.html', context)


@login_required
def team_schedule_create(request, pk):
	team = get_object_or_404(Team, pk=pk)
	schedule = TeamTrainingSchedule(team=team)
	form = TeamTrainingScheduleForm(
		request.POST or None,
		instance=schedule,
		initial={'weekday': request.GET.get('weekday')},
	)
	if request.method == 'POST' and form.is_valid():
		form.save()
		response = render(request, 'team/partials/weekly_schedule_board.html', _weekly_schedule_context(team))
		response['HX-Trigger'] = 'closeScheduleModal'
		return response

	return render(request, 'team/partials/weekly_schedule_form_modal.html', {
		'form': form,
		'team': team,
		'modal_title': 'Antrenman ekle',
	})


@login_required
def team_schedule_update(request, pk, schedule_pk):
	team = get_object_or_404(Team, pk=pk)
	schedule = get_object_or_404(TeamTrainingSchedule, pk=schedule_pk, team=team)
	form = TeamTrainingScheduleForm(request.POST or None, instance=schedule)
	if request.method == 'POST' and form.is_valid():
		form.save()
		response = render(request, 'team/partials/weekly_schedule_board.html', _weekly_schedule_context(team))
		response['HX-Trigger'] = 'closeScheduleModal'
		return response

	return render(request, 'team/partials/weekly_schedule_form_modal.html', {
		'form': form,
		'team': team,
		'schedule': schedule,
		'modal_title': 'Antrenmanı düzenle',
	})


@login_required
def team_schedule_delete(request, pk, schedule_pk):
	team = get_object_or_404(Team, pk=pk)
	if request.method == 'POST':
		get_object_or_404(TeamTrainingSchedule, pk=schedule_pk, team=team).delete()
	return render(request, 'team/partials/weekly_schedule_board.html', _weekly_schedule_context(team))


def _attendance_date(request):
	date_value = request.POST.get('training_date') or request.GET.get('training_date')
	return (parse_date(date_value) if date_value else None) or timezone.localdate()


def _today_training_context(team, selected_schedule=None, training_date=None):
	training_date = training_date or timezone.localdate()
	schedules = list(
		team.training_schedules.filter(weekday=training_date.weekday())
		.order_by('start_time', 'pk')
	)
	if selected_schedule not in schedules:
		selected_schedule = schedules[0] if schedules else None
	athletes = list(
		Athlete.objects.filter(team=team, is_active=True)
		.order_by('first_name', 'last_name')
	)
	attendance_by_athlete = {}
	if selected_schedule:
		attendance_by_athlete = {
			record.athlete_id: record
			for record in TeamTrainingAttendance.objects.filter(
				schedule=selected_schedule,
				training_date=training_date,
			)
		}
	athlete_rows = [
		{
			'athlete': athlete,
			'record': attendance_by_athlete.get(athlete.pk),
		}
		for athlete in athletes
	]
	return {
		'team': team,
		'today': training_date,
		'schedules': schedules,
		'selected_schedule': selected_schedule,
		'athletes': athletes,
		'athlete_rows': athlete_rows,
		'attendance_by_athlete': attendance_by_athlete,
	}


@login_required
def training_attendance(request):
	today = _attendance_date(request)
	schedules = list(TeamTrainingSchedule.objects.filter(
		weekday=today.weekday(),
		team__is_active=True,
	).select_related('team').annotate(
		attended_count=Count(
			'attendance_records',
			distinct=True,
			filter=Q(
				attendance_records__training_date=today,
				attendance_records__status=TeamTrainingAttendance.Status.ATTENDED,
				attendance_records__athlete__is_active=True,
			),
		)
	).annotate(
		active_athlete_count=Count(
			'team__athletes',
			filter=Q(team__athletes__is_active=True),
			distinct=True,
		)
	).order_by('start_time', 'team__name', 'pk'))
	for schedule in schedules:
		schedule.absent_count = max(
			schedule.active_athlete_count - schedule.attended_count,
			0,
		)
	return render(request, 'team/training_attendance.html', {
		'today': today,
		'selected_date': today,
		'schedules': schedules,
	})


@login_required
def training_attendance_team(request, team_pk):
	today = _attendance_date(request)
	team = get_object_or_404(Team, pk=team_pk, is_active=True)
	selected_schedule = None
	schedule_pk = request.GET.get('schedule')
	if schedule_pk:
		selected_schedule = get_object_or_404(
			TeamTrainingSchedule,
			pk=schedule_pk,
			team=team,
			weekday=today.weekday(),
		)
	return render(request, 'team/partials/training_attendance_panel.html',
		_today_training_context(team, selected_schedule, today))


@login_required
def training_attendance_schedule(request, team_pk, schedule_pk):
	today = _attendance_date(request)
	team = get_object_or_404(Team, pk=team_pk, is_active=True)
	schedule = get_object_or_404(
		TeamTrainingSchedule,
		pk=schedule_pk,
		team=team,
		weekday=today.weekday(),
	)
	return render(request, 'team/partials/training_attendance_modal.html',
		_today_training_context(team, schedule, today))


@login_required
def training_attendance_save(request, team_pk, schedule_pk):
	today = _attendance_date(request)
	team = get_object_or_404(Team, pk=team_pk, is_active=True)
	schedule = get_object_or_404(
		TeamTrainingSchedule,
		pk=schedule_pk,
		team=team,
		weekday=today.weekday(),
	)
	if request.method == 'POST':
		absent_ids = set(request.POST.getlist('absent_athletes'))
		athletes = Athlete.objects.filter(team=team, is_active=True)
		with transaction.atomic():
			for athlete in athletes:
				TeamTrainingAttendance.objects.update_or_create(
					schedule=schedule,
					athlete=athlete,
					training_date=today,
					defaults={
						'status': (
							TeamTrainingAttendance.Status.ABSENT
							if str(athlete.pk) in absent_ids
							else TeamTrainingAttendance.Status.ATTENDED
						),
					},
				)
		attended_count = TeamTrainingAttendance.objects.filter(
			schedule=schedule,
			training_date=today,
			status=TeamTrainingAttendance.Status.ATTENDED,
		).count()
		active_athlete_count = Athlete.objects.filter(team=team, is_active=True).count()
		response_body = render_to_string('team/partials/training_attendance_count.html', {
			'schedule': schedule,
			'attended_count': attended_count,
			'absent_count': max(active_athlete_count - attended_count, 0),
		})
		return HttpResponse(
			response_body,
			headers={'HX-Trigger': 'closeAttendanceModal'},
		)
	response = render(request, 'team/partials/training_attendance_modal.html',
		_today_training_context(team, schedule, today))
	return response


@login_required
def team_create(request):
	form = TeamForm(request.POST or None)
	if request.method == 'POST' and form.is_valid():
		form.save()
		response = render(request, 'team/partials/team_table.html', _team_context(request))
		response['HX-Trigger'] = 'closeTeamModal'
		return response

	return render(request, 'team/partials/team_form_modal.html', {
		'form': form,
		'modal_title': 'Yeni takım ekle',
		'submit_label': 'Takımı kaydet',
		'form_url': 'team-create',
	})

@login_required
def team_update(request, pk):
	team = get_object_or_404(Team, pk=pk)
	form = TeamForm(request.POST or None, instance=team)
	return_to_detail = request.GET.get('return_to_detail') or request.POST.get('return_to_detail')
	if request.method == 'POST' and form.is_valid():
		form.save()
		if return_to_detail:
			response = render(request, 'team/team_detail.html', {'team': team})
			response['HX-Redirect'] = request.build_absolute_uri(reverse('team-detail', args=[team.pk]))
			return response
		response = render(request, 'team/partials/team_table.html', _team_context(request))
		response['HX-Trigger'] = 'closeTeamModal'
		return response

	return render(request, 'team/partials/team_form_modal.html', {
		'form': form,
		'team': team,
		'modal_title': 'Takımı düzenle',
		'submit_label': 'Değişiklikleri kaydet',
		'form_url': 'team-update',
		'return_to_detail': return_to_detail,
	})



