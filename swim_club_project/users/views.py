# apps/users/views.py

from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    login,
    logout,
    update_session_auth_hash,
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import redirect, render


def user_login_view(request):
    """
    Kullanıcı giriş işlemi.

    Başarılı girişten sonra tüm kullanıcılar merkezi dashboard'a gider.
    Rol bazlı yönlendirme burada yapılmaz.
    """

    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is not None:
            login(request, user)
            return redirect("dashboard:index")

        messages.error(
            request,
            "Hatalı kullanıcı adı veya şifre.",
        )

    return render(request, "users/login.html")


def user_logout_view(request):
    """
    Kullanıcının oturumunu kapatır ve login sayfasına döner.
    """

    logout(request)
    return redirect("user-login")


@login_required(login_url="user-login")
def password_change_view(request):
    """
    Kullanıcının kendi şifresini değiştirmesini sağlar.
    """

    form = PasswordChangeForm(
        request.user,
        request.POST or None,
    )

    for field in form.fields.values():
        field.widget.attrs.update({
            "class": (
                "input input-bordered "
                "h-11 min-h-0 w-full rounded-xl "
                "border-base-300/80 bg-base-100 px-3 text-sm "
                "outline-none focus:border-primary/50 "
                "focus:outline-none focus:ring-2 "
                "focus:ring-primary/10"
            ),
        })

    if request.method == "POST" and form.is_valid():
        user = form.save()

        # Şifre değiştikten sonra kullanıcının oturumunu düşürmez.
        update_session_auth_hash(request, user)

        messages.success(
            request,
            "Şifreniz başarıyla değiştirildi.",
        )

        return redirect("password-change")

    return render(
        request,
        "users/password_change.html",
        {"form": form},
    )