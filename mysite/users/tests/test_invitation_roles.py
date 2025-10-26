"""Test role-based invitation functionality."""
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from mysite.circles.models import (
    Circle,
    CircleMembership,
    CircleInvitation,
    CircleInvitationStatus,
)
from mysite.users.models import User, UserRole
from mysite.circles.serializers import CircleInvitationCreateSerializer
from mysite.auth.token_utils import store_token, TOKEN_TTL_SECONDS
from mysite.emails.templates import CIRCLE_INVITATION_TEMPLATE
from mysite.circles.tasks import send_circle_invitation_reminders


class InvitationRoleTests(TestCase):
    """Test role assignment in circle invitations."""
    
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

    def test_serializer_role_validation(self):
        """Test role validation at serializer level."""
        # Valid admin role
        serializer = CircleInvitationCreateSerializer(
            data={'email': 'test@example.com', 'role': 'admin'},
            context={'circle': self.circle}
        )
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['role'], UserRole.CIRCLE_ADMIN)
        
        # Valid member role
        serializer = CircleInvitationCreateSerializer(
            data={'email': 'test2@example.com', 'role': 'member'},
            context={'circle': self.circle}
        )
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['role'], UserRole.CIRCLE_MEMBER)
        
        # Default role when not specified
        serializer = CircleInvitationCreateSerializer(
            data={'email': 'test3@example.com'},
            context={'circle': self.circle}
        )
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['role'], UserRole.CIRCLE_MEMBER)
        
        # Invalid role
        serializer = CircleInvitationCreateSerializer(
            data={'email': 'test4@example.com', 'role': 'invalid'},
            context={'circle': self.circle}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('role', serializer.errors)

    def test_serializer_existing_user_lookup(self):
        """Serializer should resolve existing users by email."""
        existing = User.objects.create_user(
            email='lookup@example.com',
            password='password123'
        )
        serializer = CircleInvitationCreateSerializer(
            data={'email': 'lookup@example.com'},
            context={'circle': self.circle}
        )
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['email'], 'lookup@example.com')
        self.assertEqual(serializer.validated_data['invited_user'], existing)

    def test_serializer_requires_email(self):
        """Serializer requires an email address."""
        serializer = CircleInvitationCreateSerializer(
            data={},
            context={'circle': self.circle}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)

    @patch('mysite.circles.services.invitation_service.send_email_task.delay')
    @patch('mysite.circles.services.invitation_service.store_token')
    def test_api_role_assignment(self, mock_store_token, mock_delay):
        """Test role assignment via API."""
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
    def test_api_invite_existing_user_by_email(self, mock_store_token, mock_delay):
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

    def test_circle_admin_can_list_invitations(self):
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

    def test_non_admin_cannot_list_invitations(self):
        """Members should not be able to view the full invitation roster."""
        self.client.force_authenticate(user=self.member)
        response = self.client.get(
            reverse('circle-invitation-create', args=[self.circle.id]),
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_circle_admin_can_cancel_invitation(self):
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
    def test_circle_admin_can_resend_invitation(self, mock_store_token, mock_delay):
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
    def test_resend_requires_pending_invitation(self, mock_delay):
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
    def test_api_requires_email(self, mock_store_token, mock_delay):
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

    def test_permission_and_validation_errors(self):
        """Test permission and validation error cases."""
        # Non-admin cannot create invitations
        self.client.force_authenticate(user=self.member)
        response = self.client.post(
            reverse('circle-invitation-create', args=[self.circle.id]),
            {'email': 'test@example.com'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Admin cannot send invalid role
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

    @patch('mysite.circles.services.invitation_service.send_email_task.delay')
    def test_new_user_onboarding_flow(self, mock_delay):
        """End-to-end invite flow for a new user completing onboarding."""
        invitation = CircleInvitation.objects.create(
            circle=self.circle,
            email='invitee@example.com',
            invited_by=self.admin,
            role=UserRole.CIRCLE_MEMBER,
        )
        CircleInvitation.objects.filter(id=invitation.id).update(created_at=timezone.now() - timedelta(minutes=120))
        invitation.refresh_from_db()

        invite_token = store_token(
            'circle-invite',
            {
                'invitation_id': str(invitation.id),
                'circle_id': self.circle.id,
                'email': invitation.email,
                'role': invitation.role,
            },
        )

        response = self.client.post(
            reverse('circle-invitation-accept'),
            {'token': invite_token},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        onboarding_token = response.json()['data']['onboarding_token']

        invitee = User.objects.create_user(
            email='invitee@example.com',
            password='InviteePass123',
        )
        self.client.force_authenticate(user=invitee)

        finalize = self.client.post(
            reverse('circle-invitation-finalize'),
            {'onboarding_token': onboarding_token},
            format='json'
        )
        self.assertEqual(finalize.status_code, status.HTTP_201_CREATED, finalize.json())

        invitation.refresh_from_db()
        self.assertEqual(invitation.status, CircleInvitationStatus.ACCEPTED)
        self.assertEqual(invitation.invited_user, invitee)
        membership_exists = CircleMembership.objects.filter(circle=self.circle, user=invitee).exists()
        self.assertTrue(membership_exists)

    @patch('mysite.circles.services.invitation_service.send_email_task.delay')
    def test_finalize_rejects_mismatched_user(self, mock_delay):
        """Finalize should fail when authenticated user email does not match invitation."""
        invitation = CircleInvitation.objects.create(
            circle=self.circle,
            email='invitee@example.com',
            invited_by=self.admin,
            role=UserRole.CIRCLE_MEMBER,
        )
        CircleInvitation.objects.filter(id=invitation.id).update(created_at=timezone.now() - timedelta(minutes=120))
        invitation.refresh_from_db()

        invite_token = store_token(
            'circle-invite',
            {
                'invitation_id': str(invitation.id),
                'circle_id': self.circle.id,
                'email': invitation.email,
                'role': invitation.role,
            },
        )

        response = self.client.post(
            reverse('circle-invitation-accept'),
            {'token': invite_token},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        onboarding_token = response.json()['data']['onboarding_token']

        other_user = User.objects.create_user(
            email='other@example.com',
            password='OtherPass123',
        )
        self.client.force_authenticate(user=other_user)

        finalize = self.client.post(
            reverse('circle-invitation-finalize'),
            {'onboarding_token': onboarding_token},
            format='json'
        )
        self.assertEqual(finalize.status_code, status.HTTP_403_FORBIDDEN)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, CircleInvitationStatus.PENDING)

    @override_settings(
        CIRCLE_INVITE_REMINDER_DELAY_MINUTES=60,
        CIRCLE_INVITE_REMINDER_COOLDOWN_MINUTES=1440,
        CIRCLE_INVITE_REMINDER_BATCH_SIZE=50,
    )
    @patch('mysite.circles.tasks.send_email_task.delay')
    def test_reminder_task_sends_email(self, mock_delay):
        invitation = CircleInvitation.objects.create(
            circle=self.circle,
            email='reminder@example.com',
            invited_by=self.admin,
            role=UserRole.CIRCLE_MEMBER,
        )
        CircleInvitation.objects.filter(id=invitation.id).update(created_at=timezone.now() - timedelta(minutes=180))
        invitation.refresh_from_db()

        sent = send_circle_invitation_reminders()
        invitation.refresh_from_db()
        self.assertEqual(sent, 1)
        mock_delay.assert_called_once()
        self.assertIsNotNone(invitation.reminder_sent_at)

        mock_delay.reset_mock()
        sent_again = send_circle_invitation_reminders()
        self.assertEqual(sent_again, 0)
        mock_delay.assert_not_called()
