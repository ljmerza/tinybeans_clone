"""Circle membership model implementation."""

from django.conf import settings
from django.db import models
from django.utils import timezone

from mysite.users.models.user import UserRole

from .circle import Circle


class CircleMembership(models.Model):
    """Represents a user's membership in a circle."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='circle_memberships',
    )
    circle = models.ForeignKey(
        Circle,
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.CIRCLE_MEMBER,
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='memberships_invited',
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        app_label = 'users'
        unique_together = ('user', 'circle')
        ordering = ['circle__name', 'user__email']

    def __str__(self) -> str:
        return f"{self.user} in {self.circle} ({self.role})"


__all__ = ['CircleMembership']
