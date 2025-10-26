"""Tests for authentication serializers."""
from django.test import TestCase

from mysite.users.models import User, UserRole
from mysite.auth.serializers import (
    EmailVerificationSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    PasswordResetRequestSerializer,
    SignupSerializer,
)


class SignupSerializerTests(TestCase):
    def test_valid_signup_data(self):
        """Test signup serializer with valid data."""
        data = {
            'email': 'new@example.com',
            'password': 'securepassword123',
            'first_name': 'New',
            'last_name': 'User',
        }

        serializer = SignupSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        # SignupSerializer.save() now returns only the user
        user = serializer.save()
        self.assertEqual(user.email, 'new@example.com')
        self.assertEqual(user.first_name, 'New')
        self.assertEqual(user.last_name, 'User')
        self.assertTrue(user.check_password('securepassword123'))
        self.assertFalse(user.email_verified)  # Email should not be verified initially
        self.assertEqual(user.circle_onboarding_status, 'pending')

    def test_signup_without_circle(self):
        """Test signup creates user without circle (circles created separately)."""
        data = {
            'email': 'new@example.com',
            'password': 'securepassword123',
            'first_name': 'Circle',
            'last_name': 'Deferred',
        }

        serializer = SignupSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        user = serializer.save()
        self.assertEqual(user.role, UserRole.CIRCLE_MEMBER)  # Default role

        # No circles should be created during signup
        from mysite.users.models import CircleMembership
        self.assertEqual(CircleMembership.objects.filter(user=user).count(), 0)

    def test_signup_password_too_short(self):
        """Test signup with password that's too short."""
        data = {
            'email': 'new@example.com',
            'password': 'short',
            'first_name': 'Short',
            'last_name': 'Pass',
        }

        serializer = SignupSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)

    def test_signup_requires_first_name(self):
        data = {
            'email': 'new@example.com',
            'password': 'securepassword123',
            'last_name': 'Missing',
        }
        serializer = SignupSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('first_name', serializer.errors)

    def test_signup_requires_last_name(self):
        data = {
            'email': 'new@example.com',
            'password': 'securepassword123',
            'first_name': 'Missing',
        }
        serializer = SignupSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('last_name', serializer.errors)

    def test_role_validation(self):
        """Test that role field is no longer accepted in signup."""
        data = {
            'email': 'new@example.com',
            'password': 'securepassword123',
            'role': UserRole.CIRCLE_ADMIN,
            'first_name': 'Admin',
            'last_name': 'Role',
        }

        serializer = SignupSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        # Role field should be ignored since it's not in the model fields
        user = serializer.save()
        self.assertEqual(user.role, UserRole.CIRCLE_MEMBER)  # Default role

    def test_empty_role_defaults_to_member(self):
        """Test that users are created with default CIRCLE_MEMBER role."""
        data = {
            'email': 'new@example.com',
            'password': 'securepassword123',
            'first_name': 'Default',
            'last_name': 'Role',
            # Don't provide role field at all to test default
        }

        serializer = SignupSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        user = serializer.save()
        self.assertEqual(user.role, UserRole.CIRCLE_MEMBER)  # Default role

    def test_circle_creation_removed_from_signup(self):
        """Test that circle creation fields are no longer supported in signup."""
        # Circle-related fields should be ignored since they're not in the serializer
        data = {
            'email': 'new_unique@example.com',
            'password': 'securepassword123',
            'first_name': 'Circle',
            'last_name': 'Ignored',
            'create_circle': True,
            'circle_name': 'My Family Circle'
        }

        serializer = SignupSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        user = serializer.save()

        # User should be created but no circles
        from mysite.users.models import CircleMembership
        self.assertEqual(CircleMembership.objects.filter(user=user).count(), 0)
        self.assertEqual(user.role, UserRole.CIRCLE_MEMBER)  # Default role


class LoginSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='password123'
        )

    def test_valid_login_with_email(self):
        """Test valid login with email."""
        data = {
            'email': 'test@example.com',
            'password': 'password123'
        }

        serializer = LoginSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['user'], self.user)

    def test_invalid_credentials(self):
        """Test login with invalid credentials."""
        data = {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        }

        serializer = LoginSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('i18n_key', serializer.errors)
        self.assertEqual(
            str(serializer.errors['i18n_key'][0]),
            'errors.invalid_credentials',
        )

    def test_missing_fields(self):
        """Test login with missing fields."""
        data = {'email': 'test@example.com'}

        serializer = LoginSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)


class EmailVerificationSerializerTests(TestCase):
    def test_valid_identifier_email(self):
        """Test email verification serializer with valid email."""
        User.objects.create_user(email='test@example.com', password='password123')
        data = {'email': 'test@example.com'}

        serializer = EmailVerificationSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['user'].email, 'test@example.com')

    def test_invalid_identifier(self):
        """Test email verification serializer with non-existent user."""
        data = {'email': 'nonexistent@example.com'}

        serializer = EmailVerificationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('i18n_key', serializer.errors)
        self.assertEqual(
            str(serializer.errors['i18n_key'][0]),
            'errors.user_not_found',
        )


class PasswordChangeSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', password='oldpassword')

    def test_valid_password_change(self):
        """Test password change with valid data."""
        data = {
            'current_password': 'oldpassword',
            'password': 'newpassword123',
            'password_confirm': 'newpassword123'
        }

        # Create a mock request
        from unittest.mock import Mock
        mock_request = Mock()
        mock_request.user = self.user

        serializer = PasswordChangeSerializer(data=data, context={'request': mock_request})
        self.assertTrue(serializer.is_valid())

    def test_short_new_password(self):
        """Test password change with too short new password."""
        data = {
            'current_password': 'oldpassword',
            'password': 'short',
            'password_confirm': 'short'
        }

        from unittest.mock import Mock
        mock_request = Mock()
        mock_request.user = self.user

        serializer = PasswordChangeSerializer(data=data, context={'request': mock_request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)

    def test_wrong_current_password(self):
        """Test password change with wrong current password."""
        data = {
            'current_password': 'wrongpassword',
            'password': 'newpassword123',
            'password_confirm': 'newpassword123'
        }

        from unittest.mock import Mock
        mock_request = Mock()
        mock_request.user = self.user

        serializer = PasswordChangeSerializer(data=data, context={'request': mock_request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('current_password', serializer.errors)

    def test_password_mismatch(self):
        """Test password change with mismatched passwords."""
        data = {
            'current_password': 'oldpassword',
            'password': 'newpassword123',
            'password_confirm': 'differentpassword123'
        }

        from unittest.mock import Mock
        mock_request = Mock()
        mock_request.user = self.user

        serializer = PasswordChangeSerializer(data=data, context={'request': mock_request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('password_confirm', serializer.errors)


class PasswordResetRequestSerializerTests(TestCase):
    def test_valid_identifier_email(self):
        """Test password reset request with email identifier."""
        data = {'email': 'test@example.com'}

        serializer = PasswordResetRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_invalid_identifier(self):
        """Test password reset request with missing user."""
        data = {'email': 'missing@example.com'}

        serializer = PasswordResetRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())
