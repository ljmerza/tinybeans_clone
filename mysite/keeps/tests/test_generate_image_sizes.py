"""Tests for the generate_image_sizes Celery task."""

from io import BytesIO
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from PIL import Image

from mysite.circles.models import Circle
from mysite.keeps.models import Keep, KeepMedia, KeepType
from mysite.keeps.tasks import generate_image_sizes

User = get_user_model()

ORIGINAL_KEY = "original/source.png"


class FakeStorageBackend:
    """In-memory stand-in for the MinIO backend."""

    def __init__(self, original: bytes, extra=None):
        self.files = {ORIGINAL_KEY: original, **(extra or {})}
        self.deleted = []

    def get_file_content(self, storage_key):
        return self.files[storage_key]

    def delete(self, storage_key):
        self.deleted.append(storage_key)
        self.files.pop(storage_key, None)
        return True

    def save(self, file_content, filename, content_type=None):
        key = f"{len(self.files)}/{filename}"
        self.files[key] = file_content
        return key


def png_bytes(mode, color, size=(400, 300)):
    buffer = BytesIO()
    Image.new(mode, size, color).save(buffer, format="PNG")
    return buffer.getvalue()


def make_media(media_type="photo", filename="source.png", content_type="image/png"):
    user = User.objects.create_user(email="thumbs@example.com", password="testpass123")
    circle = Circle.objects.create(name="Thumbs Family", created_by=user)
    keep = Keep.objects.create(circle=circle, created_by=user, keep_type=KeepType.MEDIA)
    return KeepMedia.objects.create(
        keep=keep,
        media_type=media_type,
        storage_key_original=ORIGINAL_KEY,
        original_filename=filename,
        content_type=content_type,
    )


@pytest.fixture
def photo_media(db):
    return make_media()


@pytest.fixture
def video_media(db):
    return make_media(media_type="video", filename="clip.mp4", content_type="video/mp4")


def run_task(media, original: bytes, storage=None, **kwargs) -> FakeStorageBackend:
    storage = storage or FakeStorageBackend(original)
    with patch("mysite.keeps.tasks.get_storage_backend", return_value=storage):
        assert generate_image_sizes(media.id, **kwargs) is True
    media.refresh_from_db()
    return storage


def open_image(storage, key):
    return Image.open(BytesIO(storage.files[key]))


@pytest.mark.django_db
class TestGenerateImageSizes:
    """Thumbnail/gallery renditions are JPEG, so alpha must be flattened."""

    @pytest.mark.parametrize(
        "mode,color",
        [
            ("RGBA", (255, 0, 0, 128)),
            ("LA", (128, 64)),
            ("P", 3),
            ("L", 90),
        ],
    )
    def test_non_rgb_images_produce_jpeg_renditions(self, photo_media, mode, color):
        storage = run_task(photo_media, png_bytes(mode, color))

        assert photo_media.thumbnails_generated is True
        assert (photo_media.width, photo_media.height) == (400, 300)
        for key in (photo_media.storage_key_thumbnail, photo_media.storage_key_gallery):
            image = open_image(storage, key)
            assert image.format == "JPEG"
            assert image.mode == "RGB"

    def test_transparent_pixels_flatten_onto_white(self, photo_media):
        storage = run_task(photo_media, png_bytes("RGBA", (255, 0, 0, 0)))

        thumbnail = open_image(storage, photo_media.storage_key_thumbnail).convert("RGB")
        r, g, b = thumbnail.getpixel((thumbnail.width // 2, thumbnail.height // 2))
        assert min(r, g, b) >= 250

    def test_rgb_image_still_works(self, photo_media):
        storage = run_task(photo_media, png_bytes("RGB", (0, 128, 255)))

        thumbnail = open_image(storage, photo_media.storage_key_thumbnail)
        assert thumbnail.format == "JPEG"
        assert max(thumbnail.size) <= 300
        gallery = open_image(storage, photo_media.storage_key_gallery)
        assert gallery.size[0] <= 1200 and gallery.size[1] <= 1200

    def test_rendition_sizes_fit_300_and_1200_boxes(self, photo_media):
        storage = run_task(photo_media, png_bytes("RGB", (10, 20, 30), size=(2000, 1500)))

        assert open_image(storage, photo_media.storage_key_thumbnail).size == (300, 225)
        assert open_image(storage, photo_media.storage_key_gallery).size == (1200, 900)
        assert (photo_media.width, photo_media.height) == (2000, 1500)

    def test_regeneration_deletes_previous_renditions(self, photo_media):
        storage = run_task(photo_media, png_bytes("RGB", (1, 2, 3)))
        first = (photo_media.storage_key_thumbnail, photo_media.storage_key_gallery)

        run_task(photo_media, b"", storage=storage)

        assert set(first) <= set(storage.deleted)
        assert photo_media.storage_key_thumbnail not in first

    def test_video_uses_poster_as_source_and_deletes_it(self, video_media):
        poster = png_bytes("RGB", (200, 100, 50), size=(1000, 1778))
        storage = FakeStorageBackend(b"not-an-image", extra={"tmp/poster.jpg": poster})

        run_task(video_media, b"", storage=storage, source_key="tmp/poster.jpg")

        assert video_media.thumbnails_generated is True
        assert (video_media.width, video_media.height) == (1000, 1778)
        assert open_image(storage, video_media.storage_key_thumbnail).size[1] == 300
        assert "tmp/poster.jpg" in storage.deleted
        assert ORIGINAL_KEY in storage.files  # the mp4 original is untouched

    def test_video_without_source_is_skipped(self, video_media):
        storage = FakeStorageBackend(b"not-an-image")
        with patch("mysite.keeps.tasks.get_storage_backend", return_value=storage):
            assert generate_image_sizes(video_media.id) is False
        video_media.refresh_from_db()
        assert video_media.thumbnails_generated is False
