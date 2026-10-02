"""Builders shared by the albums tests."""

from datetime import datetime, timezone

from mysite.albums.models import Album, AlbumKeep
from mysite.keeps.models import Keep, KeepMedia, KeepType

BASE_TIME = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)


def make_keep(circle, user, when=BASE_TIME, *, media=(("photo", True),), title="Memory"):
    """A keep dated `when` with one media file per (media_type, thumbnails) pair; no media = a text post."""
    keep = Keep.objects.create(
        circle=circle,
        created_by=user,
        keep_type=KeepType.MEDIA if media else KeepType.NOTE,
        title=title,
        date_of_memory=when,
    )
    for order, (media_type, thumbnails) in enumerate(media):
        KeepMedia.objects.create(
            keep=keep,
            media_type=media_type,
            upload_order=order,
            storage_key_original=f"original/{keep.id}-{order}",
            storage_key_thumbnail=f"thumb/{keep.id}-{order}" if thumbnails else "",
            storage_key_gallery=f"gallery/{keep.id}-{order}" if thumbnails else "",
            original_filename="file",
            content_type="image/jpeg" if media_type == "photo" else "video/mp4",
            thumbnails_generated=thumbnails,
        )
    return keep


def make_album(circle, user, *, name="Beach trip 2026", keeps=()):
    album = Album.objects.create(circle=circle, created_by=user, name=name)
    for keep in keeps:
        AlbumKeep.objects.create(album=album, keep=keep, added_by=user)
    return album
