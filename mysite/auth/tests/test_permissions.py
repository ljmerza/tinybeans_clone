from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from mysite.users.models import User


class EmailVerificationPermissionTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='perm@example.com',
            password='StrongPass123',
            first_name='Perm',
            last_name='User',
        )
        self.client.force_authenticate(self.user)

    @override_settings(EMAIL_VERIFICATION_ENFORCED=True)
    def test_unverified_user_blocked(self):
        response = self.client.get(reverse('circle-onboarding-status'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        body = response.json()
        self.assertEqual(body['error'], 'email_verification_required')
        self.assertEqual(body['messages'][0]['i18n_key'], 'errors.email_verification_required')
        self.assertEqual(body['redirect_to'], '/verify-email-required')

    @override_settings(EMAIL_VERIFICATION_ENFORCED=True)
    def test_verified_user_allowed(self):
        self.user.email_verified = True
        self.user.save(update_fields=['email_verified'])
        response = self.client.get(reverse('circle-onboarding-status'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
