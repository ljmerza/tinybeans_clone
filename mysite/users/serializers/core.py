"""Shared serializer primitives used across domains."""
from __future__ import annotations

from rest_framework import serializers

from ..models import Circle, User


class CircleSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Circle
        fields = ['id', 'name', 'slug', 'member_count']

    def get_member_count(self, obj):
        return obj.memberships.count()


class UserSerializer(serializers.ModelSerializer):
    needs_circle_onboarding = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'display_name',
            'role',
            'email_verified',
            'date_joined',
            'language',
            'circle_onboarding_status',
            'circle_onboarding_updated_at',
            'needs_circle_onboarding',
        ]
        read_only_fields = ['circle_onboarding_status', 'circle_onboarding_updated_at', 'needs_circle_onboarding', 'display_name']

    def get_needs_circle_onboarding(self, obj) -> bool:
        return obj.needs_circle_onboarding

    def get_display_name(self, obj) -> str:
        return obj.display_name


class PublicUserSerializer(serializers.ModelSerializer):
    """Limited user serializer safe for authentication responses."""

    needs_circle_onboarding = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'email_verified',
            'first_name',
            'last_name',
            'display_name',
            'needs_circle_onboarding',
            'circle_onboarding_status',
        ]
        read_only_fields = fields

    def get_needs_circle_onboarding(self, obj) -> bool:
        return obj.needs_circle_onboarding

    def get_display_name(self, obj) -> str:
        return obj.display_name


__all__ = ['CircleSerializer', 'UserSerializer', 'PublicUserSerializer']
