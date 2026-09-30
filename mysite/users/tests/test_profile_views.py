from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from mysite.users.models import (
    Circle,
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


class NotificationPreferencesViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="notif@example.com",
            password="password123",
        )
        self.circle = Circle.objects.create(name="Notif Circle", created_by=self.user)
        # Membership for user is auto-created by the post_save signal on Circle

    def test_get_preferences_returns_event_fields(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("user-email-preferences"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("data", response.data)
        for field in ("notify_new_media", "notify_comments", "notify_replies", "notify_likes", "channel"):
            self.assertIn(field, data)
        self.assertEqual(data["channel"], "email")
        self.assertFalse(data["per_circle_override"])

    def test_patch_updates_event_preferences(self):
        self.client.force_authenticate(user=self.user)
        payload = {"notify_likes": False, "notify_comments": False}
        response = self.client.patch(reverse("user-email-preferences"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        prefs = UserNotificationPreferences.objects.get(user=self.user, circle__isnull=True)
        self.assertFalse(prefs.notify_likes)
        self.assertFalse(prefs.notify_comments)
        self.assertTrue(prefs.notify_replies)

    def test_phone_channel_rejected_until_enabled(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(reverse("user-email-preferences"), {"channel": "sms"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(UserNotificationPreferences.objects.filter(user=self.user, channel="sms").exists())

    def test_phone_channel_accepted_when_enabled(self):
        self.client.force_authenticate(user=self.user)
        with self.settings(NOTIFICATIONS_SMS_ENABLED=True):
            response = self.client.patch(reverse("user-email-preferences"), {"channel": "sms"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(UserNotificationPreferences.objects.get(user=self.user, circle=None).channel, "sms")

    def test_get_circle_without_override_returns_global_and_creates_nothing(self):
        UserNotificationPreferences.objects.create(user=self.user, notify_likes=False)
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("user-email-preferences"), {"circle_id": self.circle.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("data", response.data)
        self.assertFalse(data["per_circle_override"])
        self.assertFalse(data["notify_likes"])
        self.assertFalse(UserNotificationPreferences.objects.filter(user=self.user, circle=self.circle).exists())

    def test_patch_circle_creates_override_seeded_from_global(self):
        UserNotificationPreferences.objects.create(user=self.user, notify_likes=False)
        self.client.force_authenticate(user=self.user)
        url = f"{reverse('user-email-preferences')}?circle_id={self.circle.id}"
        response = self.client.patch(url, {"notify_new_media": False}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("data", response.data)
        self.assertTrue(data["per_circle_override"])
        override = UserNotificationPreferences.objects.get(user=self.user, circle=self.circle)
        self.assertFalse(override.notify_new_media)
        self.assertFalse(override.notify_likes)  # copied from the global row
        global_prefs = UserNotificationPreferences.objects.get(user=self.user, circle=None)
        self.assertTrue(global_prefs.notify_new_media)

    def test_delete_circle_override_restores_global(self):
        UserNotificationPreferences.objects.create(user=self.user, circle=self.circle, notify_likes=False)
        self.client.force_authenticate(user=self.user)
        url = f"{reverse('user-email-preferences')}?circle_id={self.circle.id}"
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get("data", response.data)
        self.assertFalse(data["per_circle_override"])
        self.assertTrue(data["notify_likes"])
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
