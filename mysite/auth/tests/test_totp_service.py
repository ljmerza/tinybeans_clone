"""Unit tests for TOTP (Time-based One-Time Password) functionality"""
import pytest
from unittest.mock import Mock, patch

from mysite.auth.models import TwoFactorSettings
from mysite.auth.services.twofa_service import TwoFactorService
from .conftest import create_user


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
            local_part='testuser',
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
        user = create_user(local_part='testuser', password='testpass')
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
        user = create_user(local_part='testuser', password='testpass')
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
        user = create_user(local_part='testuser', password='testpass')
        TwoFactorSettings.objects.create(
            user=user,
            is_enabled=True,
            preferred_method='totp',
            totp_secret=None
        )

        result = TwoFactorService.verify_totp(user, '123456')
        assert result is False
