"""Serializers for Keep comments."""
from rest_framework import serializers

from ..models import KeepComment


class KeepCommentSerializer(serializers.ModelSerializer):
    """Serializer for keep comments."""

    user_display_name = serializers.CharField(source='user.display_name', read_only=True)
    
    class Meta:
        model = KeepComment
        fields = [
            'id',
            'user',
            'user_display_name',
            'comment',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
