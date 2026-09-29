"""Signal handlers for the keeps app."""

import logging

from django.db import transaction
from django.db.models import Q
from django.db.models.signals import post_delete
from django.dispatch import receiver

from . import storage
from .models import KeepMedia

logger = logging.getLogger(__name__)


def delete_unreferenced_files(keys):
    """Remove stored files that no remaining KeepMedia points at.

    Storage keys come from content hashes, so the same file uploaded twice on
    one day is a single shared object; it stays until its last user is gone.
    A storage failure is logged rather than raised: the rows are already gone.
    """
    backend = storage.get_storage_backend()
    for key in keys:
        in_use = KeepMedia.objects.filter(
            Q(storage_key_original=key) | Q(storage_key_thumbnail=key) | Q(storage_key_gallery=key)
        ).exists()
        if in_use:
            continue
        try:
            backend.delete(key)
        except Exception:
            logger.exception("Could not delete stored media file %s", key)


@receiver(post_delete, sender=KeepMedia)
def delete_media_files(sender, instance: KeepMedia, **kwargs) -> None:
    """Delete a media row's files (original and renditions) once the delete commits.

    Covers every path that removes media: deleting it directly, deleting its
    keep (cascade), and the admin.
    """
    keys = [
        key
        for key in (instance.storage_key_original, instance.storage_key_thumbnail, instance.storage_key_gallery)
        if key
    ]
    if keys:
        transaction.on_commit(lambda: delete_unreferenced_files(keys))
