from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from users.models import Circle, CircleInvitation, CircleMembership, User, UserRole


class CircleMembershipViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username='adminuser',
            email='admin@example.com',
            password='password123',
            role=UserRole.CIRCLE_ADMIN,
        )
        # Mark admin as email verified for circle creation
        self.admin.email_verified = True
        self.admin.save()
        
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
        new_circle_id = response.data['data']['circle']['id']
        self.assertTrue(
            CircleMembership.objects.filter(circle_id=new_circle_id, user=self.admin, role=UserRole.CIRCLE_ADMIN).exists()
        )

    def test_create_circle_requires_name(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(reverse('user-circle-list'), {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

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

    def test_update_circle_requires_existing_circle(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(reverse('circle-detail', args=[9999]), {'name': 'Missing'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

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

    def test_admin_add_member_rejects_existing_membership(self):
        existing_member = User.objects.create_user(
            username='existingmember',
            email='existingmember@example.com',
            password='password123',
        )
        CircleMembership.objects.create(user=existing_member, circle=self.circle, role=UserRole.CIRCLE_MEMBER)

        self.client.force_authenticate(user=self.admin)
        url = reverse('circle-member-list', args=[self.circle.id])
        response = self.client.post(url, {'user_id': existing_member.id}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_add_member_rejects_unknown_user(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse('circle-member-list', args=[self.circle.id])
        response = self.client.post(url, {'user_id': 9999}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

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

    def test_remove_member_returns_404_when_missing(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse('circle-member-remove', args=[self.circle.id, 9999])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

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

    def test_activity_feed_requires_admin(self):
        member = User.objects.create_user(
            username='activitynonadmin',
            email='activitynonadmin@example.com',
            password='password123',
        )
        CircleMembership.objects.create(user=member, circle=self.circle, role=UserRole.CIRCLE_MEMBER)

        self.client.force_authenticate(user=member)
        response = self.client.get(reverse('circle-activity', args=[self.circle.id]))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
