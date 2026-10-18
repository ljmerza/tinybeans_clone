"""Shared fixtures for the in-app AI tests. Every HTTP call to a provider is mocked."""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from mysite.ai import providers
from mysite.circles.models import Circle, CircleMembership

from .helpers import BASE_URL, MODEL

User = get_user_model()


@pytest.fixture(autouse=True)
def _clean_state():
    cache.clear()  # scan lock and rate limits
    providers._reported.clear()
    yield
    cache.clear()
    providers._reported.clear()


@pytest.fixture(autouse=True)
def no_network():
    """Fail loudly if anything tries a real provider call; tests that call one patch ``post`` themselves."""
    with patch("mysite.ai.client.requests.post", side_effect=AssertionError("unmocked provider call")) as post:
        yield post


@pytest.fixture
def ai_on(settings):
    settings.AI_BASE_URL = BASE_URL
    settings.AI_MODEL = MODEL
    settings.AI_API_KEY = ""
    return settings


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin(db):
    """Creates the circle, so the signal makes them its admin."""
    return User.objects.create_user(email="ai-admin@example.com", password="Passw0rd!", email_verified=True)


@pytest.fixture
def circle(admin):
    return Circle.objects.create(name="AI Family", created_by=admin)


@pytest.fixture
def member(circle):
    user = User.objects.create_user(email="ai-member@example.com", password="Passw0rd!", email_verified=True)
    CircleMembership.objects.create(user=user, circle=circle)
    return user


@pytest.fixture
def outsider(db):
    return User.objects.create_user(email="ai-outsider@example.com", password="Passw0rd!", email_verified=True)


@pytest.fixture
def other_circle(outsider):
    return Circle.objects.create(name="Other Family", created_by=outsider)


@pytest.fixture
def provider(no_network):
    """The mocked ``requests.post``; set ``return_value`` or ``side_effect`` to answer."""
    no_network.side_effect = None
    return no_network
