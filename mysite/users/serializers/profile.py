"""Serializers for profile and preference management."""

from __future__ import annotations

from django.conf import settings
from rest_framework import serializers

from mysite.notification_utils import create_message

from ..models import NotificationPhone, User, UserNotificationPreferences


class UserProfileSerializer(serializers.ModelSerializer):
    needs_circle_onboarding = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    has_usable_password = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "display_name",
            "role",
            "email_verified",
            "date_joined",
            "language",
            "color_theme",
            "measurement_units",
            "circle_onboarding_status",
            "circle_onboarding_updated_at",
            "needs_circle_onboarding",
            "has_usable_password",
        ]
        read_only_fields = [
            "id",
            "role",
            "email_verified",
            "date_joined",
            "circle_onboarding_status",
            "circle_onboarding_updated_at",
            "needs_circle_onboarding",
            "display_name",
        ]

    def get_needs_circle_onboarding(self, obj) -> bool:
        return obj.needs_circle_onboarding

    def get_display_name(self, obj) -> str:
        return obj.display_name

    def get_has_usable_password(self, obj) -> bool:
        """False for Google / magic-link / imported accounts that never set a password."""
        return obj.has_usable_password()


class EmailPreferencesSerializer(serializers.ModelSerializer):
    circle_id = serializers.SerializerMethodField()
    per_circle_override = serializers.SerializerMethodField()

    class Meta:
        model = UserNotificationPreferences
        fields = [
            "notify_new_media",
            "notify_comments",
            "notify_replies",
            "notify_likes",
            "email_enabled",
            "sms_enabled",
            "push_enabled",
            "email_digest",
            "circle_id",
            "per_circle_override",
        ]
        read_only_fields = ["circle_id", "per_circle_override"]

    def validate_sms_enabled(self, value):
        # Accepting texts that can't be sent would silently drop notifications.
        if value and not getattr(settings, "NOTIFICATIONS_SMS_ENABLED", False):
            raise serializers.ValidationError(create_message("errors.notification_channel_unavailable"))
        if value and not NotificationPhone.objects.filter(user=self.instance.user, verified_at__isnull=False).exists():
            raise serializers.ValidationError(create_message("errors.notification_phone_unverified"))
        return value

    def validate_push_enabled(self, value):
        if value and not getattr(settings, "NOTIFICATIONS_PUSH_ENABLED", False):
            raise serializers.ValidationError(create_message("errors.notification_channel_unavailable"))
        return value

    def validate_email_digest(self, value):
        # The digest covers every circle at once, so only the global row has a say.
        if self.instance is not None and self.instance.circle_id is not None:
            raise serializers.ValidationError(create_message("errors.notification_digest_global_only"))
        return value

    def get_per_circle_override(self, obj) -> bool:
        return obj.is_circle_override

    def get_circle_id(self, obj) -> int | None:
        return obj.circle_id


__all__ = ["UserProfileSerializer", "EmailPreferencesSerializer"]
