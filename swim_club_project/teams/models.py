# teams/models.py
from django.db import models
from django.conf import settings

class Team(models.Model):
    name = models.CharField(max_length=100, verbose_name="Takım / Grup Adı")
    description = models.TextField(blank=True, null=True, verbose_name="Açıklama / Yaş Grubu")
    monthly_fee = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00, 
        verbose_name="Varsayılan Aylık Aidat (TL)"
    )
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
        return f"{self.name} ({self.monthly_fee} TL)"