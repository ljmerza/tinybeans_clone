"""Tests for 2FA login lockouts, rate limiting, and failures"""
import pytest
from unittest.mock import patch
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from mysite.auth.models import TwoFactorSettings, TwoFactorAuditLog
from mysite.auth.token_utils import generate_partial_token

User = get_user_model()


@pytest.mark.django_db
class TestLoginRateLimiting:
    """Test rate limiting during login with 2FA"""

    def setup_method(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass',
        )
        self.twofa_settings = TwoFactorSettings.objects.create(
            user=self.user,
            is_enabled=True,
            preferred_method='totp',
            totp_secret='JBSWY3DPEHPK3PXP'
        )

    @patch('mysite.auth.services.twofa_service.TwoFactorService.is_rate_limited')
    def test_login_rate_limited(self, mock_rate_limit):
        """Test login fails when rate limited"""
        mock_rate_limit.return_value = True

        response = self.client.post('/api/auth/login/', {
            'email': 'test@example.com',
            'password': 'testpass'
        })

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


@pytest.mark.django_db
class TestVerificationFailures:
    """Test 2FA verification failures and audit logging"""

    def setup_method(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass'
        )
        self.twofa_settings = TwoFactorSettings.objects.create(
            user=self.user,
            is_enabled=True,
            preferred_method='totp',
            totp_secret='JBSWY3DPEHPK3PXP'
        )

    @patch('mysite.auth.services.twofa_service.TwoFactorService.verify_totp')
    def test_verify_login_with_invalid_code(self, mock_verify):
        """Test login verification fails with invalid code"""
        mock_verify.return_value = False
        partial_token = generate_partial_token(self.user)

        response = self.client.post('/api/auth/2fa/verify-login/', {
            'code': '999999',
            'partial_token': partial_token,
            'remember_me': False
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

        # Check audit log for failed attempt
        log = TwoFactorAuditLog.objects.filter(
            user=self.user,
            action='2fa_login_failed'
        ).first()
        assert log is not None
        assert log.success is False

    def test_verify_login_with_invalid_partial_token(self):
        """Test verification fails with invalid partial token"""
        response = self.client.post('/api/auth/2fa/verify-login/', {
            'code': '123456',
            'partial_token': 'invalid-token',
            'remember_me': False
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'partial token' in response.data['error'].lower()

    @patch('mysite.auth.services.twofa_service.TwoFactorService.verify_totp')
    def test_verify_login_with_expired_partial_token(self, mock_verify):
        """Test verification fails with expired partial token"""
        mock_verify.return_value = True

        # Use an invalid token (not in cache)
        response = self.client.post('/api/auth/2fa/verify-login/', {
            'code': '123456',
            'partial_token': 'expired-token-12345',
            'remember_me': False
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
