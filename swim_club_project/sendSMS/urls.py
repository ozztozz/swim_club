from django.urls import path
from .views import send_sms

urlpatterns = [
    path('send/', send_sms, name='send-sms'),
]