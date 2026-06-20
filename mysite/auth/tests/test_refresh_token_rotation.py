"""Refresh-token rotation and logout revocation tests (ADR-015).

Covers:
- ROTATE_REFRESH_TOKENS=True rotates the cookie and blacklists the prior token.
- A rotated (previous) refresh token cannot be replayed.
- Logout revokes (blacklists) the presented refresh token.
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from mysite.users.models import User


class RefreshTokenRotationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='rotate@example.com', password='password123')

    def _login(self):
        return self.client.post(
            reverse('auth-login'),
            {'email': self.user.email, 'password': 'password123'},
            format='json',
        )

    def test_refresh_rotates_and_blacklists_previous_token(self):
        login_response = self._login()
        original_refresh = login_response.cookies['refresh_token'].value

        # First refresh rotates the refresh token.
        self.client.cookies['refresh_token'] = original_refresh
        first_refresh = self.client.post(reverse('auth-token-refresh'))
        self.assertEqual(first_refresh.status_code, status.HTTP_200_OK)
        rotated_refresh = first_refresh.cookies['refresh_token'].value
        self.assertNotEqual(rotated_refresh, original_refresh)

        # Replaying the now-rotated original token must be rejected.
        self.client.cookies['refresh_token'] = original_refresh
        replay = self.client.post(reverse('auth-token-refresh'))
        self.assertEqual(replay.status_code, status.HTTP_401_UNAUTHORIZED)

        # The rotated token is still valid.
        self.client.cookies['refresh_token'] = rotated_refresh
        ok = self.client.post(reverse('auth-token-refresh'))
        self.assertEqual(ok.status_code, status.HTTP_200_OK)

    def test_logout_revokes_refresh_token(self):
        login_response = self._login()
        refresh_token = login_response.cookies['refresh_token'].value

        self.client.cookies['refresh_token'] = refresh_token
        logout_response = self.client.post(reverse('auth-logout'))
        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)
        # Logout clears the cookie.
        self.assertEqual(logout_response.cookies['refresh_token'].value, '')

        # The refresh token is now revoked and cannot mint new access tokens.
        self.client.cookies['refresh_token'] = refresh_token
        replay = self.client.post(reverse('auth-token-refresh'))
        self.assertEqual(replay.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_without_cookie_succeeds(self):
        # Logout must always succeed, even with no refresh cookie present.
        response = self.client.post(reverse('auth-logout'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_logout_with_invalid_cookie_succeeds(self):
        # A malformed/expired token must not break logout.
        self.client.cookies['refresh_token'] = 'not-a-real-token'
        response = self.client.post(reverse('auth-logout'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
