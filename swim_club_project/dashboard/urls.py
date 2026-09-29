# dashboard/urls.py

from django.urls import path

from .views import dashboard,athlete_search
from .account_views import payment_status_list


app_name = "dashboard"


urlpatterns = [
    path("",dashboard,name="index",),
    path("athlete-search/", athlete_search, name="athlete-search"),
    path("payment-status/<str:payment_status>/", payment_status_list, name="payment-status-list"),


]