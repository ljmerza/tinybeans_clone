"""Test admin permission and CRUD operations for circle invitations."""
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from mysite.auth.token_utils import TOKEN_TTL_SECONDS
from mysite.circles.models import Circle, CircleMembership, CircleInvitation, CircleInvitationStatus
from mysite.emails.templates import CIRCLE_INVITATION_TEMPLATE
from mysite.users.models import User, UserRole


class InvitationAdminPermissionTests(TestCase):
    """Test admin-only invitation management operations."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email='admin@example.com',
            password='password123'
        )
        self.admin.email_verified = True
        self.admin.save()

        self.circle = Circle.objects.create(name='Test Circle', created_by=self.admin)
        CircleMembership.objects.create(user=self.admin, circle=self.circle, role=UserRole.CIRCLE_ADMIN)

        self.member = User.objects.create_user(
            email='member@example.com',
            password='password123'
        )
        CircleMembership.objects.create(user=self.member, circle=self.circle, role=UserRole.CIRCLE_MEMBER)

    @patch('mysite.circles.services.invitation_service.send_email_task.delay')
    @patch('mysite.circles.services.invitation_service.store_token')
    def test_admin_can_create_invitations_with_roles(self, mock_store_token, mock_delay):
        """Admins can create invitations and assign roles."""
        mock_store_token.return_value = 'fake-token'
        self.client.force_authenticate(user=self.admin)

        # Test admin role assignment
        response = self.client.post(
            reverse('circle-invitation-create', args=[self.circle.id]),
            {'email': 'newadmin@example.com', 'role': 'admin'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED, response.json())
        payload = response.json()['data']['invitation']
        self.assertFalse(payload['existing_user'])
        self.assertIsNone(payload['invited_user'])
        invitation = CircleInvitation.objects.get(email='newadmin@example.com')
        self.assertEqual(invitation.role, UserRole.CIRCLE_ADMIN)

        # Test member role assignment
        response = self.client.post(
            reverse('circle-invitation-create', args=[self.circle.id]),
            {'email': 'newmember@example.com', 'role': 'member'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED, response.json())
        payload = response.json()['data']['invitation']
        self.assertFalse(payload['existing_user'])
        self.assertIsNone(payload['invited_user'])
        invitation = CircleInvitation.objects.get(email='newmember@example.com')
        self.assertEqual(invitation.role, UserRole.CIRCLE_MEMBER)

        # Test default role
        response = self.client.post(
            reverse('circle-invitation-create', args=[self.circle.id]),
            {'email': 'default@example.com'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED, response.json())
        payload = response.json()['data']['invitation']
        self.assertFalse(payload['existing_user'])
        self.assertIsNone(payload['invited_user'])
        invitation = CircleInvitation.objects.get(email='default@example.com')
        self.assertEqual(invitation.role, UserRole.CIRCLE_MEMBER)

    @patch('mysite.circles.services.invitation_service.send_email_task.delay')
    @patch('mysite.circles.services.invitation_service.store_token')
    def test_admin_can_invite_existing_users(self, mock_store_token, mock_delay):
        """Admins can invite existing users by email without auto-joining."""
        mock_store_token.return_value = 'fake-token'
        self.client.force_authenticate(user=self.admin)

        existing_user = User.objects.create_user(
            email='target@example.com',
            password='password123'
        )

        response = self.client.post(
            reverse('circle-invitation-create', args=[self.circle.id]),
            {'email': 'target@example.com'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED, response.json())
        payload = response.json()['data']['invitation']
        self.assertTrue(payload['existing_user'])
        self.assertEqual(payload['invited_user']['email'], 'target@example.com')

        invitation = CircleInvitation.objects.get(email='target@example.com')
        self.assertEqual(invitation.invited_user, existing_user)
        self.assertEqual(invitation.status, CircleInvitationStatus.PENDING)
        self.assertFalse(CircleMembership.objects.filter(circle=self.circle, user=existing_user).exists())

    def test_admin_can_list_invitations(self):
        """Admins should be able to list invitations for their circle."""
        CircleInvitation.objects.create(
            circle=self.circle,
            email='pending@example.com',
            invited_by=self.admin,
            role=UserRole.CIRCLE_MEMBER,
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.get(
            reverse('circle-invitation-create', args=[self.circle.id]),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        invitations = response.json()['data']['invitations']
        self.assertEqual(len(invitations), 1)
        self.assertEqual(invitations[0]['email'], 'pending@example.com')

    def test_member_cannot_list_invitations(self):
        """Members should not be able to view the full invitation roster."""
        self.client.force_authenticate(user=self.member)
        response = self.client.get(
            reverse('circle-invitation-create', args=[self.circle.id]),
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_cancel_invitation(self):
        """Admins can cancel (delete) pending invitations."""
        invitation = CircleInvitation.objects.create(
            circle=self.circle,
            email='pending@example.com',
            invited_by=self.admin,
            role=UserRole.CIRCLE_MEMBER,
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            reverse('circle-invitation-cancel', args=[self.circle.id, invitation.id]),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertFalse(
            CircleInvitation.objects.filter(id=invitation.id).exists(),
            "Invitation should be deleted after cancellation",
        )

    def test_member_cannot_cancel_invitation(self):
        """Non-admin members cannot cancel invitations."""
        invitation = CircleInvitation.objects.create(
            circle=self.circle,
            email='pending@example.com',
            invited_by=self.admin,
            role=UserRole.CIRCLE_MEMBER,
        )

        self.client.force_authenticate(user=self.member)
        response = self.client.post(
            reverse('circle-invitation-cancel', args=[self.circle.id, invitation.id]),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(
            CircleInvitation.objects.filter(id=invitation.id).exists(),
            "Invitation should remain when cancellation is forbidden",
        )

    @patch('mysite.circles.services.invitation_service.send_email_task.delay')
    @patch('mysite.circles.services.invitation_service.store_token')
    def test_admin_can_resend_invitation(self, mock_store_token, mock_delay):
        """Admins can resend pending invitations."""
        mock_store_token.return_value = 'fake-token'
        invitation = CircleInvitation.objects.create(
            circle=self.circle,
            email='pending@example.com',
            invited_by=self.admin,
            role=UserRole.CIRCLE_MEMBER,
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            reverse('circle-invitation-resend', args=[self.circle.id, invitation.id]),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED, response.json())
        invitation.refresh_from_db()
        self.assertIsNotNone(invitation.reminder_sent_at)
        mock_store_token.assert_called_once()
        call = mock_store_token.call_args
        self.assertEqual(call.args[0], 'circle-invite')
        payload = call.args[1]
        self.assertEqual(call.kwargs['ttl'], TOKEN_TTL_SECONDS)
        self.assertEqual(payload['invitation_id'], str(invitation.id))
        self.assertEqual(payload['circle_id'], self.circle.id)
        self.assertEqual(payload['email'], invitation.email)
        self.assertEqual(payload['role'], invitation.role)
        self.assertFalse(payload['existing_user'])
        self.assertIsNone(payload['invited_user_id'])
        self.assertIn('issued_at', payload)
        mock_delay.assert_called_once()
        kwargs = mock_delay.call_args.kwargs
        self.assertEqual(kwargs['to_email'], invitation.email)
        self.assertEqual(kwargs['template_id'], CIRCLE_INVITATION_TEMPLATE)

    def test_member_cannot_resend_invitation(self):
        """Non-admin members cannot resend invitations."""
        invitation = CircleInvitation.objects.create(
            circle=self.circle,
            email='pending@example.com',
            invited_by=self.admin,
            role=UserRole.CIRCLE_MEMBER,
        )

        self.client.force_authenticate(user=self.member)
        response = self.client.post(
            reverse('circle-invitation-resend', args=[self.circle.id, invitation.id]),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('mysite.circles.services.invitation_service.send_email_task.delay')
    def test_resend_requires_pending_status(self, mock_delay):
        """Resend is only allowed for pending invitations."""
        invitation = CircleInvitation.objects.create(
            circle=self.circle,
            email='processed@example.com',
            invited_by=self.admin,
            role=UserRole.CIRCLE_MEMBER,
            status=CircleInvitationStatus.ACCEPTED,
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            reverse('circle-invitation-resend', args=[self.circle.id, invitation.id]),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.json())
        mock_delay.assert_not_called()

    @patch('mysite.circles.services.invitation_service.send_email_task.delay')
    @patch('mysite.circles.services.invitation_service.store_token')
    def test_create_requires_email(self, mock_store_token, mock_delay):
        """API should enforce email validation."""
        mock_store_token.return_value = 'fake-token'
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            reverse('circle-invitation-create', args=[self.circle.id]),
            {},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        payload = response.json()
        self.assertEqual(payload['error'], 'validation_failed')
        fields = [message.get('context', {}).get('field') for message in payload.get('messages', [])]
        self.assertIn('email', fields)

    @override_settings(RATELIMIT_ENABLE=True, CIRCLE_INVITE_CIRCLE_LIMIT=1, CIRCLE_INVITE_CIRCLE_LIMIT_WINDOW_MINUTES=60)
    @patch('mysite.circles.services.invitation_service.send_email_task.delay')
    @patch('mysite.circles.services.invitation_service.store_token')
    def test_circle_rate_limit(self, mock_store_token, mock_delay):
        """Invites should respect per-circle rate limits."""
        mock_store_token.return_value = 'fake-token'
        self.client.force_authenticate(user=self.admin)

        first = self.client.post(
            reverse('circle-invitation-create', args=[self.circle.id]),
            {'email': 'first@example.com'},
            format='json'
        )
        self.assertEqual(first.status_code, status.HTTP_202_ACCEPTED, first.json())

        second = self.client.post(
            reverse('circle-invitation-create', args=[self.circle.id]),
            {'email': 'second@example.com'},
            format='json'
        )
        self.assertEqual(second.status_code, status.HTTP_429_TOO_MANY_REQUESTS, second.json())

    def test_member_cannot_create_invitations(self):
        """Non-admin cannot create invitations."""
        self.client.force_authenticate(user=self.member)
        response = self.client.post(
            reverse('circle-invitation-create', args=[self.circle.id]),
            {'email': 'test@example.com'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_role_rejected(self):
        """Admin cannot send invalid role."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            reverse('circle-invitation-create', args=[self.circle.id]),
            {'email': 'test@example.com', 'role': 'invalid'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        payload = response.json()
        fields = [
            message.get('context', {}).get('field')
            for message in payload.get('messages', [])
            if message.get('context')
        ]
        self.assertIn('role', fields)
