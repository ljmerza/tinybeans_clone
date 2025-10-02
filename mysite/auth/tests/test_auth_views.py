from unittest.mock import patch

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
        self.assertIn('tokens', body)
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
        self.assertEqual(body, {'message': 'Password reset sent'})
        mock_delay.assert_called_once()
