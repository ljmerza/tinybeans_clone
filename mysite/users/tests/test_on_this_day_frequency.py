"""The per-user "On this day" frequency preference for the home feed."""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from mysite.users.models import User


@pytest.fixture
def user():
    return User.objects.create_user(email="memories@example.com", password="password123")


@pytest.fixture
def client(user):
    api_client = APIClient()
    api_client.force_authenticate(user=user)
    return api_client


def profile_user(response):
    data = response.data.get("data", response.data)
    return data["user"]


@pytest.mark.django_db
class TestOnThisDayFrequency:
    def test_defaults_to_normal(self, client, user):
        assert user.on_this_day_frequency == "normal"
        response = client.get(reverse("user-profile"))

        assert response.status_code == status.HTTP_200_OK
        assert profile_user(response)["on_this_day_frequency"] == "normal"

    @pytest.mark.parametrize("frequency", ["off", "less", "more"])
    def test_patch_saves_frequency(self, client, user, frequency):
        response = client.patch(reverse("user-profile"), {"on_this_day_frequency": frequency}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert profile_user(response)["on_this_day_frequency"] == frequency
        user.refresh_from_db()
        assert user.on_this_day_frequency == frequency

    def test_patch_rejects_unknown_frequency(self, client, user):
        response = client.patch(reverse("user-profile"), {"on_this_day_frequency": "always"}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        user.refresh_from_db()
        assert user.on_this_day_frequency == "normal"
