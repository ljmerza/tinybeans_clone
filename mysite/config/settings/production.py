"""Production environment settings."""

import os

from django.core.exceptions import ImproperlyConfigured

os.environ.setdefault("DJANGO_DEBUG", "0")
os.environ.setdefault("DJANGO_ENVIRONMENT", "production")

from .base import *  # noqa: F401,F403

ENVIRONMENT = "production"

# Harden critical toggles for production deployments.
SECURE_SSL_REDIRECT = True
# Container healthchecks and Prometheus call these over plain HTTP from inside
# Docker or the LAN; a 301 to https would fail them. SecurityMiddleware matches
# these against the path without its leading slash ("health/", "metrics").
# /metrics still needs its bearer token, and the image's nginx only proxies it
# from loopback, Docker and private ranges.
SECURE_REDIRECT_EXEMPT = [r"^health/", r"^metrics$"]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "Strict"
CSRF_COOKIE_SAMESITE = "Strict"

EMAIL_VERIFICATION_TOKEN_TTL_HOURS = 24
EMAIL_VERIFICATION_TOKEN_TTL_SECONDS = EMAIL_VERIFICATION_TOKEN_TTL_HOURS * 60 * 60

if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("ALLOWED_HOSTS must be configured for production environments.")
