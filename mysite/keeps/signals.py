"""Signal handlers for the keeps app."""

import logging

from django.db import transaction
from django.db.models import Q
from django.db.models.signals import m2m_changed, post_delete
from django.dispatch import receiver

from mysite.users.models import ChildProfile

from . import storage
from .models import Keep, KeepMedia, KeepPerson
from .people import person_for_child

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


@receiver(m2m_changed, sender=Keep.children.through)
def mirror_children_to_people(sender, instance, action, reverse, pk_set, **kwargs) -> None:
    """Mirror ``Keep.children`` into the post's people tags.

    The Tinybeans importer only knows ``children``: linking a child tags the
    child's person in the keep's circle (created if needed), and unlinking or
    clearing untags it, so the two stay in step. Works from either side of the
    relation. Only tags are written here, never ``children``, so it can't loop.
    """
    if action == "post_add" and pk_set:
        if reverse:
            pairs = [(keep, instance) for keep in Keep.objects.filter(pk__in=pk_set)]
        else:
            pairs = [(instance, child) for child in ChildProfile.objects.filter(pk__in=pk_set)]
        for keep, child in pairs:
            KeepPerson.objects.get_or_create(keep=keep, person=person_for_child(keep.circle_id, child))
    elif action == "post_remove" and pk_set:
        if reverse:
            KeepPerson.objects.filter(keep_id__in=pk_set, person__child=instance).delete()
        else:
            KeepPerson.objects.filter(keep=instance, person__child_id__in=pk_set).delete()
    elif action == "pre_clear":
        if reverse:
            KeepPerson.objects.filter(person__child=instance).delete()
        else:
            KeepPerson.objects.filter(keep=instance, person__child__isnull=False).delete()
