"""Tests for the keep calendar view."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from mysite.circles.models import Circle
from mysite.keeps.models import Keep, KeepMedia, KeepType

User = get_user_model()

CALENDAR_URL = "/api/keeps/calendar/"


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
    """Create an API client."""
    return APIClient()


@pytest.fixture
def user():
    """Create a test user."""
    return User.objects.create_user(email="calendar@example.com", password="testpass123")


@pytest.fixture
def other_user():
    """Create another test user."""
    return User.objects.create_user(email="calendar-other@example.com", password="otherpass123")


@pytest.fixture
def circle(user):
    """Create a test circle (membership auto-created by signal)."""
    return Circle.objects.create(name="Calendar Family", created_by=user)


@pytest.fixture
def other_circle(other_user):
    """Create a circle the main user is not a member of."""
    return Circle.objects.create(name="Other Family", created_by=other_user)


def make_photo_keep(circle, user, when, *, thumbnails=True, media_type="photo"):
    """Create a keep with one media file dated `when`."""
    keep = Keep.objects.create(
        circle=circle,
        created_by=user,
        keep_type=KeepType.MEDIA,
        title="Photo memory",
        date_of_memory=when,
    )
    KeepMedia.objects.create(
        keep=keep,
        media_type=media_type,
        storage_key_original=f"original/{keep.id}.jpg",
        storage_key_thumbnail=f"thumb/{keep.id}.jpg" if thumbnails else "",
        storage_key_gallery=f"gallery/{keep.id}.jpg" if thumbnails else "",
        original_filename="photo.jpg",
        content_type="image/jpeg",
        thumbnails_generated=thumbnails,
    )
    return keep


@pytest.mark.django_db
class TestKeepCalendarView:
    """Test the month calendar endpoint."""

    def test_requires_authentication(self, api_client):
        response = api_client.get(CALENDAR_URL, {"month": "2026-07"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_missing_month_returns_400(self, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.get(CALENDAR_URL)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize("month", ["2026-13", "2026-00", "07-2026", "202607", "abc"])
    def test_invalid_month_returns_400(self, api_client, user, month):
        api_client.force_authenticate(user=user)
        response = api_client.get(CALENDAR_URL, {"month": month})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_returns_photo_entries_for_month(self, api_client, user, circle):
        keep = make_photo_keep(circle, user, datetime(2026, 7, 4, 12, 0, tzinfo=timezone.utc))
        # Outside the requested month
        make_photo_keep(circle, user, datetime(2026, 6, 30, 23, 59, tzinfo=timezone.utc))
        make_photo_keep(circle, user, datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc))

        api_client.force_authenticate(user=user)
        response = api_client.get(CALENDAR_URL, {"month": "2026-07"})

        assert response.status_code == status.HTTP_200_OK
        data = response.data["data"]
        assert data["month"] == "2026-07"
        assert len(data["entries"]) == 1
        entry = data["entries"][0]
        assert entry["keep_id"] == str(keep.id)
        assert entry["datetime"] == keep.date_of_memory.isoformat()
        assert entry["photos"] == [f"https://cdn.test/thumb/{keep.id}.jpg"]

    def test_uses_original_when_thumbnails_missing(self, api_client, user, circle):
        keep = make_photo_keep(circle, user, datetime(2026, 7, 10, tzinfo=timezone.utc), thumbnails=False)

        api_client.force_authenticate(user=user)
        response = api_client.get(CALENDAR_URL, {"month": "2026-07"})

        entries = response.data["data"]["entries"]
        assert entries[0]["photos"] == [f"https://cdn.test/original/{keep.id}.jpg"]

    def test_includes_videos_that_have_a_poster_thumbnail(self, api_client, user, circle):
        keep = make_photo_keep(circle, user, datetime(2026, 7, 16, tzinfo=timezone.utc), media_type="video")

        api_client.force_authenticate(user=user)
        response = api_client.get(CALENDAR_URL, {"month": "2026-07"})

        entries = response.data["data"]["entries"]
        assert [e["keep_id"] for e in entries] == [str(keep.id)]
        assert entries[0]["photos"] == [f"https://cdn.test/thumb/{keep.id}.jpg"]

    def test_excludes_keeps_without_photos(self, api_client, user, circle):
        # Note keep with no media, and a video-only keep with no poster yet
        Keep.objects.create(
            circle=circle,
            created_by=user,
            keep_type=KeepType.NOTE,
            title="Just a note",
            date_of_memory=datetime(2026, 7, 15, tzinfo=timezone.utc),
        )
        make_photo_keep(
            circle,
            user,
            datetime(2026, 7, 16, tzinfo=timezone.utc),
            media_type="video",
            thumbnails=False,
        )

        api_client.force_authenticate(user=user)
        response = api_client.get(CALENDAR_URL, {"month": "2026-07"})

        assert response.data["data"]["entries"] == []

    def test_excludes_other_circles(self, api_client, user, circle, other_user, other_circle):
        make_photo_keep(other_circle, other_user, datetime(2026, 7, 20, tzinfo=timezone.utc))

        api_client.force_authenticate(user=user)
        response = api_client.get(CALENDAR_URL, {"month": "2026-07"})

        assert response.data["data"]["entries"] == []

    def test_circle_slug_filters_to_one_circle(self, api_client, user, circle):
        second_circle = Circle.objects.create(name="Second Family", created_by=user)
        keep = make_photo_keep(circle, user, datetime(2026, 7, 5, tzinfo=timezone.utc))
        make_photo_keep(second_circle, user, datetime(2026, 7, 6, tzinfo=timezone.utc))

        api_client.force_authenticate(user=user)
        response = api_client.get(CALENDAR_URL, {"month": "2026-07", "circle_slug": circle.slug})

        entries = response.data["data"]["entries"]
        assert [e["keep_id"] for e in entries] == [str(keep.id)]

    def test_circle_slug_of_non_member_returns_404(self, api_client, user, other_circle):
        api_client.force_authenticate(user=user)
        response = api_client.get(CALENDAR_URL, {"month": "2026-07", "circle_slug": other_circle.slug})
        assert response.status_code == status.HTTP_404_NOT_FOUND
