"""Staging environment settings."""
import os

os.environ.setdefault('DJANGO_DEBUG', '0')
os.environ.setdefault('DJANGO_ENVIRONMENT', 'staging')

from .base import *  # noqa: F401,F403

ENVIRONMENT = 'staging'

# Ensure critical security flags remain enabled in staging by default.
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SESSION_COOKIE_SAMESITE = 'Strict'
CSRF_COOKIE_SAMESITE = 'Strict'

EMAIL_VERIFICATION_TOKEN_TTL_HOURS = 48
EMAIL_VERIFICATION_TOKEN_TTL_SECONDS = EMAIL_VERIFICATION_TOKEN_TTL_HOURS * 60 * 60
