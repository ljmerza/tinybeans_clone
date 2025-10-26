"""API tests covering 2FA setup and verification endpoints."""

import pytest
from unittest.mock import Mock, patch
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from mysite.auth.models import TwoFactorSettings
from .helpers import response_payload

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestTwoFactorSetupAPI:
    """Test 2FA setup API endpoint"""
    
    def setup_method(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass'
        )
        self.client.force_authenticate(user=self.user)
    
    @patch('mysite.auth.services.twofa_service.TwoFactorService.generate_totp_qr_code')
    @patch('mysite.auth.services.twofa_service.TwoFactorService.generate_totp_secret')
    def test_setup_totp_success(self, mock_secret, mock_qr):
        """Test successful TOTP setup"""
        mock_secret.return_value = 'JBSWY3DPEHPK3PXP'
        mock_qr.return_value = {
            'uri': 'otpauth://totp/test',
            'qr_code_image': 'data:image/png;base64,test',
            'secret': 'JBSWY3DPEHPK3PXP'
        }
        
        response = self.client.post('/api/auth/2fa/setup/', {
            'method': 'totp'
        })
        
        assert response.status_code == status.HTTP_200_OK
        payload = response_payload(response)
        assert payload['method'] == 'totp'
        assert 'qr_code' in payload
        assert 'secret' in payload
        
        # Verify settings were created
        settings_obj = TwoFactorSettings.objects.get(user=self.user)
        assert settings_obj.totp_secret is not None
        assert not settings_obj.is_enabled
    
    @patch('mysite.auth.services.twofa_service.TwoFactorService.send_otp')
    @patch('mysite.auth.services.twofa_service.TwoFactorService.is_rate_limited')
    def test_setup_email_success(self, mock_rate_limit, mock_send):
        """Test successful email 2FA setup"""
        mock_rate_limit.return_value = False
        mock_code = Mock()
        mock_send.return_value = mock_code
        
        response = self.client.post('/api/auth/2fa/setup/', {
            'method': 'email'
        })
        
        assert response.status_code == status.HTTP_200_OK
        payload = response_payload(response)
        assert payload['method'] == 'email'
        assert 'expires_in' in payload
    
    @patch('mysite.auth.services.twofa_service.TwoFactorService.is_rate_limited')
    def test_setup_rate_limited(self, mock_rate_limit):
        """Test rate limiting on setup"""
        mock_rate_limit.return_value = True
        
        response = self.client.post('/api/auth/2fa/setup/', {
            'method': 'email'
        })
        
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    
    def test_setup_sms_missing_phone(self):
        """Test SMS setup without phone number"""
        response = self.client.post('/api/auth/2fa/setup/', {
            'method': 'sms'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        payload = response_payload(response)
        assert payload['error'] == 'phone_number_required'
    
    def test_setup_invalid_method(self):
        """Test setup with invalid method"""
        response = self.client.post('/api/auth/2fa/setup/', {
            'method': 'invalid'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_setup_unauthenticated(self):
        """Test setup requires authentication"""
        self.client.force_authenticate(user=None)
        
        response = self.client.post('/api/auth/2fa/setup/', {
            'method': 'totp'
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestTwoFactorVerifySetupAPI:
    """Test 2FA setup verification endpoint"""
    
    def setup_method(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass'
        )
        self.client.force_authenticate(user=self.user)
    
    @patch('mysite.auth.services.twofa_service.TwoFactorService.verify_totp')
    @patch('mysite.auth.services.twofa_service.TwoFactorService.generate_recovery_codes')
    @patch('mysite.emails.mailers.TwoFactorMailer.send_2fa_enabled_notification')
    def test_verify_setup_totp_success(self, mock_email, mock_codes, mock_verify):
        """Test successful TOTP setup verification"""
        # Create settings
        TwoFactorSettings.objects.create(
            user=self.user,
            preferred_method='totp',
            totp_secret='JBSWY3DPEHPK3PXP'
        )
        
        # Mock verification
        mock_verify.return_value = True
        
        # Mock recovery codes
        mock_recovery_codes = [
            f'CODE-{i:04d}-TEST' for i in range(10)
        ]
        mock_codes.return_value = mock_recovery_codes
        
        response = self.client.post('/api/auth/2fa/verify-setup/', {
            'code': '123456'
        })
        
        assert response.status_code == status.HTTP_200_OK
        payload = response_payload(response)
        assert payload['enabled'] is True
        assert payload['method'] == 'totp'
        assert len(payload['recovery_codes']) == 10
        
        # Verify 2FA is enabled
        self.user.twofa_settings.refresh_from_db()
        assert self.user.twofa_settings.is_enabled
    
    @patch('mysite.auth.services.twofa_service.TwoFactorService.verify_otp')
    @patch('mysite.auth.services.twofa_service.TwoFactorService.generate_recovery_codes')
    @patch('mysite.emails.mailers.TwoFactorMailer.send_2fa_enabled_notification')
    def test_verify_setup_email_success(self, mock_email, mock_codes, mock_verify):
        """Test successful email setup verification"""
        # Create settings
        TwoFactorSettings.objects.create(
            user=self.user,
            preferred_method='email'
        )
        
        mock_verify.return_value = True
        mock_codes.return_value = ['CODE-0000-TEST']
        
        response = self.client.post('/api/auth/2fa/verify-setup/', {
            'code': '123456'
        })
        
        assert response.status_code == status.HTTP_200_OK
        payload = response_payload(response)
        assert payload['enabled'] is True
    
    @patch('mysite.auth.services.twofa_service.TwoFactorService.verify_totp')
    def test_verify_setup_invalid_code(self, mock_verify):
        """Test setup verification with invalid code"""
        TwoFactorSettings.objects.create(
            user=self.user,
            preferred_method='totp',
            totp_secret='JBSWY3DPEHPK3PXP'
        )
        
        mock_verify.return_value = False
        
        response = self.client.post('/api/auth/2fa/verify-setup/', {
            'code': '999999'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'invalid' in response.data['error'].lower()
    
    def test_verify_setup_not_initialized(self):
        """Test verification without setup"""
        response = self.client.post('/api/auth/2fa/verify-setup/', {
            'code': '123456'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'not_initialized' in response.data['error'].lower()
