"""Admin configuration for the keeps app."""
from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Keep,
    KeepMedia,
    Milestone,
    KeepReaction,
    KeepComment,
)


class KeepMediaInline(admin.TabularInline):
    """Inline admin for keep media files."""
    model = KeepMedia
    extra = 0
    readonly_fields = ['file_size', 'created_at']
    fields = ['media_type', 'caption', 'upload_order', 'file_size', 'created_at']


class MilestoneInline(admin.StackedInline):
    """Inline admin for milestone data."""
    model = Milestone
    extra = 0
    fields = ['milestone_type', 'child_profile', 'age_at_milestone', 'notes', 'is_first_time']


class KeepReactionInline(admin.TabularInline):
    """Inline admin for keep reactions."""
    model = KeepReaction
    extra = 0
    readonly_fields = ['user', 'reaction_type', 'created_at']
    fields = ['user', 'reaction_type', 'created_at']


class KeepCommentInline(admin.TabularInline):
    """Inline admin for keep comments."""
    model = KeepComment
    extra = 0
    readonly_fields = ['user', 'created_at', 'updated_at']
    fields = ['user', 'comment', 'created_at', 'updated_at']


@admin.register(Keep)
class KeepAdmin(admin.ModelAdmin):
    """Admin interface for Keep model."""
    
    list_display = [
        'title_or_type',
        'circle',
        'created_by',
        'keep_type',
        'date_of_memory',
        'is_public',
        'media_count',
        'reaction_count',
        'comment_count',
    ]
    
    list_filter = [
        'keep_type',
        'is_public',
        'circle',
        'created_at',
        'date_of_memory',
    ]
    
    search_fields = [
        'title',
        'description',
        'tags',
        'created_by__username',
        'circle__name',
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'media_count',
        'reaction_count',
        'comment_count',
    ]
    
    fields = [
        'id',
        'circle',
        'created_by',
        'keep_type',
        'title',
        'description',
        'date_of_memory',
        'is_public',
        'tags',
        'created_at',
        'updated_at',
        'media_count',
        'reaction_count',
        'comment_count',
    ]
    
    inlines = [KeepMediaInline, MilestoneInline, KeepReactionInline, KeepCommentInline]
    
    def title_or_type(self, obj):
        """Return title if available, otherwise the keep type."""
        return obj.title or obj.get_keep_type_display()
    title_or_type.short_description = 'Title/Type'
    
    def media_count(self, obj):
        """Return the number of media files."""
        return obj.media_files.count()
    media_count.short_description = 'Media Files'
    
    def reaction_count(self, obj):
        """Return the number of reactions."""
        return obj.reactions.count()
    reaction_count.short_description = 'Reactions'
    
    def comment_count(self, obj):
        """Return the number of comments."""
        return obj.comments.count()
    comment_count.short_description = 'Comments'


@admin.register(KeepMedia)
class KeepMediaAdmin(admin.ModelAdmin):
    """Admin interface for KeepMedia model."""
    
    list_display = [
        'keep_title',
        'media_type',
        'caption',
        'file_size_display',
        'upload_order',
        'created_at',
    ]
    
    list_filter = [
        'media_type',
        'created_at',
        'keep__keep_type',
        'keep__circle',
    ]
    
    search_fields = [
        'caption',
        'keep__title',
        'keep__description',
    ]
    
    readonly_fields = ['file_size', 'created_at']
    
    def keep_title(self, obj):
        """Return the keep title or type."""
        return obj.keep.title or obj.keep.get_keep_type_display()
    keep_title.short_description = 'Keep'
    
    def file_size_display(self, obj):
        """Display file size in human readable format."""
        if obj.file_size:
            size = obj.file_size
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
            return f"{size:.1f} TB"
        return '-'
    file_size_display.short_description = 'File Size'


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    """Admin interface for Milestone model."""
    
    list_display = [
        'milestone_type',
        'child_name',
        'age_at_milestone',
        'keep_title',
        'is_first_time',
    ]
    
    list_filter = [
        'milestone_type',
        'is_first_time',
        'keep__date_of_memory',
        'child_profile',
    ]
    
    search_fields = [
        'notes',
        'child_profile__name',
        'keep__title',
        'keep__description',
    ]
    
    def child_name(self, obj):
        """Return the child's name."""
        return obj.child_profile.name if obj.child_profile else '-'
    child_name.short_description = 'Child'
    
    def keep_title(self, obj):
        """Return the keep title or type."""
        return obj.keep.title or obj.keep.get_keep_type_display()
    keep_title.short_description = 'Keep'


@admin.register(KeepReaction)
class KeepReactionAdmin(admin.ModelAdmin):
    """Admin interface for KeepReaction model."""
    
    list_display = [
        'user',
        'keep_title',
        'reaction_type',
        'created_at',
    ]
    
    list_filter = [
        'reaction_type',
        'created_at',
        'keep__keep_type',
        'keep__circle',
    ]
    
    search_fields = [
        'user__username',
        'keep__title',
        'keep__description',
    ]
    
    readonly_fields = ['created_at']
    
    def keep_title(self, obj):
        """Return the keep title or type."""
        return obj.keep.title or obj.keep.get_keep_type_display()
    keep_title.short_description = 'Keep'


@admin.register(KeepComment)
class KeepCommentAdmin(admin.ModelAdmin):
    """Admin interface for KeepComment model."""
    
    list_display = [
        'user',
        'keep_title',
        'comment_preview',
        'created_at',
        'updated_at',
    ]
    
    list_filter = [
        'created_at',
        'updated_at',
        'keep__keep_type',
        'keep__circle',
    ]
    
    search_fields = [
        'user__username',
        'comment',
        'keep__title',
        'keep__description',
    ]
    
    readonly_fields = ['created_at', 'updated_at']
    
    def keep_title(self, obj):
        """Return the keep title or type."""
        return obj.keep.title or obj.keep.get_keep_type_display()
    keep_title.short_description = 'Keep'
    
    def comment_preview(self, obj):
        """Return a preview of the comment."""
        return obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment
    comment_preview.short_description = 'Comment Preview'
