"""Signal handlers for the circles domain."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from mysite.users.models import CircleOnboardingStatus, UserRole

from .models import Circle, CircleMembership


@receiver(post_save, sender=CircleMembership)
def mark_circle_onboarding_complete(sender, instance: CircleMembership, created: bool, **_: object) -> None:
    """Mark a user's onboarding as complete when they gain a circle membership."""
    if not created:
        return

    user = instance.user
    if user.circle_onboarding_status == CircleOnboardingStatus.COMPLETED:
        return

    user.set_circle_onboarding_status(CircleOnboardingStatus.COMPLETED, save=True)


@receiver(post_save, sender=Circle)
def create_owner_membership(sender, instance: Circle, created: bool, **kwargs) -> None:
    """Automatically create owner membership when circle is created.

    When a new circle is created:
    1. Create a CircleMembership for the creator
    2. Mark them as owner (is_owner=True)
    3. Give them admin role
    4. Set invited_by to None (they created it)

    Uses get_or_create to be idempotent (safe to run multiple times).
    """
    if not created:
        return

    # Create owner membership
    CircleMembership.objects.get_or_create(
        user=instance.created_by,
        circle=instance,
        defaults={
            'role': UserRole.CIRCLE_ADMIN,
            'is_owner': True,
            'invited_by': None,  # Owner wasn't invited, they created it
        }
    )
