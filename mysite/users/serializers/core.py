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
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'email_verified', 'date_joined']


__all__ = ['CircleSerializer', 'UserSerializer']
