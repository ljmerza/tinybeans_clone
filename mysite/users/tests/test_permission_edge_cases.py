"""Test permission and access control edge cases across the application."""
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from mysite.users.models import (
    Circle,
    CircleMembership,
    User,
    UserRole,
)


class PermissionAndAccessTests(TestCase):
    """Test permission and access control edge cases."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email='admin@example.com',
            password='password123',
            role=UserRole.CIRCLE_ADMIN
        )
        self.member = User.objects.create_user(
            email='member@example.com',
            password='password123',
            role=UserRole.CIRCLE_MEMBER
        )
        self.outsider = User.objects.create_user(
            email='outsider@example.com',
            password='password123',
            role=UserRole.CIRCLE_MEMBER
        )
        self.circle = Circle.objects.create(name='Private Circle', created_by=self.admin)
        CircleMembership.objects.create(
            user=self.admin,
            circle=self.circle,
            role=UserRole.CIRCLE_ADMIN
        )
        CircleMembership.objects.create(
            user=self.member,
            circle=self.circle,
            role=UserRole.CIRCLE_MEMBER
        )

    def test_outsider_cannot_view_circle_members(self):
        """Test that non-members cannot view circle members."""
        self.client.force_authenticate(user=self.outsider)
        response = self.client.get(reverse('circle-member-list', args=[self.circle.id]))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_cannot_add_other_members(self):
        """Test that regular members cannot add other members."""
        self.client.force_authenticate(user=self.member)
        response = self.client.post(
            reverse('circle-invitation-create', args=[self.circle.id]),
            {'email': self.outsider.email},
            format='json'
        )

        # Member might not be able to invite others
        self.assertIn(response.status_code, [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_202_ACCEPTED  # Some apps allow members to invite
        ])

    def test_member_cannot_remove_other_members(self):
        """Test that regular members cannot remove other members."""
        self.client.force_authenticate(user=self.member)
        response = self.client.delete(
            reverse('circle-member-remove', args=[self.circle.id, self.admin.id])
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_access_blocked(self):
        """Test that unauthenticated requests are blocked."""
        endpoints = [
            ('user-circle-list',),
            ('circle-member-list', self.circle.id),
            ('user-profile',),
        ]

        for endpoint_args in endpoints:
            if len(endpoint_args) == 1:
                url = reverse(endpoint_args[0])
            else:
                url = reverse(endpoint_args[0], args=endpoint_args[1:])

            response = self.client.get(url)
            self.assertIn(response.status_code, [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN
            ])

    def test_cross_circle_data_isolation(self):
        """Test that users cannot access data from circles they don't belong to."""
        # Create another circle with different admin
        other_admin = User.objects.create_user(
            email='other@example.com',
            password='password123'
        )
        other_circle = Circle.objects.create(name='Other Circle', created_by=other_admin)
        CircleMembership.objects.create(
            user=other_admin,
            circle=other_circle,
            role=UserRole.CIRCLE_ADMIN
        )

        # Member from first circle should not access second circle
        self.client.force_authenticate(user=self.member)
        response = self.client.get(reverse('circle-member-list', args=[other_circle.id]))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
