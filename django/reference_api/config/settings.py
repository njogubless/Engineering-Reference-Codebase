"""Settings for the Django reference API.

One env-driven settings module (12-factor) instead of settings/dev.py,
settings/prod.py, ... The *environment* changes, not the code. See
docs/patterns/26-configuration/README.md.

Rules demonstrated here:
- Required values have no default, so a missing value fails at startup
  (`ImproperlyConfigured`), not on the first request that needs it.
- Defaults are the *safe* production value (DEBUG off, no hosts allowed).
- Invariants between settings are checked at import time.
"""

import os
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

ENVIRONMENTS = ("development", "test", "staging", "production")

env = environ.Env()

# A local .env file is a development convenience only. Deployed environments
# inject real environment variables, and a real variable always wins over
# the file. DJANGO_ENV_FILE lets tests and CI select `.env.test`.
_env_file = Path(os.environ.get("DJANGO_ENV_FILE", BASE_DIR / ".env"))
if _env_file.is_file():
    env.read_env(_env_file, overwrite=False)

ENVIRONMENT = env.str("ENVIRONMENT")
if ENVIRONMENT not in ENVIRONMENTS:
    raise ImproperlyConfigured(f"ENVIRONMENT must be one of {ENVIRONMENTS}, got {ENVIRONMENT!r}")

SECRET_KEY = env.str("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS: list[str] = env.list("ALLOWED_HOSTS", default=[])

if ENVIRONMENT in ("staging", "production"):
    if DEBUG:
        raise ImproperlyConfigured("DEBUG must be off in staging/production.")
    if len(SECRET_KEY) < 50 or SECRET_KEY.startswith("django-insecure"):
        raise ImproperlyConfigured("SECRET_KEY is too weak for a deployed environment.")

# Transport security in deployed environments (hardened further in Phase 14).
if ENVIRONMENT in ("staging", "production"):
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # HSTS is hard to undo (browsers cache it); enable once HTTPS is confirmed everywhere.
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=0)
    # Only trust X-Forwarded-Proto when a trusted proxy sets it.
    if env.bool("TRUST_PROXY_SSL_HEADER", default=False):
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "apps.core",
]

MIDDLEWARE = [
    # First, so every later middleware, view and log line sees the request ID.
    "apps.core.middleware.RequestIdMiddleware",
    # Before CommonMiddleware, so CORS headers are added to every response —
    # including errors; otherwise the browser hides error bodies from the app.
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    # DRF API views are CSRF-exempt unless session auth is used (Phase 3);
    # the middleware protects any form-based views.
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
# API paths are exact (`/health/live`, not `/health/live/`); a redirect would
# turn a POST into a GET in many clients.
APPEND_SLASH = False
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {"default": env.db_url("DATABASE_URL")}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DATABASE_CONN_MAX_AGE", default=60)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
# Fail fast instead of hanging a worker when the database is unreachable.
DATABASES["default"].setdefault("OPTIONS", {})["connect_timeout"] = env.int(
    "DATABASE_CONNECT_TIMEOUT", default=5
)

REDIS_URL = env.str("REDIS_URL")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "KEY_PREFIX": "django-reference",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True  # store and compare aware datetimes in UTC; convert at the edges

# --- CORS ---------------------------------------------------------------------
# Browser origins allowed to call the API. Never "*" with credentials.
CORS_ALLOWED_ORIGINS: list[str] = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_HEADERS = (
    "accept",
    "authorization",
    "content-type",
    "x-request-id",
    "idempotency-key",
)
# Browsers hide response headers from JavaScript unless exposed.
CORS_EXPOSE_HEADERS = ("x-request-id", "retry-after")
CORS_PREFLIGHT_MAX_AGE = 600

# --- Feature flags ----------------------------------------------------------
# Typed, explicit, and listed in one place. `apps.core.features.is_enabled`
# raises on unknown names so a typo cannot silently disable a feature.
# PUBLIC_FEATURES are exposed to clients via GET /api/v1/meta; others stay server-side.
FEATURES: dict[str, bool] = {
    "search_v2": env.bool("FEATURE_SEARCH_V2", default=False),
    "maintenance_banner": env.bool("FEATURE_MAINTENANCE_BANNER", default=False),
}
PUBLIC_FEATURES = ("maintenance_banner",)

# --- Django REST Framework ----------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    # Deny by default: every public endpoint opts out explicitly.
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    # Authentication classes are added in Phase 3 (authentication).
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "UNAUTHENTICATED_USER": None,
    "EXCEPTION_HANDLER": "apps.core.errors.problem_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Reference API (Django)",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# --- Logging ----------------------------------------------------------------
LOG_LEVEL = env.str("LOG_LEVEL", default="INFO")
LOG_FORMAT = env.str("LOG_FORMAT", default="json")  # "json" | "console"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_context": {"()": "apps.core.logging.RequestContextFilter"},
    },
    "formatters": {
        "json": {"()": "apps.core.logging.JsonFormatter"},
        "console": {"format": "%(levelname)s %(name)s [%(request_id)s] %(message)s"},
    },
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "filters": ["request_context"],
            "formatter": LOG_FORMAT,
        },
    },
    "root": {"handlers": ["stdout"], "level": LOG_LEVEL},
    "loggers": {
        # Expected 4xx responses are not operational problems; keep 5xx only.
        "django.request": {"level": "ERROR"},
    },
}
