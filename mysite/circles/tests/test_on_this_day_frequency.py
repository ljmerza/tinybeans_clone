"""A circle's "On this day" frequency, set by its admins for every member."""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from mysite.circles.models import Circle, CircleMembership
from mysite.users.models import User


@pytest.fixture
def admin():
    return User.objects.create_user(email="admin@example.com", password="password123", email_verified=True)


@pytest.fixture
def member():
    return User.objects.create_user(email="member@example.com", password="password123", email_verified=True)


@pytest.fixture
def circle(admin, member):
    """The creator's admin membership is made by signal."""
    circle = Circle.objects.create(name="Family", created_by=admin)
    CircleMembership.objects.create(user=member, circle=circle)
    return circle


def client_for(user):
    api_client = APIClient()
    api_client.force_authenticate(user=user)
    return api_client


def payload(response):
    return response.data.get("data", response.data)


def url(circle):
    return reverse("circle-detail", args=[circle.id])


@pytest.mark.django_db
class TestCircleOnThisDayFrequency:
    def test_defaults_to_normal(self, circle):
        assert circle.on_this_day_frequency == "normal"

    @pytest.mark.parametrize("frequency", ["off", "less", "more"])
    def test_admin_sets_it_for_the_circle(self, admin, circle, frequency):
        response = client_for(admin).patch(url(circle), {"on_this_day_frequency": frequency}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert payload(response)["circle"]["on_this_day_frequency"] == frequency
        circle.refresh_from_db()
        assert circle.on_this_day_frequency == frequency

    def test_members_cannot_change_it(self, member, circle):
        response = client_for(member).patch(url(circle), {"on_this_day_frequency": "off"}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        circle.refresh_from_db()
        assert circle.on_this_day_frequency == "normal"

    def test_rejects_unknown_frequency(self, admin, circle):
        response = client_for(admin).patch(url(circle), {"on_this_day_frequency": "always"}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        circle.refresh_from_db()
        assert circle.on_this_day_frequency == "normal"

    def test_shown_on_the_circle_settings_page(self, admin, circle):
        response = client_for(admin).get(reverse("circle-member-list", args=[circle.id]))

        assert payload(response)["circle"]["on_this_day_frequency"] == "normal"
