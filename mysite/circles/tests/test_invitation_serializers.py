"""Test circle invitation serializer validation and data processing."""
from django.test import TestCase

from mysite.circles.models import Circle, CircleMembership
from mysite.circles.serializers import CircleInvitationCreateSerializer
from mysite.users.models import User, UserRole


class InvitationSerializerTests(TestCase):
    """Test CircleInvitationCreateSerializer validation logic."""

    def setUp(self):
        """Set up test data."""
        self.admin = User.objects.create_user(
            email='admin@example.com',
            password='password123'
        )
        self.circle = Circle.objects.create(name='Test Circle', created_by=self.admin)
        CircleMembership.objects.create(user=self.admin, circle=self.circle, role=UserRole.CIRCLE_ADMIN)

    def test_role_validation(self):
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

    def test_existing_user_lookup(self):
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

    def test_requires_email(self):
        """Serializer requires an email address."""
        serializer = CircleInvitationCreateSerializer(
            data={},
            context={'circle': self.circle}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
