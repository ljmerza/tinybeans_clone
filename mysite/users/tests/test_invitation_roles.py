"""Test role-based invitation functionality."""
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from users.models import Circle, CircleMembership, CircleInvitation, User, UserRole
from users.serializers.circles import CircleInvitationCreateSerializer


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
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        invitation = CircleInvitation.objects.get(email='newadmin@example.com')
        self.assertEqual(invitation.role, UserRole.CIRCLE_ADMIN)
        
        # Test member role assignment
        response = self.client.post(
            reverse('circle-invitation-create', args=[self.circle.id]),
            {'email': 'newmember@example.com', 'role': 'member'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        invitation = CircleInvitation.objects.get(email='newmember@example.com')
        self.assertEqual(invitation.role, UserRole.CIRCLE_MEMBER)
        
        # Test default role
        response = self.client.post(
            reverse('circle-invitation-create', args=[self.circle.id]),
            {'email': 'default@example.com'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        invitation = CircleInvitation.objects.get(email='default@example.com')
        self.assertEqual(invitation.role, UserRole.CIRCLE_MEMBER)

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
