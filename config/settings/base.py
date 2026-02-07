from pathlib import Path
import os

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(BASE_DIR / ".env")

DJANGO_ENV = os.getenv("DJANGO_ENV", "dev")
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "0") == "1"
LAUNDRY_NAME = os.getenv("LAUNDRY_NAME", "LaundryPro")

ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "apps.common",
    "apps.accounts",
    "apps.customers",
    "apps.catalog",
    "apps.orders",
    "apps.payments",
    "apps.inventory",
    "apps.reports",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "apps.common.monitoring_middleware.ServerErrorAlertMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.common.middleware.RequestContextMiddleware",
    "apps.common.security_middleware.SessionInactivityMiddleware",
    "apps.common.security_middleware.PasswordRotationMiddleware",
    "apps.common.middleware.LoginRateLimitMiddleware",
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
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": dj_database_url.parse(
        os.getenv("DATABASE_URL", "sqlite:///db.sqlite3"),
        conn_max_age=600,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": int(os.getenv("PASSWORD_MIN_LENGTH", "12"))},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "apps.common.validators.StrongPasswordComplexityValidator"},
]

LANGUAGE_CODE = "es-mx"
TIME_ZONE = "America/Mexico_City"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = int(os.getenv("SESSION_COOKIE_AGE_SECONDS", "28800"))
SESSION_SAVE_EVERY_REQUEST = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

LOGIN_RATE_LIMIT_ENABLED = os.getenv("LOGIN_RATE_LIMIT_ENABLED", "1") == "1"
LOGIN_RATE_LIMIT_MAX_ATTEMPTS = int(os.getenv("LOGIN_RATE_LIMIT_MAX_ATTEMPTS", "5"))
LOGIN_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "900"))
LOGIN_RATE_LIMIT_LOCK_SECONDS = int(os.getenv("LOGIN_RATE_LIMIT_LOCK_SECONDS", "900"))
SESSION_INACTIVITY_TIMEOUT_SECONDS = int(os.getenv("SESSION_INACTIVITY_TIMEOUT_SECONDS", "900"))
PASSWORD_MAX_AGE_DAYS = int(os.getenv("PASSWORD_MAX_AGE_DAYS", "90"))
API_THROTTLE_ANON_IP_RATE = os.getenv("API_THROTTLE_ANON_IP_RATE", "60/min")
API_THROTTLE_USER_RATE = os.getenv("API_THROTTLE_USER_RATE", "240/min")
API_THROTTLE_SENSITIVE_USER_RATE = os.getenv("API_THROTTLE_SENSITIVE_USER_RATE", "60/min")
CASH_DIFF_ALERT_THRESHOLD = os.getenv("CASH_DIFF_ALERT_THRESHOLD", "200.00")

CORS_ALLOWED_ORIGINS = []

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "apps.common.throttling.APIAnonIPRateThrottle",
        "apps.common.throttling.APIUserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "api_anon_ip": API_THROTTLE_ANON_IP_RATE,
        "api_user": API_THROTTLE_USER_RATE,
        "api_sensitive_user": API_THROTTLE_SENSITIVE_USER_RATE,
    },
    "EXCEPTION_HANDLER": "apps.common.api_exception_handler.custom_exception_handler",
}

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "security": {
            "format": "%(asctime)s %(levelname)s %(name)s path=%(path)s method=%(method)s status=%(status_code)s reason=%(reason)s ip=%(ip)s user_id=%(user_id)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "security",
        },
    },
    "loggers": {
        "security": {
            "handlers": ["console"],
            "level": os.getenv("SECURITY_LOG_LEVEL", "WARNING"),
            "propagate": False,
        },
    },
}
