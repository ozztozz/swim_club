from django.test import TestCase
from datetime import date, time
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from django.core.exceptions import ValidationError

from athletes.models import Athlete
from .models import Team, TeamTrainingAttendance, TeamTrainingSchedule
from .views import _weekly_schedule_context

User = get_user_model()


class TeamTrainingScheduleTests(TestCase):
	def setUp(self):
		self.team = Team.objects.create(name="Minikler A")
		self.user = User.objects.create_user(
			username="training-admin",
			password="test-password",
			role="club_admin",
		)

	def test_end_time_must_be_after_start_time(self):
		schedule = TeamTrainingSchedule(
			team=self.team,
			weekday=TeamTrainingSchedule.Weekday.MONDAY,
			start_time="18:00",
			end_time="17:00",
			location="Kulüp havuzu",
		)

		with self.assertRaises(ValidationError):
			schedule.full_clean()

	def test_team_can_have_multiple_schedules_per_day(self):
		TeamTrainingSchedule.objects.create(
			team=self.team,
			weekday=TeamTrainingSchedule.Weekday.MONDAY,
			training_type=TeamTrainingSchedule.TrainingType.SWIMMING,
			start_time="18:00",
			end_time="19:00",
			location="Kulüp havuzu",
		)
		second_schedule = TeamTrainingSchedule.objects.create(
			team=self.team,
			weekday=TeamTrainingSchedule.Weekday.MONDAY,
			training_type=TeamTrainingSchedule.TrainingType.LAND,
			start_time="20:00",
			end_time="21:00",
			location="Kulüp havuzu",
		)

		self.assertEqual(self.team.training_schedules.count(), 2)
		self.assertEqual(second_schedule.get_training_type_display(), "Kara")

	def test_schedule_summary_calculates_counts_and_durations_by_type(self):
		TeamTrainingSchedule.objects.create(
			team=self.team,
			weekday=TeamTrainingSchedule.Weekday.MONDAY,
			training_type=TeamTrainingSchedule.TrainingType.SWIMMING,
			start_time="06:00",
			end_time="07:30",
			location="Kulüp havuzu",
		)
		TeamTrainingSchedule.objects.create(
			team=self.team,
			weekday=TeamTrainingSchedule.Weekday.TUESDAY,
			training_type=TeamTrainingSchedule.TrainingType.SWIMMING,
			start_time="18:00",
			end_time="19:00",
			location="Kulüp havuzu",
		)
		TeamTrainingSchedule.objects.create(
			team=self.team,
			weekday=TeamTrainingSchedule.Weekday.WEDNESDAY,
			training_type=TeamTrainingSchedule.TrainingType.LAND,
			start_time="17:00",
			end_time="18:30",
			location="Salon",
		)

		context = _weekly_schedule_context(self.team)

		self.assertEqual(context['swimming_count'], 2)
		self.assertEqual(context['swimming_training_hours'], 2)
		self.assertEqual(context['swimming_training_minutes'], 30)
		self.assertEqual(context['land_count'], 1)
		self.assertEqual(context['land_training_hours'], 1)
		self.assertEqual(context['land_training_minutes'], 30)
		self.assertEqual(context['total_training_hours'], 4)
		self.assertEqual(context['total_training_minutes'], 0)

	def test_attendance_is_unique_per_athlete_schedule_and_date(self):
		athlete = Athlete.objects.create(
			parent="Veli",
			first_name="Ali",
			last_name="Yılmaz",
			birth_date=date(2015, 1, 1),
			gender="M",
			joined_date=date(2025, 1, 1),
			team=self.team,
		)
		schedule = TeamTrainingSchedule.objects.create(
			team=self.team,
			weekday=TeamTrainingSchedule.Weekday.MONDAY,
			start_time=time(18, 0),
			end_time=time(19, 0),
			location="Kulüp havuzu",
		)
		TeamTrainingAttendance.objects.create(
			schedule=schedule,
			athlete=athlete,
			training_date=date(2026, 9, 14),
			status=TeamTrainingAttendance.Status.ATTENDED,
		)
		duplicate = TeamTrainingAttendance(
			schedule=schedule,
			athlete=athlete,
			training_date=date(2026, 9, 14),
			status=TeamTrainingAttendance.Status.ABSENT,
		)

		with self.assertRaises(ValidationError):
			duplicate.full_clean()

	def test_attendance_athlete_must_belong_to_schedule_team(self):
		other_team = Team.objects.create(name="Diğer Takım")
		athlete = Athlete.objects.create(
			parent="Veli",
			first_name="Ayşe",
			last_name="Kaya",
			birth_date=date(2015, 1, 1),
			gender="F",
			joined_date=date(2025, 1, 1),
			team=other_team,
		)
		schedule = TeamTrainingSchedule.objects.create(
			team=self.team,
			weekday=TeamTrainingSchedule.Weekday.TUESDAY,
			start_time=time(18, 0),
			end_time=time(19, 0),
			location="Kulüp havuzu",
		)

		with self.assertRaises(ValidationError):
			TeamTrainingAttendance(
				schedule=schedule,
				athlete=athlete,
				training_date=date(2026, 9, 15),
			).full_clean()

	def test_attendance_page_bulk_saves_and_updates_participants(self):
		today = timezone.localdate()
		athlete_one = Athlete.objects.create(
			parent="Veli",
			first_name="Ali",
			last_name="Yılmaz",
			birth_date=date(2015, 1, 1),
			gender="M",
			joined_date=date(2025, 1, 1),
			team=self.team,
			is_active=True,
		)
		athlete_two = Athlete.objects.create(
			parent="Veli",
			first_name="Ayşe",
			last_name="Kaya",
			birth_date=date(2015, 1, 1),
			gender="F",
			joined_date=date(2025, 1, 1),
			team=self.team,
			is_active=True,
		)
		schedule = TeamTrainingSchedule.objects.create(
			team=self.team,
			weekday=today.weekday(),
			start_time=time(18, 0),
			end_time=time(19, 0),
			location="Kulüp havuzu",
		)
		self.client.force_login(self.user)
		url = reverse(
			"training-attendance-save",
			kwargs={"team_pk": self.team.pk, "schedule_pk": schedule.pk},
		)

		response = self.client.post(url, {"absent_athletes": [athlete_two.pk]})

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, f'1 katıldı')
		self.assertContains(response, f'1 katılmadı')
		self.assertTrue(
			TeamTrainingAttendance.objects.get(
				schedule=schedule, athlete=athlete_one, training_date=today
			).status == TeamTrainingAttendance.Status.ATTENDED
		)
		self.assertFalse(
			TeamTrainingAttendance.objects.get(
				schedule=schedule, athlete=athlete_two, training_date=today
			).status == TeamTrainingAttendance.Status.ATTENDED
		)

		self.client.post(url, {"absent_athletes": [athlete_one.pk]})
		self.assertFalse(
			TeamTrainingAttendance.objects.get(
				schedule=schedule, athlete=athlete_one, training_date=today
			).status == TeamTrainingAttendance.Status.ATTENDED
		)
		self.assertTrue(
			TeamTrainingAttendance.objects.get(
				schedule=schedule, athlete=athlete_two, training_date=today
			).status == TeamTrainingAttendance.Status.ATTENDED
		)

	def test_attendance_page_uses_selected_date(self):
		selected_date = date(2026, 9, 20)
		TeamTrainingSchedule.objects.create(
			team=self.team,
			weekday=selected_date.weekday(),
			start_time=time(10, 0),
			end_time=time(11, 0),
			location="Kulüp havuzu",
		)
		self.client.force_login(self.user)

		response = self.client.get(
			reverse("training-attendance"),
			{"training_date": selected_date.isoformat()},
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.context["selected_date"], selected_date)
		self.assertContains(response, self.team.name)

	def test_athlete_detail_groups_attendance_by_month(self):
		athlete = Athlete.objects.create(
			parent="Veli",
			first_name="Deniz",
			last_name="Yılmaz",
			birth_date=date(2015, 1, 1),
			gender="M",
			joined_date=date(2025, 1, 1),
			team=self.team,
			is_active=True,
		)
		schedule = TeamTrainingSchedule.objects.create(
			team=self.team,
			weekday=date(2026, 9, 14).weekday(),
			start_time=time(18, 0),
			end_time=time(19, 0),
			location="Kulüp havuzu",
		)
		TeamTrainingAttendance.objects.create(
			schedule=schedule,
			athlete=athlete,
			training_date=date(2026, 8, 31),
			status=TeamTrainingAttendance.Status.ATTENDED,
		)
		TeamTrainingAttendance.objects.create(
			schedule=schedule,
			athlete=athlete,
			training_date=date(2026, 9, 14),
			status=TeamTrainingAttendance.Status.ABSENT,
		)
		morning_schedule = TeamTrainingSchedule.objects.create(
			team=self.team,
			weekday=date(2026, 9, 14).weekday(),
			training_type=TeamTrainingSchedule.TrainingType.LAND,
			start_time=time(8, 0),
			end_time=time(9, 0),
			location="Kulüp havuzu",
		)
		TeamTrainingAttendance.objects.create(
			schedule=morning_schedule,
			athlete=athlete,
			training_date=date(2026, 9, 14),
			status=TeamTrainingAttendance.Status.ATTENDED,
		)

		self.client.force_login(self.user)
		response = self.client.get(reverse("athlete-manage-detail", args=[athlete.pk]))

		self.assertEqual(response.status_code, 200)
		months = list(response.context["attendance_months"])
		self.assertEqual([month["label"] for month in months], ["Eylül 2026"])
		self.assertEqual(response.context["attendance_total"], 2)
		self.assertEqual(response.context["attendance_absent"], 1)
		self.assertEqual(months[0]["total_count"], 2)
		self.assertEqual(months[0]["absent_count"], 1)
		self.assertEqual(months[0]["weekdays"][0]["label"], "Pazartesi")
		september_days = [
			day
			for week in months[0]["calendar_weeks"]
			for day in week
			if day is not None
		]
		self.assertEqual(len(september_days), 30)
		september_14 = next(day for day in september_days if day["number"] == 14)
		self.assertEqual(
			september_14["sessions"],
			[
				{"label": "S", "status": TeamTrainingAttendance.Status.ATTENDED},
				{"label": "A", "status": TeamTrainingAttendance.Status.ABSENT},
			],
		)
		self.assertEqual(response.context["attendance_total"], 2)
		self.assertEqual(response.context["attendance_absent"], 1)
		self.assertEqual(response.context["attendance_swimming"], 1)
		self.assertEqual(response.context["attendance_land"], 1)
		self.assertEqual(response.context["attendance_absent_swimming"], 1)
		self.assertEqual(response.context["attendance_absent_land"], 0)
		self.assertEqual(response.context["attendance_period"], "2026-09")
		self.assertEqual(response.context["attendance_previous_period"], "2026-08")
		self.assertIsNone(response.context["attendance_next_period"])
		previous_response = self.client.get(
			reverse("athlete-manage-detail", args=[athlete.pk]),
			{"attendance_month": "2026-08"},
		)
		self.assertEqual(previous_response.context["attendance_period"], "2026-08")
		self.assertEqual(previous_response.context["attendance_next_period"], "2026-09")
		august_days = [
			day
			for week in previous_response.context["attendance_months"][0]["calendar_weeks"]
			for day in week
			if day is not None
		]
		august_31 = next(day for day in august_days if day["number"] == 31)
		self.assertEqual(august_31["sessions"][0]["status"], TeamTrainingAttendance.Status.ATTENDED)
		self.assertContains(response, "Antrenman")

	def test_coach_can_see_equipment_and_training_tabs_on_athlete_detail(self):
		coach = User.objects.create_user(
			username="schedule-coach",
			email="schedule-coach@example.com",
			password="test-password",
			role="coach",
		)
		self.team.coaches.add(coach)
		athlete = Athlete.objects.create(
			parent="Veli",
			first_name="Ece",
			last_name="Kaya",
			birth_date=date(2015, 1, 1),
			gender="F",
			joined_date=date(2025, 1, 1),
			team=self.team,
			is_active=True,
		)

		self.client.force_login(coach)
		response = self.client.get(reverse("athlete-manage-detail", args=[athlete.pk]))

		self.assertEqual(response.status_code, 200)
		response_html = response.content.decode()
		self.assertEqual(response_html.count('data-payment-tab="monthly"'), 1)
		self.assertEqual(response_html.count('data-payment-tab="other"'), 1)
		self.assertContains(response, 'data-payment-tab="equipment"')
		self.assertContains(response, 'data-payment-tab="training"')
		self.assertNotContains(response, "Düzenle")
		self.assertNotContains(response, "Ödeme Ekle")

	def test_coach_logout_clears_session_and_redirects_to_login(self):
		self.client.force_login(self.user)

		response = self.client.post(reverse("user-logout"))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Hesabınıza giriş yaparak devam edin.")
		self.assertNotIn("_auth_user_id", self.client.session)

	def test_attendance_list_counts_attended_and_absent_athletes(self):
		today = timezone.localdate()
		athletes = [
			Athlete.objects.create(
				parent="Veli",
				first_name=name,
				last_name="Sporcu",
				birth_date=date(2015, 1, 1),
				gender="M",
				joined_date=date(2025, 1, 1),
				team=self.team,
				is_active=True,
			)
			for name in ("Ali", "Ayşe", "Can")
		]
		schedule = TeamTrainingSchedule.objects.create(
			team=self.team,
			weekday=today.weekday(),
			start_time=time(18, 0),
			end_time=time(19, 0),
			location="Kulüp havuzu",
		)
		for athlete, status in zip(
			athletes[:2],
			(
				TeamTrainingAttendance.Status.ATTENDED,
				TeamTrainingAttendance.Status.ABSENT,
			),
		):
			TeamTrainingAttendance.objects.create(
				schedule=schedule,
				athlete=athlete,
				training_date=today,
				status=status,
			)

		self.client.force_login(self.user)
		response = self.client.get(reverse("training-attendance"))
		listed_schedule = response.context["schedules"][0]

		self.assertEqual(listed_schedule.attended_count, 1)
		self.assertEqual(listed_schedule.absent_count, 2)
