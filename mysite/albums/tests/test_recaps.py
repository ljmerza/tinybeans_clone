"""Tests for monthly recap albums: picking posts, idempotency, the beat task, command and setting."""

from datetime import date, datetime, timedelta
from datetime import timezone as dt_timezone
from io import StringIO
from unittest.mock import patch

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from mysite.albums.models import Album, AlbumKeep, MonthlyRecap
from mysite.albums.recaps import (
    RECAP_SIZE,
    beat_today,
    create_monthly_recap,
    create_recaps_for_enabled_circles,
    previous_month,
    top_keeps,
)
from mysite.albums.tasks import create_monthly_recaps
from mysite.circles.models import Circle
from mysite.keeps.models import KeepComment, KeepReaction

from .helpers import make_album, make_keep

User = get_user_model()

SEPTEMBER = date(2026, 9, 1)
MID_SEPTEMBER = datetime(2026, 9, 15, 12, 0, tzinfo=dt_timezone.utc)


@pytest.fixture
def fans():
    """Members who like and comment; reactions are one per user per post."""
    return [
        User.objects.create_user(email=f"recap-fan{index}@example.com", password="fanpass123") for index in range(6)
    ]


def engage(keep, users, *, likes=0, comments=0, replies=0, reaction_type="like"):
    """Give `keep` `likes` reactions and `comments` top-level comments, each with `replies` replies."""
    for user in users[:likes]:
        KeepReaction.objects.create(keep=keep, user=user, reaction_type=reaction_type)
    for index in range(comments):
        comment = KeepComment.objects.create(keep=keep, user=users[0], comment=f"comment {index}")
        for reply in range(replies):
            KeepComment.objects.create(keep=keep, user=users[0], parent=comment, comment=f"reply {reply}")
    return keep


def album_titles(album):
    return list(album.album_keeps.order_by("keep__date_of_memory").values_list("keep__title", flat=True))


@pytest.mark.django_db
class TestTopKeeps:
    def test_score_is_reactions_plus_comments_and_replies(self, circle, admin, fans):
        liked = engage(make_keep(circle, admin, MID_SEPTEMBER, title="liked"), fans, likes=3)
        # Any reaction type is a like, as in the feed.
        loved = engage(make_keep(circle, admin, MID_SEPTEMBER, title="loved"), fans, likes=2, reaction_type="love")
        talked = engage(make_keep(circle, admin, MID_SEPTEMBER, title="talked"), fans, comments=1, replies=3)

        ranked = top_keeps(circle, SEPTEMBER)

        assert [(keep.title, keep.score) for keep in ranked] == [("talked", 4), ("liked", 3), ("loved", 2)]
        assert {keep.id for keep in ranked} == {liked.id, loved.id, talked.id}

    def test_posts_with_no_likes_or_comments_are_left_out(self, circle, admin, fans):
        engage(make_keep(circle, admin, MID_SEPTEMBER, title="liked"), fans, likes=1)
        make_keep(circle, admin, MID_SEPTEMBER, title="quiet")

        assert [keep.title for keep in top_keeps(circle, SEPTEMBER)] == ["liked"]

    def test_only_posts_with_a_photo_count(self, circle, admin, fans):
        engage(make_keep(circle, admin, MID_SEPTEMBER, title="photo"), fans, likes=1)
        engage(
            make_keep(circle, admin, MID_SEPTEMBER, title="mixed", media=(("video", True), ("photo", False))),
            fans,
            likes=1,
        )
        engage(make_keep(circle, admin, MID_SEPTEMBER, title="video", media=(("video", True),)), fans, likes=5)
        engage(make_keep(circle, admin, MID_SEPTEMBER, title="text", media=()), fans, likes=5)

        assert {keep.title for keep in top_keeps(circle, SEPTEMBER)} == {"photo", "mixed"}

    def test_ties_go_to_the_earlier_memory(self, circle, admin, fans):
        engage(make_keep(circle, admin, MID_SEPTEMBER + timedelta(days=2), title="later"), fans, likes=2)
        engage(make_keep(circle, admin, MID_SEPTEMBER, title="earlier"), fans, likes=2)
        engage(make_keep(circle, admin, MID_SEPTEMBER + timedelta(days=5), title="best"), fans, likes=3)

        assert [keep.title for keep in top_keeps(circle, SEPTEMBER)] == ["best", "earlier", "later"]

    def test_keeps_the_top_twelve(self, circle, admin, fans):
        for index in range(RECAP_SIZE + 3):
            keep = make_keep(circle, admin, MID_SEPTEMBER + timedelta(hours=index), title=f"post {index}")
            engage(keep, fans, comments=index + 1)

        ranked = top_keeps(circle, SEPTEMBER)

        assert len(ranked) == RECAP_SIZE
        assert ranked[0].title == f"post {RECAP_SIZE + 2}"
        assert {"post 0", "post 1", "post 2"}.isdisjoint(keep.title for keep in ranked)

    def test_month_is_the_memory_date_in_time_zone(self, circle, admin, fans):
        engage(
            make_keep(circle, admin, datetime(2026, 9, 1, 0, 0, tzinfo=dt_timezone.utc), title="first"), fans, likes=1
        )
        engage(
            make_keep(circle, admin, datetime(2026, 9, 30, 23, 59, 59, tzinfo=dt_timezone.utc), title="last"),
            fans,
            likes=1,
        )
        engage(
            make_keep(circle, admin, datetime(2026, 8, 31, 23, 59, 59, tzinfo=dt_timezone.utc), title="august"),
            fans,
            likes=1,
        )
        engage(
            make_keep(circle, admin, datetime(2026, 10, 1, 0, 0, tzinfo=dt_timezone.utc), title="october"),
            fans,
            likes=1,
        )

        assert settings.TIME_ZONE == "UTC"
        assert {keep.title for keep in top_keeps(circle, SEPTEMBER)} == {"first", "last"}

    def test_month_boundaries_follow_the_time_zone_setting(self, circle, admin, fans):
        # 02:00 UTC on Oct 1 is still Sep 30 in New York; 03:00 UTC on Sep 1 is still August there.
        engage(
            make_keep(circle, admin, datetime(2026, 10, 1, 2, 0, tzinfo=dt_timezone.utc), title="ny september"),
            fans,
            likes=1,
        )
        engage(
            make_keep(circle, admin, datetime(2026, 9, 1, 3, 0, tzinfo=dt_timezone.utc), title="ny august"),
            fans,
            likes=1,
        )

        with override_settings(TIME_ZONE="America/New_York"):
            assert [keep.title for keep in top_keeps(circle, SEPTEMBER)] == ["ny september"]

    def test_uses_the_memory_date_not_when_it_was_posted(self, circle, admin, fans):
        imported = make_keep(circle, admin, datetime(2024, 9, 10, tzinfo=dt_timezone.utc), title="imported")
        imported.created_at = MID_SEPTEMBER
        imported.save(update_fields=["created_at"])
        engage(imported, fans, likes=1)

        assert top_keeps(circle, SEPTEMBER) == []
        assert [keep.title for keep in top_keeps(circle, date(2024, 9, 1))] == ["imported"]

    def test_only_the_circles_own_posts(self, circle, admin, other_circle, outsider, fans):
        engage(make_keep(other_circle, outsider, MID_SEPTEMBER, title="elsewhere"), fans, likes=4)

        assert top_keeps(circle, SEPTEMBER) == []


@pytest.mark.django_db
class TestCreateMonthlyRecap:
    def test_makes_a_named_album_ordered_by_date_with_the_top_post_as_cover(self, circle, admin, fans):
        early = engage(make_keep(circle, admin, MID_SEPTEMBER - timedelta(days=10), title="early"), fans, likes=1)
        top = engage(make_keep(circle, admin, MID_SEPTEMBER, title="top"), fans, likes=4)
        engage(make_keep(circle, admin, MID_SEPTEMBER + timedelta(days=10), title="late"), fans, comments=2)

        album = create_monthly_recap(circle, date(2026, 9, 20))

        assert album.name == "September 2026"
        assert album.circle == circle
        assert album.created_by is None
        assert album.cover_keep == top
        assert album_titles(album) == ["early", "top", "late"]
        assert list(album.album_keeps.order_by("added_at", "id").values_list("keep", flat=True))[0] == early.id
        recap = MonthlyRecap.objects.get(circle=circle)
        assert (recap.month, recap.album) == (SEPTEMBER, album)

    def test_nothing_scored_makes_no_album_and_leaves_the_month_open(self, circle, admin, fans):
        make_keep(circle, admin, MID_SEPTEMBER, title="quiet")

        assert create_monthly_recap(circle, SEPTEMBER) is None
        assert not Album.objects.exists()
        assert not MonthlyRecap.objects.exists()

        # A like that arrives later lets a manual rerun make it after all.
        engage(circle.keeps.get(), fans, likes=1)
        assert create_monthly_recap(circle, SEPTEMBER) is not None

    def test_rerun_does_not_make_a_second_album(self, circle, admin, fans):
        engage(make_keep(circle, admin, MID_SEPTEMBER), fans, likes=1)
        first = create_monthly_recap(circle, SEPTEMBER)
        engage(make_keep(circle, admin, MID_SEPTEMBER, title="new"), fans, likes=2)

        assert create_monthly_recap(circle, SEPTEMBER) is None
        assert list(Album.objects.all()) == [first]
        assert first.album_keeps.count() == 1

    def test_a_deleted_recap_is_not_made_again(self, circle, admin, fans):
        engage(make_keep(circle, admin, MID_SEPTEMBER), fans, likes=1)
        create_monthly_recap(circle, SEPTEMBER).delete()

        assert MonthlyRecap.objects.get(circle=circle).album is None
        assert create_monthly_recap(circle, SEPTEMBER) is None
        assert not Album.objects.exists()

    def test_a_renamed_recap_still_counts(self, circle, admin, fans):
        engage(make_keep(circle, admin, MID_SEPTEMBER), fans, likes=1)
        album = create_monthly_recap(circle, SEPTEMBER)
        Album.objects.filter(pk=album.pk).update(name="Fall fun")

        assert create_monthly_recap(circle, SEPTEMBER) is None
        assert Album.objects.count() == 1

    def test_each_month_and_circle_gets_its_own(self, circle, admin, other_circle, outsider, fans):
        engage(make_keep(circle, admin, MID_SEPTEMBER), fans, likes=1)
        engage(make_keep(circle, admin, MID_SEPTEMBER - timedelta(days=30)), fans, likes=1)
        engage(make_keep(other_circle, outsider, MID_SEPTEMBER), fans, likes=1)

        create_monthly_recap(circle, SEPTEMBER)
        create_monthly_recap(circle, date(2026, 8, 1))
        create_monthly_recap(other_circle, SEPTEMBER)

        assert sorted(Album.objects.values_list("circle__name", "name")) == [
            ("Albums Family", "August 2026"),
            ("Albums Family", "September 2026"),
            ("Other Family", "September 2026"),
        ]

    def test_december_rolls_into_the_next_year(self, circle, admin, fans):
        engage(make_keep(circle, admin, datetime(2025, 12, 31, 20, 0, tzinfo=dt_timezone.utc)), fans, likes=1)

        assert create_monthly_recap(circle, date(2025, 12, 1)).name == "December 2025"
        assert previous_month(date(2026, 1, 1)) == date(2025, 12, 1)


@pytest.mark.django_db
class TestEnabledCircles:
    def test_only_enabled_circles_get_a_recap(self, circle, admin, other_circle, outsider, fans):
        Circle.objects.filter(pk=circle.pk).update(monthly_recap_enabled=True)
        engage(make_keep(circle, admin, MID_SEPTEMBER), fans, likes=1)
        engage(make_keep(other_circle, outsider, MID_SEPTEMBER), fans, likes=1)

        assert create_recaps_for_enabled_circles(SEPTEMBER) == (1, [])
        assert list(Album.objects.values_list("circle", flat=True)) == [circle.id]

    def test_off_by_default(self, admin):
        assert Circle.objects.create(name="New", created_by=admin).monthly_recap_enabled is False

    def test_one_failing_circle_does_not_stop_the_rest(self, circle, admin, other_circle, outsider, fans):
        Circle.objects.update(monthly_recap_enabled=True)
        engage(make_keep(circle, admin, MID_SEPTEMBER), fans, likes=1)
        engage(make_keep(other_circle, outsider, MID_SEPTEMBER), fans, likes=1)
        real = create_monthly_recap

        def flaky(target, month):
            if target.id == circle.id:
                raise RuntimeError("boom")
            return real(target, month)

        with patch("mysite.albums.recaps.create_monthly_recap", side_effect=flaky):
            assert create_recaps_for_enabled_circles(SEPTEMBER) == (1, [circle.id])
        assert list(Album.objects.values_list("circle", flat=True)) == [other_circle.id]


@pytest.mark.django_db
class TestBeatTask:
    def test_scheduled_on_the_first_of_the_month(self):
        entry = settings.CELERY_BEAT_SCHEDULE["create-monthly-recaps"]

        assert entry["task"] == create_monthly_recaps.name == "mysite.albums.tasks.create_monthly_recaps"
        assert entry["schedule"].day_of_month == {1}
        assert entry["schedule"].hour == {8}

    def test_makes_last_months_recap(self, circle, admin, fans):
        Circle.objects.filter(pk=circle.pk).update(monthly_recap_enabled=True)
        engage(make_keep(circle, admin, MID_SEPTEMBER), fans, likes=1)

        with patch("mysite.albums.tasks.beat_today", return_value=date(2026, 10, 1)):
            assert create_monthly_recaps.delay().get() == 1
            # The retry/rerun on the same day is a no-op.
            assert create_monthly_recaps.delay().get() == 0

        assert list(Album.objects.values_list("name", flat=True)) == ["September 2026"]

    def test_pinned_month(self, circle, admin, fans):
        Circle.objects.filter(pk=circle.pk).update(monthly_recap_enabled=True)
        engage(make_keep(circle, admin, MID_SEPTEMBER - timedelta(days=30)), fans, likes=1)

        assert create_monthly_recaps.delay(month="2026-08-01").get() == 1
        assert list(Album.objects.values_list("name", flat=True)) == ["August 2026"]

    def test_retries_the_same_month_when_a_circle_fails(self, circle):
        Circle.objects.filter(pk=circle.pk).update(monthly_recap_enabled=True)

        with (
            patch("mysite.albums.tasks.create_recaps_for_enabled_circles", return_value=(0, [circle.id])),
            patch("mysite.albums.tasks.beat_today", return_value=date(2026, 1, 1)),
            patch.object(create_monthly_recaps, "retry", return_value=RuntimeError("retry")) as retry,
            pytest.raises(RuntimeError, match="retry"),
        ):
            create_monthly_recaps()
        retry.assert_called_once_with(kwargs={"month": "2025-12-01"})

    @pytest.mark.parametrize(
        ("zone", "now_utc"),
        [
            # 8 AM on Oct 1 in each zone, whatever the UTC date is then.
            ("America/New_York", datetime(2026, 10, 1, 12, 0, tzinfo=dt_timezone.utc)),
            ("Asia/Tokyo", datetime(2026, 9, 30, 23, 0, tzinfo=dt_timezone.utc)),
        ],
    )
    def test_last_month_is_read_in_the_beat_time_zone(self, zone, now_utc):
        with override_settings(CELERY_TIMEZONE=zone), patch("django.utils.timezone.now", return_value=now_utc):
            assert previous_month(beat_today()) == SEPTEMBER


@pytest.mark.django_db
class TestCommand:
    def test_makes_a_recap_by_slug_even_when_turned_off(self, circle, admin, fans):
        engage(make_keep(circle, admin, MID_SEPTEMBER), fans, likes=1)
        out = StringIO()

        call_command("create_monthly_recap", circle.slug, "2026-09", stdout=out)

        assert 'Created "September 2026"' in out.getvalue()
        assert MonthlyRecap.objects.get(circle=circle).album.name == "September 2026"

    def test_by_id_and_rerun_reports_nothing_made(self, circle, admin, fans):
        engage(make_keep(circle, admin, MID_SEPTEMBER), fans, likes=1)
        call_command("create_monthly_recap", str(circle.id), "2026-09", stdout=StringIO())
        out = StringIO()

        call_command("create_monthly_recap", str(circle.id), "2026-09", stdout=out)

        assert "No recap made" in out.getvalue()
        assert Album.objects.count() == 1

    def test_defaults_to_last_month(self, circle, admin, fans):
        engage(make_keep(circle, admin, MID_SEPTEMBER), fans, likes=1)

        with patch("mysite.albums.management.commands.create_monthly_recap.beat_today", return_value=date(2026, 10, 5)):
            call_command("create_monthly_recap", circle.slug, stdout=StringIO())

        assert Album.objects.get().name == "September 2026"

    @pytest.mark.parametrize("args", [("no-such-circle", "2026-09"), ("{slug}", "2026-13"), ("{slug}", "Sept")])
    def test_rejects_bad_input(self, circle, args):
        with pytest.raises(CommandError):
            call_command("create_monthly_recap", *(arg.format(slug=circle.slug) for arg in args), stdout=StringIO())


@pytest.mark.django_db
class TestApi:
    @pytest.fixture
    def verified_admin(self, admin):
        admin.email_verified = True
        admin.save(update_fields=["email_verified"])
        return admin

    def test_admin_can_turn_recaps_on(self, api_client, circle, verified_admin):
        api_client.force_authenticate(verified_admin)

        response = api_client.patch(
            reverse("circle-detail", args=[circle.id]), {"monthly_recap_enabled": True}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["circle"]["monthly_recap_enabled"] is True
        circle.refresh_from_db()
        assert circle.monthly_recap_enabled is True

    def test_member_cannot_turn_recaps_on(self, api_client, circle, member):
        member.email_verified = True
        member.save(update_fields=["email_verified"])
        api_client.force_authenticate(member)

        response = api_client.patch(
            reverse("circle-detail", args=[circle.id]), {"monthly_recap_enabled": True}, format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        circle.refresh_from_db()
        assert circle.monthly_recap_enabled is False

    def test_circle_settings_page_shows_the_setting(self, api_client, circle, verified_admin):
        Circle.objects.filter(pk=circle.pk).update(monthly_recap_enabled=True)
        api_client.force_authenticate(verified_admin)

        # The circle settings page reads the circle from its (admin-only) member list.
        response = api_client.get(reverse("circle-member-list", args=[circle.id]))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["circle"]["monthly_recap_enabled"] is True

    def test_recap_albums_are_marked_and_visible_to_members(self, api_client, circle, admin, member, fans):
        engage(make_keep(circle, admin, MID_SEPTEMBER), fans, likes=1)
        recap = create_monthly_recap(circle, SEPTEMBER)
        plain = make_album(circle, admin, name="Beach")
        api_client.force_authenticate(member)

        listed = api_client.get("/api/albums/")
        detail = api_client.get(f"/api/albums/{recap.id}/")
        keeps = api_client.get(f"/api/albums/{recap.id}/keeps/")

        by_id = {item["id"]: item for item in listed.data["results"]}
        assert by_id[str(recap.id)]["recap_month"] == "2026-09-01"
        assert by_id[str(plain.id)]["recap_month"] is None
        assert detail.data["recap_month"] == "2026-09-01"
        assert detail.data["can_edit"] is False
        assert len(keeps.data["results"]) == 1

    def test_admin_deleting_a_recap_keeps_it_from_coming_back(self, api_client, circle, admin, fans):
        engage(make_keep(circle, admin, MID_SEPTEMBER), fans, likes=1)
        recap = create_monthly_recap(circle, SEPTEMBER)
        api_client.force_authenticate(admin)

        assert api_client.delete(f"/api/albums/{recap.id}/").status_code == status.HTTP_204_NO_CONTENT
        assert create_monthly_recap(circle, SEPTEMBER) is None
        assert not AlbumKeep.objects.exists()
