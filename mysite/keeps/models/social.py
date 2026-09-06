"""Social interaction models for keeps (reactions and comments)."""
from django.conf import settings
from django.db import models
from django.utils import timezone

from .keep import Keep


class KeepReaction(models.Model):
    """User reactions to keeps (likes, loves, etc.).
    
    Allows circle members to react to keeps with different emotion types.
    Each user can only have one reaction per keep.
    
    Attributes:
        keep: The keep being reacted to
        user: User who made the reaction
        reaction_type: Type of reaction (like, love, laugh, etc.)
        created_at: When the reaction was made
    """
    REACTION_CHOICES = [
        ('like', '👍 Like'),
        ('love', '❤️ Love'),
        ('laugh', '😂 Laugh'),
        ('wow', '😮 Wow'),
        ('celebrate', '🎉 Celebrate'),
    ]

    keep = models.ForeignKey(Keep, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='keep_reactions'
    )
    reaction_type = models.CharField(max_length=10, choices=REACTION_CHOICES, default='like')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('keep', 'user')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['keep', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user} {self.reaction_type} {self.keep}"


class KeepComment(models.Model):
    """Comments on keeps from circle members.
    
    Allows circle members to leave comments on keeps for discussion
    and sharing thoughts about memories.
    
    Attributes:
        keep: The keep being commented on
        user: User who made the comment
        parent: Parent comment when this is a reply (null for top-level)
        comment: The comment text
        created_at: When the comment was made
        updated_at: When the comment was last edited
    """
    keep = models.ForeignKey(Keep, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='keep_comments'
    )
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='replies',
        help_text='Comment this one replies to (same keep); null for top-level comments',
    )
    comment = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['keep', 'created_at']),
        ]

    def __str__(self):
        return f"Comment by {self.user} on {self.keep}"