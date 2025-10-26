"""Test end-to-end invitation workflows and lifecycle."""
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from mysite.auth.token_utils import store_token
from mysite.circles.models import Circle, CircleMembership, CircleInvitation, CircleInvitationStatus
from mysite.circles.tasks import send_circle_invitation_reminders
from mysite.users.models import User, UserRole


class InvitationWorkflowTests(TestCase):
    """Test complete invitation workflows from creation to acceptance."""

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

        # Verify email was auto-verified during invite acceptance
        invitee.refresh_from_db()
        self.assertTrue(invitee.email_verified, "Email should be auto-verified when accepting invitation")

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
        """Test that the reminder task sends emails for old pending invitations."""
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
