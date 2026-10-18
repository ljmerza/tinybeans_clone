"""Revoke a creator's tokens when they stop being an admin of the circle.

A backstop only: queryset ``.update()`` and ``.delete()`` skip these signals,
so the per-request creator check in ``authentication`` is the one that counts.
"""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from mysite.circles.models import Circle, CircleMembership
from mysite.users.models import UserRole

from .models import RevokeReason
from .services import revoke_tokens_for_user


@receiver(post_save, sender=CircleMembership)
def revoke_tokens_on_demotion(sender, instance: CircleMembership, **kwargs) -> None:
    # Promoting them again doesn't bring the tokens back.
    if instance.role != UserRole.CIRCLE_ADMIN:
        revoke_tokens_for_user(instance.user_id, reason=RevokeReason.CREATOR_NOT_ADMIN, circle_id=instance.circle_id)


@receiver(post_delete, sender=CircleMembership)
def revoke_tokens_on_removal(sender, instance: CircleMembership, origin=None, **kwargs) -> None:
    # Deleting the whole circle deletes its tokens too; nothing to revoke.
    if isinstance(origin, Circle):
        return
    revoke_tokens_for_user(instance.user_id, reason=RevokeReason.CREATOR_REMOVED, circle_id=instance.circle_id)
