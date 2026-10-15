from django.urls import path
from .views import  bulten_kaydet_api

urlpatterns = [

    path('bulten/bulten-kaydet-x92f8a71c/', bulten_kaydet_api, name='bulten-kaydet-api'),
]