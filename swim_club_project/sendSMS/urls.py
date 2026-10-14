from django.urls import path
from .views import send_sms, bulten_kaydet_api

urlpatterns = [
    path('send/', send_sms, name='send-sms'),
    path('bulten/bulten-kaydet-x92f8a71c/', bulten_kaydet_api, name='bulten-kaydet-api'),
]