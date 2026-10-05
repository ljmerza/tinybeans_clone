"""Stats on the person page: counts, posts per month, first and most-liked post, age."""

from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.test import APIClient

from mysite.circles.models import Circle, CircleMembership
from mysite.keeps.models import Keep, KeepMedia, KeepPerson, KeepReaction, KeepType, Person
from mysite.keeps.person_stats import age_on, person_stats
from mysite.users.models import ChildProfile

User = get_user_model()

TODAY = date(2026, 10, 5)


class FakeStorageBackend:
    def get_url(self, storage_key, expires_in=3600):
        return f"https://cdn.test/{storage_key}"


@pytest.fixture(autouse=True)
def fake_storage():
    with patch("mysite.keeps.storage.get_storage_backend", return_value=FakeStorageBackend()):
        yield


def stats_url(person_id):
    return f"/api/keeps/people/{person_id}/stats/"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin():
    return User.objects.create_user(email="stats-admin@example.com", password="adminpass123")


@pytest.fixture
def circle(admin):
    return Circle.objects.create(name="Stats Family", created_by=admin)


@pytest.fixture
def member(circle):
    user = User.objects.create_user(email="stats-member@example.com", password="memberpass123")
    CircleMembership.objects.create(user=user, circle=circle)
    return user


@pytest.fixture
def child(circle):
    return ChildProfile.objects.create(circle=circle, display_name="Sophia M", birthdate=date(2024, 8, 20))


@pytest.fixture
def person(circle, child):
    return Person.objects.create(circle=circle, child=child, name="Sophia M")


def make_keep(circle, user, when, *, media=(), title="Memory", tag=None):
    keep = Keep.objects.create(
        circle=circle,
        created_by=user,
        keep_type=KeepType.MEDIA if media else KeepType.NOTE,
        title=title,
        date_of_memory=when,
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
        )
    if tag is not None:
        KeepPerson.objects.create(keep=keep, person=tag)
    return keep


def at(year, month, day=1):
    return datetime(year, month, day, 12, tzinfo=timezone.utc)


def like(keep, *users):
    for user in users:
        KeepReaction.objects.create(keep=keep, user=user, reaction_type="love")


@pytest.mark.django_db
class TestPersonStats:
    def test_counts_and_highlights(self, circle, admin, member, person):
        first = make_keep(circle, admin, at(2024, 9, 1), title="First smile", media=[("photo", True)], tag=person)
        liked = make_keep(
            circle, admin, at(2026, 3, 10), title="Beach", media=[("photo", True), ("photo", True)], tag=person
        )
        video = make_keep(circle, admin, at(2026, 10, 2), media=[("video", True)], tag=person)
        make_keep(circle, admin, at(2026, 10, 3), title="A note", tag=person)
        # Not counted: a processing video (not shown in the feed) and an untagged post.
        hidden = make_keep(circle, admin, at(2026, 10, 4), media=[("video", False)], tag=person)
        make_keep(circle, admin, at(2026, 10, 4), media=[("photo", True)])
        like(liked, admin, member)
        like(video, admin)
        like(hidden, admin, member)

        stats = person_stats(person, today=TODAY)

        assert stats["post_count"] == 4
        assert stats["photo_count"] == 3
        assert stats["video_count"] == 1
        assert stats["first_post"]["id"] == str(first.id)
        assert stats["first_post"]["title"] == "First smile"
        assert stats["first_post"]["thumbnail_url"] == f"https://cdn.test/thumb/{first.id}-0"
        assert stats["most_liked_post"]["id"] == str(liked.id)
        assert stats["most_liked_post"]["like_count"] == 2

    def test_posts_per_month_covers_the_last_twelve_months(self, circle, admin, person):
        make_keep(circle, admin, at(2025, 10, 31), tag=person)  # 12 months back: just outside
        make_keep(circle, admin, at(2025, 11, 1), tag=person)
        make_keep(circle, admin, at(2026, 10, 1), tag=person)
        make_keep(circle, admin, at(2026, 10, 5), tag=person)

        months = person_stats(person, today=TODAY)["posts_per_month"]

        assert len(months) == 12
        assert months[0] == {"month": "2025-11", "count": 1}
        assert months[-1] == {"month": "2026-10", "count": 2}
        assert sum(month["count"] for month in months) == 3

    def test_empty(self, person):
        stats = person_stats(person, today=TODAY)

        assert stats["post_count"] == 0
        assert stats["photo_count"] == 0
        assert stats["first_post"] is None
        assert stats["most_liked_post"] is None
        assert all(month["count"] == 0 for month in stats["posts_per_month"])

    def test_nothing_liked_means_no_most_liked_post(self, circle, admin, person):
        make_keep(circle, admin, at(2026, 1, 1), tag=person)
        assert person_stats(person, today=TODAY)["most_liked_post"] is None

    def test_age_from_the_birthdate(self, person):
        stats = person_stats(person, today=TODAY)

        assert stats["birthdate"] == date(2024, 8, 20)
        assert stats["age"] == {"years": 2, "months": 1, "days": 15}

    def test_no_age_without_a_birthdate(self, circle, admin):
        member_person = Person.objects.create(circle=circle, user=admin, name="Leo")
        stats = person_stats(member_person, today=TODAY)

        assert stats["birthdate"] is None
        assert stats["age"] is None

    def test_query_count_does_not_grow_with_posts(self, circle, admin, member, person):
        def count_queries():
            with CaptureQueriesContext(connection) as queries:
                person_stats(person, today=TODAY)
            return len(queries)

        like(make_keep(circle, admin, at(2026, 1, 1), media=[("photo", True)], tag=person), admin)
        few = count_queries()
        for month in range(2, 10):
            keep = make_keep(circle, admin, at(2026, month, 1), media=[("photo", True)], tag=person)
            like(keep, admin, member)

        assert count_queries() == few


class TestAgeOn:
    @pytest.mark.parametrize(
        ("birthdate", "today", "expected"),
        [
            (date(2024, 8, 20), date(2024, 8, 20), {"years": 0, "months": 0, "days": 0}),
            (date(2024, 8, 20), date(2024, 9, 19), {"years": 0, "months": 0, "days": 30}),
            (date(2024, 8, 20), date(2025, 8, 20), {"years": 1, "months": 0, "days": 0}),
            (date(2024, 1, 31), date(2024, 3, 1), {"years": 0, "months": 1, "days": 1}),
            (date(2024, 2, 29), date(2025, 2, 28), {"years": 0, "months": 11, "days": 30}),
        ],
    )
    def test_whole_years_months_and_days(self, birthdate, today, expected):
        assert age_on(birthdate, today) == expected

    def test_not_born_yet(self):
        assert age_on(date(2027, 1, 1), TODAY) is None


@pytest.mark.django_db
class TestPersonStatsView:
    def test_member_reads_stats(self, api_client, circle, admin, member, person):
        make_keep(circle, admin, at(2026, 1, 1), tag=person)
        api_client.force_authenticate(member)

        response = api_client.get(stats_url(person.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["post_count"] == 1
        assert len(response.data["posts_per_month"]) == 12

    def test_outsider_gets_404(self, api_client, person):
        outsider = User.objects.create_user(email="stats-outsider@example.com", password="outsiderpass123")
        api_client.force_authenticate(outsider)

        assert api_client.get(stats_url(person.id)).status_code == status.HTTP_404_NOT_FOUND
