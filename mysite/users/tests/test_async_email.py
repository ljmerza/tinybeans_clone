from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from users.models import ChildProfile, Circle, CircleMembership, User, UserRole
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
        response = self.client.post(
            reverse('child-upgrade-request', args=[child.id]),
            {'email': 'parent@example.com'},
            format='json',
        )

        self.assertEqual(response.status_code, 202)
        mock_delay.assert_called_once()
        _, kwargs = mock_delay.call_args
        self.assertEqual(kwargs['template_id'], CHILD_UPGRADE_TEMPLATE)
        self.assertEqual(kwargs['to_email'], 'parent@example.com')
        self.assertIn('token', kwargs['context'])
