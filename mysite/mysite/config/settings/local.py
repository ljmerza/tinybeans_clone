"""Local development settings."""
import os

os.environ.setdefault('DJANGO_DEBUG', '1')
os.environ.setdefault('DJANGO_ENVIRONMENT', 'local')

from .base import *  # noqa: F401,F403

ENVIRONMENT = 'local'
