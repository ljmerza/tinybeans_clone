"""Test role-based invitation functionality."""
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from users.models import Circle, CircleMembership, CircleInvitation, User, UserRole


class InvitationRoleTests(TestCase):
    """Test that admins can specify roles when creating invitations."""
    
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username='adminuser',
            email='admin@example.com',
            password='password123',
            role=UserRole.CIRCLE_ADMIN,
        )
        self.admin.email_verified = True
        self.admin.save()
        
        self.circle = Circle.objects.create(name='Test Circle', created_by=self.admin)
        CircleMembership.objects.create(user=self.admin, circle=self.circle, role=UserRole.CIRCLE_ADMIN)

    @patch('users.views.circles.send_email_task.delay')
    @patch('users.views.circles.store_token')
    def test_admin_can_invite_with_admin_role(self, mock_store_token, mock_delay):
        """Test that admin can create invitation with admin role."""
        mock_store_token.return_value = 'fake-token'
        
        self.client.force_authenticate(user=self.admin)
        
        response = self.client.post(
            reverse('circle-invitation-create', args=[self.circle.id]),
            {
                'email': 'newadmin@example.com',
                'role': 'admin'
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        
        # Check invitation was created with admin role
        invitation = CircleInvitation.objects.get(email='newadmin@example.com')
        self.assertEqual(invitation.role, UserRole.CIRCLE_ADMIN)
        self.assertEqual(invitation.circle, self.circle)
        self.assertEqual(invitation.invited_by, self.admin)
        
        # Verify email was queued
        mock_delay.assert_called_once()

    @patch('users.views.circles.send_email_task.delay')
    @patch('users.views.circles.store_token')
    def test_admin_can_invite_with_member_role(self, mock_store_token, mock_delay):
        """Test that admin can create invitation with member role."""
        mock_store_token.return_value = 'fake-token'
        
        self.client.force_authenticate(user=self.admin)
        
        response = self.client.post(
            reverse('circle-invitation-create', args=[self.circle.id]),
            {
                'email': 'newmember@example.com',
                'role': 'member'
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        
        # Check invitation was created with member role
        invitation = CircleInvitation.objects.get(email='newmember@example.com')
        self.assertEqual(invitation.role, UserRole.CIRCLE_MEMBER)

    @patch('users.views.circles.send_email_task.delay')
    @patch('users.views.circles.store_token')
    def test_invitation_defaults_to_member_role(self, mock_store_token, mock_delay):
        """Test that invitations default to member role when not specified."""
        mock_store_token.return_value = 'fake-token'
        
        self.client.force_authenticate(user=self.admin)
        
        response = self.client.post(
            reverse('circle-invitation-create', args=[self.circle.id]),
            {
                'email': 'defaultrole@example.com',
                # No role specified
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        
        # Check invitation defaults to member role
        invitation = CircleInvitation.objects.get(email='defaultrole@example.com')
        self.assertEqual(invitation.role, UserRole.CIRCLE_MEMBER)

    def test_invalid_role_rejected(self):
        """Test that invalid roles are rejected."""
        self.client.force_authenticate(user=self.admin)
        
        response = self.client.post(
            reverse('circle-invitation-create', args=[self.circle.id]),
            {
                'email': 'badlrole@example.com',
                'role': 'invalid_role'
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('role', response.data)

    def test_non_admin_cannot_create_invitations(self):
        """Test that non-admin users cannot create invitations."""
        member = User.objects.create_user(
            username='memberuser',
            email='member@example.com',
            password='password123',
            role=UserRole.CIRCLE_MEMBER,
        )
        CircleMembership.objects.create(user=member, circle=self.circle, role=UserRole.CIRCLE_MEMBER)
        
        self.client.force_authenticate(user=member)
        
        response = self.client.post(
            reverse('circle-invitation-create', args=[self.circle.id]),
            {
                'email': 'unauthorized@example.com',
                'role': 'member'
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    @patch('users.views.circles.send_email_task.delay')
    @patch('users.views.circles.store_token')
    def test_comprehensive_role_assignment_demonstration(self, mock_store_token, mock_delay):
        """Comprehensive test demonstrating role assignment feature."""
        mock_store_token.return_value = 'fake-token'
        self.client.force_authenticate(user=self.admin)
        
        # Test 1: Admin invites another admin
        response = self.client.post(
            reverse('circle-invitation-create', args=[self.circle.id]),
            {'email': 'admin2@example.com', 'role': 'admin'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        admin_invitation = CircleInvitation.objects.get(email='admin2@example.com')
        self.assertEqual(admin_invitation.role, UserRole.CIRCLE_ADMIN)
        
        # Test 2: Admin invites a member (explicit)
        response = self.client.post(
            reverse('circle-invitation-create', args=[self.circle.id]),
            {'email': 'member1@example.com', 'role': 'member'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        member_invitation = CircleInvitation.objects.get(email='member1@example.com')
        self.assertEqual(member_invitation.role, UserRole.CIRCLE_MEMBER)
        
        # Test 3: Admin invites with default role (no role specified)
        response = self.client.post(
            reverse('circle-invitation-create', args=[self.circle.id]),
            {'email': 'member2@example.com'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        default_invitation = CircleInvitation.objects.get(email='member2@example.com')
        self.assertEqual(default_invitation.role, UserRole.CIRCLE_MEMBER)
        
        # Verify all invitations were created correctly
        invitations = CircleInvitation.objects.filter(circle=self.circle)
        self.assertEqual(invitations.count(), 3)
        
        # Verify roles are correctly assigned
        roles = {inv.email: inv.role for inv in invitations}
        self.assertEqual(roles['admin2@example.com'], UserRole.CIRCLE_ADMIN)
        self.assertEqual(roles['member1@example.com'], UserRole.CIRCLE_MEMBER)
        self.assertEqual(roles['member2@example.com'], UserRole.CIRCLE_MEMBER)
        
        # Verify emails were queued for all invitations
        self.assertEqual(mock_delay.call_count, 3)