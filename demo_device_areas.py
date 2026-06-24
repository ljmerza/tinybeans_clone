#!/usr/bin/env python
"""
Demo script showing how to use the device_areas API.

This script demonstrates:
1. Creating device areas
2. Syncing unassigned devices to a default area
3. Assigning specific devices to areas
4. Listing unassigned devices

Run with: python demo_device_areas.py
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

from datetime import timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone
from mysite.auth.models import TrustedDevice
from mysite.device_areas.models import DeviceArea, DeviceAreaAssignment

User = get_user_model()


def demo():
    """Run the device areas demo."""
    print("=" * 60)
    print("Device Areas Demo")
    print("=" * 60)
    
    # 1. Create a test user
    print("\n1. Creating test user...")
    user, created = User.objects.get_or_create(
        email='demo@example.com',
        defaults={'password': 'demopass123'}
    )
    print(f"   User: {user.email} ({'created' if created else 'exists'})")
    
    # 2. Create some device areas
    print("\n2. Creating device areas...")
    areas_data = [
        ('Living Room', 'Main living area with TV'),
        ('Kitchen', 'Cooking and dining area'),
        ('Home Office', 'Work from home space'),
    ]
    
    for name, description in areas_data:
        area, created = DeviceArea.objects.get_or_create(
            name=name,
            defaults={'description': description}
        )
        print(f"   Area: {name} ({'created' if created else 'exists'})")
    
    # 3. Create some trusted devices
    print("\n3. Creating trusted devices...")
    devices_data = [
        ('laptop-001', 'MacBook Pro'),
        ('phone-001', 'iPhone 14'),
        ('tablet-001', 'iPad Pro'),
    ]
    
    for device_id, device_name in devices_data:
        device, created = TrustedDevice.objects.get_or_create(
            user=user,
            device_id=device_id,
            defaults={
                'device_name': device_name,
                'ip_address': '192.168.1.100',
                'user_agent': 'Demo Device',
                'expires_at': timezone.now() + timedelta(days=30)
            }
        )
        print(f"   Device: {device_name} ({device_id}) ({'created' if created else 'exists'})")
    
    # 4. Check unassigned devices
    print("\n4. Checking unassigned devices...")
    unassigned = TrustedDevice.objects.filter(area_assignment__isnull=True)
    print(f"   Found {unassigned.count()} unassigned devices")
    for device in unassigned:
        print(f"   - {device.device_name} ({device.device_id})")
    
    # 5. Create default area and sync unassigned devices
    print("\n5. Syncing unassigned devices to default area...")
    default_area, created = DeviceArea.objects.get_or_create(
        is_default=True,
        defaults={
            'name': 'Default Area',
            'description': 'Auto-assigned devices'
        }
    )
    print(f"   Default area: {default_area.name} ({'created' if created else 'exists'})")
    
    # Sync unassigned devices
    unassigned = TrustedDevice.objects.filter(area_assignment__isnull=True)
    synced_count = 0
    for device in unassigned:
        assignment, created = DeviceAreaAssignment.objects.get_or_create(
            device=device,
            defaults={
                'area': default_area,
                'assigned_by': user
            }
        )
        if created:
            synced_count += 1
    
    print(f"   Synced {synced_count} devices to default area")
    
    # 6. Manually assign a device to a specific area
    print("\n6. Manually assigning device to area...")
    laptop = TrustedDevice.objects.get(device_id='laptop-001')
    office = DeviceArea.objects.get(name='Home Office')
    
    assignment, created = DeviceAreaAssignment.objects.update_or_create(
        device=laptop,
        defaults={
            'area': office,
            'assigned_by': user
        }
    )
    print(f"   {laptop.device_name} -> {office.name} ({'created' if created else 'updated'})")
    
    # 7. Show final state
    print("\n7. Final device assignments:")
    for area in DeviceArea.objects.all():
        assignments = DeviceAreaAssignment.objects.filter(area=area)
        print(f"\n   {area.name}:")
        if assignments.exists():
            for assignment in assignments:
                print(f"   - {assignment.device.device_name} ({assignment.device.device_id})")
        else:
            print("   - No devices")
    
    # 8. Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Total Areas: {DeviceArea.objects.count()}")
    print(f"  Total Devices: {TrustedDevice.objects.count()}")
    print(f"  Total Assignments: {DeviceAreaAssignment.objects.count()}")
    print(f"  Unassigned Devices: {TrustedDevice.objects.filter(area_assignment__isnull=True).count()}")
    print("=" * 60)


if __name__ == '__main__':
    demo()
