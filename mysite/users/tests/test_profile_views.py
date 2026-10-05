from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from mysite.users.models import (
    Circle,
    NotificationPhone,
    User,
    UserNotificationPreferences,
)


class UserProfileViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="profile@example.com",
            password="password123",
        )

    def test_get_profile_returns_user_data(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("user-profile"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("data", response.data)
        self.assertEqual(data["user"]["id"], self.user.id)
        self.assertEqual(data["user"]["email"], self.user.email)

    def test_get_profile_requires_authentication(self):
        response = self.client.get(reverse("user-profile"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_profile_includes_default_color_theme(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("user-profile"))

        data = response.data.get("data", response.data)
        self.assertEqual(data["user"]["color_theme"], "default")

    def test_patch_updates_color_theme(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(reverse("user-profile"), {"color_theme": "sage"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.color_theme, "sage")

    def test_patch_rejects_unknown_color_theme(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(reverse("user-profile"), {"color_theme": "neon"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertEqual(self.user.color_theme, "default")


class NotificationPreferencesViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="notif@example.com",
            password="password123",
        )
        self.circle = Circle.objects.create(name="Notif Circle", created_by=self.user)
        # Membership for user is auto-created by the post_save signal on Circle

    def test_get_preferences_returns_a_switch_per_event_and_channel(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("user-email-preferences"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("data", response.data)
        for event in ("new_media", "comments", "replies", "likes"):
            self.assertTrue(data[f"{event}_email"])
            self.assertFalse(data[f"{event}_sms"])
            self.assertFalse(data[f"{event}_push"])
        self.assertFalse(data["per_circle_override"])

    def test_patch_updates_event_preferences(self):
        self.client.force_authenticate(user=self.user)
        payload = {"likes_email": False, "comments_email": False}
        response = self.client.patch(reverse("user-email-preferences"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        prefs = UserNotificationPreferences.objects.get(user=self.user, circle__isnull=True)
        self.assertFalse(prefs.likes_email)
        self.assertFalse(prefs.comments_email)
        self.assertTrue(prefs.replies_email)

    def test_sms_rejected_until_enabled(self):
        NotificationPhone.objects.create(user=self.user, phone_number="+15551234567", verified_at=timezone.now())
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(reverse("user-email-preferences"), {"likes_sms": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["messages"][0]["i18n_key"], "errors.notification_channel_unavailable")
        self.assertFalse(UserNotificationPreferences.objects.filter(user=self.user, likes_sms=True).exists())

    def test_sms_rejected_without_verified_phone(self):
        NotificationPhone.objects.create(user=self.user, phone_number="+15551234567")
        self.client.force_authenticate(user=self.user)
        with self.settings(NOTIFICATIONS_SMS_ENABLED=True):
            response = self.client.patch(reverse("user-email-preferences"), {"replies_sms": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["messages"][0]["i18n_key"], "errors.notification_phone_unverified")

    def test_sms_accepted_with_verified_phone_alongside_email(self):
        NotificationPhone.objects.create(user=self.user, phone_number="+15551234567", verified_at=timezone.now())
        self.client.force_authenticate(user=self.user)
        with self.settings(NOTIFICATIONS_SMS_ENABLED=True):
            response = self.client.patch(reverse("user-email-preferences"), {"replies_sms": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        prefs = UserNotificationPreferences.objects.get(user=self.user, circle=None)
        self.assertTrue(prefs.replies_sms)
        self.assertTrue(prefs.replies_email)
        self.assertFalse(prefs.likes_sms)

    def test_push_rejected_without_vapid_keys(self):
        self.client.force_authenticate(user=self.user)
        with self.settings(NOTIFICATIONS_PUSH_ENABLED=False):
            response = self.client.patch(reverse("user-email-preferences"), {"new_media_push": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["messages"][0]["i18n_key"], "errors.notification_channel_unavailable")

    def test_turning_sms_or_push_off_needs_no_setup(self):
        self.client.force_authenticate(user=self.user)
        payload = {"likes_sms": False, "likes_push": False}
        with self.settings(NOTIFICATIONS_SMS_ENABLED=False, NOTIFICATIONS_PUSH_ENABLED=False):
            response = self.client.patch(reverse("user-email-preferences"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_channels_can_differ_per_circle(self):
        self.client.force_authenticate(user=self.user)
        url = f"{reverse('user-email-preferences')}?circle_id={self.circle.id}"
        with self.settings(NOTIFICATIONS_PUSH_ENABLED=True):
            response = self.client.patch(url, {"likes_email": False, "likes_push": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        override = UserNotificationPreferences.objects.get(user=self.user, circle=self.circle)
        self.assertEqual(override.channels_for("likes"), ["push"])
        self.assertEqual(override.channels_for("comments"), ["email"])
        self.assertFalse(UserNotificationPreferences.objects.filter(user=self.user, circle=None).exists())

    def test_email_digest_is_off_by_default(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("user-email-preferences"))

        data = response.data.get("data", response.data)
        self.assertFalse(data["email_digest"])

    def test_patch_toggles_email_digest(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(reverse("user-email-preferences"), {"email_digest": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["data"]["email_digest"])
        self.assertTrue(UserNotificationPreferences.objects.get(user=self.user, circle=None).email_digest)

        response = self.client.patch(reverse("user-email-preferences"), {"email_digest": False}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(UserNotificationPreferences.objects.get(user=self.user, circle=None).email_digest)

    def test_email_digest_cannot_be_set_per_circle(self):
        self.client.force_authenticate(user=self.user)
        url = f"{reverse('user-email-preferences')}?circle_id={self.circle.id}"
        response = self.client.patch(url, {"email_digest": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(UserNotificationPreferences.objects.filter(user=self.user, email_digest=True).exists())

    def test_get_circle_without_override_returns_global_and_creates_nothing(self):
        UserNotificationPreferences.objects.create(user=self.user, likes_email=False)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("user-email-preferences"), {"circle_id": self.circle.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("data", response.data)
        self.assertFalse(data["per_circle_override"])
        self.assertFalse(data["likes_email"])
        self.assertFalse(UserNotificationPreferences.objects.filter(user=self.user, circle=self.circle).exists())

    def test_patch_circle_creates_override_seeded_from_global(self):
        UserNotificationPreferences.objects.create(user=self.user, likes_email=False)
        self.client.force_authenticate(user=self.user)
        url = f"{reverse('user-email-preferences')}?circle_id={self.circle.id}"
        response = self.client.patch(url, {"new_media_email": False}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("data", response.data)
        self.assertTrue(data["per_circle_override"])
        override = UserNotificationPreferences.objects.get(user=self.user, circle=self.circle)
        self.assertFalse(override.new_media_email)
        self.assertFalse(override.likes_email)  # copied from the global row
        global_prefs = UserNotificationPreferences.objects.get(user=self.user, circle=None)
        self.assertTrue(global_prefs.new_media_email)

    def test_delete_circle_override_restores_global(self):
        UserNotificationPreferences.objects.create(user=self.user, circle=self.circle, likes_email=False)
        self.client.force_authenticate(user=self.user)
        url = f"{reverse('user-email-preferences')}?circle_id={self.circle.id}"
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("data", response.data)
        self.assertFalse(data["per_circle_override"])
        self.assertTrue(data["likes_email"])
        self.assertFalse(UserNotificationPreferences.objects.filter(user=self.user, circle=self.circle).exists())

    def test_delete_without_circle_is_rejected(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(reverse("user-email-preferences"))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_circle_preferences_require_membership(self):
        other = User.objects.create_user(email="other@example.com", password="password123")
        other_circle = Circle.objects.create(name="Other", created_by=other)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("user-email-preferences"), {"circle_id": other_circle.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_profile_updates_names(self):
        self.client.force_authenticate(user=self.user)
        payload = {"first_name": "Profile", "last_name": "Updated"}
        response = self.client.patch(reverse("user-profile"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, payload["first_name"])
        self.assertEqual(self.user.last_name, payload["last_name"])

    def test_patch_profile_requires_authentication(self):
        response = self.client.patch(reverse("user-profile"), {"first_name": "Anon"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
