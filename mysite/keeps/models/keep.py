"""Keep models for family memories and moments."""
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class KeepType(models.TextChoices):
    """Type of keep/memory content.
    
    Defines the different types of content that can be stored as memories.
    A keep can be either a note (text-based) or media (with attached files).
    """
    NOTE = 'note', 'Note'
    MEDIA = 'media', 'Media'
    MILESTONE = 'milestone', 'Milestone'


class Keep(models.Model):
    """A family memory or moment shared within a circle.
    
    Represents a single memory/moment that can include photos, videos, text,
    or milestone information. Each keep belongs to a circle and is created by a user.
    
    Attributes:
        id: UUID primary key for secure keep identification
        circle: The circle this keep belongs to
        created_by: User who created this keep
        keep_type: Type of content (photo, video, text, milestone)
        title: Optional title for the keep
        description: Detailed description or caption
        date_of_memory: When the memory actually occurred (can differ from created_at)
        created_at: When the keep was uploaded/created
        updated_at: When the keep was last modified
        is_public: Whether the keep is visible to all circle members
        tags: Comma-separated tags for categorization
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    circle = models.ForeignKey(
        'users.Circle',
        on_delete=models.CASCADE,
        related_name='keeps'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='keeps_created'
    )
    keep_type = models.CharField(
        max_length=20,
        choices=KeepType.choices,
        default=KeepType.NOTE
    )
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    date_of_memory = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_public = models.BooleanField(default=True)
    tags = models.CharField(max_length=500, blank=True, help_text="Comma-separated tags")

    class Meta:
        ordering = ['-date_of_memory', '-created_at']
        indexes = [
            models.Index(fields=['circle', '-date_of_memory']),
            models.Index(fields=['created_by', '-created_at']),
            models.Index(fields=['keep_type']),
        ]

    def __str__(self):
        return f"{self.title or self.keep_type} by {self.created_by} in {self.circle}"

    @property
    def tag_list(self):
        """Return tags as a list."""
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
    
    @property
    def media_types(self):
        """Return a list of media types present in this keep."""
        return list(self.media_files.values_list('media_type', flat=True).distinct())
    
    @property
    def has_photos(self):
        """Return True if this keep has photo attachments."""
        return self.media_files.filter(media_type='photo').exists()
    
    @property
    def has_videos(self):
        """Return True if this keep has video attachments."""
        return self.media_files.filter(media_type='video').exists()
    
    @property
    def primary_media_type(self):
        """Return the primary media type for display purposes."""
        media_types = self.media_types
        if not media_types:
            return None
        if 'video' in media_types:
            return 'video'  # Videos take precedence
        if 'photo' in media_types:
            return 'photo'
        return media_types[0]