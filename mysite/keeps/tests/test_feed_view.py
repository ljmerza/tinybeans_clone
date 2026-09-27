"""Tests for the home-screen photo feed."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.test import APIClient

from mysite.circles.models import Circle, CircleMembership
from mysite.keeps.models import Keep, KeepComment, KeepMedia, KeepReaction, KeepType

User = get_user_model()

FEED_URL = "/api/keeps/feed/"
COMMENTS_URL = "/api/keeps/comments/"
BASE_TIME = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)


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
    return APIClient()


@pytest.fixture
def user():
    return User.objects.create_user(email="feed@example.com", password="testpass123")


@pytest.fixture
def other_user():
    return User.objects.create_user(email="feed-other@example.com", password="otherpass123")


@pytest.fixture
def circle(user):
    """Membership for the creator is auto-created by signal."""
    return Circle.objects.create(name="Feed Family", created_by=user)


@pytest.fixture
def other_circle(other_user):
    return Circle.objects.create(name="Other Family", created_by=other_user)


def make_keep(circle, user, when, *, media=(("photo", True),), title="Memory"):
    """Create a keep dated `when` with one media file per (media_type, thumbnails) pair."""
    keep = Keep.objects.create(
        circle=circle, created_by=user, keep_type=KeepType.MEDIA, title=title, date_of_memory=when
    )
    for order, (media_type, thumbnails) in enumerate(media):
        KeepMedia.objects.create(
            keep=keep,
            media_type=media_type,
            upload_order=order,
            storage_key_original=f"original/{keep.id}-{order}",
            storage_key_thumbnail=f"thumb/{keep.id}-{order}" if thumbnails else "",
            storage_key_gallery=f"gallery/{keep.id}-{order}" if thumbnails else "",
            original_filename="file",
            content_type="image/jpeg" if media_type == "photo" else "video/mp4",
            thumbnails_generated=thumbnails,
            width=1080,
            height=1350,
        )
    return keep


def feed_ids(response):
    return [item["id"] for item in response.data["results"]]


@pytest.mark.django_db
class TestKeepFeedView:
    def test_requires_authentication(self, api_client):
        response = api_client.get(FEED_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_newest_first_across_all_member_circles(self, api_client, user, other_user, circle, other_circle):
        second_circle = Circle.objects.create(name="Grandparents", created_by=other_user)
        CircleMembership.objects.create(user=user, circle=second_circle)
        older = make_keep(circle, user, BASE_TIME)
        newer = make_keep(second_circle, other_user, BASE_TIME + timedelta(days=1))
        make_keep(other_circle, other_user, BASE_TIME + timedelta(days=2))  # not a member

        api_client.force_authenticate(user=user)
        response = api_client.get(FEED_URL)

        assert response.status_code == status.HTTP_200_OK
        assert feed_ids(response) == [str(newer.id), str(older.id)]
        assert response.data["results"][0]["circle"] == {
            "id": second_circle.id,
            "name": "Grandparents",
            "slug": second_circle.slug,
        }

    def test_only_keeps_with_displayable_media(self, api_client, user, circle):
        photo = make_keep(circle, user, BASE_TIME)
        video_with_poster = make_keep(circle, user, BASE_TIME + timedelta(hours=1), media=(("video", True),))
        make_keep(circle, user, BASE_TIME + timedelta(hours=2), media=(("video", False),))
        make_keep(circle, user, BASE_TIME + timedelta(hours=3), media=())  # text-only note

        api_client.force_authenticate(user=user)
        response = api_client.get(FEED_URL)

        assert feed_ids(response) == [str(video_with_poster.id), str(photo.id)]

    def test_media_urls_and_dimensions(self, api_client, user, circle):
        keep = make_keep(
            circle, user, BASE_TIME, media=(("photo", True), ("photo", False), ("video", True), ("video", False))
        )

        api_client.force_authenticate(user=user)
        media = api_client.get(FEED_URL).data["results"][0]["media"]

        assert [(m["media_type"], m["url"], m["poster_url"]) for m in media] == [
            ("photo", f"https://cdn.test/gallery/{keep.id}-0", None),
            ("photo", f"https://cdn.test/original/{keep.id}-1", None),
            ("video", f"https://cdn.test/original/{keep.id}-2", f"https://cdn.test/gallery/{keep.id}-2"),
        ]
        assert (media[0]["width"], media[0]["height"]) == (1080, 1350)

    def test_counts_viewer_reaction_and_recent_comments(self, api_client, user, other_user, circle):
        CircleMembership.objects.create(user=other_user, circle=circle)
        keep = make_keep(circle, user, BASE_TIME)
        untouched = make_keep(circle, user, BASE_TIME - timedelta(days=1))
        KeepReaction.objects.create(keep=keep, user=other_user, reaction_type="love")
        mine = KeepReaction.objects.create(keep=keep, user=user, reaction_type="like")
        for n in range(3):
            KeepComment.objects.create(
                keep=keep, user=other_user, comment=f"comment {n}", created_at=BASE_TIME + timedelta(minutes=n)
            )

        api_client.force_authenticate(user=user)
        first, second = api_client.get(FEED_URL).data["results"]

        assert first["reaction_count"] == 2
        assert first["comment_count"] == 3
        assert first["viewer_reaction"] == {"id": mine.id, "reaction_type": "like"}
        # The newest two, oldest first.
        assert [c["comment"] for c in first["recent_comments"]] == ["comment 1", "comment 2"]

        assert second["id"] == str(untouched.id)
        assert second["reaction_count"] == 0
        assert second["comment_count"] == 0
        assert second["viewer_reaction"] is None
        assert second["recent_comments"] == []

    def test_cursor_pagination_walks_every_keep_once(self, api_client, user, circle):
        # Several share a timestamp, like a batch of imported photos from one day.
        keeps = [make_keep(circle, user, BASE_TIME - timedelta(days=n // 2)) for n in range(7)]

        api_client.force_authenticate(user=user)
        seen = []
        url = f"{FEED_URL}?page_size=3"
        while url:
            response = api_client.get(url)
            assert response.status_code == status.HTTP_200_OK
            seen.extend(feed_ids(response))
            url = response.data["next"]

        assert sorted(seen) == sorted(str(k.id) for k in keeps)
        assert len(seen) == len(set(seen))
        # Newest memory first, including across page boundaries.
        dates = {str(k.id): k.date_of_memory for k in keeps}
        seen_dates = [dates[keep_id] for keep_id in seen]
        assert seen_dates == sorted(seen_dates, reverse=True)

    def test_query_count_does_not_grow_with_page_size(self, api_client, user, other_user, circle):
        CircleMembership.objects.create(user=other_user, circle=circle)

        def add_keeps(count, offset):
            for n in range(count):
                keep = make_keep(circle, user, BASE_TIME - timedelta(days=offset + n))
                KeepReaction.objects.create(keep=keep, user=other_user)
                KeepComment.objects.create(keep=keep, user=other_user, comment="hi")

        api_client.force_authenticate(user=user)
        add_keeps(2, 0)
        with CaptureQueriesContext(connection) as small:
            api_client.get(FEED_URL)
        add_keeps(8, 2)
        with CaptureQueriesContext(connection) as large:
            api_client.get(FEED_URL)

        assert len(large) == len(small)


@pytest.mark.django_db
class TestKeepFeedItemView:
    def test_returns_one_post_in_feed_shape(self, api_client, user, circle):
        keep = make_keep(circle, user, BASE_TIME)
        api_client.force_authenticate(user=user)

        response = api_client.get(f"{FEED_URL}{keep.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(keep.id)
        assert response.data["media"][0]["url"] == f"https://cdn.test/gallery/{keep.id}-0"

    def test_hidden_from_non_members(self, api_client, user, other_user, other_circle):
        keep = make_keep(other_circle, other_user, BASE_TIME)
        api_client.force_authenticate(user=user)

        response = api_client.get(f"{FEED_URL}{keep.id}/")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_404_for_keep_without_media(self, api_client, user, circle):
        keep = make_keep(circle, user, BASE_TIME, media=())
        api_client.force_authenticate(user=user)

        response = api_client.get(f"{FEED_URL}{keep.id}/")

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestCommentKeepFilter:
    def test_filters_comments_to_one_keep(self, api_client, user, circle):
        keep = make_keep(circle, user, BASE_TIME)
        other = make_keep(circle, user, BASE_TIME)
        KeepComment.objects.create(keep=keep, user=user, comment="on keep")
        KeepComment.objects.create(keep=other, user=user, comment="elsewhere")
        api_client.force_authenticate(user=user)

        response = api_client.get(COMMENTS_URL, {"keep": str(keep.id)})

        assert response.status_code == status.HTTP_200_OK
        assert [c["comment"] for c in response.data["results"]] == ["on keep"]

    def test_invalid_keep_id_returns_nothing(self, api_client, user, circle):
        KeepComment.objects.create(keep=make_keep(circle, user, BASE_TIME), user=user, comment="hi")
        api_client.force_authenticate(user=user)

        response = api_client.get(COMMENTS_URL, {"keep": "not-a-uuid"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"] == []
