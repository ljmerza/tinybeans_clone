"""API tests for 2FA endpoints - no external dependencies"""
import pytest
from unittest.mock import patch, Mock
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from auth.models import (
    TwoFactorSettings,
    TwoFactorCode,
    RecoveryCode,
    TrustedDevice,
    TwoFactorAuditLog,
)

User = get_user_model()


def response_payload(response):
    """Helper to unwrap success_response format."""
    data = response.data
    if isinstance(data, dict) and 'data' in data:
        return data['data']
    return data


@pytest.mark.django_db
class TestTwoFactorSetupAPI:
    """Test 2FA setup API endpoint"""
    
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
    
    @patch('auth.services.twofa_service.TwoFactorService.send_otp')
    @patch('auth.services.twofa_service.TwoFactorService.is_rate_limited')
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
    
    @patch('auth.services.twofa_service.TwoFactorService.is_rate_limited')
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


@pytest.mark.django_db
class TestTwoFactorVerifySetupAPI:
    """Test 2FA setup verification endpoint"""
    
    def setup_method(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )
        self.client.force_authenticate(user=self.user)
    
    @patch('auth.services.twofa_service.TwoFactorService.verify_totp')
    @patch('auth.services.twofa_service.TwoFactorService.generate_recovery_codes')
    @patch('emails.mailers.TwoFactorMailer.send_2fa_enabled_notification')
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
    
    @patch('auth.services.twofa_service.TwoFactorService.verify_otp')
    @patch('auth.services.twofa_service.TwoFactorService.generate_recovery_codes')
    @patch('emails.mailers.TwoFactorMailer.send_2fa_enabled_notification')
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
    
    @patch('auth.services.twofa_service.TwoFactorService.verify_totp')
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
        assert 'not initialized' in response.data['error'].lower()


@pytest.mark.django_db
class TestTwoFactorStatusAPI:
    """Test 2FA status endpoint"""
    
    def setup_method(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_status_not_configured(self):
        """Test status when 2FA not configured"""
        response = self.client.get('/api/auth/2fa/status/')
        
        assert response.status_code == status.HTTP_200_OK
        payload = response_payload(response)
        assert payload['is_enabled'] is False
        assert payload['preferred_method'] is None
    
    def test_status_configured_disabled(self):
        """Test status when 2FA configured but disabled"""
        TwoFactorSettings.objects.create(
            user=self.user,
            is_enabled=False,
            preferred_method='totp'
        )
        
        response = self.client.get('/api/auth/2fa/status/')
        
        assert response.status_code == status.HTTP_200_OK
        payload = response_payload(response)
        assert payload['is_enabled'] is False
        assert payload['preferred_method'] == 'totp'
    
    def test_status_configured_enabled(self):
        """Test status when 2FA enabled"""
        TwoFactorSettings.objects.create(
            user=self.user,
            is_enabled=True,
            preferred_method='email'
        )
        
        response = self.client.get('/api/auth/2fa/status/')
        
        assert response.status_code == status.HTTP_200_OK
        payload = response_payload(response)
        assert payload['is_enabled'] is True
        assert payload['preferred_method'] == 'email'


@pytest.mark.django_db
class TestTwoFactorDisableAPI:
    """Test 2FA disable endpoint"""
    
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
    def test_disable_success(self, mock_email, mock_verify):
        """Test successful 2FA disable"""
        TwoFactorSettings.objects.create(
            user=self.user,
            is_enabled=True,
            preferred_method='totp',
            totp_secret='JBSWY3DPEHPK3PXP'
        )
        
        mock_verify.return_value = True
        
        response = self.client.post('/api/auth/2fa/disable/', {
            'code': '123456'
        })
        
        assert response.status_code == status.HTTP_200_OK
        payload = response_payload(response)
        assert payload['enabled'] is False
        
        # Verify 2FA is disabled
        self.user.twofa_settings.refresh_from_db()
        assert not self.user.twofa_settings.is_enabled
    
    @patch('auth.services.twofa_service.TwoFactorService.verify_totp')
    @patch('auth.services.twofa_service.TwoFactorService.verify_recovery_code')
    @patch('emails.mailers.TwoFactorMailer.send_2fa_disabled_notification')
    def test_disable_with_recovery_code(self, mock_email, mock_recovery, mock_verify):
        """Test disable with recovery code"""
        TwoFactorSettings.objects.create(
            user=self.user,
            is_enabled=True,
            preferred_method='totp'
        )
        
        mock_verify.return_value = False
        mock_recovery.return_value = True
        
        response = self.client.post('/api/auth/2fa/disable/', {
            'code': 'ABCD-EFGH-IJKL'
        })
        
        assert response.status_code == status.HTTP_200_OK
        payload = response_payload(response)
        assert payload['enabled'] is False
    
    def test_disable_not_enabled(self):
        """Test disable when 2FA not enabled"""
        TwoFactorSettings.objects.create(
            user=self.user,
            is_enabled=False
        )
        
        response = self.client.post('/api/auth/2fa/disable/', {
            'code': '123456'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_disable_not_configured(self):
        """Test disable when 2FA not configured"""
        response = self.client.post('/api/auth/2fa/disable/', {
            'code': '123456'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestTwoFactorMethodRemovalAPI:
    """Test removing individual 2FA methods"""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='methoduser',
            email='method@example.com',
            password='testpass',
        )
        self.client.force_authenticate(user=self.user)

    def test_remove_totp_with_sms_fallback(self):
        settings_obj = TwoFactorSettings.objects.create(
            user=self.user,
            is_enabled=True,
            preferred_method='totp',
            totp_secret='JBSWY3DPEHPK3PXP',
            phone_number='+1234567890',
            sms_verified=True,
        )

        response = self.client.delete('/api/auth/2fa/methods/totp/')

        assert response.status_code == status.HTTP_200_OK
        payload = response_payload(response)
        assert payload['status']['preferred_method'] == 'sms'
        assert payload['status']['has_totp'] is False
        assert payload['status']['has_sms'] is True
        assert payload['preferred_method_changed'] is True
        assert payload['twofa_disabled'] is False

        settings_obj.refresh_from_db()
        assert settings_obj.totp_secret is None
        assert settings_obj.preferred_method == 'sms'
        assert settings_obj.is_enabled is True
        assert TwoFactorAuditLog.objects.filter(
            user=self.user,
            action='2fa_method_removed',
            method='totp',
        ).exists()

    def test_remove_totp_without_fallback_disables(self):
        settings_obj = TwoFactorSettings.objects.create(
            user=self.user,
            is_enabled=True,
            preferred_method='totp',
            totp_secret='JBSWY3DPEHPK3PXP',
        )

        response = self.client.delete('/api/auth/2fa/methods/totp/')

        assert response.status_code == status.HTTP_200_OK
        payload = response_payload(response)
        assert payload['twofa_disabled'] is True
        assert payload['status']['is_enabled'] is False
        assert payload['status']['has_totp'] is False

        settings_obj.refresh_from_db()
        assert settings_obj.totp_secret is None
        assert settings_obj.is_enabled is False

    def test_remove_sms_with_totp_fallback(self):
        settings_obj = TwoFactorSettings.objects.create(
            user=self.user,
            is_enabled=True,
            preferred_method='sms',
            totp_secret='JBSWY3DPEHPK3PXP',
            phone_number='+1234567890',
            sms_verified=True,
        )

        response = self.client.delete('/api/auth/2fa/methods/sms/')

        assert response.status_code == status.HTTP_200_OK
        payload = response_payload(response)
        assert payload['status']['preferred_method'] == 'totp'
        assert payload['status']['has_sms'] is False
        assert payload['preferred_method_changed'] is True
        assert payload['twofa_disabled'] is False

        settings_obj.refresh_from_db()
        assert settings_obj.phone_number is None
        assert settings_obj.sms_verified is False
        assert settings_obj.preferred_method == 'totp'
        assert settings_obj.is_enabled is True

    def test_remove_sms_without_fallback_disables(self):
        settings_obj = TwoFactorSettings.objects.create(
            user=self.user,
            is_enabled=True,
            preferred_method='sms',
            phone_number='+1234567890',
            sms_verified=True,
        )

        response = self.client.delete('/api/auth/2fa/methods/sms/')

        assert response.status_code == status.HTTP_200_OK
        payload = response_payload(response)
        assert payload['twofa_disabled'] is True
        assert payload['status']['is_enabled'] is False
        assert payload['status']['has_sms'] is False

        settings_obj.refresh_from_db()
        assert settings_obj.phone_number is None
        assert settings_obj.sms_verified is False
        assert settings_obj.is_enabled is False

    def test_remove_totp_not_configured(self):
        TwoFactorSettings.objects.create(
            user=self.user,
            is_enabled=False,
            preferred_method='sms',
        )

        response = self.client.delete('/api/auth/2fa/methods/totp/')

        payload = response_payload(response)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'not configured' in response.data['error'].lower()

    def test_remove_sms_not_configured(self):
        TwoFactorSettings.objects.create(
            user=self.user,
            is_enabled=True,
            preferred_method='totp',
            totp_secret='JBSWY3DPEHPK3PXP',
        )

        response = self.client.delete('/api/auth/2fa/methods/sms/')

        payload = response_payload(response)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'not configured' in response.data['error'].lower()

    def test_remove_method_without_settings(self):
        self.client.force_authenticate(user=None)
        # ensure authentication is required
        response = self.client.delete('/api/auth/2fa/methods/totp/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        payload = response_payload(response)

        # Re-authenticate and try without settings
        self.client.force_authenticate(user=self.user)
        response = self.client.delete('/api/auth/2fa/methods/totp/')

        payload = response_payload(response)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'not configured' in response.data['error'].lower()

    def test_remove_email_not_supported(self):
        TwoFactorSettings.objects.create(
            user=self.user,
            is_enabled=True,
            preferred_method='email',
        )

        response = self.client.delete('/api/auth/2fa/methods/email/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'cannot be removed' in response.data['error'].lower()


@pytest.mark.django_db
class TestRecoveryCodeAPI:
    """Test recovery code endpoints"""
    
    def setup_method(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.client.force_authenticate(user=self.user)
    
    @patch('auth.services.twofa_service.TwoFactorService.generate_recovery_codes')
    def test_generate_recovery_codes_success(self, mock_generate):
        """Test recovery code generation"""
        TwoFactorSettings.objects.create(
            user=self.user,
            is_enabled=True
        )
        
        mock_codes = [f'CODE-{i:04d}-TEST' for i in range(10)]
        mock_generate.return_value = mock_codes
        
        response = self.client.post('/api/auth/2fa/recovery-codes/generate/')
        
        assert response.status_code == status.HTTP_200_OK
        payload = response_payload(response)
        assert len(payload['recovery_codes']) == 10
    
    def test_generate_recovery_codes_not_enabled(self):
        """Test recovery code generation when 2FA not enabled"""
        TwoFactorSettings.objects.create(
            user=self.user,
            is_enabled=False
        )
        
        response = self.client.post('/api/auth/2fa/recovery-codes/generate/')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_download_recovery_codes_txt(self):
        """Test downloading recovery codes as TXT"""
        TwoFactorSettings.objects.create(
            user=self.user,
            is_enabled=True
        )
        
        # Create recovery codes - these will be sent in the request body
        codes = [f'CODE-{i:04d}-TEST' for i in range(5)]
        for code in codes:
            RecoveryCode.objects.create(
                user=self.user,
                code=code
            )
        
        response = self.client.post(
            '/api/auth/2fa/recovery-codes/download/',
            {'format': 'txt', 'codes': codes},
            content_type='application/json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response['Content-Type'] == 'text/plain'
        assert 'tinybeans-recovery-codes.txt' in response['Content-Disposition']
    
    @patch('auth.services.recovery_code_service.RecoveryCodeService.export_as_pdf')
    def test_download_recovery_codes_pdf(self, mock_pdf):
        """Test downloading recovery codes as PDF"""
        TwoFactorSettings.objects.create(
            user=self.user,
            is_enabled=True
        )
        
        # Create recovery codes - these will be sent in the request body
        codes = [f'CODE-{i:04d}-TEST' for i in range(5)]
        for code in codes:
            RecoveryCode.objects.create(
                user=self.user,
                code=code
            )
        
        mock_pdf.return_value = b'fake-pdf-content'
        
        response = self.client.post(
            '/api/auth/2fa/recovery-codes/download/',
            {'format': 'pdf', 'codes': codes},
            content_type='application/json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response['Content-Type'] == 'application/pdf'
        assert 'tinybeans-recovery-codes.pdf' in response['Content-Disposition']
    
    def test_download_no_codes(self):
        """Test download when no codes available"""
        response = self.client.post(
            '/api/auth/2fa/recovery-codes/download/',
            {'format': 'txt', 'codes': []},
            content_type='application/json'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestTrustedDevicesAPI:
    """Test trusted devices endpoints"""
    
    def setup_method(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_list_trusted_devices(self):
        """Test listing trusted devices"""
        # Create devices
        for i in range(3):
            TrustedDevice.objects.create(
                user=self.user,
                device_id=f'device-{i}',
                device_name=f'Device {i}',
                ip_address='127.0.0.1',
                user_agent='TestBrowser',
                expires_at=timezone.now() + timedelta(days=30)
            )
        
        response = self.client.get('/api/auth/2fa/trusted-devices/')
        
        assert response.status_code == status.HTTP_200_OK
        payload = response_payload(response)
        assert len(payload['devices']) == 3
    
    def test_list_trusted_devices_empty(self):
        """Test listing when no devices"""
        response = self.client.get('/api/auth/2fa/trusted-devices/')
        
        assert response.status_code == status.HTTP_200_OK
        payload = response_payload(response)
        assert len(payload['devices']) == 0
    
    @patch('auth.services.trusted_device_service.TrustedDeviceService.remove_trusted_device')
    def test_remove_trusted_device_success(self, mock_remove):
        """Test removing trusted device"""
        mock_remove.return_value = True
        
        response = self.client.delete('/api/auth/2fa/trusted-devices/', {
            'device_id': 'test-device-123'
        })
        
        assert response.status_code == status.HTTP_200_OK
    
    @patch('auth.services.trusted_device_service.TrustedDeviceService.remove_trusted_device')
    def test_remove_trusted_device_not_found(self, mock_remove):
        """Test removing non-existent device"""
        mock_remove.return_value = False
        
        response = self.client.delete('/api/auth/2fa/trusted-devices/', {
            'device_id': 'non-existent'
        })
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_remove_trusted_device_missing_id(self):
        """Test remove without device_id"""
        response = self.client.delete('/api/auth/2fa/trusted-devices/', {})
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @patch('auth.services.trusted_device_service.TrustedDeviceService.remove_trusted_device')
    def test_remove_by_path_success(self, mock_remove):
        """Test removing device by URL path"""
        mock_remove.return_value = True
        
        response = self.client.delete('/api/auth/2fa/trusted-devices/test-device-123/')
        
        assert response.status_code == status.HTTP_200_OK
