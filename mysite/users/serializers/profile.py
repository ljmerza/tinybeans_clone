"""Serializers for profile and preference management."""
from __future__ import annotations

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..models import User, UserNotificationPreferences


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'email_verified', 'date_joined', 'language']
        read_only_fields = ['id', 'role', 'email_verified', 'date_joined']


class EmailPreferencesSerializer(serializers.ModelSerializer):
    circle_id = serializers.SerializerMethodField()
    per_circle_override = serializers.SerializerMethodField()

    class Meta:
        model = UserNotificationPreferences
        fields = [
            'notify_new_media',
            'notify_weekly_digest',
            'digest_frequency',
            'push_enabled',
            'channel',
            'circle_id',
            'per_circle_override',
        ]
        read_only_fields = ['circle_id', 'per_circle_override']

    def get_per_circle_override(self, obj) -> bool:
        return obj.is_circle_override

    def get_circle_id(self, obj) -> int | None:
        return obj.circle_id


__all__ = ['UserProfileSerializer', 'EmailPreferencesSerializer']
