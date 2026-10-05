"""Tests for web push delivery. pywebpush is replaced with a fake: nothing leaves the process."""

import json
import sys
import types
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from mysite.messaging.push import PUSH_TTL_SECONDS, send_web_push
from mysite.messaging.tasks import send_push_async
from mysite.users.models import PushSubscription

User = get_user_model()

PAYLOAD = {"title": "Pat added a new photo to Smith Family", "body": "Beach day", "url": "/keeps/1", "tag": "/keeps/1"}


class FakeWebPushException(Exception):
    def __init__(self, message, response=None):
        super().__init__(message)
        self.response = response


@pytest.fixture
def webpush():
    """Install a fake ``pywebpush`` module and return its ``webpush`` mock."""
    module = types.ModuleType("pywebpush")
    module.WebPushException = FakeWebPushException
    module.webpush = MagicMock()
    with patch.dict(sys.modules, {"pywebpush": module}):
        yield module.webpush


@pytest.fixture(autouse=True)
def push_on():
    with override_settings(
        NOTIFICATIONS_PUSH_ENABLED=True,
        VAPID_PRIVATE_KEY="private-key",
        VAPID_PUBLIC_KEY="public-key",
        VAPID_SUBJECT="mailto:admin@example.com",
    ):
        yield


@pytest.fixture
def user():
    return User.objects.create_user(email="grandma@example.com", password="pw")


def subscribe(user, name):
    return PushSubscription.objects.create(
        user=user, endpoint=f"https://fcm.googleapis.com/fcm/send/{name}", p256dh=f"key-{name}", auth=f"auth-{name}"
    )


def failure(status_code):
    return FakeWebPushException("Push failed", response=MagicMock(status_code=status_code))


@pytest.mark.django_db
class TestSendWebPush:
    def test_pushes_to_every_device(self, webpush, user):
        phone = subscribe(user, "phone")
        subscribe(user, "laptop")

        assert send_web_push(user.id, PAYLOAD) == 2

        assert webpush.call_count == 2
        kwargs = webpush.call_args_list[0].kwargs
        assert kwargs["subscription_info"] == {
            "endpoint": phone.endpoint,
            "keys": {"p256dh": "key-phone", "auth": "auth-phone"},
        }
        assert json.loads(kwargs["data"]) == PAYLOAD
        assert kwargs["vapid_private_key"] == "private-key"
        assert kwargs["vapid_claims"] == {"sub": "mailto:admin@example.com"}
        assert kwargs["ttl"] == PUSH_TTL_SECONDS
        # Each send gets its own claims dict, since pywebpush writes aud/exp into it.
        assert webpush.call_args_list[0].kwargs["vapid_claims"] is not webpush.call_args_list[1].kwargs["vapid_claims"]
        phone.refresh_from_db()
        assert phone.last_used_at is not None

    @pytest.mark.parametrize("status_code", [404, 410])
    def test_gone_subscriptions_are_deleted(self, webpush, user, status_code):
        gone = subscribe(user, "old-phone")
        kept = subscribe(user, "laptop")
        webpush.side_effect = [failure(status_code), None]

        assert send_web_push(user.id, PAYLOAD) == 1

        assert not PushSubscription.objects.filter(pk=gone.pk).exists()
        assert PushSubscription.objects.filter(pk=kept.pk).exists()

    @pytest.mark.parametrize("status_code", [413, 429, 500])
    def test_other_failures_keep_the_subscription(self, webpush, user, status_code):
        subscription = subscribe(user, "phone")
        webpush.side_effect = failure(status_code)

        assert send_web_push(user.id, PAYLOAD) == 0

        assert PushSubscription.objects.filter(pk=subscription.pk).exists()

    def test_network_errors_do_not_stop_other_devices(self, webpush, user):
        subscribe(user, "phone")
        subscribe(user, "laptop")
        webpush.side_effect = [ConnectionError("timed out"), None]

        assert send_web_push(user.id, PAYLOAD) == 1
        assert PushSubscription.objects.filter(user=user).count() == 2

    def test_does_nothing_without_vapid_keys(self, webpush, user):
        subscribe(user, "phone")

        with override_settings(NOTIFICATIONS_PUSH_ENABLED=False):
            assert send_web_push(user.id, PAYLOAD) == 0

        webpush.assert_not_called()

    def test_missing_pywebpush_skips_push(self, user):
        subscribe(user, "phone")

        # A None entry makes ``import pywebpush`` raise ImportError.
        with patch.dict(sys.modules, {"pywebpush": None}):
            assert send_web_push(user.id, PAYLOAD) == 0

        assert PushSubscription.objects.filter(user=user).count() == 1

    def test_task_sends_push(self, webpush, user):
        subscribe(user, "phone")

        assert send_push_async.delay(user.id, PAYLOAD).get() == 1
        webpush.assert_called_once()
