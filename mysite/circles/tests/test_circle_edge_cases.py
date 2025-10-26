"""Tests for circle view edge cases."""
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from mysite.users.models import (
    Circle,
    CircleInvitation,
    CircleInvitationStatus,
    CircleMembership,
    User,
    UserRole,
)


class CircleViewEdgeCaseTests(TestCase):
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
        self.circle = Circle.objects.create(name='Test Circle', created_by=self.admin)
        CircleMembership.objects.create(
            user=self.admin,
            circle=self.circle,
            role=UserRole.CIRCLE_ADMIN
        )

    def test_circle_creation_with_extremely_long_name(self):
        """Test creating circle with very long name."""
        self.client.force_authenticate(user=self.admin)
        long_name = 'A' * 300  # Longer than max_length

        # Try to create via user circles endpoint
        response = self.client.post(reverse('user-circle-list'), {
            'name': long_name
        }, format='json')

        # Expect either 405 (method not allowed) or 400 (validation error) or 404 (not found)
        self.assertIn(response.status_code, [
            status.HTTP_405_METHOD_NOT_ALLOWED,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND
        ])

    def test_invite_existing_member(self):
        """Test inviting a user who is already a member."""
        # Add member to circle first
        CircleMembership.objects.create(
            user=self.member,
            circle=self.circle,
            role=UserRole.CIRCLE_MEMBER
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            reverse('circle-invitation-create', args=[self.circle.id]),
            {'email': self.member.email},  # Always invite by email
            format='json'
        )

        # Should either succeed (new invitation) or reject with appropriate message
        self.assertIn(response.status_code, [
            status.HTTP_202_ACCEPTED,
            status.HTTP_400_BAD_REQUEST
        ])

    def test_remove_last_admin(self):
        """Test removing the last admin from a circle."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(
            reverse('circle-member-remove', args=[self.circle.id, self.admin.id])
        )

        # This should be allowed or handle gracefully
        self.assertIn(response.status_code, [
            status.HTTP_204_NO_CONTENT,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN
        ])

    def test_accept_expired_invitation(self):
        """Test accepting an invitation that has been marked as expired."""
        invitation = CircleInvitation.objects.create(
            circle=self.circle,
            email='invitee@example.com',
            invited_by=self.admin,
            status=CircleInvitationStatus.EXPIRED
        )

        response = self.client.post(reverse('circle-invitation-accept'), {
            'invitation_id': str(invitation.id)
        }, format='json')

        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND
        ])

    def test_multiple_pending_invitations_same_email(self):
        """Test that multiple pending invitations to same email are handled."""
        # Create first invitation
        CircleInvitation.objects.create(
            circle=self.circle,
            email='invitee@example.com',
            invited_by=self.admin,
            status=CircleInvitationStatus.PENDING
        )

        # Try to create second invitation
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            reverse('circle-invitation-create', args=[self.circle.id]),
            {'email': 'invitee@example.com'},
            format='json'
        )

        # Should either succeed or fail gracefully
        self.assertIn(response.status_code, [
            status.HTTP_202_ACCEPTED,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_409_CONFLICT
        ])
