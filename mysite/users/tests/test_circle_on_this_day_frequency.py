"""Each member's own "On this day" frequency for a circle they belong to."""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from mysite.circles.models import Circle, CircleMembership
from mysite.users.models import User


@pytest.fixture
def user():
    return User.objects.create_user(email="memories@example.com", password="password123", email_verified=True)


@pytest.fixture
def owner():
    return User.objects.create_user(email="owner@example.com", password="password123", email_verified=True)


@pytest.fixture
def circle(owner, user):
    circle = Circle.objects.create(name="Family", created_by=owner)
    CircleMembership.objects.create(user=user, circle=circle)
    return circle


@pytest.fixture
def client(user):
    api_client = APIClient()
    api_client.force_authenticate(user=user)
    return api_client


def payload(response):
    return response.data.get("data", response.data)


def url(circle):
    return reverse("circle-my-membership", args=[circle.id])


@pytest.mark.django_db
class TestCircleOnThisDayFrequency:
    def test_defaults_to_normal(self, client, circle):
        response = client.get(url(circle))

        assert response.status_code == status.HTTP_200_OK
        assert payload(response)["membership"]["on_this_day_frequency"] == "normal"

    @pytest.mark.parametrize("frequency", ["off", "less", "more"])
    def test_a_plain_member_sets_their_own(self, client, user, circle, frequency):
        response = client.patch(url(circle), {"on_this_day_frequency": frequency}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert payload(response)["membership"]["on_this_day_frequency"] == frequency
        assert CircleMembership.objects.get(user=user, circle=circle).on_this_day_frequency == frequency

    def test_only_changes_the_viewers_membership(self, client, owner, circle):
        client.patch(url(circle), {"on_this_day_frequency": "off"}, format="json")

        assert CircleMembership.objects.get(user=owner, circle=circle).on_this_day_frequency == "normal"

    def test_rejects_unknown_frequency(self, client, user, circle):
        response = client.patch(url(circle), {"on_this_day_frequency": "always"}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert CircleMembership.objects.get(user=user, circle=circle).on_this_day_frequency == "normal"

    def test_404_when_not_a_member(self, client, owner):
        elsewhere = Circle.objects.create(name="Elsewhere", created_by=owner)

        assert client.get(url(elsewhere)).status_code == status.HTTP_404_NOT_FOUND
        response = client.patch(url(elsewhere), {"on_this_day_frequency": "off"}, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_listed_with_the_viewers_circles(self, client, user, circle):
        CircleMembership.objects.filter(user=user, circle=circle).update(on_this_day_frequency="less")

        response = client.get(reverse("user-circle-list"))

        circles = payload(response)["circles"]
        assert [c["on_this_day_frequency"] for c in circles if c["circle"]["id"] == circle.id] == ["less"]
