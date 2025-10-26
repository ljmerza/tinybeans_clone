"""Tests for child profile edge cases."""
from datetime import timedelta
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from mysite.users.models import (
    ChildProfile,
    ChildProfileUpgradeStatus,
    Circle,
    CircleMembership,
    User,
    UserRole,
)


class ChildProfileViewEdgeCaseTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email='parent@example.com',
            password='password123',
            role=UserRole.CIRCLE_ADMIN
        )
        self.circle = Circle.objects.create(name='Family', created_by=self.admin)
        CircleMembership.objects.create(
            user=self.admin,
            circle=self.circle,
            role=UserRole.CIRCLE_ADMIN
        )
        self.child = ChildProfile.objects.create(
            circle=self.circle,
            display_name='Test Child'
        )

    def test_upgrade_request_for_already_linked_child(self):
        """Test upgrade request for child that's already linked to a user."""
        linked_user = User.objects.create_user(
            email='child@example.com',
            password='password123'
        )
        self.child.linked_user = linked_user
        self.child.upgrade_status = ChildProfileUpgradeStatus.LINKED
        self.child.save()

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            reverse('child-upgrade-request', args=[self.child.id]),
            {
                'email': 'parent@example.com',
                'guardian_name': 'Guardian',
                'guardian_relationship': 'Parent',
                'consent_method': 'digital_signature'
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upgrade_request_with_invalid_email(self):
        """Test upgrade request with invalid email format."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            reverse('child-upgrade-request', args=[self.child.id]),
            {
                'email': 'invalid-email',
                'guardian_name': 'Guardian',
                'guardian_relationship': 'Parent',
                'consent_method': 'digital_signature'
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        fields = [
            message.get('context', {}).get('field')
            for message in data.get('messages', [])
            if message.get('context')
        ]
        self.assertIn('email', fields)

    def test_upgrade_confirm_with_expired_token(self):
        """Test upgrade confirmation with expired token."""
        # Set up child with expired token
        self.child.upgrade_token = 'expired_token'
        self.child.upgrade_token_expires_at = timezone.now() - timedelta(hours=1)
        self.child.pending_invite_email = 'parent@example.com'
        self.child.save()

        response = self.client.post(reverse('child-upgrade-confirm'), {
            'child_id': str(self.child.id),
            'token': 'expired_token',
            'first_name': 'New',
            'last_name': 'Guardian',
            'password': 'password123',
            'password_confirm': 'password123',
        }, format='json')

        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND
        ])

    def test_upgrade_confirm_password_mismatch(self):
        """Test upgrade confirmation enforces matching passwords."""
        # Set up child with valid token
        self.child.upgrade_token = 'valid_token'
        self.child.upgrade_token_expires_at = timezone.now() + timedelta(hours=1)
        self.child.pending_invite_email = 'parent@example.com'
        self.child.save()

        response = self.client.post(reverse('child-upgrade-confirm'), {
            'child_id': str(self.child.id),
            'token': 'valid_token',
            'first_name': 'Mismatch',
            'last_name': 'Guardian',
            'password': 'password123',
            'password_confirm': 'different',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
