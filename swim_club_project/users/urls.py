# apps/users/urls.py

from django.urls import path

from .views import (
    password_change_view,
    set_password_view,
    user_create_view,
    user_toggle_active_view,
    user_invite_view,
    user_list_view,
    user_login_view,
    user_logout_view,
)


urlpatterns = [
    path("login/", user_login_view, name="user-login"),
    path("logout/", user_logout_view, name="user-logout"),
    path("password-change/",password_change_view,name="password-change"),
    path("users/", user_list_view, name="user-list"),
    path("users/<int:pk>/toggle-active/", user_toggle_active_view, name="user-toggle-active"),
    path("users/new/", user_create_view, name="user-create"),
    path("users/<int:pk>/invite/", user_invite_view, name="user-invite"),
    path("set-password/<uidb64>/<token>/", set_password_view, name="user-set-password"),
]
