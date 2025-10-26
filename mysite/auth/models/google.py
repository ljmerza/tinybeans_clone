"""Google OAuth related models."""
from __future__ import annotations

from django.db import models
from django.utils import timezone


class GoogleOAuthState(models.Model):
    """Secure OAuth state token tracking."""

    state_token = models.CharField(
        max_length=128,
        unique=True,
        db_index=True,
        help_text="Unique OAuth state token"
    )
    code_verifier = models.CharField(
        max_length=128,
        help_text="PKCE code verifier"
    )
    redirect_uri = models.URLField(
        help_text="OAuth redirect URI"
    )
    nonce = models.CharField(
        max_length=64,
        help_text="Additional CSRF protection nonce"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When state was created"
    )
    used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When state was used"
    )
    ip_address = models.GenericIPAddressField(
        help_text="IP address that initiated OAuth"
    )
    user_agent = models.TextField(
        help_text="User agent that initiated OAuth"
    )
    expires_at = models.DateTimeField(
        db_index=True,
        help_text="When state expires (10 min)"
    )

    class Meta:
        verbose_name = 'Google OAuth State'
        verbose_name_plural = 'Google OAuth States'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['state_token', 'used_at'], name='auth_oauth_state_idx'),
            models.Index(fields=['expires_at'], name='auth_oauth_expires_idx'),
        ]

    def __str__(self):
        return f"OAuth State {self.state_token[:8]}... - {'Used' if self.used_at else 'Unused'}"

    def is_valid(self):
        """Check if state is still valid for use."""
        return (
            not self.used_at and
            self.expires_at > timezone.now()
        )

    def is_used(self):
        """Check if state has been used."""
        return self.used_at is not None

    def is_expired(self):
        """Check if state has expired."""
        return self.expires_at <= timezone.now()

    def mark_as_used(self):
        """Mark state as used to prevent replay attacks."""
        self.used_at = timezone.now()
        self.save(update_fields=['used_at'])
