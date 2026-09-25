# apps/users/urls.py

from django.urls import path

from .views import (
    password_change_view,
    user_login_view,
    user_logout_view,
)


urlpatterns = [
    path("login/", user_login_view, name="user-login"),
    path("logout/", user_logout_view, name="user-logout"),
    path("password-change/",password_change_view,name="password-change"),
]