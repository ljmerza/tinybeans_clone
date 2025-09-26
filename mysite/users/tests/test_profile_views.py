from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from users.models import User


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
        self.assertEqual(response.data['user']['id'], self.user.id)
        self.assertEqual(response.data['user']['email'], self.user.email)

    def test_get_profile_requires_authentication(self):
        response = self.client.get(reverse('user-profile'))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

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
