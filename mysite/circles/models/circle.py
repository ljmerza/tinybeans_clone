"""Circle model implementation for the circles app."""

from django.conf import settings
from django.db import models
from django.utils import timezone

from mysite.users.models.utils import generate_unique_slug


class Circle(models.Model):
    """A family circle for sharing content and memories."""

    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='circles_created',
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        # Keep legacy ownership under the users app until migrations relocate.
        app_label = 'users'
        ordering = ['name']

    def save(self, *args, **kwargs):
        """Persist the circle, auto-generating the slug when missing."""
        if not self.slug:
            self.slug = generate_unique_slug(self.name, Circle.objects)
        super().save(*args, **kwargs)

    def get_owner_membership(self):
        """Get the owner's membership record.

        Returns:
            CircleMembership or None if owner hasn't joined yet
        """
        from .membership import CircleMembership
        return self.memberships.filter(is_owner=True).first()

    def is_owner(self, user) -> bool:
        """Check if the given user is the circle owner.

        Args:
            user: User instance or user ID

        Returns:
            True if user is the owner, False otherwise
        """
        user_id = user.id if hasattr(user, 'id') else user
        return self.created_by_id == user_id

    def get_owner_user(self):
        """Get the user who owns this circle.

        Returns:
            User instance
        """
        return self.created_by

    def __str__(self) -> str:
        return self.name


__all__ = ['Circle']
