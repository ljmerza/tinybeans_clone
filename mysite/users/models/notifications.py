"""User notification preferences models.

This module defines models for managing user notification preferences,
which circle events a user hears about and the channel (email, phone)
they arrive on. Preferences are global or overridden per circle.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

from .circle import Circle


class NotificationChannel(models.TextChoices):
    """Available channels for sending notifications.

    Defines the different ways notifications can be delivered to users.
    """

    EMAIL = "email", "Email"
    SMS = "sms", "Phone"


class UserNotificationPreferences(models.Model):
    """User's notification preferences for a specific circle or globally.

    Stores user preferences for different types of notifications. Can be
    circle-specific (when circle is set) or global defaults (when circle is None).

    Attributes:
        user: The user these preferences belong to
        circle: Specific circle these preferences apply to (None for global)
        notify_new_media: Whether to notify about new photos/videos in the circle
        notify_comments: Whether to notify about comments on the user's posts
        notify_replies: Whether to notify when someone replies to (tags) the user in a comment
        notify_likes: Whether to notify when someone likes the user's posts
        channel: Channel notifications are delivered on (email or phone)
        email_digest: Whether to get the daily email listing new posts across all circles.
            Global only: the digest reads the user's global row, and the copy a circle
            override carries is ignored.
        digest_covered_until: Posts created up to this time were covered by an earlier
            digest (sent, or skipped because nothing was new). Global row only.
        created_at: When these preferences were created
        updated_at: When these preferences were last modified
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_preferences"
    )
    circle = models.ForeignKey(
        Circle, on_delete=models.CASCADE, related_name="notification_preferences", null=True, blank=True
    )
    notify_new_media = models.BooleanField(default=True)
    notify_comments = models.BooleanField(default=True)
    notify_replies = models.BooleanField(default=True)
    notify_likes = models.BooleanField(default=True)
    channel = models.CharField(max_length=20, choices=NotificationChannel.choices, default=NotificationChannel.EMAIL)
    email_digest = models.BooleanField(default=False)
    digest_covered_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (("user", "circle"),)

    def __str__(self):
        target = self.circle.name if self.circle else "all circles"
        return f"Preferences for {self.user} ({target})"

    @property
    def is_circle_override(self) -> bool:
        """Check if these preferences are circle-specific overrides.

        Returns:
            True if this is a circle-specific override, False if global defaults
        """
        return self.circle_id is not None

    @classmethod
    def effective_for(cls, user, circle=None) -> "UserNotificationPreferences":
        """Return the preferences that apply to ``user`` in ``circle``.

        A circle override wins over the user's global row, which wins over the
        model defaults (returned as an unsaved instance).
        """
        return cls.effective_for_users([user], circle)[user.id]

    @classmethod
    def effective_for_users(cls, users, circle=None) -> dict[int, "UserNotificationPreferences"]:
        """Resolve :meth:`effective_for` for many users in one query, keyed by user id."""
        users = list(users)
        scope = models.Q(circle__isnull=True)
        if circle is not None:
            scope |= models.Q(circle=circle)
        resolved = {}
        for prefs in cls.objects.filter(scope, user__in=users).order_by("id"):
            if prefs.circle_id is not None or prefs.user_id not in resolved:
                resolved[prefs.user_id] = prefs
        return {user.id: resolved.get(user.id) or cls(user=user) for user in users}
