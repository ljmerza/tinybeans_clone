"""Custom DRF permission classes for authentication flows."""
from __future__ import annotations

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission


class IsEmailVerified(BasePermission):
    """Require authenticated users to have verified email addresses."""

    redirect_url = '/verify-email-required'

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False
        if not user.is_active:
            return False
        if not getattr(settings, 'EMAIL_VERIFICATION_ENFORCED', True):
            return True
        if not getattr(user, 'email_verified', False):
            raise PermissionDenied(
                {
                    'error': 'email_verification_required',
                    'message_key': 'errors.email_verification_required',
                    'redirect_to': self.redirect_url,
                }
            )
        return True


__all__ = ['IsEmailVerified']
