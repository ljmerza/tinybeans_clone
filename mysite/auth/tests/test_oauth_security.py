"""
OAuth Security Validators Tests

Tests for the security validation framework including:
- Redirect URI validation
- PKCE validation
- State token validation
- Security logging
"""
import pytest
from unittest.mock import Mock, patch
from django.test import TestCase
from django.conf import settings

from mysite.auth.security.oauth_validators import (
    RedirectURIValidator,
    PKCEValidator,
    StateTokenValidator,
    SecurityLogger,
    get_client_ip,
    get_user_agent,
)


class TestRedirectURIValidator(TestCase):
    """Test redirect URI validation against whitelist."""
    
    def setUp(self):
        """Set up test redirect URIs."""
        self.allowed_uris = [
            'https://tinybeans.app/auth/google/callback',
            'http://localhost:3000/auth/google/callback',
        ]
    
    def test_valid_redirect_uri_exact_match(self):
        """Test that exact match redirect URI is valid."""
        uri = 'https://tinybeans.app/auth/google/callback'
        result = RedirectURIValidator.validate(uri, self.allowed_uris)
        self.assertTrue(result)
    
    def test_valid_redirect_uri_with_subpath(self):
        """Test that subpath of allowed URI is valid."""
        uri = 'https://tinybeans.app/auth/google/callback/extra'
        result = RedirectURIValidator.validate(uri, self.allowed_uris)
        self.assertTrue(result)
    
    def test_invalid_redirect_uri_different_domain(self):
        """Test that different domain is rejected."""
        uri = 'https://evil.com/auth/google/callback'
        result = RedirectURIValidator.validate(uri, self.allowed_uris)
        self.assertFalse(result)
    
    def test_invalid_redirect_uri_different_scheme(self):
        """Test that different scheme is rejected."""
        uri = 'http://tinybeans.app/auth/google/callback'  # http instead of https
        result = RedirectURIValidator.validate(uri, self.allowed_uris)
        self.assertFalse(result)
    
    def test_invalid_redirect_uri_subdomain_attack(self):
        """Test that subdomain attack is rejected."""
        uri = 'https://evil.tinybeans.app/auth/google/callback'
        result = RedirectURIValidator.validate(uri, self.allowed_uris)
        self.assertFalse(result)
    
    def test_invalid_redirect_uri_missing_scheme(self):
        """Test that URI without scheme is rejected."""
        uri = 'tinybeans.app/auth/google/callback'
        result = RedirectURIValidator.validate(uri, self.allowed_uris)
        self.assertFalse(result)
    
    def test_invalid_redirect_uri_javascript(self):
        """Test that javascript URI is rejected."""
        uri = 'javascript:alert("xss")'
        result = RedirectURIValidator.validate(uri, self.allowed_uris)
        self.assertFalse(result)


class TestPKCEValidator(TestCase):
    """Test PKCE code verifier validation."""
    
    def test_valid_code_verifier_minimum_length(self):
        """Test that 43-character verifier is valid."""
        verifier = 'a' * 43
        result = PKCEValidator.validate_code_verifier(verifier)
        self.assertTrue(result)
    
    def test_valid_code_verifier_maximum_length(self):
        """Test that 128-character verifier is valid."""
        verifier = 'a' * 128
        result = PKCEValidator.validate_code_verifier(verifier)
        self.assertTrue(result)
    
    def test_valid_code_verifier_allowed_characters(self):
        """Test that RFC 7636 unreserved characters are valid."""
        verifier = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~'
        result = PKCEValidator.validate_code_verifier(verifier)
        self.assertTrue(result)
    
    def test_invalid_code_verifier_too_short(self):
        """Test that verifier shorter than 43 chars is invalid."""
        verifier = 'a' * 42
        result = PKCEValidator.validate_code_verifier(verifier)
        self.assertFalse(result)
    
    def test_invalid_code_verifier_too_long(self):
        """Test that verifier longer than 128 chars is invalid."""
        verifier = 'a' * 129
        result = PKCEValidator.validate_code_verifier(verifier)
        self.assertFalse(result)
    
    def test_invalid_code_verifier_forbidden_characters(self):
        """Test that forbidden characters are rejected."""
        verifier = 'a' * 43 + '!'  # 44 chars with forbidden !
        result = PKCEValidator.validate_code_verifier(verifier)
        self.assertFalse(result)


class TestStateTokenValidator(TestCase):
    """Test state token security validation."""
    
    def test_secure_token_valid_length(self):
        """Test that 128+ character token with good entropy is secure."""
        # Token with good variety of characters (meets both length and entropy requirements)
        token = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~' * 2
        result = StateTokenValidator.is_secure_token(token)
        self.assertTrue(result)
    
    def test_secure_token_high_entropy(self):
        """Test that token with high entropy is secure."""
        # Token with good variety of characters
        token = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~' * 3
        result = StateTokenValidator.is_secure_token(token)
        self.assertTrue(result)
    
    def test_insecure_token_low_entropy(self):
        """Test that token with low entropy is insecure."""
        # Token with only one character repeated (low entropy)
        token = 'a' * 128
        result = StateTokenValidator.is_secure_token(token)
        self.assertFalse(result)
    
    def test_insecure_token_too_short(self):
        """Test that token shorter than 128 chars is insecure."""
        token = 'a' * 127
        result = StateTokenValidator.is_secure_token(token)
        self.assertFalse(result)
    
    def test_insecure_token_low_entropy(self):
        """Test that token with low entropy is insecure."""
        # Only 2 unique characters
        token = 'ababababab' * 13  # 130 chars but low variety
        result = StateTokenValidator.is_secure_token(token)
        self.assertFalse(result)
    
    def test_constant_time_compare_equal(self):
        """Test that equal strings return True."""
        a = "test_token_12345"
        b = "test_token_12345"
        result = StateTokenValidator.constant_time_compare(a, b)
        self.assertTrue(result)
    
    def test_constant_time_compare_not_equal(self):
        """Test that different strings return False."""
        a = "test_token_12345"
        b = "test_token_54321"
        result = StateTokenValidator.constant_time_compare(a, b)
        self.assertFalse(result)


class TestSecurityLogger(TestCase):
    """Test security logging functionality."""
    
    @patch('mysite.auth.security.oauth_validators.logger')
    def test_log_oauth_initiate(self, mock_logger):
        """Test OAuth initiate logging."""
        SecurityLogger.log_oauth_initiate(
            redirect_uri='https://example.com/callback',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0',
            state_token='test_token_123456'
        )
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        self.assertEqual(call_args[0][0], "OAuth flow initiated")
        self.assertIn('oauth.initiate', call_args[1]['extra']['event'])
    
    @patch('mysite.auth.security.oauth_validators.logger')
    def test_log_oauth_callback_success(self, mock_logger):
        """Test OAuth callback success logging."""
        SecurityLogger.log_oauth_callback_success(
            user_id=42,
            action='created',
            ip_address='192.168.1.1',
            google_id='123456789'
        )
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        self.assertIn('OAuth callback successful', call_args[0][0])
        self.assertEqual(call_args[1]['extra']['user_id'], 42)
    
    @patch('mysite.auth.security.oauth_validators.logger')
    def test_log_security_block(self, mock_logger):
        """Test security block logging."""
        SecurityLogger.log_security_block(
            reason='unverified_account',
            email='test@example.com',
            ip_address='192.168.1.1',
            details={'google_id': '123456789'}
        )
        
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        self.assertIn('OAuth blocked', call_args[0][0])
        self.assertEqual(call_args[1]['extra']['reason'], 'unverified_account')


class TestHelperFunctions(TestCase):
    """Test helper utility functions."""
    
    def test_get_client_ip_from_remote_addr(self):
        """Test getting IP from REMOTE_ADDR."""
        request = Mock()
        request.META = {'REMOTE_ADDR': '192.168.1.1'}
        
        ip = get_client_ip(request)
        self.assertEqual(ip, '192.168.1.1')
    
    def test_get_client_ip_from_x_forwarded_for(self):
        """Test getting IP from X-Forwarded-For header."""
        request = Mock()
        request.META = {
            'HTTP_X_FORWARDED_FOR': '203.0.113.1, 192.168.1.1',
            'REMOTE_ADDR': '192.168.1.1'
        }
        
        ip = get_client_ip(request)
        self.assertEqual(ip, '203.0.113.1')  # First IP in chain
    
    def test_get_user_agent(self):
        """Test getting user agent from request."""
        request = Mock()
        request.META = {'HTTP_USER_AGENT': 'Mozilla/5.0'}
        
        user_agent = get_user_agent(request)
        self.assertEqual(user_agent, 'Mozilla/5.0')
    
    def test_get_user_agent_missing(self):
        """Test getting user agent when missing."""
        request = Mock()
        request.META = {}
        
        user_agent = get_user_agent(request)
        self.assertEqual(user_agent, 'Unknown')
