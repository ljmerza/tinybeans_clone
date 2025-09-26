from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from users.models import (
    ChildProfile,
    Circle,
    CircleMembership,
    User,
    UserRole,
    ChildUpgradeEventType,
)
from users.tasks import (
    CHILD_UPGRADE_TEMPLATE,
    CIRCLE_INVITATION_TEMPLATE,
    EMAIL_VERIFICATION_TEMPLATE,
    PASSWORD_RESET_TEMPLATE,
)


class AsyncEmailTaskTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch('users.views.send_email_task.delay')
    def test_signup_enqueues_verification_email(self, mock_delay):
        payload = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'supersecret',
        }

        response = self.client.post(reverse('user-signup'), payload, format='json')

        self.assertEqual(response.status_code, 201)
        mock_delay.assert_called_once()
        _, kwargs = mock_delay.call_args
        self.assertEqual(kwargs['template_id'], EMAIL_VERIFICATION_TEMPLATE)
        self.assertEqual(kwargs['to_email'], payload['email'])
        self.assertIn('token', kwargs['context'])
        body = response.json()
        self.assertEqual(set(body['tokens'].keys()), {'access'})
        self.assertIsNotNone(body['circle'])
        self.assertFalse(body['pending_circle_setup'])
        self.assertIsNotNone(Circle.objects.filter(created_by__username='newuser').first())

    @patch('users.views.send_email_task.delay')
    def test_signup_can_defer_circle_creation(self, mock_delay):
        payload = {
            'username': 'latercircle',
            'email': 'later@example.com',
            'password': 'supersecret',
            'create_circle': False,
        }

        response = self.client.post(reverse('user-signup'), payload, format='json')

        self.assertEqual(response.status_code, 201)
        mock_delay.assert_called_once()
        _, kwargs = mock_delay.call_args
        self.assertEqual(kwargs['template_id'], EMAIL_VERIFICATION_TEMPLATE)
        self.assertEqual(kwargs['to_email'], payload['email'])
        body = response.json()
        self.assertEqual(set(body['tokens'].keys()), {'access'})
        self.assertIsNone(body['circle'])
        self.assertTrue(body['pending_circle_setup'])

        user = User.objects.get(username='latercircle')
        self.assertEqual(user.role, UserRole.CIRCLE_MEMBER)
        self.assertFalse(Circle.objects.filter(created_by=user).exists())
        self.assertFalse(CircleMembership.objects.filter(user=user).exists())

    @patch('users.views.send_email_task.delay')
    def test_password_reset_request_enqueues_email(self, mock_delay):
        user = User.objects.create_user(
            username='existing',
            email='existing@example.com',
            password='password123',
        )

        response = self.client.post(
            reverse('user-password-reset-request'),
            {'identifier': user.email},
            format='json',
        )

        self.assertEqual(response.status_code, 202)
        mock_delay.assert_called_once()
        _, kwargs = mock_delay.call_args
        self.assertEqual(kwargs['template_id'], PASSWORD_RESET_TEMPLATE)
        self.assertEqual(kwargs['to_email'], user.email)
        self.assertIn('token', kwargs['context'])

    @patch('users.views.send_email_task.delay')
    def test_circle_invitation_enqueues_email(self, mock_delay):
        admin = User.objects.create_user(
            username='circleadmin',
            email='circleadmin@example.com',
            password='password123',
            role=UserRole.CIRCLE_ADMIN,
        )
        circle = Circle.objects.create(name='Family', created_by=admin)
        CircleMembership.objects.create(user=admin, circle=circle, role=UserRole.CIRCLE_ADMIN)

        self.client.force_authenticate(user=admin)
        response = self.client.post(
            reverse('circle-invitation-create', args=[circle.id]),
            {'email': 'invitee@example.com'},
            format='json',
        )

        self.assertEqual(response.status_code, 202)
        mock_delay.assert_called_once()
        _, kwargs = mock_delay.call_args
        self.assertEqual(kwargs['template_id'], CIRCLE_INVITATION_TEMPLATE)
        self.assertEqual(kwargs['to_email'], 'invitee@example.com')
        self.assertIn('token', kwargs['context'])

    @patch('users.views.send_email_task.delay')
    def test_child_upgrade_request_enqueues_email(self, mock_delay):
        admin = User.objects.create_user(
            username='guardian',
            email='guardian@example.com',
            password='password123',
            role=UserRole.CIRCLE_ADMIN,
        )
        circle = Circle.objects.create(name='Family 2', created_by=admin)
        CircleMembership.objects.create(user=admin, circle=circle, role=UserRole.CIRCLE_ADMIN)
        child = ChildProfile.objects.create(circle=circle, display_name='Kiddo')

        self.client.force_authenticate(user=admin)
        payload = {
            'email': 'parent@example.com',
            'guardian_name': 'Primary Guardian',
            'guardian_relationship': 'Mother',
            'consent_method': 'digital_signature',
            'agreement_reference': 'AGREEMENT-123',
            'consent_metadata': {'ip': '127.0.0.1'},
        }

        response = self.client.post(
            reverse('child-upgrade-request', args=[child.id]),
            payload,
            format='json',
        )

        self.assertEqual(response.status_code, 202)
        mock_delay.assert_called_once()
        _, kwargs = mock_delay.call_args
        self.assertEqual(kwargs['template_id'], CHILD_UPGRADE_TEMPLATE)
        self.assertEqual(kwargs['to_email'], payload['email'])
        self.assertIn('token', kwargs['context'])
        child.refresh_from_db()
        self.assertEqual(child.pending_invite_email, payload['email'])
        self.assertIsNotNone(child.upgrade_token)
        self.assertTrue(child.guardian_consents.exists())
        consent = child.guardian_consents.first()
        self.assertEqual(consent.guardian_name, payload['guardian_name'])
        self.assertEqual(consent.guardian_relationship, payload['guardian_relationship'])
        self.assertTrue(
            child.upgrade_audit_logs.filter(event_type=ChildUpgradeEventType.REQUEST_INITIATED).exists()
        )
