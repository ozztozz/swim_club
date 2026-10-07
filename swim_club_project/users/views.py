from django.db.models import Count, Q
from django.views.decorators.http import require_POST
# apps/users/views.py

from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    login,
    logout,
    update_session_auth_hash,
)
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from .decorators import role_required
from .forms import UserCreateForm
from .models import User
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

        return redirect("dashboard:index")

    return render(
        request,
        "users/password_change.html",
        {"form": form},
    )


def _setup_link(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return request.build_absolute_uri(reverse("user-set-password", args=[uid, token]))


@role_required(allowed_roles=["admin"])
def user_list_view(request):
    query = request.GET.get("q", "").strip()
    role = request.GET.get("role", "")
    state = request.GET.get("state", "")

    base = User.objects.all()
    counts = {r: base.filter(role=r).count() for r, _ in User.Role.choices}

    users = base.annotate(child_count=Count("children"))
    if role in User.Role.values:
        users = users.filter(role=role)
    if state == "active":
        users = users.filter(is_active=True)
    elif state == "inactive":
        users = users.filter(is_active=False)
    elif state == "pending":
        users = users.filter(password__startswith="!")
    if query:
        users = users.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(phone_number__icontains=query)
        )

    return render(request, "users/user_list.html", {
        "users": users.order_by("first_name", "last_name"),
        "query": query,
        "role": role,
        "state": state,
        "total": base.count(),
        "pending_count": base.filter(password__startswith="!").count(),
        "role_tabs": [(v, l, counts[v]) for v, l in User.Role.choices],
    })


@role_required(allowed_roles=["admin"])
@require_POST
def user_toggle_active_view(request, pk):
    target = get_object_or_404(User, pk=pk)
    if target.pk == request.user.pk:
        messages.error(request, "Kendi hesabınızı pasifleştiremezsiniz.")
    else:
        target.is_active = not target.is_active
        target.save(update_fields=["is_active"])
        messages.success(request, f"{target.get_full_name() or target.username} {'aktifleştirildi' if target.is_active else 'pasifleştirildi'}.")
    return redirect(request.POST.get("next") or "user-list")

@role_required(allowed_roles=["admin"])
def user_create_view(request):
    form = UserCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        messages.success(request, "Kullanıcı oluşturuldu. Şifre belirleme bağlantısını paylaşın.")
        return redirect("user-invite", pk=user.pk)
    return render(request, "users/user_create.html", {"form": form})


@role_required(allowed_roles=["admin"])
def user_invite_view(request, pk):
    target = get_object_or_404(User, pk=pk)
    return render(request, "users/user_invite.html", {
        "target": target,
        "setup_link": _setup_link(request, target),
        "has_password": target.has_usable_password(),
        "valid_days": settings.PASSWORD_RESET_TIMEOUT // 86400,
    })


def set_password_view(request, uidb64, token):
    """Yöneticinin paylaştığı bağlantıyla kullanıcının şifre belirlemesi (giriş gerekmez)."""
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uidb64)))
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        return render(request, "users/set_password.html", {"invalid": True}, status=400)

    form = SetPasswordForm(user, request.POST or None)
    for field in form.fields.values():
        field.widget.attrs.update({"class": "ui-input"})

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Şifreniz belirlendi. Kullanıcı adınız: {user.username}")
        return redirect("user-login")

    return render(request, "users/set_password.html", {"form": form, "target": user})