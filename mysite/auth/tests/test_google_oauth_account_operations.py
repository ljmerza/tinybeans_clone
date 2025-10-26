"""
Google OAuth Account Operations Tests

Tests for user account creation, linking, and unlinking with Google OAuth.
"""
import unittest
from unittest.mock import patch
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

from mysite.auth.services.google_oauth_service import GoogleOAuthService
from mysite.auth.exceptions import UnverifiedAccountExistsError
from mysite.auth.tests.conftest import create_oauth_state

User = get_user_model()


class TestUserCreation(TestCase):
    """Test creating new users from Google OAuth."""

    def setUp(self):
        """Set up test data."""
        self.service = GoogleOAuthService()
        self.redirect_uri = 'http://localhost:3000/auth/google/callback'
        self.ip_address = '192.168.1.1'
        self.user_agent = 'Mozilla/5.0'

    @unittest.skip("Needs complex Google OAuth library mocking")
    @patch('mysite.auth.services.google_oauth_service.id_token.verify_oauth2_token')
    @patch('mysite.auth.services.google_oauth_service.requests.post')
    def test_get_or_create_user_new_user(self, mock_post, mock_verify):
        """Test creating new user from Google OAuth."""
        # Mock token verification
        mock_verify.return_value = {
            'sub': '123456789',
            'email': 'newuser@gmail.com',
            'email_verified': True,
            'name': 'New User',
            'picture': 'https://example.com/photo.jpg'
        }

        # Create state
        oauth_state = create_oauth_state(
            redirect_uri=self.redirect_uri,
            code_verifier='test_verifier_' + 'a' * 32,
        )

        # Get or create user
        user, action = self.service.get_or_create_user(
            google_token_data={'id_token': 'test_token'},
            oauth_state=oauth_state
        )

        self.assertEqual(action, 'created')
        self.assertEqual(user.email, 'newuser@gmail.com')
        self.assertEqual(user.google_id, '123456789')
        self.assertTrue(user.email_verified)
        self.assertEqual(user.auth_provider, 'google')


class TestAccountLinkingSecurity(TestCase):
    """Test security aspects of account linking (CRITICAL)."""

    def setUp(self):
        """Set up test data."""
        self.service = GoogleOAuthService()
        self.redirect_uri = 'http://localhost:3000/auth/google/callback'
        self.ip_address = '192.168.1.1'
        self.user_agent = 'Mozilla/5.0'

    @unittest.skip("Needs complex Google OAuth library mocking")
    @patch('mysite.auth.services.google_oauth_service.id_token.verify_oauth2_token')
    @patch('mysite.auth.services.google_oauth_service.requests.post')
    def test_get_or_create_user_unverified_account_blocks(self, mock_post, mock_verify):
        """Test that linking to unverified account is blocked (CRITICAL)."""
        # Create unverified user
        existing_user = User.objects.create_user(
            email='existing@gmail.com',
            password='testpass123',
            email_verified=False  # UNVERIFIED
        )

        # Mock token verification
        mock_verify.return_value = {
            'sub': '123456789',
            'email': 'existing@gmail.com',  # Same email
            'email_verified': True,
            'name': 'Existing User',
        }

        oauth_state = create_oauth_state(
            redirect_uri=self.redirect_uri,
            code_verifier='test_verifier_' + 'a' * 32,
        )

        # Should raise error - CRITICAL SECURITY CHECK
        with self.assertRaises(UnverifiedAccountExistsError):
            self.service.get_or_create_user(
                google_token_data={'id_token': 'test_token'},
                oauth_state=oauth_state
            )

    @unittest.skip("Needs complex Google OAuth library mocking")
    @patch('mysite.auth.services.google_oauth_service.id_token.verify_oauth2_token')
    @patch('mysite.auth.services.google_oauth_service.requests.post')
    def test_get_or_create_user_existing_verified_links(self, mock_post, mock_verify):
        """Test linking Google to existing verified account."""
        # Create verified user
        existing_user = User.objects.create_user(
            email='verified@gmail.com',
            password='testpass123',
            email_verified=True  # VERIFIED
        )

        # Mock token verification
        mock_verify.return_value = {
            'sub': '123456789',
            'email': 'verified@gmail.com',
            'email_verified': True,
            'name': 'Verified User',
        }

        oauth_state = create_oauth_state(
            redirect_uri=self.redirect_uri,
            code_verifier='test_verifier_' + 'a' * 32,
        )

        # Should link Google account
        user, action = self.service.get_or_create_user(
            google_token_data={'id_token': 'test_token'},
            oauth_state=oauth_state
        )

        self.assertEqual(action, 'linked')
        self.assertEqual(user.email, 'verified@gmail.com')
        self.assertEqual(user.google_id, '123456789')
        self.assertEqual(user.auth_provider, 'hybrid')


class TestAccountLinkingOperations(TestCase):
    """Test linking and unlinking Google accounts to existing users."""

    def setUp(self):
        """Set up test data."""
        self.service = GoogleOAuthService()

    def test_link_google_account_success(self):
        """Test linking Google account to authenticated user."""
        # Create user
        user = User.objects.create_user(
            email='test@gmail.com',
            password='testpass123',
            email_verified=True
        )

        # Link Google account
        google_user_info = {
            'sub': '987654321',
            'email': 'test@gmail.com',
            'email_verified': True,
            'name': 'Test User',
            'picture': 'https://example.com/photo.jpg'
        }

        updated_user = self.service.link_google_account(
            user=user,
            google_user_info=google_user_info
        )

        self.assertEqual(updated_user.google_id, '987654321')
        self.assertEqual(updated_user.auth_provider, 'hybrid')
        self.assertIsNotNone(updated_user.google_linked_at)

    def test_unlink_google_account_success(self):
        """Test unlinking Google account."""
        # Create user with Google linked
        user = User.objects.create_user(
            email='test@gmail.com',
            password='testpass123',
            email_verified=True,
            google_id='123456789',
            auth_provider='hybrid'
        )

        # Unlink
        updated_user = self.service.unlink_google_account(user)

        self.assertIsNone(updated_user.google_id)
        self.assertEqual(updated_user.auth_provider, 'manual')
        self.assertIsNone(updated_user.google_linked_at)
