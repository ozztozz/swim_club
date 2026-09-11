from django.urls import path

from . import views


urlpatterns = [
    path('', views.athlete_list, name='athlete-manage-list'),
    path('new/', views.athlete_create, name='athlete-manage-create'),
    path('<int:pk>/', views.athlete_detail, name='athlete-manage-detail'),
    path('<int:pk>/payments/<int:payment_id>/pay/', views.athlete_make_payment, name='athlete-manage-payment-by-id'),
    path('<int:athlete_id>/payments/<str:period>/pay/', views.athlete_make_payment, name='athlete-manage-payment'),
    path('<int:pk>/payments/add/', views.athlete_create_payment, name='athlete-manage-payment-create'),
    path('<int:pk>/equipment-sales/add/', views.athlete_create_equipment_sale, name='athlete-manage-equipment-sale-create'),
    path('<int:pk>/equipment-sales/<int:payment_id>/edit/', views.athlete_edit_equipment_sale, name='athlete-manage-equipment-sale-edit'),
    path('<int:pk>/payments/<int:payment_id>/edit/', views.athlete_edit_payment, name='athlete-manage-payment-edit'),
    path('<int:pk>/toggle-active/', views.athlete_toggle_active, name='athlete-manage-toggle-active'),
    path('<int:pk>/edit/', views.athlete_update, name='athlete-manage-update'),
]