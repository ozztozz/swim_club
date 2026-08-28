# athletes/models.py
from django.db import models
from django.conf import settings
from teams.models import Team

class Athlete(models.Model):
    GENDER_CHOICES = (
        ('M', 'Erkek'),
        ('F', 'Kadın'),
    )

    STATUS_CHOICES = (
        ('pending', 'Onay Bekliyor'),
        ('approved', 'Onaylandı'),
        ('rejected', 'Reddedildi'),
    )

    parent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='athletes',
        limit_choices_to={'role': 'parent'},
        verbose_name="Veli"
    )
    first_name = models.CharField(max_length=50, verbose_name="Ad")
    last_name = models.CharField(max_length=50, verbose_name="Soyad")
    tc_identity = models.CharField(max_length=11, unique=True, blank=True, null=True, verbose_name="T.C. Kimlik No")
    birth_date = models.DateField(verbose_name="Doğum Tarihi")
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, verbose_name="Cinsiyet")
    school = models.CharField(max_length=100, blank=True, null=True, verbose_name="Okul")
    license_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="Lisans No")
    joined_date = models.DateField(verbose_name="Kulübe Katılım Tarihi")
    photo = models.ImageField(upload_to='athlete_photos/', blank=True, null=True, verbose_name="Fotoğraf")
    
    # Onay ve Aktiflik Yönetimi
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name="Onay Durumu")
    is_active = models.BooleanField(default=False, verbose_name="Aktif Sporcu mu?")
    created_at = models.DateTimeField(auto_now_add=True)

    team = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='athletes',
        verbose_name="Bağlı Olduğu Takım"
    )
    custom_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Özel Aidat Tutar (TL)",
        help_text="Boş bırakılırsa takımın varsayılan aidatı uygulanır. Burslu için 0 girebilirsiniz."
    )

    @property
    def current_monthly_fee(self):
        """Sporcunun ödemesi gereken güncel net aidat tutarını döner."""
        if self.custom_fee is not None:
            return self.custom_fee
        if self.team:
            return self.team.monthly_fee
        return 0.00



    class Meta:
        verbose_name = "Sporcu"
        verbose_name_plural = "Sporcular"
        ordering = ['first_name', 'last_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_status_display()})"