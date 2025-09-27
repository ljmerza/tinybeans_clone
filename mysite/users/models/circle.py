import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone

from .user import UserRole
from .utils import generate_unique_slug


class Circle(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='circles_created',
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self.name, Circle.objects)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class CircleMembership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    circle = models.ForeignKey(Circle, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.CIRCLE_MEMBER)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='memberships_invited',
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('user', 'circle')
        ordering = ['circle__name', 'user__username']

    def __str__(self):
        return f"{self.user} in {self.circle} ({self.role})"


class CircleInvitationStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    ACCEPTED = 'accepted', 'Accepted'
    DECLINED = 'declined', 'Declined'
    CANCELLED = 'cancelled', 'Cancelled'
    EXPIRED = 'expired', 'Expired'


class CircleInvitation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    circle = models.ForeignKey(Circle, on_delete=models.CASCADE, related_name='invitations')
    email = models.EmailField()
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='circle_invitations_sent',
    )
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.CIRCLE_MEMBER)
    status = models.CharField(
        max_length=20,
        choices=CircleInvitationStatus.choices,
        default=CircleInvitationStatus.PENDING,
    )
    created_at = models.DateTimeField(default=timezone.now)
    responded_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['circle', 'email']),
        ]

    def __str__(self):
        return f"Invite {self.email} to {self.circle} ({self.status})"