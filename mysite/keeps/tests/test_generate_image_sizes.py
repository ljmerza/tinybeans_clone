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

ORIGINAL_KEY = 'original/source.png'


class FakeStorageBackend:
    """In-memory stand-in for the MinIO backend."""

    def __init__(self, original: bytes):
        self.files = {ORIGINAL_KEY: original}

    def get_file_content(self, storage_key):
        return self.files[storage_key]

    def save(self, file_content, filename, content_type=None):
        key = f'{len(self.files)}/{filename}'
        self.files[key] = file_content
        return key


def png_bytes(mode, color, size=(400, 300)):
    buffer = BytesIO()
    Image.new(mode, size, color).save(buffer, format='PNG')
    return buffer.getvalue()


@pytest.fixture
def photo_media(db):
    user = User.objects.create_user(email='thumbs@example.com', password='testpass123')
    circle = Circle.objects.create(name='Thumbs Family', created_by=user)
    keep = Keep.objects.create(circle=circle, created_by=user, keep_type=KeepType.MEDIA)
    return KeepMedia.objects.create(
        keep=keep,
        media_type='photo',
        storage_key_original=ORIGINAL_KEY,
        original_filename='source.png',
        content_type='image/png',
    )


def run_task(media, original: bytes) -> FakeStorageBackend:
    storage = FakeStorageBackend(original)
    with patch('mysite.keeps.tasks.get_storage_backend', return_value=storage):
        assert generate_image_sizes(media.id) is True
    media.refresh_from_db()
    return storage


def open_image(storage, key):
    return Image.open(BytesIO(storage.files[key]))


@pytest.mark.django_db
class TestGenerateImageSizes:
    """Thumbnail/gallery renditions are JPEG, so alpha must be flattened."""

    @pytest.mark.parametrize(
        'mode,color',
        [
            ('RGBA', (255, 0, 0, 128)),
            ('LA', (128, 64)),
            ('P', 3),
            ('L', 90),
        ],
    )
    def test_non_rgb_images_produce_jpeg_renditions(self, photo_media, mode, color):
        storage = run_task(photo_media, png_bytes(mode, color))

        assert photo_media.thumbnails_generated is True
        assert (photo_media.width, photo_media.height) == (400, 300)
        for key in (photo_media.storage_key_thumbnail, photo_media.storage_key_gallery):
            image = open_image(storage, key)
            assert image.format == 'JPEG'
            assert image.mode == 'RGB'

    def test_transparent_pixels_flatten_onto_white(self, photo_media):
        storage = run_task(photo_media, png_bytes('RGBA', (255, 0, 0, 0)))

        thumbnail = open_image(storage, photo_media.storage_key_thumbnail).convert('RGB')
        r, g, b = thumbnail.getpixel((thumbnail.width // 2, thumbnail.height // 2))
        assert min(r, g, b) >= 250

    def test_rgb_image_still_works(self, photo_media):
        storage = run_task(photo_media, png_bytes('RGB', (0, 128, 255)))

        thumbnail = open_image(storage, photo_media.storage_key_thumbnail)
        assert thumbnail.format == 'JPEG'
        assert max(thumbnail.size) <= 150
        gallery = open_image(storage, photo_media.storage_key_gallery)
        assert gallery.size[0] <= 800 and gallery.size[1] <= 600
