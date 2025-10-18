"""Pytest configuration for 2FA tests"""
import pytest
from unittest.mock import patch


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
