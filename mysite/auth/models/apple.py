"""Sign in with Apple related models."""

from __future__ import annotations

from django.db import models
from django.utils import timezone


class AppleOAuthState(models.Model):
    """One Sign in with Apple attempt, from initiate to callback.

    Apple's token endpoint takes no PKCE verifier, so the state token plus the
    nonce (checked in Apple's ID token) are what bind a callback to the browser
    that started it. Apple sends the user's name only on the very first
    authorization, in the form POST to the return view; it is parked here until
    the callback creates the account.
    """

    state_token = models.CharField(max_length=128, unique=True, db_index=True, help_text="Unique OAuth state token")
    nonce = models.CharField(max_length=64, help_text="Nonce Apple must echo in the ID token")
    return_uri = models.URLField(help_text="SPA URL the browser is sent to after Apple's POST")
    first_name = models.CharField(max_length=150, blank=True, default="", help_text="Name from Apple's first POST")
    last_name = models.CharField(max_length=150, blank=True, default="", help_text="Name from Apple's first POST")
    created_at = models.DateTimeField(auto_now_add=True, help_text="When state was created")
    used_at = models.DateTimeField(null=True, blank=True, help_text="When state was used")
    ip_address = models.GenericIPAddressField(help_text="IP address that initiated OAuth")
    user_agent = models.TextField(help_text="User agent that initiated OAuth")
    expires_at = models.DateTimeField(db_index=True, help_text="When state expires")

    class Meta:
        verbose_name = "Apple OAuth State"
        verbose_name_plural = "Apple OAuth States"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Apple OAuth State {self.state_token[:8]}... - {'Used' if self.used_at else 'Unused'}"

    def is_valid(self):
        """Check if state is still valid for use."""
        return not self.used_at and self.expires_at > timezone.now()

    def mark_as_used(self):
        """Atomically claim this state so it is usable exactly once.

        Same conditional UPDATE as ``GoogleOAuthState.mark_as_used`` (ADR-015).
        Returns ``True`` if this call claimed the state.
        """
        now = timezone.now()
        claimed = type(self).objects.filter(pk=self.pk, used_at__isnull=True).update(used_at=now)
        if claimed:
            self.used_at = now
            return True
        return False
