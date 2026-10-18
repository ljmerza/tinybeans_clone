"""Shared fixtures for the agent API tests."""

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache

from mysite.circles.models import Circle, CircleMembership
from mysite.users.models import UserRole

from .helpers import bearer_client, create_token

User = get_user_model()


@pytest.fixture(autouse=True)
def _agent_api_on(settings):
    settings.AGENT_API_ENABLED = True
    cache.clear()  # throttles and re-auth codes
    mail.outbox = []
    yield
    cache.clear()


@pytest.fixture
def admin(db):
    """Creates the circle, so the signal makes them its admin."""
    return User.objects.create_user(
        email="agent-admin@example.com",
        password="Passw0rd!",
        first_name="Ada",
        last_name="Admin",
        email_verified=True,
    )


@pytest.fixture
def circle(admin):
    return Circle.objects.create(name="Agent Family", created_by=admin)


@pytest.fixture
def co_admin(circle):
    user = User.objects.create_user(
        email="agent-coadmin@example.com", password="Passw0rd!", first_name="Cora", email_verified=True
    )
    CircleMembership.objects.create(user=user, circle=circle, role=UserRole.CIRCLE_ADMIN)
    return user


@pytest.fixture
def member(circle):
    user = User.objects.create_user(
        email="agent-member@example.com",
        password="Passw0rd!",
        first_name="Grandma",
        last_name="Jo",
        email_verified=True,
    )
    CircleMembership.objects.create(user=user, circle=circle)
    return user


@pytest.fixture
def other_circle(admin):
    """A second circle the same admin runs; tokens for ``circle`` must never see it."""
    return Circle.objects.create(name="Other Family", created_by=admin)


@pytest.fixture
def token_pair(circle, admin):
    return create_token(circle, admin)


@pytest.fixture
def token(token_pair):
    return token_pair[0]


@pytest.fixture
def raw(token_pair):
    return token_pair[1]


@pytest.fixture
def agent(raw):
    return bearer_client(raw)


@pytest.fixture
def suggest_agent(circle, admin):
    _, raw = create_token(circle, admin, name="Suggester", can_suggest=True)
    return bearer_client(raw)
