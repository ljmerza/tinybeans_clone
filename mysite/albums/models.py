"""Albums: named collections of a circle's keeps across days."""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

# Posts in an album read like a story: oldest memory first. created_at and id
# break ties between keeps imported with the same timestamp.
ALBUM_KEEP_ORDERING = ("date_of_memory", "created_at", "id")


class Album(models.Model):
    """A named collection of keeps from one circle, e.g. "Beach trip 2026".

    Every member of the circle can see it and add or remove posts; only its
    creator or a circle admin may rename or delete it. A keep can be in any
    number of the circle's albums.

    Attributes:
        circle: The circle the album and all of its keeps belong to
        name: Short name shown on the album card
        description: Optional longer text
        created_by: Who made it; kept (as null) if that user is deleted
        cover_keep: Optional post whose first photo is the cover. When unset,
            or no longer in the album, the cover is the first post's first photo.
        keeps: The posts, through AlbumKeep
        created_at: When it was created
        updated_at: Last rename or post added/removed; the list is newest first
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    circle = models.ForeignKey("users.Circle", on_delete=models.CASCADE, related_name="albums")
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="albums_created",
    )
    cover_keep = models.ForeignKey(
        "keeps.Keep",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Post whose first photo is the cover; defaults to the album's first post",
    )
    keeps = models.ManyToManyField("keeps.Keep", through="AlbumKeep", related_name="albums", blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-updated_at", "-created_at"]
        indexes = [
            models.Index(fields=["circle", "-updated_at"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.circle})"

    def touch(self):
        """Mark the album as just changed, so it moves to the top of the list."""
        self.updated_at = timezone.now()
        Album.objects.filter(pk=self.pk).update(updated_at=self.updated_at)


class AlbumKeep(models.Model):
    """One keep in one album.

    Only keeps from the album's own circle may be added; ``save`` enforces it,
    since a database check can't compare two tables' columns.

    Attributes:
        album: The album
        keep: The post in it
        added_by: Who added it (null if that user is deleted)
        added_at: When it was added
    """

    album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name="album_keeps")
    keep = models.ForeignKey("keeps.Keep", on_delete=models.CASCADE, related_name="album_memberships")
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="album_keeps_added",
    )
    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["added_at"]
        constraints = [
            models.UniqueConstraint(fields=["album", "keep"], name="albums_unique_album_keep"),
        ]
        indexes = [
            models.Index(fields=["keep"]),
        ]

    def __str__(self):
        return f"{self.keep_id} in {self.album}"

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.album.circle_id != self.keep.circle_id:
            raise ValidationError({"keep": "Only posts from the album's circle can be added."})
