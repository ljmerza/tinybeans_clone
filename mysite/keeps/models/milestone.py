"""Milestone tracking models for keeps."""
from django.db import models

from .keep import Keep


class MilestoneType(models.TextChoices):
    """Types of milestones for children.
    
    Common milestone categories for tracking child development.
    """
    FIRST_WORD = 'first_word', 'First Word'
    FIRST_STEPS = 'first_steps', 'First Steps'
    FIRST_TOOTH = 'first_tooth', 'First Tooth'
    FIRST_DAY_SCHOOL = 'first_day_school', 'First Day of School'
    BIRTHDAY = 'birthday', 'Birthday'
    HEIGHT_WEIGHT = 'height_weight', 'Height & Weight Check'
    OTHER = 'other', 'Other'


class Milestone(models.Model):
    """Milestone information for keeps marked as milestones.
    
    Stores specific milestone data when a keep is marked as a milestone.
    This allows for structured tracking of child development.
    
    Attributes:
        keep: The keep this milestone data belongs to
        milestone_type: Type of milestone achieved
        child_profile: Which child this milestone is for (optional reference)
        age_at_milestone: Child's age when milestone was reached
        notes: Additional notes about the milestone
        is_first_time: Whether this is the first time achieving this milestone
    """
    keep = models.OneToOneField(Keep, on_delete=models.CASCADE, related_name='milestone')
    milestone_type = models.CharField(
        max_length=30,
        choices=MilestoneType.choices,
        default=MilestoneType.OTHER
    )
    child_profile = models.ForeignKey(
        'users.ChildProfile',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='milestones'
    )
    age_at_milestone = models.CharField(
        max_length=50,
        blank=True,
        help_text="e.g., '18 months', '2 years 3 months'"
    )
    notes = models.TextField(blank=True)
    is_first_time = models.BooleanField(default=True)

    class Meta:
        ordering = ['-keep__date_of_memory']
        indexes = [
            models.Index(fields=['child_profile']),
            models.Index(fields=['milestone_type']),
        ]

    def __str__(self):
        child_name = self.child_profile.name if self.child_profile else "Unknown child"
        return f"{self.milestone_type} for {child_name}"