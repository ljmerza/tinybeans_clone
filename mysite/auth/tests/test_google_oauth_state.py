"""
Google OAuth State and PKCE Tests

Tests for state token generation, validation, and PKCE flow.
"""
import pytest
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone

from mysite.auth.services.google_oauth_service import GoogleOAuthService, InvalidStateError
from mysite.auth.models import GoogleOAuthState
from mysite.auth.tests.conftest import create_oauth_state


class TestGoogleOAuthURLGeneration(TestCase):
    """Test OAuth URL generation with PKCE and state tokens."""

    def setUp(self):
        """Set up test data."""
        self.service = GoogleOAuthService()
        self.redirect_uri = 'http://localhost:3000/auth/google/callback'
        self.ip_address = '192.168.1.1'
        self.user_agent = 'Mozilla/5.0'

    def test_generate_auth_url_success(self):
        """Test successful OAuth URL generation."""
        result = self.service.generate_auth_url(
            redirect_uri=self.redirect_uri,
            ip_address=self.ip_address,
            user_agent=self.user_agent
        )

        # Check response structure
        self.assertIn('url', result)
        self.assertIn('state', result)
        self.assertIn('expires_in', result)

        # Check URL contains required parameters
        url = result['url']
        self.assertIn('client_id=', url)
        self.assertIn('redirect_uri=', url)
        self.assertIn('response_type=code', url)
        self.assertIn('scope=', url)
        self.assertIn('state=', url)
        self.assertIn('code_challenge=', url)
        self.assertIn('code_challenge_method=S256', url)

        # Check state token was created in database
        state_token = result['state']
        oauth_state = GoogleOAuthState.objects.get(state_token=state_token)
        self.assertEqual(oauth_state.redirect_uri, self.redirect_uri)
        self.assertEqual(oauth_state.ip_address, self.ip_address)
        self.assertIsNotNone(oauth_state.code_verifier)
        self.assertIsNotNone(oauth_state.nonce)

    def test_generate_auth_url_invalid_redirect_uri(self):
        """Test that invalid redirect URI raises error."""
        from mysite.auth.services.google_oauth_service import InvalidRedirectURIError
        with self.assertRaises(InvalidRedirectURIError):
            self.service.generate_auth_url(
                redirect_uri='https://evil.com/callback',
                ip_address=self.ip_address,
                user_agent=self.user_agent
            )


class TestStateTokenValidation(TestCase):
    """Test state token validation logic."""

    def setUp(self):
        """Set up test data."""
        self.service = GoogleOAuthService()
        self.redirect_uri = 'http://localhost:3000/auth/google/callback'
        self.ip_address = '192.168.1.1'
        self.user_agent = 'Mozilla/5.0'

    def test_validate_state_token_success(self):
        """Test successful state token validation."""
        # Create state token
        oauth_state = create_oauth_state(
            state_token='test_state_token_123',
            redirect_uri=self.redirect_uri,
            ip_address=self.ip_address,
            user_agent=self.user_agent
        )

        # Validate
        result = self.service.validate_state_token('test_state_token_123')

        self.assertEqual(result.state_token, 'test_state_token_123')
        self.assertFalse(result.is_used())

    def test_validate_state_token_expired(self):
        """Test that expired state token raises error."""
        # Create expired state token
        create_oauth_state(
            state_token='expired_token',
            redirect_uri=self.redirect_uri,
            ip_address=self.ip_address,
            expires_at=timezone.now() - timedelta(minutes=1)  # Expired
        )

        with self.assertRaises(InvalidStateError) as context:
            self.service.validate_state_token('expired_token')

        self.assertIn('expired', str(context.exception).lower())

    def test_validate_state_token_already_used(self):
        """Test that used state token raises error."""
        # Create and mark as used
        create_oauth_state(
            state_token='used_token',
            redirect_uri=self.redirect_uri,
            ip_address=self.ip_address,
            used_at=timezone.now()
        )

        with self.assertRaises(InvalidStateError) as context:
            self.service.validate_state_token('used_token')

        self.assertIn('already used', str(context.exception).lower())

    def test_validate_state_token_not_found(self):
        """Test that non-existent state token raises error."""
        with self.assertRaises(InvalidStateError) as context:
            self.service.validate_state_token('non_existent_token')

        self.assertIn('not found', str(context.exception).lower())


class TestOAuthStateModel(TestCase):
    """Test GoogleOAuthState model methods."""

    def test_is_expired_true(self):
        """Test that expired state is detected."""
        state = create_oauth_state(
            expires_at=timezone.now() - timedelta(minutes=1)
        )

        self.assertTrue(state.is_expired())

    def test_is_expired_false(self):
        """Test that non-expired state is detected."""
        state = create_oauth_state(
            expires_at=timezone.now() + timedelta(minutes=10)
        )

        self.assertFalse(state.is_expired())

    def test_is_used_true(self):
        """Test that used state is detected."""
        state = create_oauth_state(
            used_at=timezone.now()
        )

        self.assertTrue(state.is_used())

    def test_is_used_false(self):
        """Test that unused state is detected."""
        state = create_oauth_state()

        self.assertFalse(state.is_used())

    def test_mark_as_used(self):
        """Test marking state as used."""
        state = create_oauth_state()

        self.assertIsNone(state.used_at)

        state.mark_as_used()

        self.assertIsNotNone(state.used_at)
        self.assertTrue(state.is_used())
