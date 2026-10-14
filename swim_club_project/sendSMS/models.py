from django.db import models

# Create your models here.
# models.py
from django.db import models

class GunlukBulten(models.Model):
    baslik = models.CharField(max_length=255)
    icerik_html = models.TextField()  # veya icerik_markdown
    yayin_tarihi = models.DateField(auto_now_add=True)
    aktif = models.BooleanField(default=True)

    class Meta:
        ordering = ['-yayin_tarihi']

    def __str__(self):
        return f"{self.yayin_tarihi} - {self.baslik}"