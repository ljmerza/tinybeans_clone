"""Serializers for Keep comments."""
from rest_framework import serializers

from ..models import KeepComment


class KeepCommentSerializer(serializers.ModelSerializer):
    """Serializer for keep comments."""

    user_display_name = serializers.CharField(source='user.display_name', read_only=True)
    parent = serializers.PrimaryKeyRelatedField(
        queryset=KeepComment.objects.all(), required=False, allow_null=True,
        help_text='Id of the comment this one replies to; omit for a top-level comment',
    )

    class Meta:
        model = KeepComment
        fields = [
            'id',
            'user',
            'user_display_name',
            'parent',
            'comment',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def validate(self, attrs):
        parent = attrs.get('parent')
        keep = attrs.get('keep') or getattr(self.instance, 'keep', None)
        if parent is not None and keep is not None and parent.keep_id != keep.id:
            raise serializers.ValidationError({'parent': 'Reply must be on the same keep as its parent.'})
        return attrs
