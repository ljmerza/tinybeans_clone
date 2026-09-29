"""Tests for favoriting feed posts and listing the user's favorites."""

from datetime import datetime, timedelta, timezone

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.test import APIClient

from mysite.circles.models import Circle, CircleMembership
from mysite.keeps.models import Keep, KeepFavorite, KeepType

User = get_user_model()

FEED_URL = "/api/keeps/feed/"
FAVORITES_URL = "/api/keeps/feed/favorites/"
BASE_TIME = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)


def favorite_url(keep_id):
    return f"/api/keeps/feed/{keep_id}/favorite/"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return User.objects.create_user(email="favorites@example.com", password="testpass123")


@pytest.fixture
def member(circle):
    """Another member of the same circle."""
    other = User.objects.create_user(email="favorites-member@example.com", password="memberpass123")
    CircleMembership.objects.create(user=other, circle=circle)
    return other


@pytest.fixture
def circle(user):
    """Membership for the creator is auto-created by signal."""
    return Circle.objects.create(name="Favorites Family", created_by=user)


@pytest.fixture
def outsider_keep():
    """A keep in a circle the user doesn't belong to."""
    outsider = User.objects.create_user(email="favorites-outsider@example.com", password="outsiderpass123")
    other_circle = Circle.objects.create(name="Other Family", created_by=outsider)
    return make_keep(other_circle, outsider, BASE_TIME, title="Not yours")


def make_keep(circle, user, when, *, title="Memory"):
    # Text posts always show in the feed, so no media is needed.
    return Keep.objects.create(
        circle=circle, created_by=user, keep_type=KeepType.NOTE, title=title, date_of_memory=when
    )


def favorite(user, keep, *, minutes=0):
    return KeepFavorite.objects.create(user=user, keep=keep, created_at=BASE_TIME + timedelta(minutes=minutes))


def titles(response):
    return [item["title"] for item in response.data["results"]]


@pytest.mark.django_db
class TestKeepFeedFavoriteView:
    def test_requires_authentication(self, api_client, circle, user):
        keep = make_keep(circle, user, BASE_TIME)
        assert api_client.post(favorite_url(keep.id)).status_code == status.HTTP_401_UNAUTHORIZED
        assert api_client.delete(favorite_url(keep.id)).status_code == status.HTTP_401_UNAUTHORIZED
        assert api_client.get(FAVORITES_URL).status_code == status.HTTP_401_UNAUTHORIZED

    def test_post_favorites_once(self, api_client, circle, user):
        keep = make_keep(circle, user, BASE_TIME)
        api_client.force_authenticate(user=user)

        first = api_client.post(favorite_url(keep.id))
        assert first.status_code == status.HTTP_201_CREATED
        assert first.data == {"favorited": True}

        again = api_client.post(favorite_url(keep.id))
        assert again.status_code == status.HTTP_200_OK
        assert KeepFavorite.objects.filter(user=user, keep=keep).count() == 1

    def test_delete_unfavorites_and_is_idempotent(self, api_client, circle, user):
        keep = make_keep(circle, user, BASE_TIME)
        favorite(user, keep)
        api_client.force_authenticate(user=user)

        assert api_client.delete(favorite_url(keep.id)).status_code == status.HTTP_204_NO_CONTENT
        assert not KeepFavorite.objects.filter(user=user, keep=keep).exists()
        assert api_client.delete(favorite_url(keep.id)).status_code == status.HTTP_204_NO_CONTENT

    def test_only_touches_the_viewers_own_favorite(self, api_client, circle, user, member):
        keep = make_keep(circle, user, BASE_TIME)
        favorite(member, keep)
        api_client.force_authenticate(user=user)

        api_client.post(favorite_url(keep.id))
        api_client.delete(favorite_url(keep.id))

        assert list(KeepFavorite.objects.values_list("user", flat=True)) == [member.id]

    def test_404_outside_the_users_circles(self, api_client, user, outsider_keep):
        api_client.force_authenticate(user=user)

        assert api_client.post(favorite_url(outsider_keep.id)).status_code == status.HTTP_404_NOT_FOUND
        assert api_client.delete(favorite_url(outsider_keep.id)).status_code == status.HTTP_404_NOT_FOUND
        assert not KeepFavorite.objects.exists()

    def test_404_for_a_deleted_keep(self, api_client, circle, user):
        keep = make_keep(circle, user, BASE_TIME)
        keep_id = keep.id
        keep.delete()
        api_client.force_authenticate(user=user)

        assert api_client.post(favorite_url(keep_id)).status_code == status.HTTP_404_NOT_FOUND
        assert api_client.delete(favorite_url(keep_id)).status_code == status.HTTP_404_NOT_FOUND

    def test_unfavoriting_after_leaving_the_circle_still_drops_the_row(self, api_client, circle, user, member):
        keep = make_keep(circle, user, BASE_TIME)
        favorite(member, keep)
        CircleMembership.objects.filter(user=member, circle=circle).delete()
        api_client.force_authenticate(user=member)

        assert api_client.delete(favorite_url(keep.id)).status_code == status.HTTP_404_NOT_FOUND
        assert not KeepFavorite.objects.filter(user=member).exists()


@pytest.mark.django_db
class TestFeedFavoritedFlag:
    def test_feed_reports_only_the_viewers_favorites(self, api_client, circle, user, member):
        mine = make_keep(circle, user, BASE_TIME, title="Mine")
        theirs = make_keep(circle, user, BASE_TIME - timedelta(days=1), title="Theirs")
        favorite(user, mine)
        favorite(member, theirs)
        api_client.force_authenticate(user=user)

        response = api_client.get(FEED_URL)

        flags = {item["title"]: item["favorited"] for item in response.data["results"]}
        assert flags == {"Mine": True, "Theirs": False}

    def test_single_post_reports_favorited(self, api_client, circle, user):
        keep = make_keep(circle, user, BASE_TIME)
        favorite(user, keep)
        api_client.force_authenticate(user=user)

        response = api_client.get(f"{FEED_URL}{keep.id}/")

        assert response.data["favorited"] is True


@pytest.mark.django_db
class TestKeepFeedFavoritesView:
    def test_lists_own_favorites_most_recently_favorited_first(self, api_client, circle, user, member):
        older_memory = make_keep(circle, user, BASE_TIME - timedelta(days=30), title="Old memory, new favorite")
        newer_memory = make_keep(circle, user, BASE_TIME, title="New memory, old favorite")
        make_keep(circle, user, BASE_TIME, title="Not a favorite")
        someone_elses = make_keep(circle, user, BASE_TIME, title="Someone else's favorite")
        favorite(user, newer_memory, minutes=0)
        favorite(user, older_memory, minutes=5)
        favorite(member, someone_elses)
        api_client.force_authenticate(user=user)

        response = api_client.get(FAVORITES_URL)

        assert response.status_code == status.HTTP_200_OK
        assert titles(response) == ["Old memory, new favorite", "New memory, old favorite"]
        assert all(item["favorited"] for item in response.data["results"])

    def test_paginates_by_favorite_time(self, api_client, circle, user):
        for n in range(5):
            favorite(user, make_keep(circle, user, BASE_TIME, title=f"Keep {n}"), minutes=n)
        api_client.force_authenticate(user=user)

        first = api_client.get(FAVORITES_URL, {"page_size": 3})
        second = api_client.get(first.data["next"])

        assert titles(first) == ["Keep 4", "Keep 3", "Keep 2"]
        assert titles(second) == ["Keep 1", "Keep 0"]
        assert second.data["next"] is None

    def test_deleting_a_keep_removes_it_from_every_favorites_list(self, api_client, circle, user, member):
        keep = make_keep(circle, user, BASE_TIME, title="Deleted")
        kept = make_keep(circle, user, BASE_TIME, title="Kept")
        favorite(user, keep)
        favorite(member, keep)
        favorite(user, kept)
        api_client.force_authenticate(user=user)

        response = api_client.delete(f"/api/keeps/{keep.id}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT

        assert not KeepFavorite.objects.filter(keep_id=keep.id).exists()
        assert titles(api_client.get(FAVORITES_URL)) == ["Kept"]
        api_client.force_authenticate(user=member)
        assert titles(api_client.get(FAVORITES_URL)) == []

    def test_hides_favorites_from_circles_the_user_left(self, api_client, circle, user, member):
        keep = make_keep(circle, user, BASE_TIME)
        favorite(member, keep)
        CircleMembership.objects.filter(user=member, circle=circle).delete()
        api_client.force_authenticate(user=member)

        assert titles(api_client.get(FAVORITES_URL)) == []

    def test_query_count_does_not_grow_with_favorites(self, api_client, circle, user):
        api_client.force_authenticate(user=user)
        favorite(user, make_keep(circle, user, BASE_TIME))
        with CaptureQueriesContext(connection) as small:
            api_client.get(FAVORITES_URL)

        for n in range(5):
            favorite(user, make_keep(circle, user, BASE_TIME, title=f"More {n}"), minutes=n + 1)
        with CaptureQueriesContext(connection) as large:
            api_client.get(FAVORITES_URL)

        assert len(large.captured_queries) == len(small.captured_queries)
