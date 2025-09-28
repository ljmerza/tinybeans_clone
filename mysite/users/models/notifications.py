"""User notification preferences models.

This module defines models for managing user notification preferences,
including channels (email, push) and frequency settings for different
types of notifications within circles.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

from .circle import Circle


class NotificationChannel(models.TextChoices):
    """Available channels for sending notifications.
    
    Defines the different ways notifications can be delivered to users.
    """
    EMAIL = 'email', 'Email'
    PUSH = 'push', 'Push'


class DigestFrequency(models.TextChoices):
    """Frequency options for digest notifications.
    
    Controls how often digest notifications are sent to users.
    """
    NEVER = 'never', 'Never'
    DAILY = 'daily', 'Daily'
    WEEKLY = 'weekly', 'Weekly'


class UserNotificationPreferences(models.Model):
    """User's notification preferences for a specific circle or globally.
    
    Stores user preferences for different types of notifications. Can be
    circle-specific (when circle is set) or global defaults (when circle is None).
    
    Attributes:
        user: The user these preferences belong to
        circle: Specific circle these preferences apply to (None for global)
        notify_new_media: Whether to notify about new photos/videos
        notify_weekly_digest: Whether to send weekly digest emails
        channel: Preferred notification channel (email or push)
        digest_frequency: How often to send digest notifications
        push_enabled: Whether push notifications are enabled
        created_at: When these preferences were created
        updated_at: When these preferences were last modified
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_preferences')
    circle = models.ForeignKey(Circle, on_delete=models.CASCADE, related_name='notification_preferences', null=True, blank=True)
    notify_new_media = models.BooleanField(default=True)
    notify_weekly_digest = models.BooleanField(default=True)
    channel = models.CharField(max_length=20, choices=NotificationChannel.choices, default=NotificationChannel.EMAIL)
    digest_frequency = models.CharField(
        max_length=20,
        choices=DigestFrequency.choices,
        default=DigestFrequency.WEEKLY,
    )
    push_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (('user', 'circle'),)

    @property
    def is_circle_override(self) -> bool:
        """Check if these preferences are circle-specific overrides.
        
        Returns:
            True if this is a circle-specific override, False if global defaults
        """
        return self.circle_id is not None

    def __str__(self):
        target = self.circle.name if self.circle else 'all circles'
        return f"Preferences for {self.user} ({target})"