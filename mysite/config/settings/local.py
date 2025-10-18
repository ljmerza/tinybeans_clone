"""Local development settings."""
import os

os.environ.setdefault('DJANGO_DEBUG', '1')
os.environ.setdefault('DJANGO_ENVIRONMENT', 'local')
os.environ.setdefault('POSTGRES_SSL_MODE', 'prefer')

from .base import *  # noqa: F401,F403

ENVIRONMENT = 'local'
