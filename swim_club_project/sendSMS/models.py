from django.db import models

class GunlukBulten(models.Model):
    baslik = models.CharField(max_length=255)
    yayin_tarihi = models.DateField(auto_now_add=True)
    icerik_json = models.JSONField(default=dict) # Veriyi saf JSON tutan alan
    icerik_html = models.TextField(blank=True, default="") # Eski kolon hata vermesin diye
    aktif = models.BooleanField(default=True)

    class Meta:
        ordering = ['-yayin_tarihi']

    def __str__(self):
        return f"{self.yayin_tarihi} - {self.baslik}"