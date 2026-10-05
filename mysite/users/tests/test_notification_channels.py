"""Tests for the notification phone and push subscription endpoints."""

from datetime import timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from mysite.users.models import (
    NOTIFICATION_EVENTS,
    NotificationPhone,
    PushSubscription,
    User,
    UserNotificationPreferences,
)
from mysite.users.models.notifications import PHONE_CODE_MAX_ATTEMPTS

PHONE = "+15551234567"
ENDPOINT = "https://fcm.googleapis.com/fcm/send/abc123"
SUBSCRIPTION = {"endpoint": ENDPOINT, "expirationTime": None, "keys": {"p256dh": "device-key", "auth": "device-auth"}}


def payload(response):
    return response.data.get("data", response.data)


def first_message_key(response):
    return response.data["messages"][0]["i18n_key"]


@override_settings(NOTIFICATIONS_SMS_ENABLED=True, NOTIFICATIONS_SMS_ALLOWED_PREFIXES=["+1"])
class NotificationPhoneTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user(email="grandma@example.com", password="password123")
        self.client.force_authenticate(user=self.user)
        patcher = patch("mysite.users.views.notification_channels.send_sms_async")
        self.sms = patcher.start().delay
        self.addCleanup(patcher.stop)

    def start(self, number=PHONE):
        return self.client.post(reverse("user-notification-phone"), {"phone_number": number}, format="json")

    def verify(self, code):
        return self.client.post(reverse("user-notification-phone-verify"), {"code": code}, format="json")

    def texted_code(self):
        return self.sms.call_args.args[1].split("is ")[1][:6]

    def test_channels_report_what_the_server_offers(self):
        with override_settings(NOTIFICATIONS_PUSH_ENABLED=True, VAPID_PUBLIC_KEY="public-key"):
            response = self.client.get(reverse("user-notification-channels"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            payload(response),
            {
                "sms_available": True,
                "phone_number": None,
                "phone_verified": False,
                "phone_verification_pending": False,
                "push_available": True,
                "vapid_public_key": "public-key",
                "push_device_count": 0,
            },
        )

    def test_start_texts_a_code_and_stores_only_its_hash(self):
        response = self.start("+1 (555) 123-4567")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(payload(response)["phone_number"], PHONE)
        self.assertTrue(payload(response)["phone_verification_pending"])
        self.assertFalse(payload(response)["phone_verified"])
        self.sms.assert_called_once()
        self.assertEqual(self.sms.call_args.args[0], PHONE)
        phone = NotificationPhone.objects.get(user=self.user)
        self.assertNotIn(self.texted_code(), phone.code_hash)
        self.assertIsNone(phone.verified_at)

    def test_correct_code_verifies_the_phone(self):
        self.start()

        response = self.verify(self.texted_code())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(payload(response)["phone_verified"])
        self.assertTrue(NotificationPhone.objects.get(user=self.user).is_verified)

    def test_wrong_code_is_rejected_and_counted(self):
        self.start()
        wrong = "000000" if self.texted_code() != "000000" else "111111"

        response = self.verify(wrong)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(first_message_key(response), "errors.notification_phone_code_invalid")
        phone = NotificationPhone.objects.get(user=self.user)
        self.assertEqual(phone.code_attempts, 1)
        self.assertIsNone(phone.verified_at)

    def test_code_dies_after_too_many_wrong_guesses(self):
        self.start()
        code = self.texted_code()
        NotificationPhone.objects.filter(user=self.user).update(code_attempts=PHONE_CODE_MAX_ATTEMPTS)

        response = self.verify(code)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIsNone(NotificationPhone.objects.get(user=self.user).verified_at)

    def test_expired_code_is_rejected(self):
        self.start()
        code = self.texted_code()
        NotificationPhone.objects.filter(user=self.user).update(code_expires_at=timezone.now() - timedelta(seconds=1))

        response = self.verify(code)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_code_works_only_once(self):
        self.start()
        code = self.texted_code()
        self.verify(code)

        response = self.verify(code)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_without_a_phone_is_rejected(self):
        response = self.verify("123456")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_new_number_needs_verifying_again(self):
        NotificationPhone.objects.create(user=self.user, phone_number=PHONE, verified_at=timezone.now())

        response = self.start("+15559876543")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        phone = NotificationPhone.objects.get(user=self.user)
        self.assertEqual(phone.phone_number, "+15559876543")
        self.assertIsNone(phone.verified_at)

    def test_same_verified_number_is_not_texted_again(self):
        NotificationPhone.objects.create(user=self.user, phone_number=PHONE, verified_at=timezone.now())

        response = self.start()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(payload(response)["phone_verified"])
        self.sms.assert_not_called()

    def test_invalid_number_is_rejected(self):
        response = self.start("555-1234")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.sms.assert_not_called()
        self.assertFalse(NotificationPhone.objects.exists())

    def test_number_outside_allowed_countries_is_rejected(self):
        response = self.start("+442071234567")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.sms.assert_not_called()

    @override_settings(NOTIFICATIONS_SMS_ALLOWED_PREFIXES=[])
    def test_empty_allow_list_accepts_any_country(self):
        response = self.start("+442071234567")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @override_settings(NOTIFICATIONS_SMS_ENABLED=False)
    def test_unavailable_when_sms_is_off(self):
        response = self.start()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(first_message_key(response), "errors.notification_channel_unavailable")
        self.sms.assert_not_called()

    @override_settings(RATELIMIT_ENABLE=True, NOTIFICATION_PHONE_CODE_RATELIMIT="2/15m")
    def test_code_requests_are_rate_limited(self):
        self.start()
        self.start("+15559876543")

        response = self.start()

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(self.sms.call_count, 2)

    def test_remove_phone_turns_texts_off(self):
        NotificationPhone.objects.create(user=self.user, phone_number=PHONE, verified_at=timezone.now())
        UserNotificationPreferences.objects.create(user=self.user, new_media_sms=True, likes_sms=True)

        response = self.client.delete(reverse("user-notification-phone"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(payload(response)["phone_number"])
        self.assertFalse(NotificationPhone.objects.exists())
        prefs = UserNotificationPreferences.objects.get(user=self.user)
        self.assertEqual([prefs.channels_for(event) for event in NOTIFICATION_EVENTS], [["email"]] * 4)

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.start()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@override_settings(NOTIFICATIONS_PUSH_ENABLED=True)
class PushSubscriptionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="grandma@example.com", password="password123")
        self.client.force_authenticate(user=self.user)

    def subscribe(self, body=None):
        return self.client.post(
            reverse("user-push-subscriptions"), body or SUBSCRIPTION, format="json", HTTP_USER_AGENT="Phone Browser"
        )

    def test_subscribe_saves_the_device(self):
        response = self.subscribe()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(payload(response)["push_device_count"], 1)
        subscription = PushSubscription.objects.get(user=self.user)
        self.assertEqual(subscription.endpoint, ENDPOINT)
        self.assertEqual(subscription.p256dh, "device-key")
        self.assertEqual(subscription.auth, "device-auth")
        self.assertEqual(subscription.user_agent, "Phone Browser")

    def test_subscribing_again_updates_instead_of_duplicating(self):
        self.subscribe()
        self.subscribe({**SUBSCRIPTION, "keys": {"p256dh": "new-key", "auth": "new-auth"}})

        subscription = PushSubscription.objects.get(endpoint=ENDPOINT)
        self.assertEqual(subscription.p256dh, "new-key")
        self.assertEqual(PushSubscription.objects.count(), 1)

    def test_device_moves_to_whoever_subscribes_it(self):
        other = User.objects.create_user(email="uncle@example.com", password="password123")
        PushSubscription.objects.create(user=other, endpoint=ENDPOINT, p256dh="k", auth="a")

        self.subscribe()

        self.assertEqual(PushSubscription.objects.get(endpoint=ENDPOINT).user, self.user)

    def test_unknown_push_service_is_rejected(self):
        for endpoint in (
            "https://internal.example.com/hook",
            "http://fcm.googleapis.com/fcm/send/abc",
            "https://fcm.googleapis.com.evil.example/x",
        ):
            with self.subTest(endpoint=endpoint):
                response = self.subscribe({**SUBSCRIPTION, "endpoint": endpoint})

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(PushSubscription.objects.exists())

    def test_apple_and_mozilla_push_services_are_accepted(self):
        for endpoint in (
            "https://web.push.apple.com/QAbc",
            "https://updates.push.services.mozilla.com/wpush/v2/abc",
        ):
            with self.subTest(endpoint=endpoint):
                response = self.subscribe({**SUBSCRIPTION, "endpoint": endpoint})

                self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_missing_keys_are_rejected(self):
        response = self.subscribe({"endpoint": ENDPOINT})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(NOTIFICATIONS_PUSH_ENABLED=False)
    def test_unavailable_without_vapid_keys(self):
        response = self.subscribe()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(PushSubscription.objects.exists())

    def test_unsubscribe_removes_only_your_own_device(self):
        PushSubscription.objects.create(user=self.user, endpoint=ENDPOINT, p256dh="k", auth="a")
        other = User.objects.create_user(email="uncle@example.com", password="password123")
        other_endpoint = "https://fcm.googleapis.com/fcm/send/other"
        PushSubscription.objects.create(user=other, endpoint=other_endpoint, p256dh="k", auth="a")

        response = self.client.delete(reverse("user-push-subscriptions"), {"endpoint": ENDPOINT}, format="json")
        self.client.delete(reverse("user-push-subscriptions"), {"endpoint": other_endpoint}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(payload(response)["push_device_count"], 0)
        self.assertEqual(list(PushSubscription.objects.values_list("endpoint", flat=True)), [other_endpoint])
