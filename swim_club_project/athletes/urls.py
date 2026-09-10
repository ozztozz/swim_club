# athletes/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AthleteViewSet
from athletes.views_dashboard import parent_dashboard, dashboard_index, approve_athlete_htmx, edit_athlete_team_htmx, reject_athlete_htmx, search_approved_athletes_htmx, dashboard_recent_payments_htmx

router = DefaultRouter()
router.register(r'athletes', AthleteViewSet, basename='athlete')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', dashboard_index, name='dashboard-index'),
    path('dashboard/approve/<int:pk>/', approve_athlete_htmx, name='dashboard-approve-athlete'),
    path('dashboard/reject/<int:pk>/', reject_athlete_htmx, name='dashboard-reject-athlete'),
    path('dashboard/search/', search_approved_athletes_htmx, name='dashboard-search-athletes'),
    path('dashboard/recent-payments/', dashboard_recent_payments_htmx, name='dashboard-recent-payments'),
    path('dashboard/athlete/<int:pk>/edit-team/', edit_athlete_team_htmx, name='dashboard-edit-athlete-team'),
    path('parent-dashboard/', parent_dashboard, name='parent-dashboard'),
]