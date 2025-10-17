"""Pytest configuration for Django backend tests."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
APP_ROOT = Path(__file__).resolve().parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(APP_ROOT) not in sys.path:
    sys.path.insert(1 if len(sys.path) > 0 else 0, str(APP_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.test_settings')

import django  # noqa: E402

django.setup()
