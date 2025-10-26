"""Unit tests for OTP generation and validation"""
import pytest
from datetime import timedelta
from django.utils import timezone

from mysite.auth.models import TwoFactorSettings, TwoFactorCode
from mysite.auth.services.twofa_service import TwoFactorService
from .conftest import create_user, create_code


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
        user = create_user(local_part='testuser', password='testpass')

        # Create valid code
        code_obj = create_code(user, code='123456')

        result = TwoFactorService.verify_otp(user, '123456', purpose='login')

        assert result is True
        code_obj.refresh_from_db()
        assert code_obj.is_used is True
        assert code_obj.attempts == 1

    def test_verify_otp_invalid_code(self):
        """Test OTP verification with wrong code"""
        user = create_user(local_part='testuser', password='testpass')

        result = TwoFactorService.verify_otp(user, '999999', purpose='login')
        assert result is False

    def test_verify_otp_expired_code(self):
        """Test OTP verification with expired code"""
        user = create_user(local_part='testuser', password='testpass')

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
        user = create_user(local_part='testuser', password='testpass')

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
        user = create_user(local_part='testuser', password='testpass')

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
        user = create_user(local_part='user1', password='x')
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
