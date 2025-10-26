"""Passwordless / magic link authentication models."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


class MagicLoginToken(models.Model):
    """Magic login link tokens for passwordless authentication."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='magic_login_tokens')
    token = models.CharField(max_length=64, blank=True, default='')
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    is_used = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Magic Login Token'
        verbose_name_plural = 'Magic Login Tokens'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token_hash', 'is_used'], name='auth_app_ma_tokenhash_idx'),
            models.Index(fields=['user', 'expires_at'], name='auth_app_ma_user_id_f5d5d3_idx'),
        ]

    def __str__(self):
        return f"{self.user.email} - {'Used' if self.is_used else 'Unused'} - {self.created_at}"

    def is_valid(self):
        """Check if token is still valid."""
        return not self.is_used and self.expires_at > timezone.now()

    def mark_as_used(self):
        """Mark token as used."""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])
