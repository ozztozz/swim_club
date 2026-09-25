# athletes/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from athletes.views import parent_dashboard, approve_athlete_htmx, edit_athlete_team_htmx, reject_athlete_htmx, search_approved_athletes_htmx, dashboard_recent_payments_htmx



urlpatterns = [


    path('dashboard/approve/<int:pk>/', approve_athlete_htmx, name='dashboard-approve-athlete'),
    path('dashboard/reject/<int:pk>/', reject_athlete_htmx, name='dashboard-reject-athlete'),
    path('dashboard/search/', search_approved_athletes_htmx, name='dashboard-search-athletes'),
    path('dashboard/recent-payments/', dashboard_recent_payments_htmx, name='dashboard-recent-payments'),
    path('dashboard/athlete/<int:pk>/edit-team/', edit_athlete_team_htmx, name='dashboard-edit-athlete-team'),
    path('parent-dashboard/', parent_dashboard, name='parent-dashboard'),
]