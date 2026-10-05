"""Tests for circle activity notifications (new photos, comments, replies, likes)."""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

from mysite.circles.models import Circle, CircleMembership
from mysite.keeps.models import Keep, KeepComment, KeepMedia, KeepReaction, KeepType
from mysite.keeps.notifications import ActivityEvent, media_label, send_activity
from mysite.users.models import NotificationChannel, UserNotificationPreferences

User = get_user_model()

KEEPS_URL = "/api/keeps/"
COMMENTS_URL = "/api/keeps/comments/"
REACTIONS_URL = "/api/keeps/reactions/"


def make_user(email, first_name, verified=True):
    return User.objects.create_user(email=email, password="testpass123", first_name=first_name, email_verified=verified)


def add_media(keep, *media_types):
    for order, media_type in enumerate(media_types):
        KeepMedia.objects.create(
            keep=keep, media_type=media_type, upload_order=order, storage_key_original=f"{keep.id}/{order}"
        )


def recipients():
    return sorted(address for message in mail.outbox for address in message.to)


@pytest.fixture(autouse=True)
def clear_like_window():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def poster():
    return make_user("poster@example.com", "Pat")


@pytest.fixture
def grandma():
    return make_user("grandma@example.com", "Grandma")


@pytest.fixture
def uncle():
    return make_user("uncle@example.com", "Uncle")


@pytest.fixture
def circle(poster, grandma, uncle):
    """The creator's membership comes from a signal; add the others."""
    circle = Circle.objects.create(name="Smith Family", created_by=poster)
    CircleMembership.objects.create(circle=circle, user=grandma)
    CircleMembership.objects.create(circle=circle, user=uncle)
    return circle


@pytest.fixture
def keep(circle, poster):
    return Keep.objects.create(circle=circle, created_by=poster, keep_type=KeepType.MEDIA, description="Beach day")


@pytest.mark.django_db
class TestNewMedia:
    def test_emails_every_other_member_once_per_post(self, keep):
        add_media(keep, "photo", "photo")

        send_activity(ActivityEvent.NEW_MEDIA, str(keep.id))

        assert recipients() == ["grandma@example.com", "uncle@example.com"]
        assert mail.outbox[0].subject == "Pat added 2 new photos to Smith Family"
        assert f"/keeps/{keep.id}" in mail.outbox[0].body
        assert "/profile/notifications" in mail.outbox[0].body

    def test_post_without_media_sends_nothing(self, keep):
        send_activity(ActivityEvent.NEW_MEDIA, str(keep.id))

        assert mail.outbox == []

    def test_deleted_post_sends_nothing(self, keep):
        keep_id = str(keep.id)
        keep.delete()

        send_activity(ActivityEvent.NEW_MEDIA, keep_id)

        assert mail.outbox == []

    def test_respects_global_and_circle_preferences(self, keep, circle, grandma, uncle):
        add_media(keep, "photo")
        UserNotificationPreferences.objects.create(user=grandma, notify_new_media=False)
        UserNotificationPreferences.objects.create(user=uncle, notify_new_media=True)
        UserNotificationPreferences.objects.create(user=uncle, circle=circle, notify_new_media=False)

        send_activity(ActivityEvent.NEW_MEDIA, str(keep.id))

        assert mail.outbox == []

    def test_circle_override_can_turn_on_what_global_turns_off(self, keep, circle, grandma):
        add_media(keep, "photo")
        UserNotificationPreferences.objects.create(user=grandma, notify_new_media=False)
        UserNotificationPreferences.objects.create(user=grandma, circle=circle, notify_new_media=True)

        send_activity(ActivityEvent.NEW_MEDIA, str(keep.id))

        assert "grandma@example.com" in recipients()

    def test_skips_unverified_and_inactive_members(self, keep, grandma, uncle):
        add_media(keep, "photo")
        grandma.email_verified = False
        grandma.save()
        uncle.is_active = False
        uncle.save()

        send_activity(ActivityEvent.NEW_MEDIA, str(keep.id))

        assert mail.outbox == []

    def test_phone_channel_sends_no_email(self, keep, grandma):
        add_media(keep, "photo")
        UserNotificationPreferences.objects.create(user=grandma, channel=NotificationChannel.SMS)

        send_activity(ActivityEvent.NEW_MEDIA, str(keep.id))

        assert recipients() == ["uncle@example.com"]

    @override_settings(NOTIFICATIONS_NEW_MEDIA_DELAY_SECONDS=321)
    def test_creating_a_post_queues_a_delayed_notification(
        self, api_client, poster, circle, django_capture_on_commit_callbacks
    ):
        api_client.force_authenticate(user=poster)
        with (
            patch("mysite.keeps.tasks.send_activity_notifications.apply_async") as apply_async,
            django_capture_on_commit_callbacks(execute=True),
        ):
            response = api_client.post(
                KEEPS_URL, {"circle": circle.id, "keep_type": "media", "description": "Zoo"}, format="json"
            )

        assert response.status_code == status.HTTP_201_CREATED
        apply_async.assert_called_once_with(args=[ActivityEvent.NEW_MEDIA, str(response.data["id"])], countdown=321)


@pytest.mark.parametrize(
    ("media_types", "label"),
    [
        (["photo"], "a new photo"),
        (["photo", "photo", "photo"], "3 new photos"),
        (["video"], "a new video"),
        (["video", "video"], "2 new videos"),
        (["photo", "video"], "2 new photos and videos"),
    ],
)
def test_media_label(media_types, label):
    assert media_label(media_types) == label


@pytest.mark.django_db
class TestComments:
    def post_comment(self, api_client, author, keep, text, parent=None, capture=None):
        api_client.force_authenticate(user=author)
        payload = {"keep": str(keep.id), "comment": text}
        if parent is not None:
            payload["parent"] = parent.id
        with capture(execute=True):
            response = api_client.post(COMMENTS_URL, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED, response.data
        return response

    def test_comment_emails_post_author(self, api_client, keep, grandma, django_capture_on_commit_callbacks):
        self.post_comment(api_client, grandma, keep, "Isn't she cute", capture=django_capture_on_commit_callbacks)

        assert recipients() == ["poster@example.com"]
        assert mail.outbox[0].subject == "Grandma commented on your post in Smith Family"
        assert "Isn't she cute" in mail.outbox[0].body

    def test_own_comment_sends_nothing(self, api_client, keep, poster, django_capture_on_commit_callbacks):
        self.post_comment(api_client, poster, keep, "Thanks all", capture=django_capture_on_commit_callbacks)

        assert mail.outbox == []

    def test_reply_emails_the_person_replied_to_and_the_post_author(
        self, api_client, keep, grandma, uncle, django_capture_on_commit_callbacks
    ):
        parent = KeepComment.objects.create(keep=keep, user=grandma, comment="So sweet")

        self.post_comment(
            api_client, uncle, keep, "@Grandma agreed", parent=parent, capture=django_capture_on_commit_callbacks
        )

        subjects = {message.to[0]: message.subject for message in mail.outbox}
        assert subjects == {
            "grandma@example.com": "Uncle replied to you in Smith Family",
            "poster@example.com": "Uncle commented on your post in Smith Family",
        }

    def test_reply_to_post_author_sends_only_the_reply_notice(
        self, api_client, keep, poster, grandma, django_capture_on_commit_callbacks
    ):
        parent = KeepComment.objects.create(keep=keep, user=poster, comment="Thanks!")

        self.post_comment(
            api_client, grandma, keep, "@Pat anytime", parent=parent, capture=django_capture_on_commit_callbacks
        )

        assert len(mail.outbox) == 1
        assert mail.outbox[0].subject == "Grandma replied to you in Smith Family"

    def test_replies_can_be_turned_off(self, api_client, keep, grandma, uncle, django_capture_on_commit_callbacks):
        UserNotificationPreferences.objects.create(user=grandma, notify_replies=False)
        parent = KeepComment.objects.create(keep=keep, user=grandma, comment="So sweet")

        self.post_comment(
            api_client, uncle, keep, "@Grandma agreed", parent=parent, capture=django_capture_on_commit_callbacks
        )

        assert recipients() == ["poster@example.com"]

    def test_rows_written_directly_do_not_notify(self, keep, grandma, django_capture_on_commit_callbacks):
        """The journal import writes rows through the ORM; imported history must stay quiet."""
        with django_capture_on_commit_callbacks(execute=True):
            KeepComment.objects.create(keep=keep, user=grandma, comment="Imported")
            KeepReaction.objects.create(keep=keep, user=grandma)

        assert mail.outbox == []


@pytest.mark.django_db
class TestLikes:
    def like(self, api_client, user, keep, capture):
        api_client.force_authenticate(user=user)
        with capture(execute=True):
            response = api_client.post(REACTIONS_URL, {"keep": str(keep.id), "reaction_type": "like"}, format="json")
        assert response.status_code == status.HTTP_201_CREATED, response.data
        return response

    def test_like_emails_post_author(self, api_client, keep, grandma, django_capture_on_commit_callbacks):
        self.like(api_client, grandma, keep, django_capture_on_commit_callbacks)

        assert recipients() == ["poster@example.com"]
        assert mail.outbox[0].subject == "Grandma liked your post in Smith Family"

    def test_unlike_and_like_again_sends_once(self, api_client, keep, grandma, django_capture_on_commit_callbacks):
        response = self.like(api_client, grandma, keep, django_capture_on_commit_callbacks)
        KeepReaction.objects.filter(id=response.data["id"]).delete()
        self.like(api_client, grandma, keep, django_capture_on_commit_callbacks)

        assert len(mail.outbox) == 1

    def test_likes_can_be_turned_off(self, api_client, keep, poster, grandma, django_capture_on_commit_callbacks):
        UserNotificationPreferences.objects.create(user=poster, notify_likes=False)

        self.like(api_client, grandma, keep, django_capture_on_commit_callbacks)

        assert mail.outbox == []
