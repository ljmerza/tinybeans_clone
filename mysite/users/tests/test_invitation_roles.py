"""Test role-based invitation functionality."""
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from users.models import (
    Circle,
    CircleMembership,
    CircleInvitation,
    CircleInvitationStatus,
    User,
    UserRole,
)
from users.serializers.circles import CircleInvitationCreateSerializer
from auth.token_utils import store_token


class InvitationRoleTests(TestCase):
    """Test role assignment in circle invitations."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='password123'
        )
        self.admin.email_verified = True
        self.admin.save()
        
        self.circle = Circle.objects.create(name='Test Circle', created_by=self.admin)
        CircleMembership.objects.create(user=self.admin, circle=self.circle, role=UserRole.CIRCLE_ADMIN)
        
        self.member = User.objects.create_user(
            username='member',
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

    def test_serializer_username_lookup(self):
        """Serializer should resolve usernames to existing users."""
        existing = User.objects.create_user(
            username='lookup',
            email='lookup@example.com',
            password='password123'
        )
        serializer = CircleInvitationCreateSerializer(
            data={'username': 'lookup'},
            context={'circle': self.circle}
        )
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['email'], 'lookup@example.com')
        self.assertEqual(serializer.validated_data['invited_user'], existing)

    def test_serializer_requires_identifier(self):
        """Serializer requires exactly one identifier."""
        serializer = CircleInvitationCreateSerializer(
            data={},
            context={'circle': self.circle}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('identifier', serializer.errors)

        serializer = CircleInvitationCreateSerializer(
            data={'email': 'a@example.com', 'username': 'test'},
            context={'circle': self.circle}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('identifier', serializer.errors)

    @patch('users.views.circles.send_email_task.delay')
    @patch('users.views.circles.store_token')
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

    @patch('users.views.circles.send_email_task.delay')
    @patch('users.views.circles.store_token')
    def test_api_invite_existing_user_by_username(self, mock_store_token, mock_delay):
        """Admins can invite existing users by username without auto-joining."""
        mock_store_token.return_value = 'fake-token'
        self.client.force_authenticate(user=self.admin)

        existing_user = User.objects.create_user(
            username='targetuser',
            email='target@example.com',
            password='password123'
        )

        response = self.client.post(
            reverse('circle-invitation-create', args=[self.circle.id]),
            {'username': 'targetuser'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED, response.json())
        payload = response.json()['data']['invitation']
        self.assertTrue(payload['existing_user'])
        self.assertEqual(payload['invited_user']['username'], 'targetuser')

        invitation = CircleInvitation.objects.get(email='target@example.com')
        self.assertEqual(invitation.invited_user, existing_user)
        self.assertEqual(invitation.status, CircleInvitationStatus.PENDING)
        self.assertFalse(CircleMembership.objects.filter(circle=self.circle, user=existing_user).exists())

    @patch('users.views.circles.send_email_task.delay')
    @patch('users.views.circles.store_token')
    def test_api_requires_identifier(self, mock_store_token, mock_delay):
        """API should enforce identifier validation."""
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
        keys = [message['i18n_key'] for message in payload.get('messages', [])]
        self.assertIn('errors.invitation_identifier_required', keys)
        fields = [message.get('context', {}).get('field') for message in payload.get('messages', [])]
        self.assertIn('identifier', fields)

        response = self.client.post(
            reverse('circle-invitation-create', args=[self.circle.id]),
            {'email': 'duplicate@example.com', 'username': 'dup'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        payload = response.json()
        self.assertEqual(payload['error'], 'validation_failed')
        keys = [message['i18n_key'] for message in payload.get('messages', [])]
        self.assertIn('errors.invitation_identifier_conflict', keys)

    @override_settings(RATELIMIT_ENABLE=True, CIRCLE_INVITE_CIRCLE_LIMIT=1, CIRCLE_INVITE_CIRCLE_LIMIT_WINDOW_MINUTES=60)
    @patch('users.views.circles.send_email_task.delay')
    @patch('users.views.circles.store_token')
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

    @patch('users.views.circles.send_email_task.delay')
    def test_new_user_onboarding_flow(self, mock_delay):
        """End-to-end invite flow for a new user completing onboarding."""
        invitation = CircleInvitation.objects.create(
            circle=self.circle,
            email='invitee@example.com',
            invited_by=self.admin,
            role=UserRole.CIRCLE_MEMBER,
        )

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
            username='invitee',
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

    @patch('users.views.circles.send_email_task.delay')
    def test_finalize_rejects_mismatched_user(self, mock_delay):
        """Finalize should fail when authenticated user email does not match invitation."""
        invitation = CircleInvitation.objects.create(
            circle=self.circle,
            email='invitee@example.com',
            invited_by=self.admin,
            role=UserRole.CIRCLE_MEMBER,
        )

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
            username='other',
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
