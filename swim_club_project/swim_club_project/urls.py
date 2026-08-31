"""
URL configuration for swim_club_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

# swim_club_project/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from users.views import user_login_view, user_logout_view  # users view'larınızı içe aktarın

urlpatterns = [
    # Auth Yolları
    path('login/', user_login_view, name='user-login'),
    path('logout/', user_logout_view, name='user-logout'),
    # Kök adrese (/) gelen istekleri doğrudan /dashboard/ adresine yönlendirir
    path('', lambda request: redirect('dashboard-index')),
    
    path('admin/', admin.site.urls),
    path('api/', include('users.urls')),
    path('api/', include('athletes.urls')),
    path('', include('athletes.urls')), # Dashboard URL'lerini dahil etmek için
    path('finance/', include('finance.urls')),
]

# Geliştirme ortamında medya dosyalarını sunmak için
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)