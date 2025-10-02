"""Tests for Two-Factor Authentication"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from auth.models import TwoFactorSettings, TwoFactorCode, RecoveryCode, TrustedDevice
from auth.services.twofa_service import TwoFactorService

User = get_user_model()


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
        user = User.objects.create_user(username='testuser', password='testpass')
        codes = TwoFactorService.generate_recovery_codes(user, count=10)
        
        assert len(codes) == 10
        for code in codes:
            assert isinstance(code, RecoveryCode)
            assert len(code.code) == 14  # XXXX-XXXX-XXXX format
            assert not code.is_used


@pytest.mark.django_db
class TestTwoFactorSetupView:
    """Test 2FA setup endpoint"""
    
    def test_totp_setup(self):
        """Test TOTP setup"""
        user = User.objects.create_user(username='testuser', password='testpass')
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.post('/api/auth/2fa/setup/', {'method': 'totp'})
        
        assert response.status_code == 200
        assert 'qr_code' in response.data
        assert 'secret' in response.data
        assert response.data['method'] == 'totp'
        
        # Check settings were created
        settings = TwoFactorSettings.objects.get(user=user)
        assert settings.totp_secret is not None
        assert not settings.is_enabled  # Not enabled until verified
    
    def test_email_setup(self):
        """Test email 2FA setup"""
        user = User.objects.create_user(
            username='testuser',
            password='testpass',
            email='test@example.com'
        )
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.post('/api/auth/2fa/setup/', {'method': 'email'})
        
        assert response.status_code == 200
        assert response.data['method'] == 'email'
        assert 'expires_in' in response.data
        
        # Check OTP code was created
        code = TwoFactorCode.objects.filter(user=user, purpose='setup').first()
        assert code is not None
        assert len(code.code) == 6


@pytest.mark.django_db
class TestTwoFactorStatusView:
    """Test 2FA status endpoint"""
    
    def test_status_not_configured(self):
        """Test status when 2FA not configured"""
        user = User.objects.create_user(username='testuser', password='testpass')
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.get('/api/auth/2fa/status/')
        
        assert response.status_code == 200
        assert response.data['is_enabled'] is False
    
    def test_status_configured(self):
        """Test status when 2FA is configured"""
        user = User.objects.create_user(username='testuser', password='testpass')
        TwoFactorSettings.objects.create(
            user=user,
            is_enabled=True,
            preferred_method='totp'
        )
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.get('/api/auth/2fa/status/')
        
        assert response.status_code == 200
        assert response.data['is_enabled'] is True
        assert response.data['preferred_method'] == 'totp'


@pytest.mark.django_db
class TestRecoveryCodeGeneration:
    """Test recovery code generation"""
    
    def test_generate_recovery_codes(self):
        """Test recovery code generation endpoint"""
        user = User.objects.create_user(username='testuser', password='testpass')
        TwoFactorSettings.objects.create(
            user=user,
            is_enabled=True,
            preferred_method='totp'
        )
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.post('/api/auth/2fa/recovery-codes/generate/')
        
        assert response.status_code == 200
        assert 'recovery_codes' in response.data
        assert len(response.data['recovery_codes']) == 10
        
        # Check codes were created in database
        codes = RecoveryCode.objects.filter(user=user, is_used=False)
        assert codes.count() == 10


@pytest.mark.django_db
class TestTrustedDevices:
    """Test trusted device management"""
    
    def test_list_trusted_devices(self):
        """Test listing trusted devices"""
        user = User.objects.create_user(username='testuser', password='testpass')
        
        # Create a trusted device
        from datetime import timedelta
        from django.utils import timezone
        TrustedDevice.objects.create(
            user=user,
            device_id='test-device-id',
            device_name='Test Browser',
            ip_address='127.0.0.1',
            user_agent='Test Agent',
            expires_at=timezone.now() + timedelta(days=30)
        )
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        response = client.get('/api/auth/2fa/trusted-devices/')
        
        assert response.status_code == 200
        assert 'devices' in response.data
        assert len(response.data['devices']) == 1
        assert response.data['devices'][0]['device_name'] == 'Test Browser'
