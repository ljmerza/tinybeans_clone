"""User notification preferences models.

This module defines models for managing user notification preferences,
which circle events a user hears about and the channels (email, text
message, web push) they arrive on. Preferences are global or overridden per
circle. It also holds the phone number texts go to and each device's push
subscription.
"""

from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.crypto import constant_time_compare, get_random_string, salted_hmac

from .circle import Circle


class NotificationChannel(models.TextChoices):
    """Available channels for sending notifications.

    Defines the different ways notifications can be delivered to users.
    """

    EMAIL = "email", "Email"
    SMS = "sms", "Phone"
    PUSH = "push", "Push"


# The preferences switch that turns each channel on.
CHANNEL_FIELDS = {
    NotificationChannel.EMAIL: "email_enabled",
    NotificationChannel.SMS: "sms_enabled",
    NotificationChannel.PUSH: "push_enabled",
}


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
        email_enabled: Whether notifications are sent by email
        sms_enabled: Whether notifications are texted to the user's verified phone
        push_enabled: Whether notifications are pushed to the user's subscribed devices
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
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    push_enabled = models.BooleanField(default=False)
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

    def enabled_channels(self) -> list[str]:
        """The channels these preferences send on, in a stable order."""
        return [channel for channel, field in CHANNEL_FIELDS.items() if getattr(self, field)]

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


# A texted verification code works this long, for this many guesses.
PHONE_CODE_TTL = timedelta(minutes=10)
PHONE_CODE_MAX_ATTEMPTS = 5


def _hash_phone_code(code: str) -> str:
    return salted_hmac("users.NotificationPhone.code", code, algorithm="sha256").hexdigest()


class NotificationPhone(models.Model):
    """The phone number a user's notification texts go to.

    Separate from the 2FA phone: verifying that one turns on two-factor login.
    Texts are only sent once ``verified_at`` is set; saving a new number clears it.

    Attributes:
        user: Owner of the number
        phone_number: E.164 number, e.g. +15551234567
        verified_at: When the user confirmed the number with a texted code (None until then)
        code_hash: HMAC of the pending verification code
        code_expires_at: When the pending code stops working
        code_attempts: Wrong guesses against the pending code
    """

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_phone")
    phone_number = models.CharField(max_length=20)
    verified_at = models.DateTimeField(null=True, blank=True)
    code_hash = models.CharField(max_length=64, blank=True, default="")
    code_expires_at = models.DateTimeField(null=True, blank=True)
    code_attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Notification phone for {self.user} (...{self.phone_number[-4:]})"

    @property
    def is_verified(self) -> bool:
        return self.verified_at is not None

    @property
    def is_pending(self) -> bool:
        """A code was texted, hasn't been used up, and hasn't expired."""
        return (
            bool(self.code_hash)
            and self.code_expires_at is not None
            and self.code_expires_at > timezone.now()
            and self.code_attempts < PHONE_CODE_MAX_ATTEMPTS
        )

    def issue_code(self) -> str:
        """Start a new verification: return a fresh code and keep only its hash (caller saves)."""
        code = get_random_string(6, allowed_chars="0123456789")
        self.code_hash = _hash_phone_code(code)
        self.code_expires_at = timezone.now() + PHONE_CODE_TTL
        self.code_attempts = 0
        return code

    def check_code(self, code: str) -> bool:
        """Mark the number verified if ``code`` matches the pending one; count a wrong guess otherwise."""
        if not self.is_pending:
            return False
        if not constant_time_compare(self.code_hash, _hash_phone_code(code)):
            self.code_attempts += 1
            self.save(update_fields=["code_attempts", "updated_at"])
            return False
        self.verified_at = timezone.now()
        self.code_hash = ""
        self.code_expires_at = None
        self.code_attempts = 0
        self.save(update_fields=["verified_at", "code_hash", "code_expires_at", "code_attempts", "updated_at"])
        return True


class PushSubscription(models.Model):
    """One browser or installed app that receives a user's web push notifications.

    The fields mirror the browser's ``PushSubscription.toJSON()``. An endpoint
    belongs to one browser profile, so it's unique across users.

    Attributes:
        user: Who the device's notifications are for
        endpoint: Push service URL for this device
        p256dh: Device public key used to encrypt payloads
        auth: Device auth secret used to encrypt payloads
        user_agent: Browser that subscribed, to tell devices apart
        last_used_at: Last time a notification was accepted by the push service
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="push_subscriptions")
    endpoint = models.URLField(max_length=1000, unique=True)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=100)
    user_agent = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)
    last_used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Push subscription for {self.user} ({self.user_agent[:40] or 'unknown device'})"

    def subscription_info(self) -> dict:
        """The subscription in the shape pywebpush expects."""
        return {"endpoint": self.endpoint, "keys": {"p256dh": self.p256dh, "auth": self.auth}}
