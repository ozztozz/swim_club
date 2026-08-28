from django.db import models
from django.conf import settings
from datetime import date
from athletes.models import Athlete

class PaymentRecord(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Bekliyor'),
        ('paid', 'Ödendi'),
        ('cancelled', 'İptal Edildi'),
    ]

    athlete = models.ForeignKey(
        Athlete, 
        on_delete=models.CASCADE, 
        related_name='payments',
        verbose_name="Sporcu"
    )
    period = models.CharField(
        max_length=7, 
        db_index=True,
        help_text="Format: YYYY-MM (Örn: 2026-08)",
        verbose_name="Aidat Dönemi"
    )
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Aidat Tutarı (TL)"
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        verbose_name="Ödeme Durumu"
    )
    due_date = models.DateField(
        verbose_name="Son Ödeme Tarihi"
    )
    paid_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Ödenme Zamanı"
    )
    collected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='collected_payments',
        verbose_name="Tahsil Eden"
    )
    notes = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Not / Dekont No"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ödeme Kaydı"
        verbose_name_plural = "Ödeme Kayıtları"
        unique_together = ['athlete', 'period']
        ordering = ['-period', 'athlete__first_name']

    def __str__(self):
        return f"{self.athlete.get_full_name()} - {self.period} ({self.get_status_display()})"

    @property
    def is_overdue(self):
        """Ödeme henüz yapılmadıysa ve son ödeme tarihi geçtiyse True döner."""
        if self.status == 'pending' and self.due_date < date.today():
            return True
        return False



class ExpenseCategory(models.Model):
    """Harcama Kategorileri (örn: Havuz Kirası, Personel Maaşı, Ekipman, Organizasyon)"""
    name = models.CharField(max_length=100, verbose_name="Kategori Adı")
    description = models.TextField(blank=True, null=True, verbose_name="Açıklama")

    class Meta:
        verbose_name = "Harcama Kategorisi"
        verbose_name_plural = "Harcama Kategorileri"

    def __str__(self):
        return self.name


class Expense(models.Model):
    """Kulüp Harcama/Gider Kaydı"""
    title = models.CharField(max_length=200, verbose_name="Harcama/Gider Başlığı")
    category = models.ForeignKey(
        ExpenseCategory, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='expenses',
        verbose_name="Kategori"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Tutar (TL)")
    expense_date = models.DateField(verbose_name="Harcama Tarihi")
    period = models.CharField(
        max_length=7, 
        db_index=True, 
        help_text="Format: YYYY-MM (Örn: 2026-08)",
        verbose_name="Ait Olduğu Dönem"
    )
    receipt_no = models.CharField(max_length=100, blank=True, null=True, verbose_name="Fatura / Fiş / Dekont No")
    notes = models.TextField(blank=True, null=True, verbose_name="Açıklama / Detay")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Kaydı Oluşturan"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Harcama / Gider Kaydı"
        verbose_name_plural = "Harcama / Gider Kayıtları"
        ordering = ['-expense_date']

    def __str__(self):
        return f"{self.title} - {self.amount} TL ({self.expense_date})"