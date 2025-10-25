"""Production environment settings."""
import os

from django.core.exceptions import ImproperlyConfigured

os.environ.setdefault('DJANGO_DEBUG', '0')
os.environ.setdefault('DJANGO_ENVIRONMENT', 'production')

from .base import *  # noqa: F401,F403

ENVIRONMENT = 'production'

# Harden critical toggles for production deployments.
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = 'Strict'
CSRF_COOKIE_SAMESITE = 'Strict'

EMAIL_VERIFICATION_TOKEN_TTL_HOURS = 24
EMAIL_VERIFICATION_TOKEN_TTL_SECONDS = EMAIL_VERIFICATION_TOKEN_TTL_HOURS * 60 * 60

if not ALLOWED_HOSTS:
    raise ImproperlyConfigured('ALLOWED_HOSTS must be configured for production environments.')
