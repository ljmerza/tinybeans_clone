"""Signal handlers for the circles domain."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from mysite.users.models import CircleOnboardingStatus

from .models import CircleMembership


@receiver(post_save, sender=CircleMembership)
def mark_circle_onboarding_complete(sender, instance: CircleMembership, created: bool, **_: object) -> None:
    """Mark a user's onboarding as complete when they gain a circle membership."""
    if not created:
        return

    user = instance.user
    if user.circle_onboarding_status == CircleOnboardingStatus.COMPLETED:
        return

    user.set_circle_onboarding_status(CircleOnboardingStatus.COMPLETED, save=True)
