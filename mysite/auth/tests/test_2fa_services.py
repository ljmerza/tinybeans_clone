"""Unit tests for 2FA services - no external dependencies"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.test import RequestFactory

from mysite.auth.models import (
    TwoFactorSettings,
    TwoFactorCode,
    RecoveryCode,
    TrustedDevice,
    TwoFactorAuditLog
)
from mysite.auth.services.twofa_service import TwoFactorService
from mysite.auth.services.trusted_device_service import TrustedDeviceService, TrustedDeviceToken
from mysite.auth.services.recovery_code_service import RecoveryCodeService

User = get_user_model()


def create_user(username='testuser', email=None, password='testpass', **extra):
    """Utility helper to create users with required email field."""
    if email is None:
        email = f"{username}@example.com"
    return User.objects.create_user(username=username, email=email, password=password, **extra)


def create_code(user, code='123456', **kwargs):
    """Helper to create hashed TwoFactorCode records."""
    defaults = {
        'code_hash': TwoFactorService._hash_otp(code),
        'code_preview': code[-6:],
        'method': 'email',
        'purpose': 'login',
        'is_used': False,
        'attempts': 0,
        'max_attempts': 5,
        'expires_at': timezone.now() + timedelta(minutes=10),
    }
    defaults.update(kwargs)
    return TwoFactorCode.objects.create(user=user, **defaults)


@pytest.mark.django_db
class TestTwoFactorServiceOTP:
    """Test OTP generation and validation"""
    
    def test_generate_otp_format(self):
        """Test OTP is 6 digits"""
        otp = TwoFactorService.generate_otp()
        assert len(otp) == 6
        assert otp.isdigit()
        assert 0 <= int(otp) <= 999999
    
    def test_generate_otp_randomness(self):
        """Test OTP generation produces different codes"""
        codes = [TwoFactorService.generate_otp() for _ in range(10)]
        # At least 8 out of 10 should be unique (probability check)
        assert len(set(codes)) >= 8
    
    def test_verify_otp_valid_code(self):
        """Test OTP verification with valid code"""
        user = create_user(username='testuser', password='testpass')
        
        # Create valid code
        code_obj = create_code(user, code='123456')
        
        result = TwoFactorService.verify_otp(user, '123456', purpose='login')
        
        assert result is True
        code_obj.refresh_from_db()
        assert code_obj.is_used is True
        assert code_obj.attempts == 1
    
    def test_verify_otp_invalid_code(self):
        """Test OTP verification with wrong code"""
        user = create_user(username='testuser', password='testpass')
        
        result = TwoFactorService.verify_otp(user, '999999', purpose='login')
        assert result is False
    
    def test_verify_otp_expired_code(self):
        """Test OTP verification with expired code"""
        user = create_user(username='testuser', password='testpass')
        
        # Create expired code
        create_code(
            user,
            code='123456',
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        
        result = TwoFactorService.verify_otp(user, '123456', purpose='login')
        assert result is False
    
    def test_verify_otp_max_attempts_exceeded(self):
        """Test OTP verification fails after max attempts"""
        user = create_user(username='testuser', password='testpass')
        
        # Create code with max attempts reached
        create_code(
            user,
            code='123456',
            attempts=5,
            max_attempts=5
        )
        
        result = TwoFactorService.verify_otp(user, '123456', purpose='login')
        assert result is False
    
    def test_verify_otp_already_used(self):
        """Test OTP verification fails for already used code"""
        user = create_user(username='testuser', password='testpass')
        
        # Create used code
        create_code(
            user,
            code='123456',
            is_used=True,
            attempts=1
        )
        
        result = TwoFactorService.verify_otp(user, '123456', purpose='login')
        assert result is False


    def test_send_otp_invalidates_previous_unused_codes(self):
        """Requesting a new OTP should invalidate previous unused codes for same purpose/method"""
        user = create_user(username='user1', password='x')
        TwoFactorSettings.objects.create(user=user, preferred_method='email', is_enabled=True)

        # Create an existing, unused code
        old_code = create_code(
            user,
            code='111111',
            purpose='setup',
            method='email',
            is_used=False,
            expires_at=timezone.now() + timedelta(minutes=10),
        )

        # Send a new OTP for same method/purpose
        TwoFactorService.send_otp(user, method='email', purpose='setup')

        # Old code should be invalidated (marked used and expired)
        old_code.refresh_from_db()
        assert old_code.is_used is True
        assert old_code.expires_at <= timezone.now()

        # New code should be the only valid one remaining
        valid_count = TwoFactorCode.objects.filter(
            user=user,
            method='email',
            purpose='setup',
            is_used=False,
            expires_at__gt=timezone.now(),
        ).count()
        assert valid_count == 1

@pytest.mark.django_db
class TestTwoFactorServiceTOTP:
    """Test TOTP generation and validation"""
    
    def test_generate_totp_secret_format(self):
        """Test TOTP secret is base32 encoded"""
        secret = TwoFactorService.generate_totp_secret()
        assert len(secret) == 32
        assert secret.isalnum()
        assert secret.isupper()  # base32 is uppercase
    
    def test_generate_totp_secret_uniqueness(self):
        """Test TOTP secrets are unique"""
        secrets = [TwoFactorService.generate_totp_secret() for _ in range(10)]
        assert len(set(secrets)) == 10
    
    @patch('mysite.auth.services.twofa_service.pyotp.TOTP')
    @patch('mysite.auth.services.twofa_service.qrcode.QRCode')
    def test_generate_totp_qr_code(self, mock_qrcode, mock_totp):
        """Test QR code generation"""
        user = create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )
        secret = 'JBSWY3DPEHPK3PXP'
        
        # Mock TOTP
        mock_totp_instance = Mock()
        mock_totp_instance.provisioning_uri.return_value = 'otpauth://totp/test'
        mock_totp.return_value = mock_totp_instance
        
        # Mock QR code
        mock_qr_instance = Mock()
        mock_img = Mock()
        mock_qr_instance.make_image.return_value = mock_img
        mock_qrcode.return_value = mock_qr_instance
        
        result = TwoFactorService.generate_totp_qr_code(user, secret)
        
        assert 'uri' in result
        assert 'qr_code_image' in result
        assert 'secret' in result
        assert result['secret'] == secret
    
    @patch('mysite.auth.services.twofa_service.pyotp.TOTP')
    def test_verify_totp_valid(self, mock_totp):
        """Test TOTP verification with valid code"""
        user = create_user(username='testuser', password='testpass')
        TwoFactorSettings.objects.create(
            user=user,
            is_enabled=True,
            preferred_method='totp',
            totp_secret='JBSWY3DPEHPK3PXP'
        )
        
        # Mock TOTP verification
        mock_totp_instance = Mock()
        mock_totp_instance.verify.return_value = True
        mock_totp.return_value = mock_totp_instance
        
        result = TwoFactorService.verify_totp(user, '123456')
        assert result is True
    
    @patch('mysite.auth.services.twofa_service.pyotp.TOTP')
    def test_verify_totp_invalid(self, mock_totp):
        """Test TOTP verification with invalid code"""
        user = create_user(username='testuser', password='testpass')
        TwoFactorSettings.objects.create(
            user=user,
            is_enabled=True,
            preferred_method='totp',
            totp_secret='JBSWY3DPEHPK3PXP'
        )
        
        # Mock TOTP verification
        mock_totp_instance = Mock()
        mock_totp_instance.verify.return_value = False
        mock_totp.return_value = mock_totp_instance
        
        result = TwoFactorService.verify_totp(user, '999999')
        assert result is False
    
    def test_verify_totp_no_secret(self):
        """Test TOTP verification fails without secret"""
        user = create_user(username='testuser', password='testpass')
        TwoFactorSettings.objects.create(
            user=user,
            is_enabled=True,
            preferred_method='totp',
            totp_secret=None
        )
        
        result = TwoFactorService.verify_totp(user, '123456')
        assert result is False


@pytest.mark.django_db
class TestRecoveryCodeService:
    """Test recovery code generation and verification"""
    
    def test_generate_recovery_codes_count(self):
        """Test correct number of recovery codes generated"""
        user = create_user(username='testuser', password='testpass')
        
        codes = TwoFactorService.generate_recovery_codes(user, count=10)
        
        assert len(codes) == 10
        assert RecoveryCode.objects.filter(user=user).count() == 10
    
    def test_generate_recovery_codes_format(self):
        """Test recovery code format"""
        user = create_user(username='testuser', password='testpass')
        
        codes = TwoFactorService.generate_recovery_codes(user, count=5)
        
        for code in codes:
            # Format: XXXX-XXXX-XXXX
            assert isinstance(code, str)
            assert len(code) == 14
            assert code.count('-') == 2
            parts = code.split('-')
            assert len(parts) == 3
            for part in parts:
                assert len(part) == 4
                assert part.isalnum()
    
    def test_generate_recovery_codes_uniqueness(self):
        """Test recovery codes are unique"""
        user = create_user(username='testuser', password='testpass')
        
        codes = TwoFactorService.generate_recovery_codes(user, count=10)
        
        assert len(set(codes)) == 10
    
    def test_generate_recovery_codes_deletes_old(self):
        """Test generating new codes deletes old unused codes"""
        user = create_user(username='testuser', password='testpass')
        
        # Generate first batch
        TwoFactorService.generate_recovery_codes(user, count=5)
        old_ids = set(
            RecoveryCode.objects.filter(user=user).values_list('id', flat=True)
        )
        
        # Generate new batch
        TwoFactorService.generate_recovery_codes(user, count=5)
        new_ids = set(
            RecoveryCode.objects.filter(user=user).values_list('id', flat=True)
        )
        
        # Old codes should be deleted
        assert old_ids.isdisjoint(new_ids)
        # New codes should exist
        assert RecoveryCode.objects.filter(user=user).count() == 5
    
    def test_verify_recovery_code_valid(self):
        """Test recovery code verification"""
        user = create_user(username='testuser', password='testpass')
        
        codes = TwoFactorService.generate_recovery_codes(user, count=1)
        code_value = codes[0]
        
        result = TwoFactorService.verify_recovery_code(user, code_value)
        
        assert result is True
        record = RecoveryCode.objects.get(user=user)
        record.refresh_from_db()
        assert record.is_used is True
        assert record.used_at is not None
    
    def test_verify_recovery_code_case_insensitive(self):
        """Test recovery code verification is case insensitive"""
        user = create_user(username='testuser', password='testpass')
        
        codes = TwoFactorService.generate_recovery_codes(user, count=1)
        code_value = codes[0].lower()  # Use lowercase
        
        result = TwoFactorService.verify_recovery_code(user, code_value)
        assert result is True
    
    def test_verify_recovery_code_invalid(self):
        """Test recovery code verification with invalid code"""
        user = create_user(username='testuser', password='testpass')
        
        result = TwoFactorService.verify_recovery_code(user, 'INVALID-CODE-1234')
        assert result is False
    
    def test_verify_recovery_code_already_used(self):
        """Test recovery code verification fails for used code"""
        user = create_user(username='testuser', password='testpass')
        
        codes = TwoFactorService.generate_recovery_codes(user, count=1)
        code_value = codes[0]
        
        # Use code once
        TwoFactorService.verify_recovery_code(user, code_value)
        
        # Try to use again
        result = TwoFactorService.verify_recovery_code(user, code_value)
        assert result is False
    
    def test_export_recovery_codes_txt(self):
        """Test TXT export of recovery codes"""
        user = create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )
        
        codes = TwoFactorService.generate_recovery_codes(user, count=10)
        
        txt_content = RecoveryCodeService.export_as_txt(user, codes)
        
        assert 'Tinybeans Recovery Codes' in txt_content
        assert user.email in txt_content
        assert 'IMPORTANT:' in txt_content
        
        # Check all codes are present
        for code in codes:
            assert code in txt_content
    
    @patch('mysite.auth.services.recovery_code_service.SimpleDocTemplate')
    def test_export_recovery_codes_pdf(self, mock_doc):
        """Test PDF export of recovery codes"""
        user = create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )
        
        codes = TwoFactorService.generate_recovery_codes(user, count=10)
        
        # Mock PDF generation
        mock_doc_instance = Mock()
        mock_doc.return_value = mock_doc_instance
        
        pdf_bytes = RecoveryCodeService.export_as_pdf(user, codes)
        
        # Verify doc.build was called
        mock_doc_instance.build.assert_called_once()


@pytest.mark.django_db
class TestTrustedDeviceService:
    """Test trusted device management"""
    
    def test_generate_device_id_format(self):
        """Test device ID generation"""
        factory = RequestFactory()
        request = factory.get('/')
        request.META['HTTP_USER_AGENT'] = 'TestBrowser/1.0'
        
        device_id = TrustedDeviceService.generate_device_id(request)
        
        assert len(device_id) == 64  # SHA256 hex digest
        assert all(c in '0123456789abcdef' for c in device_id)
    
    def test_generate_device_id_uniqueness(self):
        """Test device IDs are unique"""
        factory = RequestFactory()
        request = factory.get('/')
        request.META['HTTP_USER_AGENT'] = 'TestBrowser/1.0'
        
        device_ids = [
            TrustedDeviceService.generate_device_id(request)
            for _ in range(5)
        ]
        
        # Should be unique due to random salt
        assert len(set(device_ids)) == 5
    
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
        user = create_user(username='testuser', password='testpass')
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
        user = create_user(username='testuser', password='testpass')
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
        user = create_user(username='testuser', password='testpass')
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
        user = create_user(username='testuser', password='testpass')
        
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
        user = create_user(username='testuser', password='testpass')
        
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
        user = create_user(username='testuser', password='testpass')
        
        request = RequestFactory().get('/')
        request.META['HTTP_USER_AGENT'] = 'TestBrowser/1.0'
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        token = TrustedDeviceToken(device_id='non-existent', signed_value='invalid')
        result, rotated = TrustedDeviceService.is_trusted_device(user, token, request)
        assert result is False
        assert rotated is None
    
    def test_remove_trusted_device(self):
        """Test removing trusted device"""
        user = create_user(username='testuser', password='testpass')
        
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
        user = create_user(username='testuser', password='testpass')
        
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
        user = create_user(username='testuser', password='testpass')
        
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


@pytest.mark.django_db
class TestRateLimiting:
    """Test rate limiting functionality"""
    
    def test_is_rate_limited_under_limit(self, settings):
        """Test rate limiting when under limit"""
        settings.TWOFA_RATE_LIMIT_MAX = 3
        settings.TWOFA_RATE_LIMIT_WINDOW = 900
        user = create_user(username='testuser', password='testpass')
        
        # Create 2 codes (under limit of 3)
        for i in range(2):
            create_code(
                user,
                code=f'12345{i}',
                expires_at=timezone.now() + timedelta(minutes=10)
            )
        
        result = TwoFactorService.is_rate_limited(user)
        assert result is False
    
    def test_is_rate_limited_at_limit(self, settings):
        """Test rate limiting when at limit"""
        settings.TWOFA_RATE_LIMIT_MAX = 3
        settings.TWOFA_RATE_LIMIT_WINDOW = 900
        user = create_user(username='testuser', password='testpass')
        
        # Create 3 codes (at limit)
        for i in range(3):
            create_code(
                user,
                code=f'12345{i}',
                expires_at=timezone.now() + timedelta(minutes=10)
            )
        
        result = TwoFactorService.is_rate_limited(user)
        assert result is True
    
    def test_is_rate_limited_expired_codes(self, settings):
        """Test rate limiting ignores expired codes"""
        settings.TWOFA_RATE_LIMIT_MAX = 3
        settings.TWOFA_RATE_LIMIT_WINDOW = 900
        user = create_user(username='testuser', password='testpass')
        
        # Create old codes (outside rate limit window)
        for i in range(5):
            code = create_code(
                user,
                code=f'12345{i}',
                expires_at=timezone.now() + timedelta(minutes=10)
            )
            # Manually set created_at to 20 minutes ago
            code.created_at = timezone.now() - timedelta(minutes=20)
            code.save()
        
        result = TwoFactorService.is_rate_limited(user)
        assert result is False
