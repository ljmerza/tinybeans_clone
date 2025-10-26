"""Tests for circle serializers."""
from django.test import TestCase

from mysite.users.models import Circle, User
from mysite.users.serializers import CircleCreateSerializer, CircleSerializer


class CircleSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='creator@example.com', password='password123')
        self.circle = Circle.objects.create(name='Test Family', created_by=self.user)

    def test_circle_serialization(self):
        """Test serializing a circle."""
        serializer = CircleSerializer(self.circle)
        data = serializer.data

        self.assertEqual(data['name'], 'Test Family')
        self.assertEqual(data['slug'], 'test-family')
        self.assertIn('member_count', data)
        self.assertEqual(data['member_count'], 1)  # Owner membership is auto-created


class CircleCreateSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='password123',
            email_verified=True
        )
        self.unverified_user = User.objects.create_user(
            email='unverified@example.com',
            password='password123',
            email_verified=False
        )

    def test_valid_circle_creation(self):
        """Test creating a circle with valid data and verified email."""
        data = {'name': 'New Family Circle'}

        serializer = CircleCreateSerializer(data=data, context={'user': self.user})
        self.assertTrue(serializer.is_valid())

    def test_email_verification_required(self):
        """Test that email verification is required for circle creation."""
        data = {'name': 'New Family Circle'}

        serializer = CircleCreateSerializer(data=data, context={'user': self.unverified_user})
        self.assertFalse(serializer.is_valid())
        self.assertIn('i18n_key', serializer.errors)
        self.assertEqual(
            str(serializer.errors['i18n_key'][0]),
            'errors.email_verification_required',
        )

    def test_empty_name_validation(self):
        """Test that empty name is rejected."""
        data = {'name': ''}

        serializer = CircleCreateSerializer(data=data, context={'user': self.user})
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)

    def test_whitespace_only_name_validation(self):
        """Test that whitespace-only name is rejected."""
        data = {'name': '   '}

        serializer = CircleCreateSerializer(data=data, context={'user': self.user})
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)
