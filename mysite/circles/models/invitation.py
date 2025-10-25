"""Circle invitation model implementations."""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from mysite.users.models.user import UserRole

from .circle import Circle


class CircleInvitationStatus(models.TextChoices):
    """Status options for circle invitations."""

    PENDING = 'pending', 'Pending'
    ACCEPTED = 'accepted', 'Accepted'
    DECLINED = 'declined', 'Declined'
    CANCELLED = 'cancelled', 'Cancelled'
    EXPIRED = 'expired', 'Expired'


class CircleInvitation(models.Model):
    """An invitation for someone to join a circle."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    circle = models.ForeignKey(
        Circle,
        on_delete=models.CASCADE,
        related_name='invitations',
    )
    email = models.EmailField()
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='circle_invitations_sent',
    )
    invited_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='circle_invitations_received',
    )
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.CIRCLE_MEMBER,
    )
    status = models.CharField(
        max_length=20,
        choices=CircleInvitationStatus.choices,
        default=CircleInvitationStatus.PENDING,
    )
    created_at = models.DateTimeField(default=timezone.now)
    responded_at = models.DateTimeField(blank=True, null=True)
    reminder_sent_at = models.DateTimeField(blank=True, null=True)
    # ADR-0007: Auto-prune accepted invitations; archival metadata
    archived_at = models.DateTimeField(blank=True, null=True)
    archived_reason = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        app_label = 'users'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['circle', 'email']),
            models.Index(fields=['circle', 'invited_user']),
            models.Index(fields=['status', 'reminder_sent_at']),
            models.Index(fields=["circle", "archived_at"]),
        ]

    def __str__(self) -> str:
        identifier = self.invited_user.display_name if self.invited_user_id else self.email
        return f"Invite {identifier} to {self.circle} ({self.status})"


__all__ = ['CircleInvitation', 'CircleInvitationStatus']
