# teams/admin.py
from django.contrib import admin
from .models import Team, TeamTrainingAttendance, TeamTrainingSchedule


class TeamTrainingScheduleInline(admin.TabularInline):
    model = TeamTrainingSchedule
    extra = 1

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    filter_horizontal = ('coaches',)
    inlines = (TeamTrainingScheduleInline,)


@admin.register(TeamTrainingSchedule)
class TeamTrainingScheduleAdmin(admin.ModelAdmin):
    list_display = ('team', 'weekday', 'start_time', 'end_time', 'location')
    list_filter = ('weekday',)
    search_fields = ('team__name', 'location')


@admin.register(TeamTrainingAttendance)
class TeamTrainingAttendanceAdmin(admin.ModelAdmin):
    list_display = ('training_date', 'athlete', 'schedule', 'status')
    list_filter = ('status', 'training_date', 'schedule__training_type')
    search_fields = ('athlete__first_name', 'athlete__last_name', 'schedule__team__name')