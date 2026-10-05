# dashboard/views.py

from django.contrib.auth.decorators import login_required

from django.shortcuts import render
from users.models import User
from .views_accounts import _get_admin_dashboard_context
from .views_coach import _get_coach_dashboard_context
@login_required(login_url="user-login")
def dashboard(request):
    """
    Tüm kullanıcıların giriş sonrası geldiği merkezi dashboard.
    Dashboard içeriği kullanıcının rolüne göre belirlenir.
    """

    role = request.user.role

    context = {
        "dashboard_role": role,
    }

    if role == User.Role.ADMIN:
        template = "dashboard/admin.html"

        context.update(
            _get_admin_dashboard_context()
        )

    elif role == User.Role.COACH:
        template = "dashboard/coach.html"
        context.update(_get_coach_dashboard_context(request.user))

    elif role == User.Role.FINANCE:
        template = "dashboard/finance.html"

    elif role == User.Role.PARENT:
        template = "dashboard/parent.html"

    else:
        template = "dashboard/unknown.html"

    return render(
        request,
        template,
        context,
    )

@login_required(login_url="user-login")
def athlete_search(request):
    # Implement the athlete search view logic here
    return render(request, "dashboard/partials/_athlete_search.html", {})
    