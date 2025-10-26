"""Pytest configuration for auth tests (2FA and OAuth)"""
import pytest
from unittest.mock import patch
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model

from mysite.auth.models import TwoFactorCode, GoogleOAuthState
from mysite.auth.services.twofa_service import TwoFactorService

User = get_user_model()


@pytest.fixture
def mock_email_send():
    """Mock email sending for all tests"""
    with patch('mysite.emails.mailers.TwoFactorMailer.send_2fa_code') as mock:
        yield mock


@pytest.fixture
def mock_sms_send():
    """Mock SMS sending for all tests"""
    with patch('mysite.messaging.tasks.send_2fa_sms') as mock:
        yield mock


@pytest.fixture
def mock_totp_verify():
    """Mock TOTP verification"""
    with patch('mysite.auth.services.twofa_service.TwoFactorService.verify_totp') as mock:
        mock.return_value = True
        yield mock


@pytest.fixture
def mock_otp_verify():
    """Mock OTP verification"""
    with patch('mysite.auth.services.twofa_service.TwoFactorService.verify_otp') as mock:
        mock.return_value = True
        yield mock


@pytest.fixture
def disable_rate_limiting():
    """Disable rate limiting for tests"""
    with patch('mysite.auth.services.twofa_service.TwoFactorService.is_rate_limited') as mock:
        mock.return_value = False
        yield mock


# Shared helper functions for 2FA service tests
def create_user(local_part='testuser', email=None, password='testpass', **extra):
    """Create a test user with reasonable defaults."""
    if email is None:
        email = f"{local_part}@example.com"
    extra.setdefault('first_name', local_part.title())
    extra.setdefault('last_name', 'User')
    return User.objects.create_user(email=email, password=password, **extra)


def create_code(user, code='123456', **kwargs):
    """Helper to create hashed TwoFactorCode records."""
    defaults = {
        'code_hash': TwoFactorService._hash_otp(code),
        'code_preview': code[-6:],
        'method': 'email',
        'purpose': 'login',
        'is_used': False,
        'attempts': 0,
        'max_attempts': 5,
        'expires_at': timezone.now() + timedelta(minutes=10),
    }
    defaults.update(kwargs)
    return TwoFactorCode.objects.create(user=user, **defaults)


# OAuth-specific fixtures and helpers

@pytest.fixture
def oauth_redirect_uri():
    """Standard OAuth redirect URI for tests."""
    return 'http://localhost:3000/auth/google/callback'


@pytest.fixture
def oauth_ip_address():
    """Standard IP address for OAuth tests."""
    return '192.168.1.1'


@pytest.fixture
def oauth_user_agent():
    """Standard user agent for OAuth tests."""
    return 'Mozilla/5.0'


def create_oauth_state(redirect_uri='http://localhost:3000/auth/google/callback',
                       ip_address='192.168.1.1', **kwargs):
    """Helper to create GoogleOAuthState records."""
    defaults = {
        'state_token': 'test_state_token',
        'redirect_uri': redirect_uri,
        'ip_address': ip_address,
        'user_agent': 'Mozilla/5.0',
        'code_verifier': 'test_verifier',
        'nonce': 'test_nonce',
        'expires_at': timezone.now() + timedelta(minutes=10),
    }
    defaults.update(kwargs)
    return GoogleOAuthState.objects.create(**defaults)
