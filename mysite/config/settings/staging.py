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
