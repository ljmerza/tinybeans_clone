"""Tests for sending activity notifications on every channel a member turned on."""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone

from mysite.circles.models import Circle, CircleMembership
from mysite.keeps.models import Keep, KeepComment, KeepMedia, KeepType
from mysite.keeps.notifications import ActivityEvent, send_activity
from mysite.messaging.providers.console import ConsoleSMSProvider
from mysite.messaging.services import SMSService
from mysite.users.models import NotificationPhone, PushSubscription, UserNotificationPreferences

User = get_user_model()

PHONE = "+15551234567"


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def channels_on():
    with override_settings(NOTIFICATIONS_SMS_ENABLED=True, NOTIFICATIONS_PUSH_ENABLED=True):
        yield


@pytest.fixture
def sms():
    with patch("mysite.keeps.notifications.send_sms_async") as task:
        yield task.delay


@pytest.fixture
def push():
    with patch("mysite.keeps.notifications.send_push_async") as task:
        yield task.delay


@pytest.fixture
def poster():
    return User.objects.create_user(email="poster@example.com", password="pw", first_name="Pat", email_verified=True)


@pytest.fixture
def grandma():
    return User.objects.create_user(
        email="grandma@example.com", password="pw", first_name="Grandma", email_verified=True
    )


@pytest.fixture
def circle(poster, grandma):
    circle = Circle.objects.create(name="Smith Family", created_by=poster)
    CircleMembership.objects.create(circle=circle, user=grandma)
    return circle


@pytest.fixture
def keep(circle, poster):
    keep = Keep.objects.create(circle=circle, created_by=poster, keep_type=KeepType.MEDIA, description="Beach day")
    KeepMedia.objects.create(keep=keep, media_type="photo", upload_order=0, storage_key_original=f"{keep.id}/0")
    return keep


def verified_phone(user, number=PHONE):
    return NotificationPhone.objects.create(user=user, phone_number=number, verified_at=timezone.now())


def subscribe(user):
    return PushSubscription.objects.create(
        user=user, endpoint=f"https://fcm.googleapis.com/fcm/send/{user.id}", p256dh="key", auth="secret"
    )


def emailed():
    return sorted(address for message in mail.outbox for address in message.to)


@pytest.mark.django_db
class TestChannelFanOut:
    def test_sends_on_every_enabled_channel(self, keep, grandma, sms, push):
        UserNotificationPreferences.objects.create(
            user=grandma, email_enabled=True, sms_enabled=True, push_enabled=True
        )
        verified_phone(grandma)
        subscribe(grandma)

        send_activity(ActivityEvent.NEW_MEDIA, str(keep.id))

        assert emailed() == ["grandma@example.com"]
        sms.assert_called_once_with(
            PHONE, f"Circles: Pat added a new photo to Smith Family http://localhost:3000/keeps/{keep.id}"
        )
        push.assert_called_once()
        user_id, payload = push.call_args.args
        assert user_id == grandma.id
        assert payload == {
            "title": "Pat added a new photo to Smith Family",
            "body": "Beach day",
            "url": f"http://localhost:3000/keeps/{keep.id}",
            "tag": f"http://localhost:3000/keeps/{keep.id}",
        }

    def test_defaults_to_email_only(self, keep, grandma, sms, push):
        verified_phone(grandma)
        subscribe(grandma)

        send_activity(ActivityEvent.NEW_MEDIA, str(keep.id))

        assert emailed() == ["grandma@example.com"]
        sms.assert_not_called()
        push.assert_not_called()

    def test_no_channels_sends_nothing(self, keep, grandma, sms, push):
        UserNotificationPreferences.objects.create(user=grandma, email_enabled=False)

        send_activity(ActivityEvent.NEW_MEDIA, str(keep.id))

        assert mail.outbox == []
        sms.assert_not_called()
        push.assert_not_called()

    def test_event_switched_off_sends_on_no_channel(self, keep, grandma, sms, push):
        UserNotificationPreferences.objects.create(user=grandma, notify_new_media=False, sms_enabled=True)
        verified_phone(grandma)

        send_activity(ActivityEvent.NEW_MEDIA, str(keep.id))

        assert mail.outbox == []
        sms.assert_not_called()


@pytest.mark.django_db
class TestCircleOverrides:
    def test_circle_override_picks_its_own_channels(self, keep, circle, grandma, sms, push):
        UserNotificationPreferences.objects.create(user=grandma, email_enabled=True)
        UserNotificationPreferences.objects.create(user=grandma, circle=circle, email_enabled=False, sms_enabled=True)
        verified_phone(grandma)

        send_activity(ActivityEvent.NEW_MEDIA, str(keep.id))

        assert mail.outbox == []
        sms.assert_called_once()

    def test_global_channels_apply_to_circles_without_override(self, keep, poster, grandma, sms, push):
        other = Circle.objects.create(name="Other", created_by=poster)
        CircleMembership.objects.create(circle=other, user=grandma)
        UserNotificationPreferences.objects.create(user=grandma, email_enabled=False, push_enabled=True)
        UserNotificationPreferences.objects.create(user=grandma, circle=other, email_enabled=True)
        subscribe(grandma)

        send_activity(ActivityEvent.NEW_MEDIA, str(keep.id))

        assert mail.outbox == []
        push.assert_called_once()


@pytest.mark.django_db
class TestSms:
    def test_only_verified_phones_get_texts(self, keep, grandma, sms):
        UserNotificationPreferences.objects.create(user=grandma, sms_enabled=True)
        NotificationPhone.objects.create(user=grandma, phone_number=PHONE)

        send_activity(ActivityEvent.NEW_MEDIA, str(keep.id))

        sms.assert_not_called()

    def test_no_phone_gets_no_text(self, keep, grandma, sms):
        UserNotificationPreferences.objects.create(user=grandma, sms_enabled=True)

        send_activity(ActivityEvent.NEW_MEDIA, str(keep.id))

        sms.assert_not_called()

    def test_server_flag_off_sends_no_text(self, keep, grandma, sms):
        UserNotificationPreferences.objects.create(user=grandma, sms_enabled=True)
        verified_phone(grandma)

        with override_settings(NOTIFICATIONS_SMS_ENABLED=False):
            send_activity(ActivityEvent.NEW_MEDIA, str(keep.id))

        sms.assert_not_called()

    @override_settings(NOTIFICATIONS_SMS_DAILY_LIMIT=1)
    def test_daily_limit_caps_texts(self, keep, grandma, sms):
        UserNotificationPreferences.objects.create(user=grandma, sms_enabled=True)
        verified_phone(grandma)

        send_activity(ActivityEvent.NEW_MEDIA, str(keep.id))
        send_activity(ActivityEvent.NEW_MEDIA, str(keep.id))

        assert sms.call_count == 1

    def test_comment_text_stays_out_of_texts(self, keep, poster, grandma, sms):
        UserNotificationPreferences.objects.create(user=poster, sms_enabled=True)
        verified_phone(poster)
        comment = KeepComment.objects.create(keep=keep, user=grandma, comment="A private thought")

        send_activity(ActivityEvent.COMMENT, str(comment.id))

        message = sms.call_args.args[1]
        assert message == (
            f"Circles: Grandma commented on your post in Smith Family http://localhost:3000/keeps/{keep.id}"
        )
        assert "private" not in message

    @override_settings(SMS_PROVIDER="console")
    def test_text_goes_through_the_console_provider(self, keep, grandma):
        UserNotificationPreferences.objects.create(user=grandma, email_enabled=False, sms_enabled=True)
        verified_phone(grandma)
        provider = ConsoleSMSProvider()

        with (
            patch.object(SMSService, "_provider", provider),
            patch.object(provider, "send_sms", wraps=provider.send_sms) as send_sms,
        ):
            send_activity(ActivityEvent.NEW_MEDIA, str(keep.id))

        send_sms.assert_called_once()
        assert send_sms.call_args.args[0] == PHONE


@pytest.mark.django_db
class TestPush:
    def test_comment_push_shows_the_comment(self, keep, poster, grandma, push):
        UserNotificationPreferences.objects.create(user=poster, email_enabled=False, push_enabled=True)
        subscribe(poster)
        comment = KeepComment.objects.create(keep=keep, user=grandma, comment="So cute")

        send_activity(ActivityEvent.COMMENT, str(comment.id))

        payload = push.call_args.args[1]
        assert payload["title"] == "Grandma commented on your post in Smith Family"
        assert payload["body"] == "So cute"

    def test_no_devices_queues_nothing(self, keep, grandma, push):
        UserNotificationPreferences.objects.create(user=grandma, push_enabled=True)

        send_activity(ActivityEvent.NEW_MEDIA, str(keep.id))

        push.assert_not_called()

    def test_push_off_server_side_queues_nothing(self, keep, grandma, push):
        UserNotificationPreferences.objects.create(user=grandma, push_enabled=True)
        subscribe(grandma)

        with override_settings(NOTIFICATIONS_PUSH_ENABLED=False):
            send_activity(ActivityEvent.NEW_MEDIA, str(keep.id))

        push.assert_not_called()
