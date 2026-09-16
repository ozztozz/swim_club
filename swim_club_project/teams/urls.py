from django.urls import path

from . import views


urlpatterns = [
    path('', views.team_list, name='team-list'),
    path('new/', views.team_create, name='team-create'),
    path('schedule/', views.team_schedule_home, name='team-schedule-home'),
    path('<int:pk>/', views.team_detail, name='team-detail'),
    path('<int:pk>/schedule/', views.team_schedule, name='team-schedule'),
    path('<int:pk>/schedule/new/', views.team_schedule_create, name='team-schedule-create'),
    path('<int:pk>/schedule/<int:schedule_pk>/edit/', views.team_schedule_update, name='team-schedule-update'),
    path('<int:pk>/schedule/<int:schedule_pk>/delete/', views.team_schedule_delete, name='team-schedule-delete'),
    path('attendance/', views.training_attendance, name='training-attendance'),
    path('attendance/team/<int:team_pk>/', views.training_attendance_team, name='training-attendance-team'),
    path('attendance/team/<int:team_pk>/schedule/<int:schedule_pk>/', views.training_attendance_schedule, name='training-attendance-schedule'),
    path('attendance/team/<int:team_pk>/schedule/<int:schedule_pk>/save/', views.training_attendance_save, name='training-attendance-save'),
    path('<int:pk>/edit/', views.team_update, name='team-update'),
]