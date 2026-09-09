# finance/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.finance_dashboard, name='finance-dashboard'),
    path('payments/<str:payment_status>/', views.payment_status_list, name='payment-status-list'),
    path('expenses/', views.expense_list, name='expense-list'),
    path('expenses/summary/', views.expense_summary_htmx, name='expense-summary'),
    path('expenses/new/', views.create_expense_htmx, name='expense-create'),
    path('expenses/<int:pk>/edit/', views.update_expense_htmx, name='expense-update'),
    path('expenses/categories/new/', views.create_expense_category_htmx, name='expense-category-create'),
    path('regular-expenses/', views.regular_expense_list, name='regular-expense-list'),
    path('regular-expenses/new/', views.create_regular_expense_htmx, name='regular-expense-create'),
    path('regular-expenses/<int:pk>/edit/', views.update_regular_expense_htmx, name='regular-expense-update'),
    path('regular-expenses/<int:pk>/convert/', views.convert_regular_expense_htmx, name='regular-expense-convert'),
    path('equipment/', views.equipment_list, name='equipment-list'),
    path('equipment/new/', views.equipment_create, name='equipment-create'),
    path('equipment/<int:pk>/edit/', views.equipment_update, name='equipment-update'),
    path('equipment/<int:pk>/delete/', views.equipment_delete, name='equipment-delete'),
    path('payment/<int:pk>/mark-paid/', views.mark_payment_paid_htmx, name='finance-mark-paid'),
    path('fee-management/', views.fee_management, name='fee-management'),
    path('fee-management/team/<int:team_id>/update/', views.update_team_fee, name='update-team-fee'),
]