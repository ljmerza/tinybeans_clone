"""API tests for 2FA status, disable, and method-removal endpoints."""

import pytest
from unittest.mock import patch
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from mysite.auth.models import TwoFactorAuditLog, TwoFactorSettings
from .helpers import response_payload

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestTwoFactorStatusAPI:
    """Test 2FA status endpoint"""
    
    def setup_method(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(email='testuser@example.com', password='testpass')
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


class TestTwoFactorDisableAPI:
    """Test 2FA disable endpoint"""
    
    def setup_method(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(email='testuser@example.com', password='testpass')
        self.client.force_authenticate(user=self.user)
    
    @patch('mysite.auth.services.twofa_service.TwoFactorService.verify_totp')
    @patch('mysite.emails.mailers.TwoFactorMailer.send_2fa_disabled_notification')
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
    
    @patch('mysite.auth.services.twofa_service.TwoFactorService.verify_totp')
    @patch('mysite.auth.services.twofa_service.TwoFactorService.verify_recovery_code')
    @patch('mysite.emails.mailers.TwoFactorMailer.send_2fa_disabled_notification')
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


class TestTwoFactorMethodRemovalAPI:
    """Test removing individual 2FA methods"""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='method@example.com', password='testpass')
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
