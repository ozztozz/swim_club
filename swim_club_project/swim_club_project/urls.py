from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.urls import include, path

from .pwa import manifest, service_worker


urlpatterns = [
    path(
        "manifest.webmanifest",
        manifest,
        name="web-manifest",
    ),
    path(
        "sw.js",
        service_worker,
        name="service-worker",
    ),

    # Kullanıcı / Authentication
    path(
        "",
        include("users.urls"),
    ),

    # Merkezi Dashboard
    path(
        "dashboard/",
        include("dashboard.urls"),
    ),

    # Ana sayfa
    path(
        "",
        lambda request: redirect("dashboard:index"),
    ),

    path(
        "admin/",
        admin.site.urls,
    ),

    # Sporcular
    path(
        "athletes/manage/",
        include("athletes.web_urls"),
    ),

    # Diğer sporcu URL'leri
    path(
        "",
        include("athletes.urls"),
    ),

    # Finans
    path(
        "finance/",
        include("finance.urls"),
    ),

    # Takımlar
    path(
        "teams/",
        include("teams.urls"),
    ),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )