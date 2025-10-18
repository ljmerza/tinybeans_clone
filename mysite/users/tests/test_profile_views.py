from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from mysite.users.models import (
    Circle,
    CircleMembership,
    User,
    UserNotificationPreferences,
    UserRole,
)


class UserProfileViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='profileuser',
            email='profile@example.com',
            password='password123',
        )

    def test_get_profile_returns_user_data(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('user-profile'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get('data', response.data)
        self.assertEqual(data['user']['id'], self.user.id)
        self.assertEqual(data['user']['email'], self.user.email)

    def test_get_profile_requires_authentication(self):
        response = self.client.get(reverse('user-profile'))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class NotificationPreferencesViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='notifuser',
            email='notif@example.com',
            password='password123',
        )
        self.circle = Circle.objects.create(name='Notif Circle', created_by=self.user)
        CircleMembership.objects.create(
            user=self.user,
            circle=self.circle,
            role=UserRole.CIRCLE_ADMIN,
        )

    def test_get_preferences_returns_extended_fields(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('user-email-preferences'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get('data', response.data)
        self.assertIn('digest_frequency', data)
        self.assertIn('push_enabled', data)
        self.assertIn('per_circle_override', data)
        self.assertFalse(data['per_circle_override'])

    def test_patch_updates_digest_and_push_preferences(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            'digest_frequency': 'daily',
            'push_enabled': True,
        }
        response = self.client.patch(reverse('user-email-preferences'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        prefs = UserNotificationPreferences.objects.get(user=self.user, circle__isnull=True)
        self.assertEqual(prefs.digest_frequency, payload['digest_frequency'])
        self.assertTrue(prefs.push_enabled)

    def test_circle_override_creates_separate_preferences(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            reverse('user-email-preferences'),
            {'circle_id': self.circle.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get('data', response.data)
        self.assertTrue(data['per_circle_override'])
        override = UserNotificationPreferences.objects.get(user=self.user, circle=self.circle)
        self.assertIsNotNone(override)

    def test_patch_profile_updates_names(self):
        self.client.force_authenticate(user=self.user)
        payload = {'first_name': 'Profile', 'last_name': 'Updated'}
        response = self.client.patch(reverse('user-profile'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, payload['first_name'])
        self.assertEqual(self.user.last_name, payload['last_name'])

    def test_patch_profile_requires_authentication(self):
        response = self.client.patch(reverse('user-profile'), {'first_name': 'Anon'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
