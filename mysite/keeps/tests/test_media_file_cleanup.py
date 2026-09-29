"""Tests for removing stored files when media rows are deleted."""

from contextlib import suppress
from unittest.mock import Mock, patch

import pytest
from django.contrib.auth import get_user_model
from django.db import transaction

from mysite.circles.models import Circle
from mysite.keeps.models import Keep, KeepMedia, KeepType

User = get_user_model()


@pytest.fixture
def backend():
    fake = Mock()
    with patch("mysite.keeps.storage.get_storage_backend", return_value=fake):
        yield fake


@pytest.fixture
def keep():
    user = User.objects.create_user(email="cleanup@example.com", password="testpass123")
    circle = Circle.objects.create(name="Cleanup Family", created_by=user)
    return Keep.objects.create(circle=circle, created_by=user, keep_type=KeepType.MEDIA)


def add_media(keep, name, *, thumbnails=True):
    return KeepMedia.objects.create(
        keep=keep,
        media_type="photo",
        storage_key_original=f"keeps/{name}.jpg",
        storage_key_thumbnail=f"keeps/{name}-thumb.jpg" if thumbnails else "",
        storage_key_gallery=f"keeps/{name}-gallery.jpg" if thumbnails else "",
        original_filename=f"{name}.jpg",
        content_type="image/jpeg",
    )


def deleted_keys(backend):
    return sorted(call.args[0] for call in backend.delete.call_args_list)


@pytest.mark.django_db
class TestMediaFileCleanup:
    def test_deleting_a_keep_removes_every_file_of_its_media(self, backend, keep, django_capture_on_commit_callbacks):
        add_media(keep, "a")
        add_media(keep, "b", thumbnails=False)

        with django_capture_on_commit_callbacks(execute=True):
            keep.delete()

        assert deleted_keys(backend) == [
            "keeps/a-gallery.jpg",
            "keeps/a-thumb.jpg",
            "keeps/a.jpg",
            "keeps/b.jpg",
        ]

    def test_deleting_one_media_item_removes_only_its_files(self, backend, keep, django_capture_on_commit_callbacks):
        media = add_media(keep, "a")
        add_media(keep, "b")

        with django_capture_on_commit_callbacks(execute=True):
            media.delete()

        assert deleted_keys(backend) == ["keeps/a-gallery.jpg", "keeps/a-thumb.jpg", "keeps/a.jpg"]

    def test_keeps_files_another_media_row_still_uses(self, backend, keep, django_capture_on_commit_callbacks):
        # Same content uploaded twice on one day shares a content-hash key.
        other_keep = Keep.objects.create(circle=keep.circle, created_by=keep.created_by, keep_type=KeepType.MEDIA)
        add_media(keep, "same")
        add_media(other_keep, "same")

        with django_capture_on_commit_callbacks(execute=True):
            keep.delete()

        backend.delete.assert_not_called()

    def test_nothing_is_removed_when_the_delete_rolls_back(self, backend, keep, django_capture_on_commit_callbacks):
        add_media(keep, "a")
        keep_id = keep.id  # delete() clears the pk even when it rolls back

        with django_capture_on_commit_callbacks(execute=True), suppress(RuntimeError), transaction.atomic():
            keep.delete()
            raise RuntimeError("rolled back")

        backend.delete.assert_not_called()
        assert KeepMedia.objects.filter(keep_id=keep_id).exists()

    def test_a_storage_error_is_logged_not_raised(self, backend, keep, django_capture_on_commit_callbacks, caplog):
        add_media(keep, "a", thumbnails=False)
        backend.delete.side_effect = OSError("minio down")

        with django_capture_on_commit_callbacks(execute=True):
            keep.delete()

        assert not Keep.objects.filter(id=keep.id).exists()
        assert "Could not delete stored media file keeps/a.jpg" in caplog.text
