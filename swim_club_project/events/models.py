from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models


class CompetitionEvent(models.Model):
    POOL_TYPE_CHOICES = (
        ("25", "25"),
        ("50", "50"),
    )

    event_date = models.DateField("Tarih")
    name = models.CharField("Müsabaka adı", max_length=200)
    pool_type = models.CharField("25/50", max_length=2, choices=POOL_TYPE_CHOICES)
    age_group_start = models.CharField("Yaş Grubu (Başlangıç)", max_length=150)
    age_group_end = models.CharField("Yaş Grubu (Bitiş) ", max_length=150)
    place = models.CharField("Yer", max_length=200)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="competition_events",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-event_date", "name")
        verbose_name = "Yarışma / etkinlik"
        verbose_name_plural = "Yarışmalar ve etkinlikler"

    def __str__(self):
        return f"{self.name} - {self.event_date:%d.%m.%Y}"


class EventAttachment(models.Model):
    event = models.ForeignKey(
        CompetitionEvent,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name="Yarışma / etkinlik",
    )
    file_name = models.CharField("Dosya Adı", max_length=255)
    file = models.FileField(
        "Dosya",
        upload_to="events/%Y/%m/",
        validators=[
            FileExtensionValidator(
                allowed_extensions=["pdf", "xls", "xlsx", "csv", "jpg", "jpeg", "png", "webp"]
            )
        ],
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-uploaded_at",)
        verbose_name = "Etkinlik dosyası"
        verbose_name_plural = "Etkinlik dosyaları"

    def __str__(self):
        return self.file.name.rsplit("/", 1)[-1]
