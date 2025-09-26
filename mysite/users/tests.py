from unittest.mock import patch

from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import ChildProfile, Circle, CircleInvitation, CircleMembership, User, UserRole
from .tasks import (
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


class UserProfileViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='profileuser',
            email='profile@example.com',
            password='password123',
        )

    def test_get_profile_returns_user_data(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('user-profile'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['id'], self.user.id)
        self.assertEqual(response.data['user']['email'], self.user.email)

    def test_patch_profile_updates_names(self):
        self.client.force_authenticate(user=self.user)
        payload = {'first_name': 'Profile', 'last_name': 'Updated'}
        response = self.client.patch(reverse('user-profile'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, payload['first_name'])
        self.assertEqual(self.user.last_name, payload['last_name'])


class CircleMembershipViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username='adminuser',
            email='admin@example.com',
            password='password123',
            role=UserRole.CIRCLE_ADMIN,
        )
        self.circle = Circle.objects.create(name='Admin Circle', created_by=self.admin)
        CircleMembership.objects.create(user=self.admin, circle=self.circle, role=UserRole.CIRCLE_ADMIN)

    def test_list_user_circles_returns_memberships(self):
        other_circle = Circle.objects.create(name='Second Circle', created_by=self.admin)
        CircleMembership.objects.create(user=self.admin, circle=other_circle, role=UserRole.CIRCLE_ADMIN)

        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse('user-circle-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['circles']), 2)
        circle_names = {item['circle']['name'] for item in response.data['circles']}
        self.assertIn(self.circle.name, circle_names)
        self.assertIn(other_circle.name, circle_names)

    def test_create_circle_assigns_admin_membership(self):
        self.client.force_authenticate(user=self.admin)
        payload = {'name': 'New Circle'}
        response = self.client.post(reverse('user-circle-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_circle_id = response.data['circle']['id']
        self.assertTrue(
            CircleMembership.objects.filter(circle_id=new_circle_id, user=self.admin, role=UserRole.CIRCLE_ADMIN).exists()
        )

    def test_admin_can_update_circle_name(self):
        self.client.force_authenticate(user=self.admin)
        payload = {'name': 'Renamed Circle'}
        response = self.client.patch(reverse('circle-detail', args=[self.circle.id]), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.circle.refresh_from_db()
        self.assertEqual(self.circle.name, payload['name'])

    def test_member_cannot_update_circle_name(self):
        member = User.objects.create_user(
            username='memberrename',
            email='memberrename@example.com',
            password='password123',
        )
        CircleMembership.objects.create(user=member, circle=self.circle, role=UserRole.CIRCLE_MEMBER)

        self.client.force_authenticate(user=member)
        response = self.client.patch(reverse('circle-detail', args=[self.circle.id]), {'name': 'Nope'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.circle.refresh_from_db()
        self.assertNotEqual(self.circle.name, 'Nope')

    def test_circle_admin_can_view_members(self):
        member = User.objects.create_user(
            username='memberuser',
            email='member@example.com',
            password='password123',
        )
        CircleMembership.objects.create(user=member, circle=self.circle, role=UserRole.CIRCLE_MEMBER)

        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse('circle-member-list', args=[self.circle.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        member_ids = {item['user']['id'] for item in response.data['members']}
        self.assertIn(member.id, member_ids)
        self.assertIn(self.admin.id, member_ids)

    def test_admin_can_add_member(self):
        new_user = User.objects.create_user(
            username='addmember',
            email='addmember@example.com',
            password='password123',
        )

        self.client.force_authenticate(user=self.admin)
        url = reverse('circle-member-list', args=[self.circle.id])
        response = self.client.post(url, {'user_id': new_user.id}, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(CircleMembership.objects.filter(circle=self.circle, user=new_user).exists())

    def test_non_admin_cannot_view_circle_members(self):
        member = User.objects.create_user(
            username='memberuser2',
            email='member2@example.com',
            password='password123',
        )
        CircleMembership.objects.create(user=member, circle=self.circle, role=UserRole.CIRCLE_MEMBER)

        self.client.force_authenticate(user=member)
        response = self.client.get(reverse('circle-member-list', args=[self.circle.id]))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_admin_cannot_add_member(self):
        member = User.objects.create_user(
            username='memberadd',
            email='memberadd@example.com',
            password='password123',
        )
        CircleMembership.objects.create(user=member, circle=self.circle, role=UserRole.CIRCLE_MEMBER)
        target = User.objects.create_user(
            username='targetuser',
            email='target@example.com',
            password='password123',
        )

        self.client.force_authenticate(user=member)
        url = reverse('circle-member-list', args=[self.circle.id])
        response = self.client.post(url, {'user_id': target.id}, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(CircleMembership.objects.filter(circle=self.circle, user=target).exists())

    def test_user_can_remove_self_from_circle(self):
        member = User.objects.create_user(
            username='memberuser3',
            email='member3@example.com',
            password='password123',
        )
        CircleMembership.objects.create(user=member, circle=self.circle, role=UserRole.CIRCLE_MEMBER)

        self.client.force_authenticate(user=member)
        url = reverse('circle-member-remove', args=[self.circle.id, member.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CircleMembership.objects.filter(circle=self.circle, user=member).exists())

    def test_non_admin_cannot_remove_other_member(self):
        member = User.objects.create_user(
            username='memberuser4',
            email='member4@example.com',
            password='password123',
        )
        other_member = User.objects.create_user(
            username='memberuser5',
            email='member5@example.com',
            password='password123',
        )
        CircleMembership.objects.create(user=member, circle=self.circle, role=UserRole.CIRCLE_MEMBER)
        CircleMembership.objects.create(user=other_member, circle=self.circle, role=UserRole.CIRCLE_MEMBER)

        self.client.force_authenticate(user=member)
        url = reverse('circle-member-remove', args=[self.circle.id, other_member.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(CircleMembership.objects.filter(circle=self.circle, user=other_member).exists())

    def test_admin_can_remove_member(self):
        member = User.objects.create_user(
            username='memberuser6',
            email='member6@example.com',
            password='password123',
        )
        CircleMembership.objects.create(user=member, circle=self.circle, role=UserRole.CIRCLE_MEMBER)

        self.client.force_authenticate(user=self.admin)
        url = reverse('circle-member-remove', args=[self.circle.id, member.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CircleMembership.objects.filter(circle=self.circle, user=member).exists())

    def test_activity_feed_contains_members_and_invitations(self):
        member = User.objects.create_user(
            username='activitymember',
            email='activitymember@example.com',
            password='password123',
        )
        CircleMembership.objects.create(user=member, circle=self.circle, role=UserRole.CIRCLE_MEMBER)
        CircleInvitation.objects.create(
            circle=self.circle,
            email='invitee@example.com',
            invited_by=self.admin,
            role=UserRole.CIRCLE_MEMBER,
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse('circle-activity', args=[self.circle.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event_types = {event['type'] for event in response.data['events']}
        self.assertIn('member_joined', event_types)
        self.assertIn('invitation', event_types)
