"""Local development settings."""
import os

os.environ.setdefault('DJANGO_DEBUG', '1')
os.environ.setdefault('DJANGO_ENVIRONMENT', 'local')
os.environ.setdefault('POSTGRES_SSL_MODE', 'prefer')

from .base import *  # noqa: F401,F403

ENVIRONMENT = 'local'

# Disable API throttling for the local development environment.
REST_FRAMEWORK = REST_FRAMEWORK.copy()
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {}

# Ensure django-ratelimit protections remain off while developing locally.
RATELIMIT_ENABLE = False
