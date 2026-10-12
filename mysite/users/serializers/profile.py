"""Serializers for profile and preference management."""

from __future__ import annotations

from django.conf import settings
from rest_framework import serializers

from mysite.notification_utils import create_message

from ..models import (
    NotificationChannel,
    NotificationPhone,
    User,
    UserNotificationPreferences,
    channel_fields,
)


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
            "new_media_email",
            "new_media_sms",
            "new_media_push",
            "comments_email",
            "comments_sms",
            "comments_push",
            "replies_email",
            "replies_sms",
            "replies_push",
            "likes_email",
            "likes_sms",
            "likes_push",
            "email_digest",
            "circle_id",
            "per_circle_override",
        ]
        read_only_fields = ["circle_id", "per_circle_override"]

    def validate(self, attrs):
        # Accepting texts or pushes that can't be sent would silently drop notifications.
        errors = {}
        sms_on = [field for field in channel_fields(NotificationChannel.SMS) if attrs.get(field)]
        if sms_on:
            if not getattr(settings, "NOTIFICATIONS_SMS_ENABLED", False):
                errors.update(dict.fromkeys(sms_on, create_message("errors.notification_channel_unavailable")))
            elif not NotificationPhone.objects.filter(user=self.instance.user, verified_at__isnull=False).exists():
                errors.update(dict.fromkeys(sms_on, create_message("errors.notification_phone_unverified")))
        push_on = [field for field in channel_fields(NotificationChannel.PUSH) if attrs.get(field)]
        if push_on and not getattr(settings, "NOTIFICATIONS_PUSH_ENABLED", False):
            errors.update(dict.fromkeys(push_on, create_message("errors.notification_channel_unavailable")))
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

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
