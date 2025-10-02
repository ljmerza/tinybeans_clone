"""
Pytest configuration for tests.
Ensures tests run with test_settings and don't rely on external services.
"""
import os
import django
from django.conf import settings

# Set Django settings module for tests
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.test_settings')

# Setup Django
django.setup()
