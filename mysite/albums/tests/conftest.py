"""Shared fixtures for the albums tests."""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from mysite.circles.models import Circle, CircleMembership

User = get_user_model()


class FakeStorageBackend:
    """Deterministic stand-in for the MinIO backend."""

    def get_url(self, storage_key, expires_in=3600):
        return f"https://cdn.test/{storage_key}"


@pytest.fixture(autouse=True)
def fake_storage():
    """Serve predictable URLs instead of presigning against MinIO."""
    with patch("mysite.keeps.storage.get_storage_backend", return_value=FakeStorageBackend()):
        yield


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin():
    """Creates the circle, so the signal makes them its admin."""
    return User.objects.create_user(email="albums-admin@example.com", password="adminpass123")


@pytest.fixture
def circle(admin):
    return Circle.objects.create(name="Albums Family", created_by=admin)


@pytest.fixture
def member(circle):
    user = User.objects.create_user(email="albums-member@example.com", password="memberpass123")
    CircleMembership.objects.create(user=user, circle=circle)
    return user


@pytest.fixture
def other_member(circle):
    user = User.objects.create_user(email="albums-member2@example.com", password="memberpass123")
    CircleMembership.objects.create(user=user, circle=circle)
    return user


@pytest.fixture
def outsider():
    return User.objects.create_user(email="albums-outsider@example.com", password="outsiderpass123")


@pytest.fixture
def other_circle(outsider):
    return Circle.objects.create(name="Other Family", created_by=outsider)
