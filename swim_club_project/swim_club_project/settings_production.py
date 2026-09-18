"""Production settings for deployments outside the source directory."""

import os
from pathlib import Path

from .settings import *


DEBUG = False

SECRET_KEY = os.environ["SECRET_KEY"]

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ["ALLOWED_HOSTS"].split(",")
    if host.strip()
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ["CSRF_TRUSTED_ORIGINS"].split(",")
    if origin.strip()
]

DATABASE_DIR = BASE_DIR.parent / "database"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATABASE_DIR / "alpha.sqlite3",
    }
}

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "True").lower() in (
    "true",
    "1",
    "t",
)
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")