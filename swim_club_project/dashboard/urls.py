# dashboard/urls.py

from django.urls import path

from .views import athlete_search, dashboard
from .views_accounts import (
    admin_finance,
    finance_dashboard,
    payment_list,
    payment_list_export,
)

app_name = "dashboard"

urlpatterns = [
    path("", dashboard, name="index"),
    path("athlete-search/", athlete_search, name="athlete-search"),
    path("payment-list/<str:payment_status>/", payment_list, name="payment-list"),
    path("payment-list/<str:payment_status>/export/", payment_list_export, name="payment-list-export"),
    path("admin/finance/", admin_finance, name="admin-finance"),
    path("admin/finance/expenses/", finance_dashboard, name="dashboard-finance"),
]