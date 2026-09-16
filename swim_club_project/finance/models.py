from io import BytesIO

from django.core.files.base import ContentFile
from django.db import models
from django.conf import settings
from datetime import date
from athletes.models import Athlete,Team
from PIL import Image


class TeamFeeHistory(models.Model):
    """Takımların tarih bazlı fiyat geçmişi"""
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='fee_histories')
    monthly_fee = models.IntegerField()
    start_date = models.DateField(help_text="Fiyatın geçerli olmaya başladığı tarih")
    end_date = models.DateField(null=True, blank=True, help_text="Boş ise halen geçerlidir")

    class Meta:
        ordering = ['-start_date']

class PaymentRecord(models.Model):
    PAYMENT_TYPE_CHOICES = [
        ('fee', 'Aidat'),
        ('donation', 'Bağış'),
        ('membership', 'Üyelik'),
        ('bank_transfer', 'Banka / Havale Geliri'),
        ('equipment_sale', 'Malzeme Satışı'),
        ('sponsorship', 'Sponsorluk'),
        ('camping_fee', 'Kamp Ücreti'),
        ('other', 'Diğer'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('bank', 'Banka Transferi / EFT / Havale'),
        ('cash', 'Nakit'),
        ('credit_card', 'Kredi Kartı'),
        ('other', 'Diğer'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Bekliyor'),
        ('paid', 'Ödendi'),
        ('cancelled', 'İptal Edildi'),
    ]

    athlete = models.ForeignKey(
        Athlete, 
        on_delete=models.CASCADE, 
        related_name='payments',
        verbose_name="Sporcu",
        null=True,  # Sporcuya bağlı olmayan genel kulüp bağışları/gelirleri için null yapılabilir
        blank=True
    )
    payment_type = models.CharField(
        max_length=30,
        choices=PAYMENT_TYPE_CHOICES,
        default='fee',
        verbose_name="Ödeme Türü"
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='bank',
        verbose_name="Ödeme Yöntemi"
    )
    period = models.CharField(
        max_length=7, 
        db_index=True,
        help_text="Format: YYYY-MM (Örn: 2026-08)",
        verbose_name="Gelir Dönemi"
    )
    amount = models.IntegerField(
        verbose_name="Tutar (TL)"
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
        verbose_name="Not / Dekont No / Açıklama"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Gelir Kaydı"
        verbose_name_plural = "Gelir Kayıtları"
        # Unique kısıtı sadece 'aidat' türündeki ödemeler için geçerli olsun diye kaldırma veya şartlı kısıtlama yapılabilir.
        # Aidatlarda aynı sporcu aynı ay mükerrer olmasın:
        #unique_together = ['athlete', 'period', 'payment_type']
        ordering = ['-period', 'created_at']

    def __str__(self):
        athlete_str = self.athlete.get_full_name() if self.athlete else "Genel Kulüp Geliri"
        return f"{athlete_str} - {self.get_payment_type_display()} ({self.period}): {self.amount} TL"

    @property
    def is_overdue(self):
        if self.status == 'pending' and self.due_date < date.today():
            return True
        return False


class Equipment(models.Model):
    name = models.CharField(max_length=150, verbose_name="Malzeme Türü")
    colors = models.JSONField(default=list, blank=True, verbose_name='Renk seçenekleri')
    sizes = models.JSONField(default=list, blank=True, verbose_name='Beden seçenekleri')
    price = models.IntegerField(verbose_name="Fiyat")
    is_active = models.BooleanField(default=True, verbose_name="Aktif mi?")

    class Meta:
        verbose_name = "Malzeme"
        verbose_name_plural = "Malzemeler"
        ordering = ['name']

    @property
    def display_name(self):
        return self.name

    @property
    def variant_summary(self):
        parts = []
        if self.colors:
            parts.append(f'Renk: {", ".join(self.colors)}')
        if self.sizes:
            parts.append(f'Beden: {", ".join(self.sizes)}')
        return ' · '.join(parts)

    def __str__(self):
        return self.display_name


class EquipmentImage(models.Model):
    MAX_IMAGE_SIZE = (800, 800)
    JPEG_QUALITY = 72

    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='Malzeme',
    )
    image = models.ImageField(
        upload_to='equipment_images/',
        verbose_name='Görsel',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'pk']
        verbose_name = 'Malzeme görseli'
        verbose_name_plural = 'Malzeme görselleri'

    def save(self, *args, **kwargs):
        if self.image and (self._state.adding or getattr(self.image, '_committed', True) is False):
            output = BytesIO()
            with Image.open(self.image) as opened_image:
                opened_image.thumbnail(self.MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)

                if opened_image.mode in ('RGBA', 'LA') or 'transparency' in opened_image.info:
                    source = Image.new('RGB', opened_image.size, 'white')
                    alpha = opened_image.convert('RGBA')
                    source.paste(alpha, mask=alpha.getchannel('A'))
                else:
                    source = opened_image.convert('RGB')

                source.save(
                    output,
                    format='JPEG',
                    quality=self.JPEG_QUALITY,
                    optimize=True,
                    progressive=True,
                )
            filename = f'{self.image.name.rsplit(".", 1)[0]}.jpg'
            self.image.save(filename, ContentFile(output.getvalue()), save=False)

        super().save(*args, **kwargs)


class EquipmentSaleItem(models.Model):
    payment = models.ForeignKey(
        PaymentRecord,
        on_delete=models.CASCADE,
        related_name='equipment_sale_items',
        verbose_name='Satış',
    )
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.PROTECT,
        related_name='sale_items',
        verbose_name='Malzeme',
    )
    quantity = models.PositiveIntegerField(verbose_name='Adet')
    unit_price = models.IntegerField(verbose_name='Satış Birim Fiyatı')
    selected_color = models.CharField(max_length=50, blank=True, default='', verbose_name='Seçilen renk')
    selected_size = models.CharField(max_length=20, blank=True, default='', verbose_name='Seçilen beden')

    class Meta:
        verbose_name = 'Malzeme Satış Satırı'
        verbose_name_plural = 'Malzeme Satış Satırları'

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    def __str__(self):
        variant = ' / '.join(filter(None, (self.selected_color, self.selected_size)))
        suffix = f' ({variant})' if variant else ''
        return f'{self.equipment.name}{suffix} x{self.quantity}'


class EquipmentStockMovement(models.Model):
    MOVEMENT_TYPES = [
        ('stock_in', 'Stok girişi'),
        ('coach_transfer', 'Antrenöre teslim'),
        ('athlete_distribution', 'Sporcuya dağıtım'),
        ('coach_return', 'Antrenörden iade'),
    ]

    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.PROTECT,
        related_name='stock_movements',
        verbose_name='Malzeme',
    )
    movement_type = models.CharField(max_length=30, choices=MOVEMENT_TYPES)
    quantity = models.PositiveIntegerField(verbose_name='Adet')
    selected_color = models.CharField(max_length=50, blank=True, default='', verbose_name='Renk')
    selected_size = models.CharField(max_length=20, blank=True, default='', verbose_name='Beden')
    coach = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='equipment_stock_movements',
        verbose_name='Antrenör',
    )
    athlete = models.ForeignKey(
        Athlete,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='equipment_distributions',
        verbose_name='Sporcu',
    )
    payment = models.ForeignKey(
        PaymentRecord,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movement',
        verbose_name='Tahsilat kaydı',
    )
    sale_item = models.ForeignKey(
        'EquipmentSaleItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements',
        verbose_name='Satış satırı',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_stock_movements',
    )
    notes = models.TextField(blank=True, default='', verbose_name='Not')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-pk']
        verbose_name = 'Malzeme stok hareketi'
        verbose_name_plural = 'Malzeme stok hareketleri'

    def __str__(self):
        return f'{self.get_movement_type_display()} - {self.equipment} x{self.quantity}'


class ExpenseCategory(models.Model):
    """Harcama Kategorileri (örn: Havuz Kirası, Personel Maaşı, Ekipman, Organizasyon)"""
    name = models.CharField(max_length=100, verbose_name="Kategori Adı")
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        verbose_name="Üst Kategori",
    )
    description = models.TextField(blank=True, null=True, verbose_name="Açıklama")

    class Meta:
        verbose_name = "Gider Kategorisi"
        verbose_name_plural = "Gider Kategorileri"

    def __str__(self):
        return self.name


class Expense(models.Model):
    """Kulüp Harcama/Gider Kaydı"""
    STATUS_CHOICES = [
        ('pending', 'Bekliyor'),
        ('paid', 'Ödendi'),
        ('cancelled', 'İptal Edildi'),
    ]

    category = models.ForeignKey(
        ExpenseCategory, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='expenses',
        verbose_name="Kategori"
    )
    regular_expense = models.ForeignKey(
        'RegularExpense',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_expenses',
        verbose_name="Düzenli gider kaynağı"
    )
    amount = models.IntegerField(verbose_name="Tutar (TL)")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Gider Durumu",
    )
    reciever = models.CharField(
        null=True, 
        blank=True,
        max_length=200, 
        verbose_name="Alıcı / Firma / Kişi")
    expense_date = models.DateField(verbose_name="Harcama Tarihi")
    is_active = models.BooleanField(default=True, verbose_name="Aktif mi?")
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
    updated_at = models.DateTimeField(auto_now=True)
   
    class Meta:
        verbose_name = "Gider Kaydı"
        verbose_name_plural = "Gider Kayıtları"
        ordering = ['updated_at']

    def save(self, *args, **kwargs):
        if self.expense_date:
            self.period = self.expense_date.strftime('%Y-%m')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category.name} - {self.amount} TL ({self.expense_date})"

class RegularExpense(models.Model):
    """Düzenli Giderler (örn: Havuz Kirası, Personel Maaşı)"""
    category = models.ForeignKey(
        ExpenseCategory, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='regular_expenses',
        verbose_name="Kategori"
    )
    amount = models.IntegerField(verbose_name="Tutar (TL)")
    reciever = models.CharField(max_length=200, verbose_name="Alıcı / Firma / Kişi")
    start_date = models.DateField(verbose_name="Başlangıç Tarihi")
    end_date = models.DateField(null=True, blank=True, verbose_name="Bitiş Tarihi (Opsiyonel)")
    frequency = models.CharField(
        max_length=20,
        choices=[
            ('monthly', 'Aylık'),
            ('quarterly', '3 Aylık'),
            ('yearly', 'Yıllık'),
        ],
        default='monthly',
        verbose_name="Frekans"
    )
    paymentDay = models.PositiveSmallIntegerField(
        default=1,
        null=True,
        blank=True,
        verbose_name="Ödeme Günü",
        help_text="Örn: 15, 30. Boş bırakılırsa ödeme günü belirtilmemiş olur."
    )
    notes = models.TextField(blank=True, null=True, verbose_name="Açıklama / Detay")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Kaydı Oluşturan"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Düzenli Gider"
        verbose_name_plural = "Düzenli Giderler"
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.category.name} - {self.amount} TL ({self.frequency})"