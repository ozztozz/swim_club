# finance/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.finance_dashboard, name='finance-dashboard'),
    path('payment/<int:pk>/mark-paid/', views.mark_payment_paid_htmx, name='finance-mark-paid'),
    path('fee-management/', views.fee_management, name='fee-management'),
    path('fee-management/team/<int:team_id>/update/', views.update_team_fee, name='update-team-fee'),
    path('fee-management/athlete/<int:athlete_id>/custom/', views.add_athlete_custom_fee, name='add-athlete-custom-fee'),
]