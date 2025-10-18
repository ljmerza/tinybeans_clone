from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from mysite.users.models import User


class AuthTokenCookieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='cookieuser',
            email='cookie@example.com',
            password='password123',
        )

    def _login(self):
        return self.client.post(
            reverse('auth-login'),
            {'username': self.user.username, 'password': 'password123'},
            format='json',
        )

    def test_login_sets_secure_http_only_refresh_cookie(self):
        response = self._login()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual(set(body['data']['tokens'].keys()), {'access'})
        cookie = response.cookies['refresh_token']
        self.assertTrue(bool(cookie['httponly']))
        self.assertTrue(bool(cookie['secure']))
        self.assertEqual(cookie['path'], '/api/auth/token/refresh/')

    @override_settings(DEBUG=True)
    def test_login_cookie_not_secure_in_debug(self):
        response = self._login()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cookie = response.cookies['refresh_token']
        # httponly should remain enabled
        self.assertTrue(bool(cookie['httponly']))
        self.assertFalse(bool(cookie['secure']))

    def test_refresh_endpoint_issues_new_access_token(self):
        login_response = self._login()
        refresh_cookie = login_response.cookies['refresh_token'].value
        self.client.cookies['refresh_token'] = refresh_cookie

        refresh_response = self.client.post(reverse('auth-token-refresh'))

        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        body = refresh_response.json()
        self.assertIn('access', body.get('data', body))
        # cookie should be reset (same or rotated value) and remain http-only
        cookie = refresh_response.cookies['refresh_token']
        self.assertTrue(bool(cookie['httponly']))

    def test_refresh_without_cookie_is_unauthorized(self):
        response = self.client.post(reverse('auth-token-refresh'))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        body = response.json()
        self.assertTrue('detail' in body or 'error' in body)

    def test_refresh_with_invalid_cookie_clears_cookie(self):
        self.client.cookies['refresh_token'] = 'invalid'

        response = self.client.post(reverse('auth-token-refresh'))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        expired_cookie = response.cookies.get('refresh_token')
        self.assertIsNotNone(expired_cookie)
        self.assertEqual(expired_cookie.value, '')
