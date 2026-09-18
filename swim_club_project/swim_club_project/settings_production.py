"""Production settings for deployments outside the source directory."""

from .settings import *


DEBUG = False

SECRET_KEY = "41wmeVGEKdurlzGzNgYRdhDCOtnmYfA2Wg7Wos90lM36-6BSbzgHWtkXPGOioxsio4ZS0K8-jA0yMve74IDAfg"

ALLOWED_HOSTS = ["ozz1.pythonanywhere.com"]

CSRF_TRUSTED_ORIGINS = ["https://ozz1.pythonanywhere.com"]

DATABASE_DIR = BASE_DIR.parent.parent / "database"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATABASE_DIR / "alpha.sqlite3",
    }
}

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")