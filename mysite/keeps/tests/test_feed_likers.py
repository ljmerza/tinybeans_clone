"""Tests for listing who liked a feed post."""

from datetime import datetime, timedelta, timezone

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.test import APIClient

from mysite.circles.models import Circle, CircleMembership
from mysite.keeps.models import Keep, KeepReaction, KeepType

User = get_user_model()

BASE_TIME = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)


def likers_url(keep):
    return f"/api/keeps/feed/{keep.id}/likers/"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return User.objects.create_user(email="likers@example.com", password="testpass123")


@pytest.fixture
def circle(user):
    """Membership for the creator is auto-created by signal."""
    return Circle.objects.create(name="Likers Family", created_by=user)


@pytest.fixture
def keep(circle, user):
    return Keep.objects.create(
        circle=circle, created_by=user, keep_type=KeepType.MEDIA, title="Memory", date_of_memory=BASE_TIME
    )


def add_liker(keep, n, *, reaction_type="like", minutes=0):
    member = User.objects.create_user(
        email=f"liker{n}@example.com", password="pass12345", first_name=f"Liker{n}", last_name="Test"
    )
    CircleMembership.objects.create(user=member, circle=keep.circle)
    return KeepReaction.objects.create(
        keep=keep, user=member, reaction_type=reaction_type, created_at=BASE_TIME + timedelta(minutes=minutes)
    )


@pytest.mark.django_db
class TestKeepFeedLikersView:
    def test_requires_authentication(self, api_client, keep):
        response = api_client.get(likers_url(keep))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_lists_every_reaction_newest_first(self, api_client, user, keep):
        older = add_liker(keep, 1, minutes=1)
        newer = add_liker(keep, 2, reaction_type="love", minutes=2)
        mine = KeepReaction.objects.create(keep=keep, user=user, created_at=BASE_TIME)
        other_keep = Keep.objects.create(
            circle=keep.circle, created_by=user, keep_type=KeepType.MEDIA, date_of_memory=BASE_TIME
        )
        KeepReaction.objects.create(keep=other_keep, user=newer.user)
        api_client.force_authenticate(user=user)

        response = api_client.get(likers_url(keep))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 3
        # Any reaction type counts as a like, including the viewer's own.
        assert [(r["id"], r["user"], r["user_display_name"], r["reaction_type"]) for r in response.data["results"]] == [
            (newer.id, newer.user.id, "Liker2 Test", "love"),
            (older.id, older.user.id, "Liker1 Test", "like"),
            (mine.id, user.id, user.display_name, "like"),
        ]
        assert set(response.data["results"][0]) == {"id", "user", "user_display_name", "reaction_type", "created_at"}

    def test_hidden_from_non_members(self, api_client, keep):
        add_liker(keep, 1)
        outsider = User.objects.create_user(email="outsider@example.com", password="pass12345")
        api_client.force_authenticate(user=outsider)

        response = api_client.get(likers_url(keep))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_404_for_unknown_keep(self, api_client, user):
        api_client.force_authenticate(user=user)

        response = api_client.get("/api/keeps/feed/00000000-0000-0000-0000-000000000000/likers/")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_limit_offset_pagination_is_capped(self, api_client, user, keep):
        for n in range(5):
            add_liker(keep, n, minutes=n)
        api_client.force_authenticate(user=user)

        page = api_client.get(likers_url(keep), {"limit": 2, "offset": 1}).data
        assert page["count"] == 5
        assert [r["user_display_name"] for r in page["results"]] == ["Liker3 Test", "Liker2 Test"]
        assert page["next"] is not None

        capped = api_client.get(likers_url(keep), {"limit": 10_000})
        assert capped.status_code == status.HTTP_200_OK
        assert len(capped.data["results"]) == 5

    def test_query_count_does_not_grow_with_likers(self, api_client, user, keep):
        api_client.force_authenticate(user=user)
        add_liker(keep, 0)
        with CaptureQueriesContext(connection) as few:
            api_client.get(likers_url(keep))
        for n in range(1, 10):
            add_liker(keep, n, minutes=n)
        with CaptureQueriesContext(connection) as many:
            response = api_client.get(likers_url(keep))

        assert len(response.data["results"]) == 10
        assert len(many) == len(few)
