"""Tests for user serializers."""
from django.test import TestCase

from mysite.users.models import User, UserRole
from mysite.users.serializers import UserSerializer


class UserSerializerTests(TestCase):
    def test_user_serialization(self):
        """Test serializing a user."""
        user = User.objects.create_user(
            email='test@example.com',
            password='password123',
            role=UserRole.CIRCLE_ADMIN,
            first_name='Test',
            last_name='User',
        )

        serializer = UserSerializer(user)
        data = serializer.data

        self.assertEqual(data['email'], 'test@example.com')
        self.assertEqual(data['display_name'], 'Test User')
        self.assertEqual(data['first_name'], 'Test')
        self.assertEqual(data['last_name'], 'User')
        self.assertEqual(data['role'], UserRole.CIRCLE_ADMIN)
        self.assertFalse(data['email_verified'])
        self.assertEqual(data['circle_onboarding_status'], 'pending')
        self.assertTrue(data['needs_circle_onboarding'])
        self.assertIsNone(data['circle_onboarding_updated_at'])
        self.assertIn('date_joined', data)
