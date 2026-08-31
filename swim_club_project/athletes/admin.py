from django.contrib import admin
from .models import Athlete
# Register your models here.
@admin.register(Athlete)
class AthleteAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name',   'birth_date')
    search_fields = ('first_name', 'last_name')
    ordering = ('last_name', 'first_name')

