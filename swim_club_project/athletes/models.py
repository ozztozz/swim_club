# athletes/models.py
from django.db import models
from teams.models import Team

class Athlete(models.Model):
    GENDER_CHOICES = (
        ('M', 'Erkek'),
        ('F', 'Kadın'),
    )

    parent = models.CharField(max_length=150, verbose_name="Veli")
    parent_phone = models.CharField(max_length=20, blank=True, default='', verbose_name="Veli Telefonu")
    parent_email = models.EmailField(blank=True, default='', verbose_name="Veli E-postası")
    first_name = models.CharField(max_length=50, verbose_name="Ad")
    last_name = models.CharField(max_length=50, verbose_name="Soyad")
    phone_number = models.CharField(max_length=20, blank=True, default='', verbose_name="Sporcu Telefonu")
    tc_identity = models.CharField(max_length=11, unique=True, blank=True, null=True, verbose_name="T.C. Kimlik No")
    birth_date = models.DateField(verbose_name="Doğum Tarihi")
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, verbose_name="Cinsiyet")
    school = models.CharField(max_length=100, blank=True, null=True, verbose_name="Okul")
    license_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="Lisans No")
    joined_date = models.DateField(verbose_name="Kulübe Katılım Tarihi")
    photo = models.ImageField(upload_to='athlete_photos/', blank=True, null=True, verbose_name="Fotoğraf")
    
    # Onay ve Aktiflik Yönetimi
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
    custom_fee = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Özel Aidat Tutar (TL)",
        help_text="Boş bırakılırsa takımın varsayılan aidatı uygulanır. Burslu için 0 girebilirsiniz."
    )
    discount_percentage = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="İndirim Yüzdesi",
        help_text="Boş bırakılırsa indirim uygulanmaz."
    )
    regular_payment_day = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        verbose_name="Düzenli Ödeme Günü"
    )
    @property
    def current_monthly_fee(self):
        """Sporcunun ödemesi gereken güncel net aidat tutarını döner."""
        if self.custom_fee is not None:
            return self.custom_fee
        if self.team:
            from datetime import date
            from finance.models import TeamFeeHistory

            current_fee = TeamFeeHistory.objects.filter(
                team=self.team,
                start_date__lte=date.today(),
            ).filter(
                models.Q(end_date__isnull=True) | models.Q(end_date__gte=date.today())
            ).first()
            return current_fee.monthly_fee if current_fee else 0.00
        return 0.00

    def save(self, *args, **kwargs):
        # Keep legacy callers working while parent is stored as text.
        if not isinstance(self.parent, str):
            parent_user = self.parent
            full_name = f'{parent_user.first_name} {parent_user.last_name}'.strip()
            self.parent = full_name or parent_user.email
            self.parent_email = self.parent_email or parent_user.email
            self.parent_phone = self.parent_phone or parent_user.phone_number or ''
        super().save(*args, **kwargs)



    class Meta:
        verbose_name = "Sporcu"
        verbose_name_plural = "Sporcular"
        ordering = ['first_name', 'last_name']

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return self.get_full_name()