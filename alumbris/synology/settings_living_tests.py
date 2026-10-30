"""Run real MariaDB migrations in the disposable staging test database."""

from .settings_living import *  # noqa: F403

# Django's test client is HTTP; production staging remains HTTPS-only.
SECURE_SSL_REDIRECT = False
PASSWORD_HASHERS = ("django.contrib.auth.hashers.MD5PasswordHasher",)
