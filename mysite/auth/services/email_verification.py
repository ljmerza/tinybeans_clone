"""Service layer for email verification and auto-login."""
from __future__ import annotations

import logging
from typing import Tuple

from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework_simplejwt.tokens import RefreshToken

from mysite.users.models import User

logger = logging.getLogger(__name__)


class EmailVerificationError(Exception):
    """Raised when email verification cannot be completed."""


class EmailVerificationService:
    """Encapsulates the email verification workflow."""

    @transaction.atomic
    def verify_and_login(self, user: User) -> Tuple[str, str]:
        """Verify the user's email and issue fresh JWT tokens.

        Args:
            user: User instance whose email should be verified.

        Returns:
            Tuple of (access_token, refresh_token).

        Raises:
            EmailVerificationError: If verification cannot proceed (e.g. inactive user).
        """
        if not user.is_active:
            raise EmailVerificationError(_('Cannot verify inactive user account'))

        if user.email_verified:
            logger.warning(
                "Re-verification attempt for already verified user",
                extra={'user_id': user.id},
            )
        else:
            user.email_verified = True
            user.save(update_fields=['email_verified'])

        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token), str(refresh)


__all__ = ['EmailVerificationService', 'EmailVerificationError']
