"""API tests for trusted device management endpoints."""

from datetime import timedelta

import pytest
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from mysite.auth.models import TrustedDevice
from mysite.auth.services.trusted_device_service import TrustedDeviceToken
from .helpers import response_payload

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestTrustedDevicesAPI:
    """Test trusted devices endpoints"""
    
    def setup_method(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(email='testuser@example.com', password='testpass')
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
    
    @patch('mysite.auth.services.trusted_device_service.TrustedDeviceService.remove_trusted_device')
    def test_remove_trusted_device_success(self, mock_remove):
        """Test removing trusted device"""
        mock_remove.return_value = True
        
        response = self.client.delete('/api/auth/2fa/trusted-devices/', {
            'device_id': 'test-device-123'
        })
        
        assert response.status_code == status.HTTP_200_OK
    
    @patch('mysite.auth.services.trusted_device_service.TrustedDeviceService.remove_trusted_device')
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
    
    @patch('mysite.auth.services.trusted_device_service.TrustedDeviceService.remove_trusted_device')
    def test_remove_by_path_success(self, mock_remove):
        """Test removing device by URL path"""
        mock_remove.return_value = True
        
        response = self.client.delete('/api/auth/2fa/trusted-devices/test-device-123/')
        
        assert response.status_code == status.HTTP_200_OK

    @patch('mysite.auth.services.trusted_device_service.TrustedDeviceService.set_trusted_device_cookie')
    @patch('mysite.auth.services.trusted_device_service.TrustedDeviceService.add_trusted_device')
    def test_add_trusted_device_success(self, mock_add, mock_set_cookie):
        """Test adding current device as trusted"""
        device = TrustedDevice.objects.create(
            user=self.user,
            device_id='device-123',
            device_name='Test Device',
            ip_address='127.0.0.1',
            user_agent='TestAgent/1.0',
            expires_at=timezone.now() + timedelta(days=30)
        )
        token = TrustedDeviceToken(device_id=device.device_id, signed_value='signed-value')
        mock_add.return_value = (device, token, True)
        
        response = self.client.post('/api/auth/2fa/trusted-devices/')
        
        assert response.status_code == status.HTTP_201_CREATED
        payload = response_payload(response)
        assert payload['device']['device_id'] == device.device_id
        mock_add.assert_called_once()
        mock_set_cookie.assert_called_once()

    @patch('mysite.auth.services.trusted_device_service.TrustedDeviceService.add_trusted_device')
    def test_add_trusted_device_failure(self, mock_add):
        """Test handling errors when adding trusted device"""
        mock_add.side_effect = Exception("boom")
        
        response = self.client.post('/api/auth/2fa/trusted-devices/')
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data['error'] == 'device_add_failed'

    @patch('mysite.auth.services.trusted_device_service.TrustedDeviceService.set_trusted_device_cookie')
    @patch('mysite.auth.services.trusted_device_service.TrustedDeviceService.add_trusted_device')
    def test_add_trusted_device_already_trusted(self, mock_add, mock_set_cookie):
        """Adding an already-trusted device returns existing record"""
        device = TrustedDevice.objects.create(
            user=self.user,
            device_id='device-456',
            device_name='Existing Device',
            ip_address='127.0.0.1',
            user_agent='TestAgent/1.0',
            expires_at=timezone.now() + timedelta(days=30)
        )
        token = TrustedDeviceToken(device_id=device.device_id, signed_value='signed-existing')
        mock_add.return_value = (device, token, False)

        response = self.client.post('/api/auth/2fa/trusted-devices/')

        assert response.status_code == status.HTTP_200_OK
        payload = response_payload(response)
        assert payload['device']['device_id'] == device.device_id
        assert payload['created'] is False
        mock_set_cookie.assert_called_once()
