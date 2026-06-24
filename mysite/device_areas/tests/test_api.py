"""Tests for device area API endpoints."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from mysite.auth.models import TrustedDevice
from mysite.device_areas.models import DeviceArea, DeviceAreaAssignment

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestDeviceAreaAPI:
    """Test device area API endpoints."""
    
    def setup_method(self):
        """Set up test client and user."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_list_areas(self):
        """Test listing device areas."""
        DeviceArea.objects.create(name='Living Room')
        DeviceArea.objects.create(name='Kitchen')
        
        response = self.client.get('/api/device-areas/areas/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['count'] == 2
        assert len(data['results']) == 2
    
    def test_create_area(self):
        """Test creating a new area."""
        data = {
            'name': 'Bedroom',
            'description': 'Master bedroom'
        }
        
        response = self.client.post('/api/device-areas/areas/', data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert DeviceArea.objects.filter(name='Bedroom').exists()
    
    def test_sync_unassigned_devices(self):
        """Test syncing unassigned devices to default area."""
        # Create devices without assignments
        for i in range(3):
            TrustedDevice.objects.create(
                user=self.user,
                device_id=f'device-{i}',
                device_name=f'Device {i}',
                ip_address='127.0.0.1',
                user_agent='TestBrowser',
                expires_at=timezone.now() + timedelta(days=30)
            )
        
        response = self.client.post('/api/device-areas/areas/sync_unassigned/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['devices_synced'] == 3
        assert data['default_area_created'] is True
        
        # Verify default area was created
        default_area = DeviceArea.objects.get(is_default=True)
        assert default_area.name == 'Default Area'
        
        # Verify all devices are now assigned
        assert TrustedDevice.objects.filter(area_assignment__isnull=True).count() == 0
    
    def test_sync_with_existing_default_area(self):
        """Test syncing when default area already exists."""
        # Create default area
        default_area = DeviceArea.objects.create(
            name='My Default',
            is_default=True
        )
        
        # Create unassigned device
        TrustedDevice.objects.create(
            user=self.user,
            device_id='device-1',
            device_name='Device 1',
            ip_address='127.0.0.1',
            user_agent='TestBrowser',
            expires_at=timezone.now() + timedelta(days=30)
        )
        
        response = self.client.post('/api/device-areas/areas/sync_unassigned/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['devices_synced'] == 1
        assert data['default_area_created'] is False
        assert data['default_area_name'] == 'My Default'
    
    def test_assign_devices_to_area(self):
        """Test bulk assigning devices to an area."""
        area = DeviceArea.objects.create(name='Office')
        
        # Create devices
        device1 = TrustedDevice.objects.create(
            user=self.user,
            device_id='device-1',
            device_name='Device 1',
            ip_address='127.0.0.1',
            user_agent='TestBrowser',
            expires_at=timezone.now() + timedelta(days=30)
        )
        device2 = TrustedDevice.objects.create(
            user=self.user,
            device_id='device-2',
            device_name='Device 2',
            ip_address='127.0.0.1',
            user_agent='TestBrowser',
            expires_at=timezone.now() + timedelta(days=30)
        )
        
        data = {
            'device_ids': [device1.id, device2.id],
            'area_id': area.id
        }
        
        response = self.client.post(
            f'/api/device-areas/areas/{area.id}/assign_devices/',
            data,
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert result['assignments_created'] == 2
        
        # Verify assignments
        assert DeviceAreaAssignment.objects.filter(
            device=device1,
            area=area
        ).exists()
        assert DeviceAreaAssignment.objects.filter(
            device=device2,
            area=area
        ).exists()


class TestDeviceAreaAssignmentAPI:
    """Test device area assignment API endpoints."""
    
    def setup_method(self):
        """Set up test client and user."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_list_assignments(self):
        """Test listing device area assignments."""
        area = DeviceArea.objects.create(name='Living Room')
        device = TrustedDevice.objects.create(
            user=self.user,
            device_id='device-1',
            device_name='Device 1',
            ip_address='127.0.0.1',
            user_agent='TestBrowser',
            expires_at=timezone.now() + timedelta(days=30)
        )
        
        DeviceAreaAssignment.objects.create(
            device=device,
            area=area,
            assigned_by=self.user
        )
        
        response = self.client.get('/api/device-areas/assignments/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['count'] == 1
        assert len(data['results']) == 1
        assert data['results'][0]['area_name'] == 'Living Room'
        assert data['results'][0]['device_name'] == 'Device 1'
    
    def test_create_assignment(self):
        """Test creating a device area assignment."""
        area = DeviceArea.objects.create(name='Kitchen')
        device = TrustedDevice.objects.create(
            user=self.user,
            device_id='device-2',
            device_name='Device 2',
            ip_address='127.0.0.1',
            user_agent='TestBrowser',
            expires_at=timezone.now() + timedelta(days=30)
        )
        
        data = {
            'device': device.id,
            'area': area.id
        }
        
        response = self.client.post(
            '/api/device-areas/assignments/',
            data,
            format='json'
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        assert DeviceAreaAssignment.objects.filter(
            device=device,
            area=area
        ).exists()
    
    def test_list_unassigned_devices(self):
        """Test listing devices without area assignments."""
        # Create assigned device
        area = DeviceArea.objects.create(name='Office')
        assigned_device = TrustedDevice.objects.create(
            user=self.user,
            device_id='device-1',
            device_name='Assigned Device',
            ip_address='127.0.0.1',
            user_agent='TestBrowser',
            expires_at=timezone.now() + timedelta(days=30)
        )
        DeviceAreaAssignment.objects.create(
            device=assigned_device,
            area=area,
            assigned_by=self.user
        )
        
        # Create unassigned device
        unassigned_device = TrustedDevice.objects.create(
            user=self.user,
            device_id='device-2',
            device_name='Unassigned Device',
            ip_address='127.0.0.1',
            user_agent='TestBrowser',
            expires_at=timezone.now() + timedelta(days=30)
        )
        
        response = self.client.get('/api/device-areas/assignments/unassigned/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['count'] == 1
        assert data['devices'][0]['device_name'] == 'Unassigned Device'
    
    def test_user_can_only_see_own_assignments(self):
        """Test that regular users can only see their own device assignments."""
        # Create another user
        other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass'
        )
        
        area = DeviceArea.objects.create(name='Shared Area')
        
        # Create device for other user
        other_device = TrustedDevice.objects.create(
            user=other_user,
            device_id='other-device',
            device_name='Other Device',
            ip_address='127.0.0.1',
            user_agent='TestBrowser',
            expires_at=timezone.now() + timedelta(days=30)
        )
        DeviceAreaAssignment.objects.create(
            device=other_device,
            area=area,
            assigned_by=other_user
        )
        
        # Current user should not see other user's assignments
        response = self.client.get('/api/device-areas/assignments/')
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['count'] == 0
        assert len(data['results']) == 0
