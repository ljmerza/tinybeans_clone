"""Tests for 2FA login happy paths and successful flows"""
import pytest
from unittest.mock import patch
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from mysite.auth.models import TwoFactorSettings, TwoFactorAuditLog
from mysite.auth.token_utils import generate_partial_token

User = get_user_model()


@pytest.mark.django_db
class TestLoginWithout2FA:
    """Test login flow when 2FA is not enabled"""

    def setup_method(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass',
        )

    def test_normal_login_no_2fa(self):
        """Test normal login when 2FA is not configured"""
        response = self.client.post('/api/auth/login/', {
            'email': 'test@example.com',
            'password': 'testpass'
        })

        assert response.status_code == status.HTTP_200_OK
        assert 'user' in response.data
        assert 'tokens' in response.data
        assert 'access' in response.data['tokens']
        assert 'requires_2fa' not in response.data

    def test_normal_login_2fa_disabled(self):
        """Test normal login when 2FA is configured but disabled"""
        TwoFactorSettings.objects.create(
            user=self.user,
            is_enabled=False,
            preferred_method='totp'
        )

        response = self.client.post('/api/auth/login/', {
            'email': 'test@example.com',
            'password': 'testpass'
        })

        assert response.status_code == status.HTTP_200_OK
        assert 'user' in response.data
        assert 'tokens' in response.data


@pytest.mark.django_db
class TestLoginWith2FA:
    """Test login flow when 2FA is enabled"""

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
    def test_login_requires_2fa(self, mock_rate_limit):
        """Test login returns requires_2fa when 2FA is enabled"""
        mock_rate_limit.return_value = False

        response = self.client.post('/api/auth/login/', {
            'email': 'test@example.com',
            'password': 'testpass'
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data['requires_2fa'] is True
        assert response.data['method'] == 'totp'
        assert 'partial_token' in response.data
        assert 'tokens' not in response.data

    @patch('mysite.auth.services.twofa_service.TwoFactorService.send_otp')
    @patch('mysite.auth.services.twofa_service.TwoFactorService.is_rate_limited')
    def test_login_sends_otp_for_email_method(self, mock_rate_limit, mock_send):
        """Test OTP is sent for email 2FA method"""
        mock_rate_limit.return_value = False
        self.twofa_settings.preferred_method = 'email'
        self.twofa_settings.save()

        response = self.client.post('/api/auth/login/', {
            'email': 'test@example.com',
            'password': 'testpass'
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data['requires_2fa'] is True
        mock_send.assert_called_once()


@pytest.mark.django_db
class TestTwoFactorVerifyLogin:
    """Test 2FA verification during login - successful cases"""

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
    def test_verify_login_with_valid_totp(self, mock_verify):
        """Test successful login verification with TOTP"""
        mock_verify.return_value = True
        partial_token = generate_partial_token(self.user)

        response = self.client.post('/api/auth/2fa/verify-login/', {
            'code': '123456',
            'partial_token': partial_token,
            'remember_me': False
        })

        assert response.status_code == status.HTTP_200_OK
        assert 'user' in response.data
        assert 'tokens' in response.data
        assert 'access' in response.data['tokens']

        # Check audit log
        log = TwoFactorAuditLog.objects.filter(
            user=self.user,
            action='2fa_login_success'
        ).first()
        assert log is not None
        assert log.success is True

    @patch('mysite.auth.services.twofa_service.TwoFactorService.verify_otp')
    def test_verify_login_with_email_otp(self, mock_verify):
        """Test login verification with email OTP"""
        self.twofa_settings.preferred_method = 'email'
        self.twofa_settings.save()

        mock_verify.return_value = True
        partial_token = generate_partial_token(self.user)

        response = self.client.post('/api/auth/2fa/verify-login/', {
            'code': '123456',
            'partial_token': partial_token,
            'remember_me': False
        })

        assert response.status_code == status.HTTP_200_OK
        assert 'tokens' in response.data

    @patch('mysite.auth.services.twofa_service.TwoFactorService.verify_totp')
    @patch('mysite.auth.services.twofa_service.TwoFactorService.verify_recovery_code')
    def test_verify_login_with_recovery_code(self, mock_recovery, mock_totp):
        """Test login verification with recovery code"""
        mock_totp.return_value = False
        mock_recovery.return_value = True

        partial_token = generate_partial_token(self.user)

        response = self.client.post('/api/auth/2fa/verify-login/', {
            'code': 'ABCD-EFGH-IJKL',
            'partial_token': partial_token,
            'remember_me': False
        })

        assert response.status_code == status.HTTP_200_OK
        assert 'tokens' in response.data

        # Check audit log shows recovery code usage
        log = TwoFactorAuditLog.objects.filter(
            user=self.user,
            action='2fa_login_success'
        ).first()
        assert log is not None
        assert log.method == 'recovery_code'


@pytest.mark.django_db
class TestCompleteLoginFlow:
    """Integration tests for complete login flows"""

    def setup_method(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass'
        )

    @patch('mysite.auth.services.twofa_service.TwoFactorService.verify_totp')
    @patch('mysite.auth.services.twofa_service.TwoFactorService.is_rate_limited')
    def test_complete_2fa_login_flow(self, mock_rate, mock_verify):
        """Test complete flow from login to 2FA verification"""
        # Enable 2FA
        TwoFactorSettings.objects.create(
            user=self.user,
            is_enabled=True,
            preferred_method='totp',
            totp_secret='JBSWY3DPEHPK3PXP'
        )

        mock_rate.return_value = False

        # Step 1: Login
        login_response = self.client.post('/api/auth/login/', {
            'email': 'test@example.com',
            'password': 'testpass'
        })

        assert login_response.status_code == status.HTTP_200_OK
        assert login_response.data['requires_2fa'] is True
        partial_token = login_response.data['partial_token']

        # Step 2: Verify 2FA
        mock_verify.return_value = True

        verify_response = self.client.post('/api/auth/2fa/verify-login/', {
            'code': '123456',
            'partial_token': partial_token,
            'remember_me': False
        })

        assert verify_response.status_code == status.HTTP_200_OK
        assert 'tokens' in verify_response.data
        assert 'user' in verify_response.data

    def test_login_without_2fa_is_unchanged(self):
        """Test that login without 2FA still works as before"""
        response = self.client.post('/api/auth/login/', {
            'email': 'test@example.com',
            'password': 'testpass'
        })

        assert response.status_code == status.HTTP_200_OK
        assert 'tokens' in response.data
        assert 'user' in response.data
        assert 'requires_2fa' not in response.data
