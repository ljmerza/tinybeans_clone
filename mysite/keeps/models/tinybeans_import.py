"""Bookkeeping model for content imported from the real Tinybeans service.

Each row maps one remote Tinybeans object (journal, entry, comment, emotion,
user, child) to the local record it produced. The unique (object_type,
tinybeans_id) pair is what makes `manage.py sync_tinybeans` idempotent: an
object already recorded here is skipped on later runs.

All local foreign keys use CASCADE, so deleting a locally imported object also
removes its mapping row — a later sync run will then re-import that object.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone


class TinybeansObjectType(models.TextChoices):
    """Kinds of remote Tinybeans objects tracked by the importer."""

    JOURNAL = "journal", "Journal"
    CHILD = "child", "Child"
    USER = "user", "User"
    ENTRY = "entry", "Entry"
    COMMENT = "comment", "Comment"
    EMOTION = "emotion", "Emotion"


class TinybeansImportRecord(models.Model):
    """Maps a remote Tinybeans object id to the local record created for it.

    Exactly one of the local foreign keys is set, matching object_type:
    journal->circle, child->child, user->user, entry->keep, comment->comment,
    emotion->reaction.
    """

    object_type = models.CharField(max_length=20, choices=TinybeansObjectType.choices)
    tinybeans_id = models.CharField(max_length=64)

    circle = models.ForeignKey(
        "users.Circle",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="tinybeans_import_records",
    )
    child = models.ForeignKey(
        "users.ChildProfile",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="tinybeans_import_records",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="tinybeans_import_records",
    )
    keep = models.ForeignKey(
        "keeps.Keep",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="tinybeans_import_records",
    )
    comment = models.ForeignKey(
        "keeps.KeepComment",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="tinybeans_import_records",
    )
    reaction = models.ForeignKey(
        "keeps.KeepReaction",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="tinybeans_import_records",
    )

    payload = models.JSONField(default=dict, blank=True, help_text="Raw remote object snapshot for debugging")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("object_type", "tinybeans_id")
        indexes = [
            models.Index(fields=["object_type", "tinybeans_id"], name="keeps_tinyb_object__idx"),
        ]

    def __str__(self):
        return f"tinybeans {self.object_type} {self.tinybeans_id}"


class TinybeansSyncStatus(models.TextChoices):
    RUNNING = "running", "Running"
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"


class TinybeansSyncRun(models.Model):
    """One execution of ``manage.py sync_tinybeans`` (dry runs are not recorded).

    ``--since-last-run`` takes the ``started_at`` of the latest successful run
    (minus a safety margin) as the cutoff for its incremental walk, so a run
    that fails part-way never advances the cutoff.
    """

    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=TinybeansSyncStatus.choices,
        default=TinybeansSyncStatus.RUNNING,
    )
    incremental = models.BooleanField(default=False)
    counts = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"tinybeans sync {self.started_at:%Y-%m-%d %H:%M} ({self.status})"

    @classmethod
    def last_successful(cls):
        return cls.objects.filter(status=TinybeansSyncStatus.SUCCESS).order_by("-started_at").first()

    def finish(self, status, counts=None, error=""):
        self.status = status
        self.finished_at = timezone.now()
        self.counts = counts or {}
        self.error = error
        self.save(update_fields=["status", "finished_at", "counts", "error"])
