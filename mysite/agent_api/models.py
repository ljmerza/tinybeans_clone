"""API tokens scoped to one circle."""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class TokenStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    EXPIRED = "expired", "Expired"
    REVOKED = "revoked", "Revoked"


class RevokeReason(models.TextChoices):
    MANUAL = "manual", "Revoked by an admin"
    CREATOR_NOT_ADMIN = "creator_not_admin", "Creator is no longer a circle admin"
    CREATOR_REMOVED = "creator_removed", "Creator left the circle"
    CREATOR_INACTIVE = "creator_inactive", "Creator's account was deactivated"
    CREATOR_UNVERIFIED = "creator_unverified", "Creator's email is not verified"
    PASSWORD_CHANGED = "password_changed", "Creator changed their password"


class CircleApiToken(models.Model):
    """A bearer token that reads one circle through the agent API, and nothing else.

    Only the SHA-256 of the token is stored; the plaintext is shown once, when
    it is created. A token works only while its creator is still an active,
    verified admin of the circle; it is revoked automatically the first time
    that check fails, and never comes back.

    Attributes:
        circle: The only circle the token can read
        created_by: The circle admin who made it
        name: What the admin called it, e.g. "Claude Code on my laptop"
        token_hash: sha256 hex of the plaintext token
        display_prefix: The token's first 12 characters ("circ_" + 7), safe to show and log
        can_suggest: Whether it may propose milestones; fixed when created
        expires_at: When it stops working; null means never
        revoked_at: When it was revoked, by an admin or automatically
        revoked_by: The admin who revoked it (null when automatic)
        revoked_reason: Why it was revoked (see ``RevokeReason``)
        last_used_at: Last successful use, updated at most once a minute
        last_used_ip: The client address of that use
        created_at: When it was created
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    circle = models.ForeignKey("users.Circle", on_delete=models.CASCADE, related_name="api_tokens")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    name = models.CharField(max_length=100)
    token_hash = models.CharField(max_length=64, unique=True)
    display_prefix = models.CharField(max_length=12)
    can_suggest = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    revoked_reason = models.CharField(max_length=24, blank=True, choices=RevokeReason.choices)
    last_used_at = models.DateTimeField(null=True, blank=True)
    last_used_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["circle", "revoked_at"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.display_prefix}) in {self.circle}"

    @property
    def status(self) -> str:
        """Revoked, else expired, else active."""
        if self.revoked_at is not None:
            return TokenStatus.REVOKED
        if self.expires_at is not None and self.expires_at <= timezone.now():
            return TokenStatus.EXPIRED
        return TokenStatus.ACTIVE
