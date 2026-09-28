"""Tests for creating posts from the web client: keep creation, uploads, and processing."""

import os
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import Mock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient

from mysite.circles.models import Circle
from mysite.keeps.models import Keep, KeepMedia, KeepType, MediaUpload, MediaUploadStatus
from mysite.keeps.storage import MinIOStorageBackend
from mysite.keeps.tasks import process_media_upload, validate_media_file

User = get_user_model()

KEEPS_URL = "/api/keeps/"
UPLOAD_URL = "/api/keeps/upload/"
FEED_URL = "/api/keeps/feed/"
BASE_TIME = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)


def jpeg_bytes():
    buffer = BytesIO()
    Image.new("RGB", (4, 4), "red").save(buffer, format="JPEG")
    return buffer.getvalue()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return User.objects.create_user(email="poster@example.com", password="testpass123")


@pytest.fixture
def circle(user):
    """Membership for the creator is auto-created by signal."""
    return Circle.objects.create(name="Post Family", created_by=user)


@pytest.fixture
def upload_dir(tmp_path):
    with override_settings(UPLOAD_TEMP_DIR=str(tmp_path / "upload-tmp")):
        yield tmp_path / "upload-tmp"


@pytest.fixture
def media_keep(circle, user):
    return Keep.objects.create(circle=circle, created_by=user, keep_type=KeepType.MEDIA, date_of_memory=BASE_TIME)


@pytest.mark.django_db
class TestCreateKeep:
    def test_media_keep_can_start_without_files_and_returns_id(self, api_client, user, circle):
        api_client.force_authenticate(user=user)
        response = api_client.post(
            KEEPS_URL,
            {"circle": circle.id, "keep_type": "media", "description": "Beach day"},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        keep = Keep.objects.get(id=response.data["id"])
        assert keep.keep_type == KeepType.MEDIA
        assert keep.created_by == user

    def test_text_post(self, api_client, user, circle):
        api_client.force_authenticate(user=user)
        response = api_client.post(
            KEEPS_URL,
            {"circle": circle.id, "keep_type": "note", "description": "First word today!"},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert Keep.objects.get(id=response.data["id"]).description == "First word today!"


@pytest.mark.django_db
class TestMediaUploadView:
    def post_upload(self, api_client, keep, media_type, file, **extra):
        return api_client.post(
            UPLOAD_URL, {"keep_id": str(keep.id), "media_type": media_type, "file": file, **extra}, format="multipart"
        )

    @patch("mysite.keeps.views.uploads.validate_media_file")
    def test_parks_file_in_shared_dir_and_queues_validation(
        self, mock_validate, api_client, user, media_keep, upload_dir
    ):
        api_client.force_authenticate(user=user)
        photo = SimpleUploadedFile("beach.jpg", jpeg_bytes(), content_type="image/jpeg")

        response = self.post_upload(api_client, media_keep, "photo", photo, upload_order=2)

        assert response.status_code == status.HTTP_202_ACCEPTED
        upload = MediaUpload.objects.get(id=response.data["data"]["id"])
        assert os.path.dirname(upload.temp_file_path) == str(upload_dir)
        assert os.path.exists(upload.temp_file_path)
        assert upload.upload_order == 2
        assert upload.poster_temp_path == ""
        mock_validate.delay.assert_called_once_with(str(upload.id))

    @patch("mysite.keeps.views.uploads.validate_media_file")
    def test_video_with_poster(self, mock_validate, api_client, user, media_keep, upload_dir):
        api_client.force_authenticate(user=user)
        video = SimpleUploadedFile("clip.mp4", b"\x00" * 64, content_type="video/mp4")
        poster = SimpleUploadedFile("poster.jpg", jpeg_bytes(), content_type="image/jpeg")

        response = self.post_upload(api_client, media_keep, "video", video, poster=poster)

        assert response.status_code == status.HTTP_202_ACCEPTED
        upload = MediaUpload.objects.get(id=response.data["data"]["id"])
        assert os.path.dirname(upload.poster_temp_path) == str(upload_dir)
        assert os.path.exists(upload.poster_temp_path)

    @patch("mysite.keeps.views.uploads.validate_media_file")
    def test_poster_ignored_for_photos(self, mock_validate, api_client, user, media_keep, upload_dir):
        api_client.force_authenticate(user=user)
        photo = SimpleUploadedFile("beach.jpg", jpeg_bytes(), content_type="image/jpeg")
        poster = SimpleUploadedFile("poster.jpg", jpeg_bytes(), content_type="image/jpeg")

        response = self.post_upload(api_client, media_keep, "photo", photo, poster=poster)

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert MediaUpload.objects.get().poster_temp_path == ""

    @patch("mysite.keeps.views.uploads.validate_media_file")
    def test_rejects_non_image_poster(self, mock_validate, api_client, user, media_keep, upload_dir):
        api_client.force_authenticate(user=user)
        video = SimpleUploadedFile("clip.mp4", b"\x00" * 64, content_type="video/mp4")
        poster = SimpleUploadedFile("poster.mp4", b"\x00" * 64, content_type="video/mp4")

        response = self.post_upload(api_client, media_keep, "video", video, poster=poster)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "invalid_file_type"
        assert not MediaUpload.objects.exists()

    @patch("mysite.keeps.views.uploads.validate_media_file")
    def test_videos_have_their_own_size_limit(self, mock_validate, api_client, user, media_keep, upload_dir):
        api_client.force_authenticate(user=user)

        with override_settings(MAX_UPLOAD_SIZE=10, MAX_VIDEO_UPLOAD_SIZE=100):
            video = SimpleUploadedFile("clip.mp4", b"\x00" * 50, content_type="video/mp4")
            accepted = self.post_upload(api_client, media_keep, "video", video)
            too_big = SimpleUploadedFile("long.mp4", b"\x00" * 101, content_type="video/mp4")
            rejected = self.post_upload(api_client, media_keep, "video", too_big)
            photo = SimpleUploadedFile("big.jpg", b"\x00" * 50, content_type="image/jpeg")
            rejected_photo = self.post_upload(api_client, media_keep, "photo", photo)

        assert accepted.status_code == status.HTTP_202_ACCEPTED
        assert rejected.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        assert rejected.data["error"] == "file_too_large"
        assert rejected.data["messages"][0]["context"] == {"maxSize": 100}
        assert rejected_photo.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE

    def test_rejects_wrong_type(self, api_client, user, media_keep, upload_dir):
        api_client.force_authenticate(user=user)
        text = SimpleUploadedFile("notes.txt", b"hi", content_type="text/plain")

        response = self.post_upload(api_client, media_keep, "photo", text)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "invalid_file_type"

    def test_non_member_cannot_upload(self, api_client, media_keep, upload_dir):
        outsider = User.objects.create_user(email="outsider@example.com", password="testpass123")
        api_client.force_authenticate(user=outsider)
        photo = SimpleUploadedFile("beach.jpg", jpeg_bytes(), content_type="image/jpeg")

        response = self.post_upload(api_client, media_keep, "photo", photo)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["error"] == "access_denied"


def park(directory, name, content):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_bytes(content)
    return str(path)


@pytest.mark.django_db
class TestUploadTasks:
    def make_upload(self, keep, media_type, temp_file_path, poster_temp_path="", **extra):
        return MediaUpload.objects.create(
            keep=keep,
            media_type=media_type,
            original_filename="clip.mp4" if media_type == "video" else "beach.jpg",
            content_type="video/mp4" if media_type == "video" else "image/jpeg",
            file_size=os.path.getsize(temp_file_path),
            temp_file_path=temp_file_path,
            poster_temp_path=poster_temp_path,
            **extra,
        )

    @patch("mysite.keeps.tasks.process_media_upload")
    def test_validation_uses_video_limit(self, mock_process, media_keep, upload_dir):
        upload = self.make_upload(media_keep, "video", park(upload_dir, "clip.mp4", b"\x00" * 50))

        with override_settings(MAX_UPLOAD_SIZE=10, MAX_VIDEO_UPLOAD_SIZE=100):
            assert validate_media_file(str(upload.id)) is True

        mock_process.delay.assert_called_once_with(str(upload.id))

    @patch("mysite.keeps.tasks.process_media_upload")
    def test_validation_rejects_broken_poster(self, mock_process, media_keep, upload_dir):
        upload = self.make_upload(
            media_keep,
            "video",
            park(upload_dir, "clip.mp4", b"\x00" * 50),
            park(upload_dir, "clip.poster", b"not an image"),
        )

        with pytest.raises(ValueError, match="Invalid poster image"):
            validate_media_file(str(upload.id))

        upload.refresh_from_db()
        assert upload.status == MediaUploadStatus.FAILED
        mock_process.delay.assert_not_called()

    @patch("mysite.keeps.tasks.generate_image_sizes")
    @patch("mysite.keeps.tasks.get_storage_backend")
    def test_video_streams_to_storage_and_derives_renditions_from_poster(
        self, mock_get_storage, mock_generate, media_keep, upload_dir
    ):
        storage = Mock()
        storage.save_file.side_effect = ["keeps/clip.mp4", "keeps/poster.jpg"]
        storage.get_metadata.return_value = {"size": 50}
        mock_get_storage.return_value = storage
        video_path = park(upload_dir, "clip.mp4", b"\x00" * 50)
        poster_path = park(upload_dir, "clip.poster", jpeg_bytes())
        upload = self.make_upload(media_keep, "video", video_path, poster_path, upload_order=1)

        assert process_media_upload(str(upload.id)) is True

        media = KeepMedia.objects.get(keep=media_keep)
        assert (media.media_type, media.storage_key_original, media.upload_order) == ("video", "keeps/clip.mp4", 1)
        storage.save.assert_not_called()  # never loaded into memory
        assert storage.save_file.call_args_list[0].args == (video_path,)
        assert storage.save_file.call_args_list[1].args == (poster_path,)
        mock_generate.delay.assert_called_once_with(media.id, "keeps/poster.jpg")
        assert not os.path.exists(video_path)
        assert not os.path.exists(poster_path)
        upload.refresh_from_db()
        assert upload.status == MediaUploadStatus.COMPLETED

    @patch("mysite.keeps.tasks.generate_image_sizes")
    @patch("mysite.keeps.tasks.get_storage_backend")
    def test_video_without_poster_gets_no_renditions(self, mock_get_storage, mock_generate, media_keep, upload_dir):
        storage = Mock()
        storage.save_file.return_value = "keeps/clip.mp4"
        storage.get_metadata.return_value = {}
        mock_get_storage.return_value = storage
        upload = self.make_upload(media_keep, "video", park(upload_dir, "clip.mp4", b"\x00" * 50))

        assert process_media_upload(str(upload.id)) is True

        assert KeepMedia.objects.get(keep=media_keep).file_size == 50  # falls back to the upload's size
        mock_generate.delay.assert_not_called()

    @patch("mysite.keeps.tasks.generate_image_sizes")
    @patch("mysite.keeps.tasks.get_storage_backend")
    def test_photo_queues_renditions_from_original(self, mock_get_storage, mock_generate, media_keep, upload_dir):
        storage = Mock()
        storage.save_file.return_value = "keeps/beach.jpg"
        storage.get_metadata.return_value = {"size": 10}
        mock_get_storage.return_value = storage
        upload = self.make_upload(media_keep, "photo", park(upload_dir, "beach.jpg", jpeg_bytes()))

        process_media_upload(str(upload.id))

        mock_generate.delay.assert_called_once_with(KeepMedia.objects.get().id, None)


class TestMinIOSaveFile:
    @patch("minio.Minio")
    def test_streams_from_disk_under_content_hash_key(self, mock_minio_class, tmp_path):
        mock_client = Mock()
        mock_minio_class.return_value = mock_client
        path = tmp_path / "clip.MP4"
        path.write_bytes(b"video bytes")

        with override_settings(
            MINIO_ENDPOINT="http://localhost:9000",
            MINIO_ACCESS_KEY="test",
            MINIO_SECRET_KEY="test",
            MINIO_BUCKET_NAME="test-bucket",
            MINIO_PUBLIC_ENDPOINT="",
        ):
            backend = MinIOStorageBackend()
            key = backend.save_file(str(path), "clip.MP4", "video/mp4")

        expected_hash = backend.calculate_content_hash(b"video bytes")
        assert key.startswith("keeps/") and key.endswith(f"/{expected_hash[:16]}.mp4")
        mock_client.fput_object.assert_called_once_with(
            bucket_name="test-bucket", object_name=key, file_path=str(path), content_type="video/mp4"
        )
        mock_client.put_object.assert_not_called()


class FakeStorageBackend:
    def get_url(self, storage_key, expires_in=3600):
        return f"https://cdn.test/{storage_key}"


@pytest.mark.django_db
class TestTextPostsInFeed:
    @pytest.fixture(autouse=True)
    def fake_storage(self):
        with patch("mysite.keeps.storage.get_storage_backend", return_value=FakeStorageBackend()):
            yield

    def test_text_posts_show_but_empty_media_keeps_wait(self, api_client, user, circle, media_keep):
        note = Keep.objects.create(
            circle=circle, created_by=user, keep_type=KeepType.NOTE, description="Hi", date_of_memory=BASE_TIME
        )

        api_client.force_authenticate(user=user)
        response = api_client.get(FEED_URL)

        assert [item["id"] for item in response.data["results"]] == [str(note.id)]
        assert response.data["results"][0]["media"] == []

    def test_text_post_in_day_view_and_single_item(self, api_client, user, circle):
        note = Keep.objects.create(
            circle=circle, created_by=user, keep_type=KeepType.NOTE, description="Hi", date_of_memory=BASE_TIME
        )

        api_client.force_authenticate(user=user)
        day = api_client.get(FEED_URL, {"date": "2026-07-01"})
        item = api_client.get(f"{FEED_URL}{note.id}/")

        assert [entry["id"] for entry in day.data["results"]] == [str(note.id)]
        assert item.status_code == status.HTTP_200_OK
