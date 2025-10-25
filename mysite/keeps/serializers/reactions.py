"""Serializers for Keep reactions."""
from rest_framework import serializers

from ..models import KeepReaction


class KeepReactionSerializer(serializers.ModelSerializer):
    """Serializer for keep reactions."""

    user_display_name = serializers.CharField(source='user.display_name', read_only=True)

    class Meta:
        model = KeepReaction
        fields = [
            'id',
            'user',
            'user_display_name',
            'reaction_type',
            'created_at',
        ]
        read_only_fields = ['id', 'user', 'created_at']
