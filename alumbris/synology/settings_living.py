"""Isolated staging settings; financial integrations remain disabled."""

import os

from .settings_defaults import *  # noqa: F403
from .settings_defaults import CACHES, MIDDLEWARE

DEBUG = False
ALUMBRIS_CURRENCY = "EUR"
LANGUAGE_CODE = "pt-pt"
LANGUAGES = [("pt-pt", "Português"), ("en", "English")]
TIME_ZONE = "Europe/Lisbon"
BASE_URL = os.environ.get("LIVING_BASE_URL", "https://localhost:18443")
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "web", "testserver"]
CSRF_TRUSTED_ORIGINS = [BASE_URL]
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = CSRF_COOKIE_SAMESITE = "Lax"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = False
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_REFERRER_POLICY = "same-origin"
STATIC_ROOT = "/data/static"
MEDIA_ROOT = "/data/media"
SMEDIA_ROOT = "/data/smedia"
MIDDLEWARE = tuple(MIDDLEWARE)
CACHES["default"]["LOCATION"] = "redis://redis:6379/2"
CELERY_BROKER_URL = "redis://redis:6379/0"
# No scheduler/worker is started; no outbound real-world notifications or bank operations.
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
FINANCIAL_ACCOUNTING_DEFAULT_BACKEND = "staging_dummy"
FINANCIAL_ACCOUNTING_BACKENDS = {
    "staging_dummy": {
        "BACKEND": "finance.accounting.DummyBook",
        "OPTIONS": {"SAVE_TRANSACTIONS": True},
    }
}
ALLOW_IMPORT = False
COHIVA_REPORT_API_TOKEN = ""
ALUMBRIS_RESIDENT_DOCUMENT_TYPES = ()
