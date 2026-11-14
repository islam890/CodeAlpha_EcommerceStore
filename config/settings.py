"""Django settings for the CodeAlpha E-Commerce Store."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.validators import validate_email

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


def parse_email_bool(environment, setting_name, default=False):
    raw_value = environment.get(setting_name)
    if raw_value is None:
        return default
    value = str(raw_value).strip().lower()
    if value in {"1", "true", "yes"}:
        return True
    if value in {"0", "false", "no"}:
        return False
    raise ImproperlyConfigured(
        f"{setting_name} must be true or false."
    )


def get_email_config(environ=None):
    environment = os.environ if environ is None else environ
    configured_environment = str(
        environment.get("DJANGO_ENV", ENVIRONMENT)
    ).strip().lower()
    requested_backend = environment.get("DJANGO_EMAIL_BACKEND")
    if requested_backend is None or not str(requested_backend).strip():
        requested_backend = "smtp" if configured_environment == "production" else "console"
    backend = str(requested_backend).strip().lower()
    backend_aliases = {
        "console": "django.core.mail.backends.console.EmailBackend",
        "django.core.mail.backends.console.emailbackend": "django.core.mail.backends.console.EmailBackend",
        "smtp": "django.core.mail.backends.smtp.EmailBackend",
        "django.core.mail.backends.smtp.emailbackend": "django.core.mail.backends.smtp.EmailBackend",
    }
    if backend not in backend_aliases:
        raise ImproperlyConfigured(
            "DJANGO_EMAIL_BACKEND must be console or smtp."
        )
    email_backend = backend_aliases[backend]
    if configured_environment == "production" and email_backend != backend_aliases["smtp"]:
        raise ImproperlyConfigured(
            "Production email must use the SMTP backend."
        )

    host = str(environment.get("DJANGO_EMAIL_HOST", "")).strip()
    from_email = str(environment.get("DJANGO_DEFAULT_FROM_EMAIL", "")).strip()
    if email_backend == backend_aliases["smtp"] and not host:
        raise ImproperlyConfigured(
            "DJANGO_EMAIL_HOST is required for the SMTP email backend."
        )
    if configured_environment == "production" and not from_email:
        raise ImproperlyConfigured(
            "DJANGO_DEFAULT_FROM_EMAIL is required in production."
        )
    if from_email:
        try:
            validate_email(from_email)
        except ValidationError as exc:
            raise ImproperlyConfigured(
                "DJANGO_DEFAULT_FROM_EMAIL must be a valid email address."
            ) from exc

    use_tls = parse_email_bool(environment, "DJANGO_EMAIL_USE_TLS")
    use_ssl = parse_email_bool(environment, "DJANGO_EMAIL_USE_SSL")
    if use_tls and use_ssl:
        raise ImproperlyConfigured(
            "DJANGO_EMAIL_USE_TLS and DJANGO_EMAIL_USE_SSL cannot both be enabled."
        )
    username = str(environment.get("DJANGO_EMAIL_HOST_USER", "")).strip()
    password = environment.get("DJANGO_EMAIL_HOST_PASSWORD", "")
    if bool(username) != bool(password):
        raise ImproperlyConfigured(
            "DJANGO_EMAIL_HOST_USER and DJANGO_EMAIL_HOST_PASSWORD must be provided together."
        )

    return {
        "EMAIL_BACKEND": email_backend,
        "EMAIL_HOST": host,
        "EMAIL_PORT": parse_database_int(
            environment.get("DJANGO_EMAIL_PORT"),
            setting_name="DJANGO_EMAIL_PORT",
            default=25,
            minimum=1,
        ),
        "EMAIL_USE_TLS": use_tls,
        "EMAIL_USE_SSL": use_ssl,
        "EMAIL_HOST_USER": username,
        "EMAIL_HOST_PASSWORD": password,
        "EMAIL_TIMEOUT": parse_database_int(
            environment.get("DJANGO_EMAIL_TIMEOUT"),
            setting_name="DJANGO_EMAIL_TIMEOUT",
            default=10,
            minimum=1,
        ),
        "DEFAULT_FROM_EMAIL": from_email or "webmaster@localhost",
        "SERVER_EMAIL": from_email or "webmaster@localhost",
    }


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


def parse_database_int(raw_value, *, setting_name, default, minimum=0):
    value = str(default) if raw_value is None else str(raw_value).strip()
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ImproperlyConfigured(f"{setting_name} must be an integer.") from exc
    if parsed < minimum:
        raise ImproperlyConfigured(
            f"{setting_name} must be greater than or equal to {minimum}."
        )
    return parsed


def get_database_config(environ=None):
    environment = os.environ if environ is None else environ
    raw_engine = environment.get("DJANGO_DB_ENGINE", "sqlite").strip().lower()
    if raw_engine in {"sqlite", "sqlite3", "django.db.backends.sqlite3"}:
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": environment.get("DJANGO_DB_NAME") or BASE_DIR / "db.sqlite3",
        }
    if raw_engine not in {"postgres", "postgresql", "django.db.backends.postgresql"}:
        raise ImproperlyConfigured(
            "DJANGO_DB_ENGINE must be sqlite or postgresql."
        )

    required = {
        "DJANGO_DB_NAME": environment.get("DJANGO_DB_NAME", "").strip(),
        "DJANGO_DB_USER": environment.get("DJANGO_DB_USER", "").strip(),
        "DJANGO_DB_HOST": environment.get("DJANGO_DB_HOST", "").strip(),
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise ImproperlyConfigured(
            "PostgreSQL configuration is missing: " + ", ".join(missing)
        )

    options = {}
    sslmode = environment.get("DJANGO_DB_SSLMODE", "").strip()
    if sslmode:
        options["sslmode"] = sslmode

    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": required["DJANGO_DB_NAME"],
        "USER": required["DJANGO_DB_USER"],
        "PASSWORD": environment.get("DJANGO_DB_PASSWORD", ""),
        "HOST": required["DJANGO_DB_HOST"],
        "PORT": str(
            parse_database_int(
                environment.get("DJANGO_DB_PORT"),
                setting_name="DJANGO_DB_PORT",
                default=5432,
                minimum=1,
            )
        ),
        "CONN_MAX_AGE": parse_database_int(
            environment.get("DJANGO_DB_CONN_MAX_AGE"),
            setting_name="DJANGO_DB_CONN_MAX_AGE",
            default=0,
            minimum=0,
        ),
        "OPTIONS": options,
    }

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

DATABASES = {"default": get_database_config()}
EMAIL_CONFIG = get_email_config()
EMAIL_BACKEND = EMAIL_CONFIG["EMAIL_BACKEND"]
EMAIL_HOST = EMAIL_CONFIG["EMAIL_HOST"]
EMAIL_PORT = EMAIL_CONFIG["EMAIL_PORT"]
EMAIL_USE_TLS = EMAIL_CONFIG["EMAIL_USE_TLS"]
EMAIL_USE_SSL = EMAIL_CONFIG["EMAIL_USE_SSL"]
EMAIL_HOST_USER = EMAIL_CONFIG["EMAIL_HOST_USER"]
EMAIL_HOST_PASSWORD = EMAIL_CONFIG["EMAIL_HOST_PASSWORD"]
EMAIL_TIMEOUT = EMAIL_CONFIG["EMAIL_TIMEOUT"]
DEFAULT_FROM_EMAIL = EMAIL_CONFIG["DEFAULT_FROM_EMAIL"]
SERVER_EMAIL = EMAIL_CONFIG["SERVER_EMAIL"]

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
