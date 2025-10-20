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

    def __str__(self) -> str:
        return self.name


__all__ = ['Circle']
