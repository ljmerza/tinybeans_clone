"""Tests for the daily new-post email digest."""

import importlib
from datetime import timedelta

import pytest
from django.core import mail
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from mysite.circles.models import Circle, CircleMembership
from mysite.keeps.digest import DIGEST_MAX_POSTS, send_digest
from mysite.keeps.models import Keep, KeepMedia, KeepType
from mysite.keeps.tasks import send_new_post_digests
from mysite.users.models import User, UserNotificationPreferences

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("no_settle_delay")]


def make_user(email, first_name, verified=True):
    return User.objects.create_user(email=email, password="testpass123", first_name=first_name, email_verified=verified)


def make_post(circle, author, *media_types, hours_ago=1, **fields):
    keep = Keep.objects.create(
        circle=circle,
        created_by=author,
        keep_type=KeepType.MEDIA if media_types else KeepType.NOTE,
        created_at=timezone.now() - timedelta(hours=hours_ago),
        **fields,
    )
    for order, media_type in enumerate(media_types):
        KeepMedia.objects.create(
            keep=keep, media_type=media_type, upload_order=order, storage_key_original=f"{keep.id}/{order}"
        )
    return keep


def opt_in(user, **fields):
    return UserNotificationPreferences.objects.create(user=user, email_digest=True, **fields)


@pytest.fixture
def no_settle_delay(settings):
    settings.NOTIFICATIONS_NEW_MEDIA_DELAY_SECONDS = 0


@pytest.fixture
def run_digests(django_capture_on_commit_callbacks):
    """Run the beat task; the digest emails are queued on commit."""

    def run():
        with django_capture_on_commit_callbacks(execute=True):
            send_new_post_digests()

    return run


@pytest.fixture
def poster():
    return make_user("poster@example.com", "Pat")


@pytest.fixture
def grandma():
    return make_user("grandma@example.com", "Grandma")


@pytest.fixture
def circle(poster, grandma):
    """The creator's membership comes from a signal; add grandma."""
    circle = Circle.objects.create(name="Smith Family", created_by=poster)
    CircleMembership.objects.create(circle=circle, user=grandma)
    return circle


class TestDefaults:
    def test_digest_is_off_by_default(self, grandma):
        assert UserNotificationPreferences.effective_for(grandma).email_digest is False
        assert UserNotificationPreferences.objects.create(user=grandma).email_digest is False

    def test_migration_leaves_existing_rows_off(self):
        migration = importlib.import_module("mysite.users.migrations.0006_notification_email_digest").Migration
        add_digest = next(op for op in migration.operations if getattr(op, "name", "") == "email_digest")

        assert add_digest.field.default is False
        # Nothing flips existing rows on afterwards.
        assert not any(type(op).__name__ in {"RunPython", "RunSQL"} for op in migration.operations)


class TestDigest:
    def test_lists_new_posts_from_my_circles_but_not_mine(self, run_digests, circle, poster, grandma):
        other_circle = Circle.objects.create(name="Strangers", created_by=make_user("x@example.com", "X"))
        theirs = make_post(circle, poster, "photo", "photo", description="Beach day")
        note = make_post(circle, poster, title="Lost tooth")
        mine = make_post(circle, grandma, "photo")
        elsewhere = make_post(other_circle, other_circle.created_by, "photo")
        opt_in(grandma)

        run_digests()

        assert len(mail.outbox) == 1
        message = mail.outbox[0]
        assert message.to == ["grandma@example.com"]
        assert message.subject == "2 new posts in your circles"
        assert f"/keeps/{theirs.id}" in message.body
        assert "Pat added 2 new photos to Smith Family" in message.body
        assert f"/keeps/{note.id}" in message.body
        assert "Pat posted in Smith Family" in message.body
        assert f"/keeps/{mine.id}" not in message.body
        assert f"/keeps/{elsewhere.id}" not in message.body
        assert "/profile/notifications" in message.body

    def test_skips_posts_the_feed_hides(self, run_digests, circle, poster, grandma):
        make_post(circle, poster, "video")  # no poster frame yet
        Keep.objects.create(circle=circle, created_by=poster, keep_type=KeepType.MEDIA)  # uploads still processing
        opt_in(grandma)

        run_digests()

        assert mail.outbox == []

    def test_window_uses_arrival_not_memory_date(self, run_digests, circle, poster, grandma):
        covered_until = timezone.now() - timedelta(hours=10)
        imported = make_post(circle, poster, "photo", hours_ago=2, date_of_memory=timezone.now() - timedelta(days=900))
        already_sent = make_post(circle, poster, "photo", hours_ago=12)
        opt_in(grandma, digest_covered_until=covered_until)

        run_digests()

        assert len(mail.outbox) == 1
        assert f"/keeps/{imported.id}" in mail.outbox[0].body
        assert f"/keeps/{already_sent.id}" not in mail.outbox[0].body

    def test_first_digest_looks_back_one_day(self, run_digests, circle, poster, grandma):
        recent = make_post(circle, poster, "photo", hours_ago=20)
        old = make_post(circle, poster, "photo", hours_ago=30)
        opt_in(grandma)

        run_digests()

        assert f"/keeps/{recent.id}" in mail.outbox[0].body
        assert f"/keeps/{old.id}" not in mail.outbox[0].body

    def test_records_coverage_so_the_next_run_does_not_repeat(self, run_digests, circle, poster, grandma):
        make_post(circle, poster, "photo")
        prefs = opt_in(grandma)
        before = timezone.now()

        run_digests()
        prefs.refresh_from_db()
        assert prefs.digest_covered_until >= before

        run_digests()
        assert len(mail.outbox) == 1

    @override_settings(NOTIFICATIONS_NEW_MEDIA_DELAY_SECONDS=600)
    def test_leaves_posts_still_settling_for_the_next_digest(
        self, django_capture_on_commit_callbacks, circle, poster, grandma
    ):
        just_posted = Keep.objects.create(circle=circle, created_by=poster, keep_type=KeepType.NOTE)
        prefs = opt_in(grandma)

        with django_capture_on_commit_callbacks(execute=True):
            assert send_digest(grandma.id) is False

        prefs.refresh_from_db()
        assert prefs.digest_covered_until < just_posted.created_at

    def test_nothing_new_sends_nothing_but_moves_the_window(self, run_digests, circle, poster, grandma):
        make_post(circle, poster, "photo", hours_ago=30)
        prefs = opt_in(grandma)

        run_digests()

        assert mail.outbox == []
        prefs.refresh_from_db()
        assert prefs.digest_covered_until is not None

    def test_caps_the_list_and_counts_the_rest(self, run_digests, circle, poster, grandma):
        for hour in range(DIGEST_MAX_POSTS + 2):
            make_post(circle, poster, "photo", hours_ago=hour + 1)
        opt_in(grandma)

        run_digests()

        body = mail.outbox[0].body
        assert mail.outbox[0].subject == f"{DIGEST_MAX_POSTS + 2} new posts in your circles"
        assert body.count("/keeps/") == DIGEST_MAX_POSTS
        assert "...and 2 more." in body

    def test_query_count_does_not_grow_with_posts(self, circle, poster, grandma):
        def queries_for_one_digest():
            UserNotificationPreferences.objects.filter(user=grandma).update(digest_covered_until=None)
            with CaptureQueriesContext(connection) as captured:
                assert send_digest(grandma.id) is True
            return len(captured)

        opt_in(grandma)
        make_post(circle, poster, "photo")
        one_post = queries_for_one_digest()
        for _ in range(5):
            make_post(circle, poster, "photo", "video", "photo")

        assert queries_for_one_digest() == one_post

    def test_opted_out_users_get_nothing(self, run_digests, circle, poster, grandma):
        make_post(circle, poster, "photo")
        make_post(circle, grandma, "photo")
        UserNotificationPreferences.objects.create(user=grandma, email_digest=False)
        # Poster has no preferences row at all.

        run_digests()

        assert mail.outbox == []

    def test_circle_override_cannot_opt_in(self, run_digests, circle, poster, grandma):
        make_post(circle, poster, "photo")
        UserNotificationPreferences.objects.create(user=grandma, circle=circle, email_digest=True)

        run_digests()

        assert mail.outbox == []

    def test_circle_override_cannot_opt_out(self, run_digests, circle, poster, grandma):
        make_post(circle, poster, "photo")
        opt_in(grandma)
        UserNotificationPreferences.objects.create(user=grandma, circle=circle, email_digest=False)

        run_digests()

        assert [message.to for message in mail.outbox] == [["grandma@example.com"]]

    def test_skips_unverified_and_inactive_users(self, run_digests, circle, poster, grandma):
        uncle = make_user("uncle@example.com", "Uncle", verified=False)
        CircleMembership.objects.create(circle=circle, user=uncle)
        make_post(circle, poster, "photo")
        opt_in(grandma)
        opt_in(uncle)
        grandma.is_active = False
        grandma.save()

        run_digests()

        assert mail.outbox == []
