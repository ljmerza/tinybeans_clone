"""Shared test fixtures for circle invitation tests."""
import pytest
from rest_framework.test import APIClient

from mysite.circles.models import Circle, CircleMembership
from mysite.users.models import User, UserRole


@pytest.fixture
def api_client():
    """Return an API client instance."""
    return APIClient()


@pytest.fixture
def admin_user(db):
    """Create an admin user with verified email."""
    user = User.objects.create_user(
        email='admin@example.com',
        password='password123'
    )
    user.email_verified = True
    user.save()
    return user


@pytest.fixture
def member_user(db):
    """Create a regular member user."""
    return User.objects.create_user(
        email='member@example.com',
        password='password123'
    )


@pytest.fixture
def circle(admin_user):
    """Create a test circle with the admin as owner."""
    return Circle.objects.create(name='Test Circle', created_by=admin_user)


@pytest.fixture
def circle_with_members(circle, admin_user, member_user):
    """Create a circle with both admin and member memberships."""
    CircleMembership.objects.create(
        user=admin_user,
        circle=circle,
        role=UserRole.CIRCLE_ADMIN
    )
    CircleMembership.objects.create(
        user=member_user,
        circle=circle,
        role=UserRole.CIRCLE_MEMBER
    )
    return circle
