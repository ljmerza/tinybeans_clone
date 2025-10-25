"""Serializers for Keep models.

This module provides serializers for creating, updating, and retrieving
family memories (keeps) with their associated data.
"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from ..models import Keep, KeepType, KeepMedia, Milestone
from mysite.circles.models import CircleMembership
from mysite.users.models import UserRole
from .core import KeepMediaSerializer, MilestoneSerializer
from mysite.notification_utils import create_message


class KeepSerializer(serializers.ModelSerializer):
    """Basic serializer for keeps - used in list views."""

    created_by_display_name = serializers.CharField(source='created_by.display_name', read_only=True)
    circle_name = serializers.CharField(source='circle.name', read_only=True)
    media_count = serializers.SerializerMethodField()
    reaction_count = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    tag_list = serializers.SerializerMethodField()
    
    class Meta:
        model = Keep
        fields = [
            'id',
            'circle',
            'circle_name',
            'created_by',
            'created_by_display_name',
            'keep_type',
            'title',
            'description',
            'date_of_memory',
            'created_at',
            'updated_at',
            'is_public',
            'tags',
            'tag_list',
            'media_count',
            'reaction_count',
            'comment_count',
        ]
        read_only_fields = [
            'id',
            'created_by',
            'created_at',
            'updated_at',
            'media_count',
            'reaction_count',
            'comment_count',
        ]
    
    @extend_schema_field({'type': 'integer'})
    def get_media_count(self, obj):
        """Return the number of media files for this keep."""
        return obj.media_files.count()
    
    @extend_schema_field({'type': 'integer'})
    def get_reaction_count(self, obj):
        """Return the number of reactions for this keep."""
        return obj.reactions.count()
    
    @extend_schema_field({'type': 'integer'})
    def get_comment_count(self, obj):
        """Return the number of comments for this keep."""
        return obj.comments.count()
    
    @extend_schema_field({'type': 'array', 'items': {'type': 'string'}})
    def get_tag_list(self, obj):
        """Return tags as a list of strings."""
        if obj.tags:
            return [tag.strip() for tag in obj.tags.split(',') if tag.strip()]
        return []


class KeepDetailSerializer(KeepSerializer):
    """Detailed serializer for keeps - includes related objects."""
    
    from .reactions import KeepReactionSerializer
    from .comments import KeepCommentSerializer
    
    media_files = KeepMediaSerializer(many=True, read_only=True)
    milestone = MilestoneSerializer(read_only=True)
    reactions = KeepReactionSerializer(many=True, read_only=True)
    comments = KeepCommentSerializer(many=True, read_only=True)
    
    class Meta(KeepSerializer.Meta):
        fields = KeepSerializer.Meta.fields + [
            'media_files',
            'milestone', 
            'reactions',
            'comments',
        ]


class KeepCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new keeps."""
    
    media_files = KeepMediaSerializer(many=True, required=False)
    milestone_data = MilestoneSerializer(required=False, write_only=True)
    
    class Meta:
        model = Keep
        fields = [
            'circle',
            'keep_type',
            'title',
            'description',
            'date_of_memory',
            'is_public',
            'tags',
            'media_files',
            'milestone_data',
        ]
    
    def validate(self, data):
        """Validate keep data based on type and user permissions."""
        keep_type = data.get('keep_type')
        milestone_data = data.get('milestone_data')
        media_files = data.get('media_files', [])
        circle = data.get('circle')
        user = self.context['request'].user
        
        # Check if user is a member of the circle
        if circle:
            try:
                CircleMembership.objects.get(user=user, circle=circle)
            except CircleMembership.DoesNotExist:
                raise serializers.ValidationError({
                    'circle': create_message('errors.circle_membership_required')
                })
        
        # Milestone keeps should have milestone data
        if keep_type == KeepType.MILESTONE and not milestone_data:
            raise serializers.ValidationError({
                'milestone_data': create_message('errors.milestone_required')
            })
        
        # Non-milestone keeps shouldn't have milestone data
        if keep_type != KeepType.MILESTONE and milestone_data:
            raise serializers.ValidationError({
                'milestone_data': create_message('errors.milestone_not_allowed')
            })
        
        # Media keeps should have media files
        if keep_type == KeepType.MEDIA and not media_files:
            raise serializers.ValidationError({
                'media_files': create_message('errors.media_files_required')
            })
        
        # Note keeps don't require media files but can have them
        # (Notes can optionally include media attachments)
        
        return data
    
    def create(self, validated_data):
        """Create a new keep with related objects."""
        media_files_data = validated_data.pop('media_files', [])
        milestone_data = validated_data.pop('milestone_data', None)
        
        # Set the creator to the current user
        validated_data['created_by'] = self.context['request'].user
        
        # Create the keep
        keep = Keep.objects.create(**validated_data)
        
        # Create media files
        for media_data in media_files_data:
            KeepMedia.objects.create(keep=keep, **media_data)
        
        # Create milestone data if provided
        if milestone_data:
            Milestone.objects.create(keep=keep, **milestone_data)
        
        return keep


class KeepUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating existing keeps."""
    
    class Meta:
        model = Keep
        fields = [
            'title',
            'description',
            'date_of_memory',
            'is_public',
            'tags',
        ]
    
    def validate(self, data):
        """Ensure user can update this keep (creator or circle admin)."""
        user = self.context['request'].user
        keep = self.instance
        
        # Check if user is creator
        if keep.created_by == user:
            return data
        
        # Check if user is circle admin
        try:
            membership = CircleMembership.objects.get(user=user, circle=keep.circle)
            if membership.role == UserRole.CIRCLE_ADMIN:
                return data
        except CircleMembership.DoesNotExist:
            pass
        
        raise serializers.ValidationError(
            create_message('errors.keep_update_forbidden')
        )
