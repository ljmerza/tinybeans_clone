"""Media file models for keeps."""
import uuid
import os
import tempfile
from django.db import models
from django.utils import timezone

from .keep import Keep


class MediaUploadStatus(models.TextChoices):
    """Status choices for media uploads."""
    PENDING = 'pending', 'Pending'
    VALIDATING = 'validating', 'Validating'
    PROCESSING = 'processing', 'Processing'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'


class MediaUpload(models.Model):
    """Tracks the status of media uploads being processed asynchronously."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    keep = models.ForeignKey(Keep, on_delete=models.CASCADE, related_name='uploads')
    media_type = models.CharField(
        max_length=10,
        choices=[
            ('photo', 'Photo'),
            ('video', 'Video'),
        ]
    )
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    file_size = models.PositiveIntegerField()
    caption = models.CharField(max_length=500, blank=True)
    upload_order = models.PositiveSmallIntegerField(default=0)
    temp_file_path = models.CharField(max_length=500)
    
    status = models.CharField(
        max_length=20,
        choices=MediaUploadStatus.choices,
        default=MediaUploadStatus.PENDING
    )
    error_message = models.TextField(blank=True)
    
    media_file = models.ForeignKey(
        'KeepMedia',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='upload_record'
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Upload {self.original_filename} for {self.keep}"


class KeepMedia(models.Model):
    """Media files associated with a keep.
    
    Stores photos and videos for keeps. For photos, generates multiple sizes:
    - thumbnail: 150x150 for quick previews
    - gallery: 800x600 for gallery display
    - full: original size for full viewing
    
    Videos are stored as-is without processing for now.
    """
    keep = models.ForeignKey(Keep, on_delete=models.CASCADE, related_name='media_files')
    media_type = models.CharField(
        max_length=10,
        choices=[
            ('photo', 'Photo'),
            ('video', 'Video'),
        ]
    )
    caption = models.CharField(max_length=500, blank=True)
    upload_order = models.PositiveSmallIntegerField(default=0)
    
    # Storage information
    storage_key_original = models.CharField(max_length=500)  # Original file
    storage_key_thumbnail = models.CharField(max_length=500, blank=True)  # 150x150
    storage_key_gallery = models.CharField(max_length=500, blank=True)    # 800x600
    
    # File metadata
    file_size = models.PositiveIntegerField(null=True, blank=True)
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    
    # Image dimensions (for photos)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    
    # Processing flags
    thumbnails_generated = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['upload_order', 'created_at']
        indexes = [
            models.Index(fields=['keep', 'upload_order']),
            models.Index(fields=['media_type']),
        ]

    def __str__(self):
        return f"{self.media_type} for {self.keep}"
    
    def get_url(self, size: str = 'original', expires_in: int = 3600) -> str:
        """Get URL for accessing this media file.
        
        Args:
            size: 'original', 'gallery', or 'thumbnail'
            expires_in: URL expiration time in seconds
        """
        from .storage import get_storage_backend
        
        storage = get_storage_backend()
        
        if size == 'thumbnail' and self.storage_key_thumbnail:
            storage_key = self.storage_key_thumbnail
        elif size == 'gallery' and self.storage_key_gallery:
            storage_key = self.storage_key_gallery
        else:
            storage_key = self.storage_key_original
        
        return storage.get_url(storage_key, expires_in)
    
    def get_all_urls(self, expires_in: int = 3600) -> dict:
        """Get URLs for all available sizes."""
        urls = {
            'original': self.get_url('original', expires_in)
        }
        
        if self.media_type == 'photo' and self.thumbnails_generated:
            urls.update({
                'thumbnail': self.get_url('thumbnail', expires_in),
                'gallery': self.get_url('gallery', expires_in),
            })
        
        return urls
    
    def delete_from_storage(self):
        """Delete this media file and all sizes from storage."""
        from .storage import get_storage_backend
        
        storage = get_storage_backend()
        
        # Delete all versions
        storage.delete(self.storage_key_original)
        if self.storage_key_thumbnail:
            storage.delete(self.storage_key_thumbnail)
        if self.storage_key_gallery:
            storage.delete(self.storage_key_gallery)