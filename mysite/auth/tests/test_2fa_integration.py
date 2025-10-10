"""Integration tests for complete 2FA flows"""
import hashlib
import pytest
from unittest.mock import patch, Mock
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from rest_framework.test import APIClient
from rest_framework import status

from auth.models import (
    TwoFactorSettings,
    TwoFactorCode,
    RecoveryCode,
    TrustedDevice,
    TwoFactorAuditLog
)
from auth.services.trusted_device_service import TrustedDeviceService

User = get_user_model()


def recovery_hash(value: str) -> str:
    """Helper to compute recovery code hash."""
    return hashlib.sha256(value.encode()).hexdigest()


@pytest.mark.django_db
class TestCompleteTOTPFlow:
    """Test complete TOTP setup and usage flow"""
    
    def setup_method(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )
        self.client.force_authenticate(user=self.user)
    
    @patch('auth.services.twofa_service.TwoFactorService.generate_totp_qr_code')
    @patch('auth.services.twofa_service.TwoFactorService.generate_totp_secret')
    @patch('auth.services.twofa_service.TwoFactorService.verify_totp')
    @patch('emails.mailers.TwoFactorMailer.send_2fa_enabled_notification')
    def test_complete_totp_setup_flow(self, mock_email, mock_verify, mock_secret, mock_qr):
        """Test complete TOTP setup flow from start to finish"""
        # Step 1: Initiate setup
        mock_secret.return_value = 'JBSWY3DPEHPK3PXP'
        mock_qr.return_value = {
            'uri': 'otpauth://totp/test',
            'qr_code_image': 'data:image/png;base64,test',
            'secret': 'JBSWY3DPEHPK3PXP'
        }
        
        setup_response = self.client.post('/api/auth/2fa/setup/', {
            'method': 'totp'
        })
        
        assert setup_response.status_code == status.HTTP_200_OK
        assert 'qr_code' in setup_response.data
        
        # Step 2: Check status (should be disabled)
        status_response = self.client.get('/api/auth/2fa/status/')
        assert status_response.data['is_enabled'] is False
        
        # Step 3: Verify setup with code
        mock_verify.return_value = True
        verify_response = self.client.post('/api/auth/2fa/verify-setup/', {
            'code': '123456'
        })
        
        assert verify_response.status_code == status.HTTP_200_OK
        assert verify_response.data['enabled'] is True
        assert 'recovery_codes' in verify_response.data
        
        # Step 4: Check status again (should be enabled)
        status_response2 = self.client.get('/api/auth/2fa/status/')
        assert status_response2.data['is_enabled'] is True
        assert status_response2.data['preferred_method'] == 'totp'
        
        # Verify audit log entries
        audit_logs = TwoFactorAuditLog.objects.filter(user=self.user)
        assert audit_logs.count() > 0
        assert audit_logs.filter(action='2fa_enabled').exists()


@pytest.mark.django_db
class TestCompleteEmailFlow:
    """Test complete email 2FA flow"""
    
    def setup_method(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )
        self.client.force_authenticate(user=self.user)
    
    @patch('auth.services.twofa_service.TwoFactorService.generate_otp', return_value='654321')
    @patch('emails.mailers.TwoFactorMailer.send_2fa_code')
    @patch('auth.services.twofa_service.TwoFactorService.is_rate_limited')
    @patch('emails.mailers.TwoFactorMailer.send_2fa_enabled_notification')
    def test_complete_email_setup_flow(self, mock_notif, mock_rate, mock_send, mock_generate):
        """Test complete email 2FA setup flow"""
        mock_rate.return_value = False
        
        # Step 1: Initiate setup
        setup_response = self.client.post('/api/auth/2fa/setup/', {
            'method': 'email'
        })
        
        assert setup_response.status_code == status.HTTP_200_OK
        
        # Verify OTP code was created
        code_obj = TwoFactorCode.objects.filter(
            user=self.user,
            purpose='setup'
        ).first()
        assert code_obj is not None
        
        # Step 2: Verify with correct code
        verify_response = self.client.post('/api/auth/2fa/verify-setup/', {
            'code': '654321'
        })
        
        assert verify_response.status_code == status.HTTP_200_OK
        assert verify_response.data['enabled'] is True
        
        # Verify settings
        settings = TwoFactorSettings.objects.get(user=self.user)
        assert settings.is_enabled
        assert settings.preferred_method == 'email'


@pytest.mark.django_db
class TestRecoveryCodeFlow:
    """Test recovery code generation and usage"""
    
    def setup_method(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.client.force_authenticate(user=self.user)
        
        # Enable 2FA
        TwoFactorSettings.objects.create(
            user=self.user,
            is_enabled=True,
            preferred_method='totp'
        )
    
    def test_recovery_code_lifecycle(self):
        """Test generating, downloading, and using recovery codes"""
        # Step 1: Generate recovery codes
        gen_response = self.client.post('/api/auth/2fa/recovery-codes/generate/')
        
        assert gen_response.status_code == status.HTTP_200_OK
        assert len(gen_response.data['recovery_codes']) == 10
        
        # Get recovery codes
        recovery_codes = gen_response.data['recovery_codes']
        first_code = recovery_codes[0]
        
        # Step 2: Download recovery codes (TXT) - using POST with codes in body
        download_response = self.client.post(
            '/api/auth/2fa/recovery-codes/download/',
            {'format': 'txt', 'codes': recovery_codes},
            content_type='application/json'
        )
        
        assert download_response.status_code == status.HTTP_200_OK
        assert first_code in download_response.content.decode()
        
        # Step 3: Verify code is unused
        code_obj = RecoveryCode.objects.get(code_hash=recovery_hash(first_code))
        assert not code_obj.is_used
        
        # Step 4: Use recovery code
        from auth.services.twofa_service import TwoFactorService
        result = TwoFactorService.verify_recovery_code(self.user, first_code)
        
        assert result is True
        code_obj.refresh_from_db()
        assert code_obj.is_used
        assert code_obj.used_at is not None
        
        # Step 5: Try to reuse same code
        result2 = TwoFactorService.verify_recovery_code(self.user, first_code)
        assert result2 is False
    
    def test_regenerate_recovery_codes(self):
        """Test regenerating recovery codes invalidates old ones"""
        # Generate first batch
        gen_response1 = self.client.post('/api/auth/2fa/recovery-codes/generate/')
        old_codes = gen_response1.data['recovery_codes']
        
        # Generate second batch
        gen_response2 = self.client.post('/api/auth/2fa/recovery-codes/generate/')
        new_codes = gen_response2.data['recovery_codes']
        
        # Old codes should not exist
        for old_code in old_codes:
            assert not RecoveryCode.objects.filter(
                code_hash=recovery_hash(old_code),
                is_used=False
            ).exists()
        
        # New codes should exist
        for new_code in new_codes:
            assert RecoveryCode.objects.filter(
                code_hash=recovery_hash(new_code),
                is_used=False
            ).exists()


@pytest.mark.django_db
class TestTrustedDeviceFlow:
    """Test trusted device management flow"""
    
    def setup_method(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_trusted_device_lifecycle(self):
        """Test adding, listing, and removing trusted devices"""
        # Step 1: Add trusted devices
        factory = RequestFactory()
        for _ in range(3):
            request = factory.get('/')
            request.META['HTTP_USER_AGENT'] = 'TestBrowser/1.0'
            request.META['REMOTE_ADDR'] = '127.0.0.1'
            TrustedDeviceService.add_trusted_device(self.user, request)
        
        # Step 2: List devices
        list_response = self.client.get('/api/auth/2fa/trusted-devices/')
        
        assert list_response.status_code == status.HTTP_200_OK
        assert len(list_response.data['devices']) == 3
        
        # Step 3: Remove one device
        device_id = list_response.data['devices'][0]['device_id']
        remove_response = self.client.delete('/api/auth/2fa/trusted-devices/', {
            'device_id': device_id
        })
        
        assert remove_response.status_code == status.HTTP_200_OK
        
        # Step 4: List devices again (should have 2)
        list_response2 = self.client.get('/api/auth/2fa/trusted-devices/')
        assert len(list_response2.data['devices']) == 2
        
        # Verify audit log
        log = TwoFactorAuditLog.objects.filter(
            user=self.user,
            action='trusted_device_removed'
        ).first()
        assert log is not None


@pytest.mark.django_db
class TestDisableFlow:
    """Test 2FA disable flow"""
    
    def setup_method(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.client.force_authenticate(user=self.user)
    
    @patch('auth.services.twofa_service.TwoFactorService.verify_totp')
    @patch('emails.mailers.TwoFactorMailer.send_2fa_disabled_notification')
    def test_disable_with_totp(self, mock_email, mock_verify):
        """Test disabling 2FA with TOTP code"""
        # Enable 2FA
        TwoFactorSettings.objects.create(
            user=self.user,
            is_enabled=True,
            preferred_method='totp',
            totp_secret='JBSWY3DPEHPK3PXP'
        )
        
        # Verify status
        status_response = self.client.get('/api/auth/2fa/status/')
        assert status_response.data['is_enabled'] is True
        
        # Disable with code
        mock_verify.return_value = True
        disable_response = self.client.post('/api/auth/2fa/disable/', {
            'code': '123456'
        })
        
        assert disable_response.status_code == status.HTTP_200_OK
        assert disable_response.data['enabled'] is False
        
        # Verify status again
        status_response2 = self.client.get('/api/auth/2fa/status/')
        assert status_response2.data['is_enabled'] is False
        
        # Verify audit log
        log = TwoFactorAuditLog.objects.filter(
            user=self.user,
            action='2fa_disabled'
        ).first()
        assert log is not None
    
    @patch('auth.services.twofa_service.TwoFactorService.verify_totp')
    @patch('emails.mailers.TwoFactorMailer.send_2fa_disabled_notification')
    def test_disable_with_recovery_code(self, mock_email, mock_verify):
        """Test disabling 2FA with recovery code"""
        # Enable 2FA and create recovery codes
        TwoFactorSettings.objects.create(
            user=self.user,
            is_enabled=True,
            preferred_method='totp'
        )
        
        plain_code = 'ABCD-EFGH-IJKL'
        RecoveryCode.create_recovery_code(self.user, plain_code)
        recovery_code = RecoveryCode.objects.get(code_hash=recovery_hash(plain_code))
        
        # Try with wrong TOTP
        mock_verify.return_value = False
        
        # Disable with recovery code
        disable_response = self.client.post('/api/auth/2fa/disable/', {
            'code': plain_code
        })
        
        assert disable_response.status_code == status.HTTP_200_OK
        
        # Verify recovery code was used
        recovery_code.refresh_from_db()
        assert recovery_code.is_used


@pytest.mark.django_db
class TestRateLimitingFlow:
    """Test rate limiting behavior"""
    
    def setup_method(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )
        self.client.force_authenticate(user=self.user)
    
    @patch('emails.mailers.TwoFactorMailer.send_2fa_code')
    def test_rate_limiting_enforced(self, mock_send):
        """Test rate limiting prevents excessive requests"""
        # Make requests up to limit
        for i in range(3):
            response = self.client.post('/api/auth/2fa/setup/', {
                'method': 'email'
            })
            assert response.status_code == status.HTTP_200_OK
        
        # Next request should be rate limited
        response = self.client.post('/api/auth/2fa/setup/', {
            'method': 'email'
        })
        
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
