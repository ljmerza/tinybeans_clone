"""Tests for 2FA login lockouts, rate limiting, and failures"""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from mysite.auth.models import TwoFactorAuditLog, TwoFactorSettings
from mysite.auth.token_utils import generate_partial_token

User = get_user_model()


@pytest.mark.django_db
class TestLoginRateLimiting:
    """Test rate limiting during login with 2FA"""

    def setup_method(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass",
        )
        self.twofa_settings = TwoFactorSettings.objects.create(
            user=self.user, is_enabled=True, preferred_method="totp", totp_secret="JBSWY3DPEHPK3PXP"
        )

    @patch("mysite.auth.services.twofa_service.TwoFactorService.is_rate_limited")
    def test_login_rate_limited(self, mock_rate_limit):
        """Test login fails when rate limited"""
        mock_rate_limit.return_value = True

        response = self.client.post("/api/auth/login/", {"email": "test@example.com", "password": "testpass"})

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


@pytest.mark.django_db
class TestVerificationFailures:
    """Test 2FA verification failures and audit logging"""

    def setup_method(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(email="test@example.com", password="testpass")
        self.twofa_settings = TwoFactorSettings.objects.create(
            user=self.user, is_enabled=True, preferred_method="totp", totp_secret="JBSWY3DPEHPK3PXP"
        )

    @patch("mysite.auth.services.twofa_service.TwoFactorService.verify_totp")
    def test_verify_login_with_invalid_code(self, mock_verify):
        """Test login verification fails with invalid code"""
        mock_verify.return_value = False
        partial_token = generate_partial_token(self.user)

        response = self.client.post(
            "/api/auth/2fa/verify-login/", {"code": "999999", "partial_token": partial_token, "remember_me": False}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

        # Check audit log for failed attempt
        log = TwoFactorAuditLog.objects.filter(user=self.user, action="2fa_login_failed").first()
        assert log is not None
        assert log.success is False

    def test_verify_login_with_invalid_partial_token(self):
        """Test verification fails with invalid partial token"""
        response = self.client.post(
            "/api/auth/2fa/verify-login/", {"code": "123456", "partial_token": "invalid-token", "remember_me": False}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "partial_token_invalid"

    @patch("mysite.auth.services.twofa_service.TwoFactorService.verify_totp")
    def test_verify_login_with_expired_partial_token(self, mock_verify):
        """Test verification fails with expired partial token"""
        mock_verify.return_value = True

        # Use an invalid token (not in cache)
        response = self.client.post(
            "/api/auth/2fa/verify-login/",
            {"code": "123456", "partial_token": "expired-token-12345", "remember_me": False},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestAuditLogClientIP:
    """The 2FA audit log records the proxy-aware client IP, not the proxy's."""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="audit-ip@example.com", password="testpass")
        TwoFactorSettings.objects.create(
            user=self.user, is_enabled=True, preferred_method="totp", totp_secret="JBSWY3DPEHPK3PXP"
        )

    def _fail_verification(self):
        with patch("mysite.auth.services.twofa_service.TwoFactorService.verify_totp", return_value=False):
            self.client.post(
                "/api/auth/2fa/verify-login/",
                {"code": "999999", "partial_token": generate_partial_token(self.user), "remember_me": False},
                HTTP_X_FORWARDED_FOR="198.51.100.66, 203.0.113.7",
                REMOTE_ADDR="127.0.0.1",
            )
        return TwoFactorAuditLog.objects.get(user=self.user, action="2fa_login_failed")

    def test_behind_trusted_proxy_logs_the_client(self, settings):
        settings.DEBUG = False
        settings.TRUST_FORWARDED_FOR = True
        settings.TRUSTED_PROXY_IPS = ["127.0.0.1", "::1"]
        # The right-most untrusted entry, not the client-written left-most one.
        assert self._fail_verification().ip_address == "203.0.113.7"

    def test_forwarded_header_from_untrusted_peer_is_ignored(self, settings):
        settings.DEBUG = False
        settings.TRUST_FORWARDED_FOR = True
        settings.TRUSTED_PROXY_IPS = []
        assert self._fail_verification().ip_address == "127.0.0.1"
