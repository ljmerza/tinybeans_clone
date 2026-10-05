"""The per-user measurement units preference (imperial or metric)."""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from mysite.users.models import User


@pytest.fixture
def user():
    return User.objects.create_user(email="units@example.com", password="password123")


@pytest.fixture
def client(user):
    api_client = APIClient()
    api_client.force_authenticate(user=user)
    return api_client


def profile_user(response):
    data = response.data.get("data", response.data)
    return data["user"]


@pytest.mark.django_db
class TestMeasurementUnits:
    def test_defaults_to_imperial(self, client, user):
        assert user.measurement_units == "imperial"
        response = client.get(reverse("user-profile"))

        assert response.status_code == status.HTTP_200_OK
        assert profile_user(response)["measurement_units"] == "imperial"

    def test_patch_saves_metric(self, client, user):
        response = client.patch(reverse("user-profile"), {"measurement_units": "metric"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert profile_user(response)["measurement_units"] == "metric"
        user.refresh_from_db()
        assert user.measurement_units == "metric"

    def test_patch_rejects_unknown_units(self, client, user):
        response = client.patch(reverse("user-profile"), {"measurement_units": "furlongs"}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        user.refresh_from_db()
        assert user.measurement_units == "imperial"
