
# apps/users/models.py
import re
from django.contrib.auth.models import AbstractUser
from django.db import models

TR_MAP = str.maketrans('çğıöşüÇĞİÖŞÜ', 'cgiosuCGIOSU')

class User(AbstractUser):
    class Role(models.TextChoices):
        PARENT = 'parent', 'Veli'
        ADMIN = 'admin', 'Yönetici'
        COACH = 'coach', 'Antrenör'
        FINANCE = 'finance', 'Mali İşler'

    email = models.EmailField(unique=True, verbose_name="E-posta Adresi")
    role = models.CharField(
        max_length=20, 
        choices=Role.choices, 
        default=Role.PARENT,
        verbose_name="Kullanıcı Rolü"
    )
    phone_number = models.CharField(max_length=15, blank=True, null=True, verbose_name="Telefon Numarası")
    tc_identity = models.CharField(max_length=11, blank=True, null=True, verbose_name="T.C. Kimlik No")

    # Kullanıcı girişi kullanıcı adı ile yapılır; e-posta hesap iletişimi için tutulur.
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']

    class Meta:
        verbose_name = "Kullanıcı"
        verbose_name_plural = "Kullanıcılar"

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"

    @classmethod
    def generate_username(cls, first_name, last_name, exclude_pk=None):
        """Ad ve soyaddan ascii, küçük harfli ve benzersiz kullanıcı adı üretir (ali.yilmaz, ali.yilmaz2)."""
        parts = f'{first_name or ""} {last_name or ""}'.translate(TR_MAP).lower().split()
        base = '.'.join(re.sub(r'[^a-z0-9]', '', part) for part in parts)
        base = re.sub(r'\.+', '.', base).strip('.')[:140] or 'kullanici'
        existing = cls.objects.exclude(pk=exclude_pk)
        candidate, counter = base, 1
        while existing.filter(username__iexact=candidate).exists():
            counter += 1
            candidate = f'{base}{counter}'
        return candidate

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.generate_username(self.first_name, self.last_name, self.pk)
        super().save(*args, **kwargs)
    @property
    def is_parent(self):
        return self.role == self.Role.PARENT

    @property
    def is_club_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_coach(self):
        return self.role == self.Role.COACH

    @property
    def is_finance(self):
        return self.role == self.Role.FINANCE

    @property
    def athletes(self):
        from athletes.models import Athlete
        return Athlete.objects.for_parent(self)