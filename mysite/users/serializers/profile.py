"""Serializers for profile and preference management."""

from __future__ import annotations

from django.conf import settings
from rest_framework import serializers

from mysite.notification_utils import create_message

from ..models import NotificationChannel, User, UserNotificationPreferences


class UserProfileSerializer(serializers.ModelSerializer):
    needs_circle_onboarding = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()

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
            "circle_onboarding_status",
            "circle_onboarding_updated_at",
            "needs_circle_onboarding",
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
            "channel",
            "circle_id",
            "per_circle_override",
        ]
        read_only_fields = ["circle_id", "per_circle_override"]

    def validate_channel(self, value):
        # Phone delivery is not wired up yet; accepting it would silently drop notifications.
        if value == NotificationChannel.SMS and not getattr(settings, "NOTIFICATIONS_SMS_ENABLED", False):
            raise serializers.ValidationError(create_message("errors.notification_channel_unavailable"))
        return value

    def get_per_circle_override(self, obj) -> bool:
        return obj.is_circle_override

    def get_circle_id(self, obj) -> int | None:
        return obj.circle_id


__all__ = ["UserProfileSerializer", "EmailPreferencesSerializer"]
