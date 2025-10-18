"""Pytest configuration for Django backend tests."""
from __future__ import annotations

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.test_settings')

import django  # noqa: E402

django.setup()
