"""Unit tests for rate limiting functionality"""
import pytest
from datetime import timedelta
from django.utils import timezone

from mysite.auth.services.twofa_service import TwoFactorService
from .conftest import create_user, create_code


@pytest.mark.django_db
class TestRateLimiting:
    """Test rate limiting functionality"""

    def test_is_rate_limited_under_limit(self, settings):
        """Test rate limiting when under limit"""
        settings.TWOFA_RATE_LIMIT_MAX = 3
        settings.TWOFA_RATE_LIMIT_WINDOW = 900
        user = create_user(local_part='testuser', password='testpass')

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
        user = create_user(local_part='testuser', password='testpass')

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
        user = create_user(local_part='testuser', password='testpass')

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
