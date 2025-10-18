"""Circle management models.

This module defines models for family circles, including circle creation,
membership management, and invitation system for the Tinybeans application.
"""
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone

from .user import UserRole
from .utils import generate_unique_slug


class Circle(models.Model):
    """A family circle for sharing content and memories.
    
    A circle represents a family group where members can share photos, videos,
    and other content related to children and family life. Each circle has a
    unique slug for URL-friendly access.
    
    Attributes:
        name: Human-readable name of the circle
        slug: URL-friendly unique identifier (auto-generated from name)
        created_by: User who created the circle
        created_at: Timestamp when the circle was created
    """
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
        """Save the circle, auto-generating slug if not provided."""
        if not self.slug:
            self.slug = generate_unique_slug(self.name, Circle.objects)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class CircleMembership(models.Model):
    """Represents a user's membership in a circle.
    
    Tracks which users belong to which circles, their roles within those circles,
    and who invited them. Each user can only be a member of a circle once.
    
    Attributes:
        user: The user who is a member of the circle
        circle: The circle the user belongs to
        role: The user's role within this specific circle
        invited_by: The user who invited this member (optional)
        created_at: When the membership was created
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='circle_memberships',
    )
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
    """Status options for circle invitations.
    
    Tracks the lifecycle of invitations from creation to resolution.
    """
    PENDING = 'pending', 'Pending'
    ACCEPTED = 'accepted', 'Accepted'
    DECLINED = 'declined', 'Declined'
    CANCELLED = 'cancelled', 'Cancelled'
    EXPIRED = 'expired', 'Expired'


class CircleInvitation(models.Model):
    """An invitation for someone to join a circle.
    
    Represents pending invitations sent to email addresses. Uses UUID as primary
    key for security and includes tracking of invitation lifecycle.
    
    Attributes:
        id: UUID primary key for secure invitation links
        circle: The circle being invited to
        email: Email address of the invited person
        invited_by: User who sent the invitation
        role: Role the invitee will have if they accept
        status: Current status of the invitation
        created_at: When the invitation was sent
        responded_at: When the invitation was responded to (if applicable)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    circle = models.ForeignKey(Circle, on_delete=models.CASCADE, related_name='invitations')
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
            models.Index(fields=['circle', 'invited_user']),
        ]

    def __str__(self):
        identifier = self.invited_user.username if self.invited_user_id else self.email
        return f"Invite {identifier} to {self.circle} ({self.status})"
