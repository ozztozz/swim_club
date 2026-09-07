from django.urls import path

from . import views


urlpatterns = [
    path('', views.athlete_list, name='athlete-manage-list'),
    path('new/', views.athlete_create, name='athlete-manage-create'),
    path('<int:pk>/', views.athlete_detail, name='athlete-manage-detail'),
    path('<int:pk>/payments/<str:period>/pay/', views.athlete_make_payment, name='athlete-manage-payment'),
    path('<int:pk>/payments/add/', views.athlete_create_payment, name='athlete-manage-payment-create'),
    path('<int:pk>/payments/<str:period>/edit/', views.athlete_edit_payment, name='athlete-manage-payment-edit'),
    path('<int:pk>/toggle-active/', views.athlete_toggle_active, name='athlete-manage-toggle-active'),
    path('<int:pk>/edit/', views.athlete_update, name='athlete-manage-update'),
    path('<int:pk>/delete/', views.athlete_delete, name='athlete-manage-delete'),
]