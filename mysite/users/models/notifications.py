from django.conf import settings
from django.db import models
from django.utils import timezone

from .circle import Circle


class NotificationChannel(models.TextChoices):
    EMAIL = 'email', 'Email'
    PUSH = 'push', 'Push'


class DigestFrequency(models.TextChoices):
    NEVER = 'never', 'Never'
    DAILY = 'daily', 'Daily'
    WEEKLY = 'weekly', 'Weekly'


class UserNotificationPreferences(models.Model):
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
        return self.circle_id is not None

    def __str__(self):
        target = self.circle.name if self.circle else 'all circles'
        return f"Preferences for {self.user} ({target})"