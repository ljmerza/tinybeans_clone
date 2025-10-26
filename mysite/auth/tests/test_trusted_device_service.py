"""Unit tests for trusted device management"""
import pytest
from unittest.mock import Mock, patch
from datetime import timedelta
from django.utils import timezone
from django.test import RequestFactory

from mysite.auth.models import TrustedDevice, TwoFactorAuditLog
from mysite.auth.services.trusted_device_service import TrustedDeviceService, TrustedDeviceToken
from .conftest import create_user


@pytest.mark.django_db
class TestTrustedDeviceService:
    """Test trusted device management"""

    @patch('user_agents.parse')
    def test_get_device_name(self, mock_parse):
        """Test device name extraction"""
        factory = RequestFactory()
        request = factory.get('/')
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'

        # Mock user agent parser
        mock_ua = Mock()
        mock_ua.browser.family = 'Chrome'
        mock_ua.browser.version_string = '120.0'
        mock_ua.os.family = 'Windows'
        mock_ua.os.version_string = '10'
        mock_ua.device.family = 'Other'
        mock_parse.return_value = mock_ua

        device_name = TrustedDeviceService.get_device_name(request)

        assert 'Chrome' in device_name
        assert 'Windows' in device_name

    def test_add_trusted_device(self):
        """Test adding trusted device"""
        user = create_user(local_part='testuser', password='testpass')
        factory = RequestFactory()
        request = factory.get('/')
        request.META['HTTP_USER_AGENT'] = 'TestBrowser/1.0'
        request.META['REMOTE_ADDR'] = '127.0.0.1'

        device, token, created = TrustedDeviceService.add_trusted_device(user, request, days=30)

        assert device.user == user
        assert device.device_id == token.device_id
        assert device.ip_address == '127.0.0.1'
        assert device.expires_at > timezone.now()
        assert device.ip_hash
        assert device.ua_hash
        assert created is True

        # Check audit log
        log = TwoFactorAuditLog.objects.filter(
            user=user,
            action='trusted_device_added'
        ).first()
        assert log is not None

    def test_add_trusted_device_is_idempotent(self):
        """Adding the same device twice should refresh instead of duplicating"""
        user = create_user(local_part='testuser', password='testpass')
        factory = RequestFactory()
        request = factory.get('/')
        request.META['HTTP_USER_AGENT'] = 'TestBrowser/1.0'
        request.META['REMOTE_ADDR'] = '127.0.0.1'

        first_device, first_token, first_created = TrustedDeviceService.add_trusted_device(
            user, request, days=30
        )
        second_device, second_token, second_created = TrustedDeviceService.add_trusted_device(
            user, request, days=30
        )

        assert first_created is True
        assert second_created is False
        assert first_device.pk == second_device.pk
        assert first_token.device_id == second_token.device_id
        assert TrustedDevice.objects.filter(user=user).count() == 1

        refresh_log = TwoFactorAuditLog.objects.filter(
            user=user,
            action='trusted_device_refreshed'
        ).first()
        assert refresh_log is not None

    def test_add_trusted_device_max_limit(self):
        """Test max trusted devices limit"""
        user = create_user(local_part='testuser', password='testpass')
        factory = RequestFactory()

        # Add max devices
        for i in range(6):
            request = factory.get('/')
            request.META['HTTP_USER_AGENT'] = f'Browser{i}/1.0'
            request.META['REMOTE_ADDR'] = '127.0.0.1'
            TrustedDeviceService.add_trusted_device(user, request, days=30)

        # Should only have 5 (oldest removed)
        active_devices = TrustedDevice.objects.filter(
            user=user,
            expires_at__gt=timezone.now()
        ).count()

        assert active_devices == 5

    def test_is_trusted_device_valid(self):
        """Test checking trusted device"""
        user = create_user(local_part='testuser', password='testpass')

        request = RequestFactory().get('/')
        request.META['HTTP_USER_AGENT'] = 'TestBrowser/1.0'
        request.META['REMOTE_ADDR'] = '127.0.0.1'

        device, token, _ = TrustedDeviceService.add_trusted_device(user, request, days=30)

        result, rotated = TrustedDeviceService.is_trusted_device(user, token, request)

        assert result is True
        assert rotated is None or isinstance(rotated, TrustedDeviceToken)
        device.refresh_from_db()
        assert device.last_used_at is not None

    def test_is_trusted_device_expired(self):
        """Test expired trusted device"""
        user = create_user(local_part='testuser', password='testpass')

        request = RequestFactory().get('/')
        request.META['HTTP_USER_AGENT'] = 'TestBrowser/1.0'
        request.META['REMOTE_ADDR'] = '127.0.0.1'

        device, token, _ = TrustedDeviceService.add_trusted_device(user, request, days=1)
        device.expires_at = timezone.now() - timedelta(days=1)
        device.save(update_fields=['expires_at'])

        result, rotated = TrustedDeviceService.is_trusted_device(user, token, request)
        assert result is False
        assert rotated is None

    def test_is_trusted_device_not_found(self):
        """Test non-existent trusted device"""
        user = create_user(local_part='testuser', password='testpass')

        request = RequestFactory().get('/')
        request.META['HTTP_USER_AGENT'] = 'TestBrowser/1.0'
        request.META['REMOTE_ADDR'] = '127.0.0.1'

        token = TrustedDeviceToken(device_id='non-existent', signed_value='invalid')
        result, rotated = TrustedDeviceService.is_trusted_device(user, token, request)
        assert result is False
        assert rotated is None

    def test_remove_trusted_device(self):
        """Test removing trusted device"""
        user = create_user(local_part='testuser', password='testpass')

        TrustedDevice.objects.create(
            user=user,
            device_id='test-device-123',
            device_name='Test Device',
            ip_address='127.0.0.1',
            user_agent='TestBrowser',
            expires_at=timezone.now() + timedelta(days=30)
        )

        result = TrustedDeviceService.remove_trusted_device(user, 'test-device-123')

        assert result is True
        assert not TrustedDevice.objects.filter(device_id='test-device-123').exists()

        # Check audit log
        log = TwoFactorAuditLog.objects.filter(
            user=user,
            action='trusted_device_removed'
        ).first()
        assert log is not None

    def test_get_trusted_devices(self):
        """Test getting all trusted devices"""
        user = create_user(local_part='testuser', password='testpass')

        # Create active devices
        for i in range(3):
            TrustedDevice.objects.create(
                user=user,
                device_id=f'device-{i}',
                device_name=f'Device {i}',
                ip_address='127.0.0.1',
                user_agent='TestBrowser',
                expires_at=timezone.now() + timedelta(days=30)
            )

        # Create expired device
        TrustedDevice.objects.create(
            user=user,
            device_id='expired-device',
            device_name='Expired Device',
            ip_address='127.0.0.1',
            user_agent='TestBrowser',
            expires_at=timezone.now() - timedelta(days=1)
        )

        devices = TrustedDeviceService.get_trusted_devices(user)

        assert len(devices) == 3  # Only active devices

    def test_cleanup_expired_devices(self):
        """Test cleanup of expired devices"""
        user = create_user(local_part='testuser', password='testpass')

        # Create expired devices
        for i in range(3):
            TrustedDevice.objects.create(
                user=user,
                device_id=f'expired-{i}',
                device_name=f'Expired {i}',
                ip_address='127.0.0.1',
                user_agent='TestBrowser',
                expires_at=timezone.now() - timedelta(days=1)
            )

        # Create active device
        TrustedDevice.objects.create(
            user=user,
            device_id='active-device',
            device_name='Active Device',
            ip_address='127.0.0.1',
            user_agent='TestBrowser',
            expires_at=timezone.now() + timedelta(days=30)
        )

        count = TrustedDeviceService.cleanup_expired_devices()

        assert count == 3
        assert TrustedDevice.objects.filter(user=user).count() == 1
