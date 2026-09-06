"""Serializers for Keep comments."""
from rest_framework import serializers

from mysite.circles.models import CircleMembership
from mysite.notification_utils import create_message

from ..models import Keep, KeepComment


class KeepCommentSerializer(serializers.ModelSerializer):
    """Serializer for keep comments."""

    user_display_name = serializers.CharField(source='user.display_name', read_only=True)
    keep = serializers.PrimaryKeyRelatedField(queryset=Keep.objects.all())
    parent = serializers.PrimaryKeyRelatedField(
        queryset=KeepComment.objects.all(), required=False, allow_null=True,
        help_text='Id of the comment this one replies to; omit for a top-level comment',
    )

    class Meta:
        model = KeepComment
        fields = [
            'id',
            'keep',
            'user',
            'user_display_name',
            'parent',
            'comment',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def validate_keep(self, keep):
        user = self.context['request'].user
        if not CircleMembership.objects.filter(user=user, circle=keep.circle).exists():
            raise serializers.ValidationError(create_message('errors.circle_membership_required'))
        return keep

    def validate(self, attrs):
        parent = attrs.get('parent')
        keep = attrs.get('keep') or getattr(self.instance, 'keep', None)
        if parent is not None and keep is not None and parent.keep_id != keep.id:
            raise serializers.ValidationError({'parent': 'Reply must be on the same keep as its parent.'})
        return attrs
