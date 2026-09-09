from django.urls import path

from . import views


urlpatterns = [
    path('', views.team_list, name='team-list'),
    path('new/', views.team_create, name='team-create'),
    path('<int:pk>/', views.team_detail, name='team-detail'),
    path('<int:pk>/edit/', views.team_update, name='team-update'),
]