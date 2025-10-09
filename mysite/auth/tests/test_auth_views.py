from unittest.mock import patch
import unittest

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from users.models import User


class AuthViewSecurityTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    @patch('auth.views.send_email_task.delay')
    def test_signup_does_not_expose_verification_token(self, mock_delay):
        response = self.client.post(
            reverse('auth-signup'),
            {
                'username': 'secureuser',
                'email': 'secure@example.com',
                'password': 'StrongPass123',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        body = response.json()
        self.assertNotIn('verification_token', body)
        self.assertNotIn('verification_token', body.get('data', {}))
        self.assertIn('tokens', body['data'])
        mock_delay.assert_called_once()

    @patch('auth.views.send_email_task.delay')
    def test_verification_resend_does_not_expose_token(self, mock_delay):
        User.objects.create_user(
            username='existinguser',
            email='existing@example.com',
            password='pw123456',
        )

        response = self.client.post(
            reverse('auth-verify-resend'),
            {'identifier': 'existing@example.com'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        body = response.json()
        self.assertNotIn('token', body)
        mock_delay.assert_called_once()

    def test_login_rate_limit_blocks_after_threshold(self):
        # Skip when rate limiting disabled in test settings
        if not getattr(settings, 'RATELIMIT_ENABLE', True):
            self.skipTest('Rate limiting disabled in test settings')
        user = User.objects.create_user(
            username='ratelimit',
            email='ratelimit@example.com',
            password='SuperSecret123',
        )

        login_payload = {'username': user.username, 'password': 'SuperSecret123'}

        # First five attempts should succeed
        for _ in range(5):
            success_response = self.client.post(reverse('auth-login'), login_payload, format='json')
            self.assertEqual(success_response.status_code, status.HTTP_200_OK)

        blocked_response = self.client.post(reverse('auth-login'), login_payload, format='json')
        self.assertIn(blocked_response.status_code, {status.HTTP_403_FORBIDDEN, status.HTTP_429_TOO_MANY_REQUESTS})

    @patch('auth.views.send_email_task.delay')
    def test_password_reset_request_does_not_expose_token(self, mock_delay):
        User.objects.create_user(
            username='resetuser',
            email='reset@example.com',
            password='pw123456',
        )

        response = self.client.post(
            reverse('auth-password-reset-request'),
            {'identifier': 'reset@example.com'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        body = response.json()
        self.assertEqual(body, {'data': {}, 'messages': [{'i18n_key': 'notifications.auth.password_reset'}]})
        mock_delay.assert_called_once()
        _, kwargs = mock_delay.call_args
        context = kwargs['context']
        from django.conf import settings
        expected_base = (getattr(settings, 'ACCOUNT_FRONTEND_BASE_URL', 'http://localhost:3000') or 'http://localhost:3000').rstrip('/')
        self.assertIn('reset_link', context)
        self.assertIn('token', context)
        self.assertIn(context['token'], context['reset_link'])
        self.assertTrue(context['reset_link'].startswith(f'{expected_base}/password/reset/confirm?'))
        self.assertGreaterEqual(context.get('expires_in_minutes', 0), 1)
