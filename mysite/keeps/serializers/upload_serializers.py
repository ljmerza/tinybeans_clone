"""Serializers for media upload functionality."""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from ..models import MediaUpload, KeepMedia


class MediaUploadSerializer(serializers.ModelSerializer):
    """Serializer for media upload records."""
    
    keep_title = serializers.CharField(source='keep.title', read_only=True)
    
    class Meta:
        model = MediaUpload
        fields = [
            'id',
            'keep',
            'keep_title',
            'media_type',
            'original_filename',
            'content_type',
            'file_size',
            'caption',
            'upload_order',
            'status',
            'error_message',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'status',
            'error_message',
            'created_at',
            'updated_at',
        ]


class MediaUploadStatusSerializer(serializers.ModelSerializer):
    """Serializer for media upload status checks."""
    
    keep_title = serializers.CharField(source='keep.title', read_only=True)
    media_urls = serializers.SerializerMethodField()
    progress_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = MediaUpload
        fields = [
            'id',
            'keep',
            'keep_title',
            'media_type',
            'original_filename',
            'status',
            'error_message',
            'progress_percentage',
            'media_urls',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'keep',
            'keep_title',
            'media_type',
            'original_filename',
            'status',
            'error_message',
            'progress_percentage',
            'media_urls',
            'created_at',
            'updated_at',
        ]
    
    @extend_schema_field({'type': 'object', 'properties': {
        'original': {'type': 'string', 'format': 'uri'},
        'thumbnail': {'type': 'string', 'format': 'uri'},
        'gallery': {'type': 'string', 'format': 'uri'},
    }, 'nullable': True})
    def get_media_urls(self, obj):
        """Get URLs for completed media file."""
        if obj.status == 'completed' and obj.media_file:
            return obj.media_file.get_all_urls()
        return None
    
    @extend_schema_field({'type': 'integer', 'minimum': 0, 'maximum': 100})
    def get_progress_percentage(self, obj):
        """Get upload progress as percentage."""
        status_progress = {
            'pending': 0,
            'validating': 25,
            'processing': 50,
            'completed': 100,
            'failed': 0,
        }
        return status_progress.get(obj.status, 0)


class KeepMediaDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for keep media with URLs."""
    
    urls = serializers.SerializerMethodField()
    
    class Meta:
        model = KeepMedia
        fields = [
            'id',
            'keep',
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
            'keep',
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
    
    def get_urls(self, obj):
        """Get URLs for all available sizes."""
        return obj.get_all_urls()