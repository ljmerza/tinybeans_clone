"""Unit tests for recovery code generation and verification"""
import pytest
from unittest.mock import Mock, patch

from mysite.auth.models import RecoveryCode
from mysite.auth.services.twofa_service import TwoFactorService
from mysite.auth.services.recovery_code_service import RecoveryCodeService
from .conftest import create_user


@pytest.mark.django_db
class TestRecoveryCodeService:
    """Test recovery code generation and verification"""

    def test_generate_recovery_codes_count(self):
        """Test correct number of recovery codes generated"""
        user = create_user(local_part='testuser', password='testpass')

        codes = TwoFactorService.generate_recovery_codes(user, count=10)

        assert len(codes) == 10
        assert RecoveryCode.objects.filter(user=user).count() == 10

    def test_generate_recovery_codes_format(self):
        """Test recovery code format"""
        user = create_user(local_part='testuser', password='testpass')

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
        user = create_user(local_part='testuser', password='testpass')

        codes = TwoFactorService.generate_recovery_codes(user, count=10)

        assert len(set(codes)) == 10

    def test_generate_recovery_codes_deletes_old(self):
        """Test generating new codes deletes old unused codes"""
        user = create_user(local_part='testuser', password='testpass')

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
        user = create_user(local_part='testuser', password='testpass')

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
        user = create_user(local_part='testuser', password='testpass')

        codes = TwoFactorService.generate_recovery_codes(user, count=1)
        code_value = codes[0].lower()  # Use lowercase

        result = TwoFactorService.verify_recovery_code(user, code_value)
        assert result is True

    def test_verify_recovery_code_invalid(self):
        """Test recovery code verification with invalid code"""
        user = create_user(local_part='testuser', password='testpass')

        result = TwoFactorService.verify_recovery_code(user, 'INVALID-CODE-1234')
        assert result is False

    def test_verify_recovery_code_already_used(self):
        """Test recovery code verification fails for used code"""
        user = create_user(local_part='testuser', password='testpass')

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
            local_part='testuser',
            email='test@example.com',
            password='testpass'
        )

        codes = TwoFactorService.generate_recovery_codes(user, count=10)

        txt_content = RecoveryCodeService.export_as_txt(user, codes)

        assert 'Tinybeans Recovery Codes' in txt_content
        assert user.display_name in txt_content
        assert 'IMPORTANT:' in txt_content

        # Check all codes are present
        for code in codes:
            assert code in txt_content

    @patch('mysite.auth.services.recovery_code_service.SimpleDocTemplate')
    def test_export_recovery_codes_pdf(self, mock_doc):
        """Test PDF export of recovery codes"""
        user = create_user(
            local_part='testuser',
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
