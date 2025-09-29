"""Serializers for Keep reactions."""
from rest_framework import serializers

from ..models import KeepReaction


class KeepReactionSerializer(serializers.ModelSerializer):
    """Serializer for keep reactions."""
    
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = KeepReaction
        fields = [
            'id',
            'user',
            'user_username',
            'reaction_type',
            'created_at',
        ]
        read_only_fields = ['id', 'user', 'created_at']
