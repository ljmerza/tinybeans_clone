"""Tests for Two-Factor Authentication"""
import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from rest_framework.test import APIClient

from mysite.auth.models import TwoFactorSettings, TwoFactorCode, RecoveryCode, TrustedDevice
from mysite.auth.services.twofa_service import TwoFactorService
from mysite.auth.services.trusted_device_service import TrustedDeviceService

User = get_user_model()


def create_user(username='testuser', email=None, password='testpass'):
    """Utility helper to satisfy required email field on custom user model."""
    if email is None:
        email = f"{username}@example.com"
    return User.objects.create_user(
        email=email,
        password=password,
        first_name=username.title(),
        last_name='User',
    )


def response_payload(response):
    """Extract payload from success_response wrapper."""
    data = response.data
    if isinstance(data, dict) and 'data' in data:
        return data['data']
    return data


@pytest.mark.django_db
class TestTwoFactorService:
    """Test TwoFactorService methods"""
    
    def test_generate_otp(self):
        """Test OTP generation"""
        otp = TwoFactorService.generate_otp()
        assert len(otp) == 6
        assert otp.isdigit()
    
    def test_generate_totp_secret(self):
        """Test TOTP secret generation"""
        secret = TwoFactorService.generate_totp_secret()
        assert len(secret) == 32
        assert secret.isalnum()
    
    def test_generate_recovery_codes(self):
        """Test recovery code generation"""
        user = create_user()
        codes = TwoFactorService.generate_recovery_codes(user, count=10)
        
        assert len(codes) == 10
        for code in codes:
            assert isinstance(code, str)
            assert len(code) == 14  # XXXX-XXXX-XXXX format
            assert code.count('-') == 2
        # Ensure hashed codes persisted
        assert RecoveryCode.objects.filter(user=user, is_used=False).count() == 10


@pytest.mark.django_db
class TestTwoFactorSetupView:
    """Test 2FA setup endpoint"""
    
    def test_totp_setup(self):
        """Test TOTP setup"""
        user = create_user()
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.post('/api/auth/2fa/setup/', {'method': 'totp'})
        
        assert response.status_code == 200
        payload = response_payload(response)
        assert 'qr_code' in payload
        assert 'secret' in payload
        assert payload['method'] == 'totp'
        
        # Check settings were created
        settings = TwoFactorSettings.objects.get(user=user)
        assert settings.totp_secret is not None
        assert not settings.is_enabled  # Not enabled until verified
    
    def test_email_setup(self):
        """Test email 2FA setup"""
        user = create_user(email='test@example.com')
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.post('/api/auth/2fa/setup/', {'method': 'email'})
        
        assert response.status_code == 200
        payload = response_payload(response)
        assert payload['method'] == 'email'
        assert 'expires_in' in payload
        
        # Check OTP code was created
        code = TwoFactorCode.objects.filter(user=user, purpose='setup').first()
        assert code is not None
        assert len(code.code_preview or '') == 6


@pytest.mark.django_db
class TestTwoFactorStatusView:
    """Test 2FA status endpoint"""
    
    def test_status_not_configured(self):
        """Test status when 2FA not configured"""
        user = create_user()
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.get('/api/auth/2fa/status/')
        
        assert response.status_code == 200
        payload = response_payload(response)
        assert payload['is_enabled'] is False
    
    def test_status_configured(self):
        """Test status when 2FA is configured"""
        user = create_user()
        settings_obj = TwoFactorSettings.objects.create(
            user=user,
            is_enabled=True,
            preferred_method='totp'
        )
        settings_obj.totp_secret = TwoFactorService.generate_totp_secret()
        settings_obj.totp_verified = True
        settings_obj.save(update_fields=['_totp_secret_encrypted', 'totp_verified'])
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.get('/api/auth/2fa/status/')
        
        assert response.status_code == 200
        payload = response_payload(response)
        assert payload['is_enabled'] is True
        assert payload['preferred_method'] == 'totp'


@pytest.mark.django_db
class TestRecoveryCodeGeneration:
    """Test recovery code generation"""
    
    def test_generate_recovery_codes(self):
        """Test recovery code generation endpoint"""
        user = create_user()
        TwoFactorSettings.objects.create(
            user=user,
            is_enabled=True,
            preferred_method='totp'
        )
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.post('/api/auth/2fa/recovery-codes/generate/')
        
        assert response.status_code == 200
        payload = response_payload(response)
        assert 'recovery_codes' in payload
        assert len(payload['recovery_codes']) == 10
        
        # Check codes were created in database
        codes = RecoveryCode.objects.filter(user=user, is_used=False)
        assert codes.count() == 10


@pytest.mark.django_db
class TestTrustedDevices:
    """Test trusted device management"""
    
    def test_list_trusted_devices(self):
        """Test listing trusted devices"""
        user = create_user()
        
        # Create a trusted device
        factory = RequestFactory()
        request = factory.get('/')
        request.META['HTTP_USER_AGENT'] = 'Test Agent'
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        TrustedDeviceService.add_trusted_device(user, request)
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.get('/api/auth/2fa/trusted-devices/')
        
        assert response.status_code == 200
        payload = response_payload(response)
        assert 'devices' in payload
        assert len(payload['devices']) == 1
        assert payload['devices'][0]['device_name']
