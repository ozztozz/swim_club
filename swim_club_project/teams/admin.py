# teams/admin.py
from django.contrib import admin
from .models import Team

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'monthly_fee', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    filter_horizontal = ('coaches',)