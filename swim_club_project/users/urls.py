# apps/users/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import UserViewSet, UserProfileView

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    # JWT Login & Refresh
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Kullanıcının Kendi Profili
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    
    # Yönetici İşlemleri (CRUD)
    path('', include(router.urls)),
]