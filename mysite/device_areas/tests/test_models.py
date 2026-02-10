"""Tests for device area models."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import IntegrityError

from mysite.auth.models import TrustedDevice
from mysite.device_areas.models import DeviceArea, DeviceAreaAssignment

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestDeviceAreaModel:
    """Test DeviceArea model."""
    
    def test_create_area(self):
        """Test creating a device area."""
        area = DeviceArea.objects.create(
            name='Living Room',
            description='Main living area'
        )
        assert area.name == 'Living Room'
        assert area.description == 'Main living area'
        assert area.is_default is False
    
    def test_area_unique_name(self):
        """Test that area names must be unique."""
        DeviceArea.objects.create(name='Kitchen')
        
        with pytest.raises(IntegrityError):
            DeviceArea.objects.create(name='Kitchen')
    
    def test_default_area_exclusivity(self):
        """Test that only one area can be default."""
        area1 = DeviceArea.objects.create(
            name='Area 1',
            is_default=True
        )
        assert area1.is_default is True
        
        # Create second default area
        area2 = DeviceArea.objects.create(
            name='Area 2',
            is_default=True
        )
        
        # First area should no longer be default
        area1.refresh_from_db()
        assert area1.is_default is False
        assert area2.is_default is True
    
    def test_area_string_representation(self):
        """Test string representation of area."""
        area = DeviceArea.objects.create(name='Bedroom')
        assert str(area) == 'Bedroom'


class TestDeviceAreaAssignmentModel:
    """Test DeviceAreaAssignment model."""
    
    def test_create_assignment(self):
        """Test creating a device area assignment."""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass'
        )
        area = DeviceArea.objects.create(name='Office')
        device = TrustedDevice.objects.create(
            user=user,
            device_id='test-device-1',
            device_name='Test Device',
            ip_address='127.0.0.1',
            user_agent='TestBrowser',
            expires_at=timezone.now() + timedelta(days=30)
        )
        
        assignment = DeviceAreaAssignment.objects.create(
            device=device,
            area=area,
            assigned_by=user
        )
        
        assert assignment.device == device
        assert assignment.area == area
        assert assignment.assigned_by == user
    
    def test_assignment_one_to_one_device(self):
        """Test that a device can only have one assignment."""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass'
        )
        area1 = DeviceArea.objects.create(name='Area 1')
        area2 = DeviceArea.objects.create(name='Area 2')
        device = TrustedDevice.objects.create(
            user=user,
            device_id='test-device-2',
            device_name='Test Device 2',
            ip_address='127.0.0.1',
            user_agent='TestBrowser',
            expires_at=timezone.now() + timedelta(days=30)
        )
        
        # First assignment
        DeviceAreaAssignment.objects.create(
            device=device,
            area=area1,
            assigned_by=user
        )
        
        # Second assignment should fail
        with pytest.raises(IntegrityError):
            DeviceAreaAssignment.objects.create(
                device=device,
                area=area2,
                assigned_by=user
            )
    
    def test_assignment_string_representation(self):
        """Test string representation of assignment."""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass'
        )
        area = DeviceArea.objects.create(name='Garage')
        device = TrustedDevice.objects.create(
            user=user,
            device_id='test-device-3',
            device_name='My Phone',
            ip_address='127.0.0.1',
            user_agent='TestBrowser',
            expires_at=timezone.now() + timedelta(days=30)
        )
        
        assignment = DeviceAreaAssignment.objects.create(
            device=device,
            area=area,
            assigned_by=user
        )
        
        assert str(assignment) == 'My Phone -> Garage'
