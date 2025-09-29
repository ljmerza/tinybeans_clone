"""Core serializers for shared Keep models.

This module provides serializers for models that are used across
multiple features: media files and milestones.
"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from ..models import KeepMedia, Milestone


class KeepMediaSerializer(serializers.ModelSerializer):
    """Serializer for keep media files."""
    
    urls = serializers.SerializerMethodField()
    
    class Meta:
        model = KeepMedia
        fields = [
            'id',
            'media_type',
            'caption',
            'upload_order',
            'file_size',
            'original_filename',
            'content_type',
            'width',
            'height',
            'thumbnails_generated',
            'urls',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'file_size',
            'original_filename',
            'content_type',
            'width',
            'height',
            'thumbnails_generated',
            'urls',
            'created_at'
        ]
    
    @extend_schema_field({'type': 'object', 'properties': {
        'original': {'type': 'string', 'format': 'uri'},
        'thumbnail': {'type': 'string', 'format': 'uri'},
        'gallery': {'type': 'string', 'format': 'uri'},
    }})
    def get_urls(self, obj):
        """Get URLs for all available sizes."""
        return obj.get_all_urls()


class MilestoneSerializer(serializers.ModelSerializer):
    """Serializer for milestone information."""
    
    child_name = serializers.CharField(source='child_profile.name', read_only=True)
    
    class Meta:
        model = Milestone
        fields = [
            'milestone_type',
            'child_profile',
            'child_name',
            'age_at_milestone',
            'notes',
            'is_first_time',
        ]
