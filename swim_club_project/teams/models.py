# teams/models.py
from django.db import models
from django.conf import settings


class Team(models.Model):
    name = models.CharField(max_length=100, verbose_name="Takım / Grup Adı")
    description = models.TextField(blank=True, null=True, verbose_name="Açıklama / Yaş Grubu")
    coaches = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        limit_choices_to={'role__in': ['coach', 'club_admin']},
        related_name='assigned_teams',
        verbose_name="Sorumlu Antrenörler"
    )
    is_active = models.BooleanField(default=True, verbose_name="Aktif mi?")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Takım"
        verbose_name_plural = "Takımlar"

    def __str__(self):
        return self.name


class TeamTrainingSchedule(models.Model):
    class TrainingType(models.TextChoices):
        LAND = "land", "Kara"
        SWIMMING = "swimming", "Yüzme"

    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Pazartesi"
        TUESDAY = 1, "Salı"
        WEDNESDAY = 2, "Çarşamba"
        THURSDAY = 3, "Perşembe"
        FRIDAY = 4, "Cuma"
        SATURDAY = 5, "Cumartesi"
        SUNDAY = 6, "Pazar"

    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="training_schedules",
        verbose_name="Takım",
    )
    weekday = models.PositiveSmallIntegerField(
        choices=Weekday.choices,
        verbose_name="Gün",
    )
    training_type = models.CharField(
        max_length=10,
        choices=TrainingType.choices,
        default=TrainingType.SWIMMING,
        verbose_name="Antrenman türü",
    )
    start_time = models.TimeField(verbose_name="Başlangıç saati")
    end_time = models.TimeField(verbose_name="Bitiş saati")
    location = models.CharField(max_length=255, verbose_name="Yer")

    class Meta:
        verbose_name = "Haftalık Antrenman Programı"
        verbose_name_plural = "Haftalık Antrenman Programları"
        ordering = ("weekday", "start_time")

    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            from django.core.exceptions import ValidationError

            raise ValidationError({"end_time": "Bitiş saati başlangıç saatinden sonra olmalıdır."})

    def __str__(self):
        return f"{self.team} - {self.get_weekday_display()}"


class TeamTrainingAttendance(models.Model):
    class Status(models.TextChoices):
        ATTENDED = "attended", "Katıldı"
        ABSENT = "absent", "Katılmadı"

    schedule = models.ForeignKey(
        TeamTrainingSchedule,
        on_delete=models.CASCADE,
        related_name="attendance_records",
        verbose_name="Haftalık antrenman",
    )
    athlete = models.ForeignKey(
        "athletes.Athlete",
        on_delete=models.CASCADE,
        related_name="training_attendance_records",
        verbose_name="Sporcu",
    )
    training_date = models.DateField(verbose_name="Antrenman tarihi")
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ABSENT,
        verbose_name="Katılım durumu",
    )
    notes = models.TextField(blank=True, default="", verbose_name="Not")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Antrenman katılım kaydı"
        verbose_name_plural = "Antrenman katılım kayıtları"
        ordering = ("-training_date", "athlete__first_name", "athlete__last_name")
        constraints = [
            models.UniqueConstraint(
                fields=("schedule", "athlete", "training_date"),
                name="unique_training_attendance_record",
            ),
        ]

    def clean(self):
        super().clean()
        if self.schedule_id and self.athlete_id:
            if self.athlete.team_id != self.schedule.team_id:
                from django.core.exceptions import ValidationError

                raise ValidationError({
                    "athlete": "Sporcu, antrenmanın ait olduğu takımda olmalıdır."
                })

    def __str__(self):
        return f"{self.athlete} - {self.schedule} - {self.training_date} ({self.get_status_display()})"