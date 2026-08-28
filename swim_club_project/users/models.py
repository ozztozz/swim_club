
# apps/users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

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

    # Giriş işlemlerinde kullanıcı adı yerine e-posta kullanılacaksa
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = "Kullanıcı"
        verbose_name_plural = "Kullanıcılar"

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"

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