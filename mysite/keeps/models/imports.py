"""Bookkeeping model for content imported from an external journal service.

Each row maps one remote object (journal, entry, comment, emotion, user,
child) to the local record it produced. The unique (object_type, source_id)
pair is what makes the importer's sync idempotent: an object already recorded
here is skipped on later runs. The importer is a separate service; these
tables stay here because the delete tombstones below depend on them.

Journals, children and users use CASCADE, so deleting one of those locally
also removes its mapping row — a later sync run will then re-import it.
Entries, comments and emotions are different: deleting the imported keep,
comment or reaction leaves its row with the link null as a tombstone, so
something a person deleted (or unliked) here stays that way.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone


class ImportObjectType(models.TextChoices):
    """Kinds of remote objects tracked by the importer."""

    JOURNAL = "journal", "Journal"
    CHILD = "child", "Child"
    USER = "user", "User"
    ENTRY = "entry", "Entry"
    COMMENT = "comment", "Comment"
    EMOTION = "emotion", "Emotion"


class ImportRecord(models.Model):
    """Maps a remote object id to the local record created for it.

    Exactly one of the local foreign keys is set, matching object_type:
    journal->circle, child->child, user->user, entry->keep, comment->comment,
    emotion->reaction.
    """

    object_type = models.CharField(max_length=20, choices=ImportObjectType.choices)
    source_id = models.CharField(max_length=64)

    circle = models.ForeignKey(
        "users.Circle",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="import_records",
    )
    child = models.ForeignKey(
        "users.ChildProfile",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="import_records",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="import_records",
    )
    # SET_NULL, not CASCADE (like comment and reaction): the row outlives a
    # deleted keep so the sync doesn't re-import it.
    keep = models.ForeignKey(
        "keeps.Keep",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="import_records",
    )
    comment = models.ForeignKey(
        "keeps.KeepComment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="import_records",
    )
    reaction = models.ForeignKey(
        "keeps.KeepReaction",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="import_records",
    )

    payload = models.JSONField(default=dict, blank=True, help_text="Raw remote object snapshot for debugging")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("object_type", "source_id")
        indexes = [
            models.Index(fields=["object_type", "source_id"], name="keeps_import_object_idx"),
        ]

    def __str__(self):
        return f"import {self.object_type} {self.source_id}"


class ImportSyncStatus(models.TextChoices):
    RUNNING = "running", "Running"
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"


class ImportSyncRun(models.Model):
    """One execution of the importer's sync (dry runs are not recorded).

    ``--since-last-run`` takes the ``started_at`` of the latest successful run
    (minus a safety margin) as the cutoff for its incremental walk, so a run
    that fails part-way never advances the cutoff.
    """

    account_key = models.CharField(
        max_length=254,
        blank=True,
        default="",
        help_text="Which configured import account this run belongs to (its email, normally).",
    )
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=ImportSyncStatus.choices,
        default=ImportSyncStatus.RUNNING,
    )
    incremental = models.BooleanField(default=False)
    counts = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["account_key", "status", "-started_at"], name="keeps_import_sync_acct_idx"),
        ]

    def __str__(self):
        label = self.account_key or "default"
        return f"import sync {label} {self.started_at:%Y-%m-%d %H:%M} ({self.status})"

    @classmethod
    def last_successful(cls, account_key: str = ""):
        """Latest successful run for one account; cursors never cross accounts."""
        return (
            cls.objects.filter(status=ImportSyncStatus.SUCCESS, account_key=account_key).order_by("-started_at").first()
        )

    def finish(self, status, counts=None, error=""):
        self.status = status
        self.finished_at = timezone.now()
        self.counts = counts or {}
        self.error = error
        self.save(update_fields=["status", "finished_at", "counts", "error"])
