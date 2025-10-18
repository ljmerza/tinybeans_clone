"""Tests for 2FA login integration"""
import pytest
from unittest.mock import patch, Mock
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from mysite.auth.models import (
    TwoFactorSettings,
    TwoFactorCode,
    RecoveryCode,
    TrustedDevice,
    TwoFactorAuditLog
)
from mysite.auth.token_utils import generate_partial_token
from mysite.auth.services.trusted_device_service import TrustedDeviceToken

User = get_user_model()


@pytest.mark.django_db
class TestLoginWithout2FA:
    """Test login flow when 2FA is not enabled"""
    
    def setup_method(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )
    
    def test_normal_login_no_2fa(self):
        """Test normal login when 2FA is not configured"""
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
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
            'username': 'testuser',
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
            username='testuser',
            email='test@example.com',
            password='testpass'
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
            'username': 'testuser',
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
            'username': 'testuser',
            'password': 'testpass'
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['requires_2fa'] is True
        mock_send.assert_called_once()
    
    @patch('mysite.auth.services.twofa_service.TwoFactorService.is_rate_limited')
    def test_login_rate_limited(self, mock_rate_limit):
        """Test login fails when rate limited"""
        mock_rate_limit.return_value = True
        
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'testpass'
        })
        
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


@pytest.mark.django_db
class TestLoginWithTrustedDevice:
    """Test login flow with trusted devices"""
    
    def setup_method(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )
        self.twofa_settings = TwoFactorSettings.objects.create(
            user=self.user,
            is_enabled=True,
            preferred_method='totp'
        )
    
    @patch('mysite.auth.services.trusted_device_service.TrustedDeviceService.is_trusted_device')
    @patch('mysite.auth.services.trusted_device_service.TrustedDeviceService.get_device_id_from_request')
    def test_login_skips_2fa_for_trusted_device(self, mock_get_device, mock_is_trusted):
        """Test 2FA is skipped for trusted devices"""
        mock_get_device.return_value = TrustedDeviceToken(
            device_id='device-123',
            signed_value='signed-device-123'
        )
        mock_is_trusted.return_value = (True, None)
        
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'testpass'
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert 'tokens' in response.data
        assert response.data.get('trusted_device') is True
        assert 'requires_2fa' not in response.data
    
    @patch('mysite.auth.services.trusted_device_service.TrustedDeviceService.is_trusted_device')
    @patch('mysite.auth.services.trusted_device_service.TrustedDeviceService.get_device_id_from_request')
    @patch('mysite.auth.services.twofa_service.TwoFactorService.is_rate_limited')
    def test_login_requires_2fa_for_untrusted_device(self, mock_rate, mock_get_device, mock_is_trusted):
        """Test 2FA is required for untrusted devices"""
        mock_get_device.return_value = TrustedDeviceToken(
            device_id='device-123',
            signed_value='signed-device-123'
        )
        mock_is_trusted.return_value = (False, None)
        mock_rate.return_value = False
        
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'testpass'
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['requires_2fa'] is True


@pytest.mark.django_db
class TestTwoFactorVerifyLogin:
    """Test 2FA verification during login"""
    
    def setup_method(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
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
class TestRememberMeFeature:
    """Test remember me (trusted device) feature during login"""
    
    def setup_method(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )
        self.twofa_settings = TwoFactorSettings.objects.create(
            user=self.user,
            is_enabled=True,
            preferred_method='totp'
        )
    
    @patch('mysite.auth.services.trusted_device_service.TrustedDeviceService.add_trusted_device')
    @patch('mysite.auth.services.twofa_service.TwoFactorService.verify_totp')
    def test_remember_me_creates_trusted_device(self, mock_verify, mock_add_device):
        """Test remember_me creates a trusted device"""
        mock_verify.return_value = True
        mock_device = Mock()
        mock_device.device_id = 'new-device-123'
        mock_token = TrustedDeviceToken(device_id='new-device-123', signed_value='signed-new-device-123')
        mock_add_device.return_value = (mock_device, mock_token, True)
        
        partial_token = generate_partial_token(self.user)
        
        response = self.client.post('/api/auth/2fa/verify-login/', {
            'code': '123456',
            'partial_token': partial_token,
            'remember_me': True
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['trusted_device'] is True
        mock_add_device.assert_called_once()
        
        # Check device_id cookie is set
        assert 'device_id' in response.cookies
    
    @patch('mysite.auth.services.twofa_service.TwoFactorService.verify_totp')
    def test_without_remember_me_no_device_created(self, mock_verify):
        """Test without remember_me, no trusted device is created"""
        mock_verify.return_value = True
        partial_token = generate_partial_token(self.user)
        
        response = self.client.post('/api/auth/2fa/verify-login/', {
            'code': '123456',
            'partial_token': partial_token,
            'remember_me': False
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['trusted_device'] is False
        
        # No trusted devices should be created
        assert TrustedDevice.objects.filter(user=self.user).count() == 0


@pytest.mark.django_db
class TestCompleteLoginFlow:
    """Integration tests for complete login flows"""
    
    def setup_method(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
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
            'username': 'testuser',
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
            'username': 'testuser',
            'password': 'testpass'
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert 'tokens' in response.data
        assert 'user' in response.data
        assert 'requires_2fa' not in response.data
