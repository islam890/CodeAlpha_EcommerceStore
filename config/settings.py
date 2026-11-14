"""Django settings for the CodeAlpha E-Commerce Store."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() in {"1", "true", "yes"}
ENVIRONMENT = os.environ.get("DJANGO_ENV", "development").lower()
DEVELOPMENT_SECRET_KEY = "phase-two-development-key-do-not-use-in-production"
INSECURE_PRODUCTION_SECRET_KEYS = {
    DEVELOPMENT_SECRET_KEY,
    "replace-this-development-secret",
}
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")


def parse_allowed_hosts(raw_hosts):
    return [host.strip() for host in raw_hosts.split(",") if host.strip()]


ALLOWED_HOSTS = parse_allowed_hosts(
    os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost")
)


def validate_production_configuration(
    *, environment, debug, secret_key, allowed_hosts, allowed_hosts_configured=None
):
    if environment not in {"development", "production"}:
        raise ImproperlyConfigured("DJANGO_ENV must be development or production.")
    if environment == "production" and debug:
        raise ImproperlyConfigured("DJANGO_DEBUG must be False when DJANGO_ENV=production.")
    if not secret_key:
        if environment == "production" or not debug:
            raise ImproperlyConfigured(
                "DJANGO_SECRET_KEY must be set when production settings are active."
            )
        return DEVELOPMENT_SECRET_KEY
    if environment == "production" and (
        secret_key in INSECURE_PRODUCTION_SECRET_KEYS or len(secret_key) < 50
    ):
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY must be a unique, sufficiently strong production secret."
        )
    hosts_configured = (
        allowed_hosts_configured
        if allowed_hosts_configured is not None
        else bool(allowed_hosts)
    )
    if environment == "production" and (not allowed_hosts or not hosts_configured):
        raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must contain a production host.")
    return secret_key


SECRET_KEY = validate_production_configuration(
    environment=ENVIRONMENT,
    debug=DEBUG,
    secret_key=SECRET_KEY,
    allowed_hosts=ALLOWED_HOSTS,
)


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).lower() in {"1", "true", "yes"}


def validate_production_security(
    *,
    environment,
    secure_ssl_redirect,
    session_cookie_secure,
    csrf_cookie_secure,
    hsts_seconds,
):
    if environment != "production":
        return
    if not secure_ssl_redirect:
        raise ImproperlyConfigured("SECURE_SSL_REDIRECT must be enabled in production.")
    if not session_cookie_secure:
        raise ImproperlyConfigured("SESSION_COOKIE_SECURE must be enabled in production.")
    if not csrf_cookie_secure:
        raise ImproperlyConfigured("CSRF_COOKIE_SECURE must be enabled in production.")
    if hsts_seconds <= 0:
        raise ImproperlyConfigured("SECURE_HSTS_SECONDS must be positive in production.")


SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT")
SESSION_COOKIE_SECURE = env_bool("DJANGO_SESSION_COOKIE_SECURE")
CSRF_COOKIE_SECURE = env_bool("DJANGO_CSRF_COOKIE_SECURE")
try:
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_SECURE_HSTS_SECONDS", "0"))
except ValueError as exc:
    raise ImproperlyConfigured("DJANGO_SECURE_HSTS_SECONDS must be an integer.") from exc
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS")
SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD")
validate_production_security(
    environment=ENVIRONMENT,
    secure_ssl_redirect=SECURE_SSL_REDIRECT,
    session_cookie_secure=SESSION_COOKIE_SECURE,
    csrf_cookie_secure=CSRF_COOKIE_SECURE,
    hsts_seconds=SECURE_HSTS_SECONDS,
)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.accounts",
    "apps.catalog",
    "apps.cart",
    "apps.orders",
    "apps.reviews",
    "apps.wishlist",
    "apps.dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.cart.context_processors.cart_summary",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:profile"
LOGOUT_REDIRECT_URL = "home"
