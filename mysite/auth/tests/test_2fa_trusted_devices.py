"""Tests for 2FA login with trusted devices"""
import pytest
from unittest.mock import patch, Mock
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from mysite.auth.models import TwoFactorSettings, TrustedDevice
from mysite.auth.token_utils import generate_partial_token
from mysite.auth.services.trusted_device_service import TrustedDeviceToken

User = get_user_model()


@pytest.mark.django_db
class TestLoginWithTrustedDevice:
    """Test login flow with trusted devices"""

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
            'email': 'test@example.com',
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
            'email': 'test@example.com',
            'password': 'testpass'
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data['requires_2fa'] is True


@pytest.mark.django_db
class TestRememberMeFeature:
    """Test remember me (trusted device) feature during login"""

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
