"""Celery tasks for media upload and processing."""

import os
from io import BytesIO

from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from PIL import Image, ImageOps

from mysite import project_logging

from .digest import digest_recipient_ids, send_digest
from .models import KeepMedia, MediaUpload, MediaUploadStatus
from .notifications import send_activity
from .storage import get_storage_backend

logger = get_task_logger(__name__)


def max_upload_size(media_type: str) -> int:
    """Largest accepted upload, in bytes, for a photo or video."""
    return settings.MAX_VIDEO_UPLOAD_SIZE if media_type == "video" else settings.MAX_UPLOAD_SIZE


def remove_upload_temp_files(upload) -> None:
    """Delete an upload's parked file and poster frame, if still on disk."""
    for path in (upload.temp_file_path, upload.poster_temp_path):
        if path and os.path.exists(path):
            os.remove(path)


@shared_task(bind=True, max_retries=3)
def process_media_upload(self, upload_id: str):
    """Process a media upload asynchronously."""
    with project_logging.log_context(task="keeps.process_media_upload", upload_id=upload_id):
        try:
            upload = MediaUpload.objects.get(id=upload_id)
        except MediaUpload.DoesNotExist:
            logger.warning(
                "Media upload not found for processing",
                extra={"event": "keeps.media.upload_missing", "extra": {"upload_id": upload_id}},
            )
            return False

        with project_logging.log_context(keep_id=upload.keep_id, media_type=upload.media_type):
            try:
                upload.status = MediaUploadStatus.PROCESSING
                upload.save(update_fields=["status"])

                logger.info(
                    "Processing media upload",
                    extra={
                        "event": "keeps.media.process_start",
                        "extra": {
                            "upload_id": upload_id,
                            "keep_id": upload.keep_id,
                            "media_type": upload.media_type,
                            "content_type": upload.content_type,
                        },
                    },
                )

                storage = get_storage_backend()
                storage_key_original = storage.save_file(
                    upload.temp_file_path, filename=upload.original_filename, content_type=upload.content_type
                )

                metadata = storage.get_metadata(storage_key_original)
                file_size = metadata.get("size", upload.file_size)

                # A video's poster frame (captured by the browser) becomes the
                # source for its thumbnail/gallery renditions.
                poster_key = None
                if upload.media_type == "video" and upload.poster_temp_path:
                    poster_key = storage.save_file(
                        upload.poster_temp_path, filename="poster.jpg", content_type="image/jpeg"
                    )

                media = KeepMedia.objects.create(
                    keep=upload.keep,
                    media_type=upload.media_type,
                    caption=upload.caption,
                    upload_order=upload.upload_order,
                    storage_key_original=storage_key_original,
                    file_size=file_size,
                    original_filename=upload.original_filename,
                    content_type=upload.content_type,
                )

                if upload.media_type == "photo" or poster_key:
                    generate_image_sizes.delay(media.id, poster_key)
                    logger.info(
                        "Queued image resize task",
                        extra={
                            "event": "keeps.media.image_resize_queued",
                            "extra": {"media_id": media.id},
                        },
                    )

                upload.status = MediaUploadStatus.COMPLETED
                upload.media_file = media
                upload.error_message = ""
                upload.save(update_fields=["status", "media_file", "error_message"])

                remove_upload_temp_files(upload)

                logger.info(
                    "Successfully processed media upload",
                    extra={
                        "event": "keeps.media.process_success",
                        "extra": {
                            "upload_id": upload_id,
                            "media_id": media.id,
                            "keep_id": upload.keep_id,
                        },
                    },
                )
                return True
            except Exception as exc:  # noqa: BLE001 - ensure we capture and persist failure details
                logger.exception(
                    "Failed to process media upload",
                    extra={
                        "event": "keeps.media.process_failure",
                        "extra": {"upload_id": upload_id},
                    },
                )

                try:
                    upload.status = MediaUploadStatus.FAILED
                    upload.error_message = str(exc)
                    upload.save(update_fields=["status", "error_message"])
                except MediaUpload.DoesNotExist:
                    logger.warning(
                        "Media upload missing during failure handling",
                        extra={"event": "keeps.media.upload_missing_on_failure"},
                    )

                if self.request.retries < self.max_retries:
                    attempt = self.request.retries + 1
                    logger.info(
                        "Retrying media upload processing",
                        extra={
                            "event": "keeps.media.retry_scheduled",
                            "extra": {"upload_id": upload_id, "attempt": attempt},
                        },
                    )
                    raise self.retry(countdown=60 * (2**self.request.retries)) from exc

                raise


def _to_rgb(image: Image.Image) -> Image.Image:
    """Return an RGB copy suitable for JPEG output.

    JPEG cannot store alpha, so RGBA/LA/transparent-palette images are
    flattened onto a white background; any other non-RGB mode is converted.
    """
    if image.mode == "RGB":
        return image
    has_alpha = image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info)
    if has_alpha:
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return image.convert("RGB")


# Bounding boxes for the derived renditions. 300px keeps calendar tiles crisp on
# high-DPI screens; 1200px fills a phone screen at 2x and is adequate on desktop.
THUMBNAIL_SIZE = (300, 300)
GALLERY_SIZE = (1200, 1200)


def _delete_quietly(storage, storage_key: str, media_id: int, what: str) -> None:
    if not storage_key:
        return
    try:
        storage.delete(storage_key)
    except Exception:
        logger.warning(
            "Could not delete superseded %s",
            what,
            extra={"event": "keeps.media.cleanup_failed", "extra": {"media_id": media_id, "storage_key": storage_key}},
        )


@shared_task(bind=True, max_retries=3)
def generate_image_sizes(self, media_id: int, source_key: str | None = None):
    """Generate thumbnail and gallery size images.

    ``source_key`` points at an alternative image to derive the renditions
    from (a video's poster frame). It is treated as temporary and deleted once
    the renditions exist. Without it only photo media is processed.
    """
    with project_logging.log_context(task="keeps.generate_image_sizes", media_id=media_id):
        try:
            media = KeepMedia.objects.get(id=media_id)
        except KeepMedia.DoesNotExist:
            logger.warning(
                "Media record not found for image sizing",
                extra={"event": "keeps.media.image_sizes_missing", "extra": {"media_id": media_id}},
            )
            # Deleted before its renditions were made: the temporary source (a
            # video's poster frame) has no other owner that would remove it.
            if source_key:
                _delete_quietly(get_storage_backend(), source_key, media_id, "source image")
            return False

        with project_logging.log_context(keep_id=media.keep_id, media_type=media.media_type):
            if media.media_type != "photo" and not source_key:
                logger.info(
                    "Skipping image processing for non-photo media",
                    extra={
                        "event": "keeps.media.image_sizes_skipped",
                        "extra": {"media_id": media_id, "media_type": media.media_type},
                    },
                )
                return False

            try:
                storage = get_storage_backend()
                image_key = source_key or media.storage_key_original
                image_data = storage.get_file_content(image_key)
                image = Image.open(BytesIO(image_data))
                image = ImageOps.exif_transpose(image)
                media.width, media.height = image.size
                image = _to_rgb(image)

                previous_keys = [k for k in (media.storage_key_thumbnail, media.storage_key_gallery) if k]

                thumbnail_image = image.copy()
                thumbnail_image.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
                thumbnail_io = BytesIO()
                thumbnail_image.save(thumbnail_io, format="JPEG", quality=85, optimize=True)
                thumbnail_data = thumbnail_io.getvalue()
                media.storage_key_thumbnail = storage.save(
                    file_content=thumbnail_data, filename="thumbnail.jpg", content_type="image/jpeg"
                )

                gallery_image = image.copy()
                gallery_image.thumbnail(GALLERY_SIZE, Image.Resampling.LANCZOS)
                gallery_io = BytesIO()
                gallery_image.save(gallery_io, format="JPEG", quality=90, optimize=True)
                gallery_data = gallery_io.getvalue()
                media.storage_key_gallery = storage.save(
                    file_content=gallery_data, filename="gallery.jpg", content_type="image/jpeg"
                )

                media.thumbnails_generated = True
                media.save(
                    update_fields=[
                        "width",
                        "height",
                        "storage_key_thumbnail",
                        "storage_key_gallery",
                        "thumbnails_generated",
                    ]
                )

                # Renditions were regenerated: drop the superseded objects, and
                # the temporary source image if one was supplied.
                for key in previous_keys:
                    if key not in (media.storage_key_thumbnail, media.storage_key_gallery):
                        _delete_quietly(storage, key, media_id, "rendition")
                if source_key and source_key != media.storage_key_original:
                    _delete_quietly(storage, source_key, media_id, "source image")

                logger.info(
                    "Successfully generated image sizes",
                    extra={
                        "event": "keeps.media.image_sizes_success",
                        "extra": {
                            "media_id": media_id,
                            "keep_id": media.keep_id,
                            "width": media.width,
                            "height": media.height,
                        },
                    },
                )
                return True
            except Exception as exc:
                logger.exception(
                    "Failed to generate image sizes",
                    extra={
                        "event": "keeps.media.image_sizes_failure",
                        "extra": {"media_id": media_id},
                    },
                )

                if self.request.retries < self.max_retries:
                    attempt = self.request.retries + 1
                    logger.info(
                        "Retrying image processing",
                        extra={
                            "event": "keeps.media.image_sizes_retry",
                            "extra": {"media_id": media_id, "attempt": attempt},
                        },
                    )
                    raise self.retry(countdown=60 * (2**self.request.retries)) from exc

                raise


@shared_task
def cleanup_failed_uploads():
    """Clean up failed upload temporary files."""
    from datetime import timedelta

    from django.utils import timezone

    with project_logging.log_context(task="keeps.cleanup_failed_uploads"):
        cutoff = timezone.now() - timedelta(hours=1)
        failed_uploads = MediaUpload.objects.filter(status=MediaUploadStatus.FAILED, created_at__lt=cutoff)

        removed_count = 0
        for upload in failed_uploads:
            for temp_path in (upload.temp_file_path, upload.poster_temp_path):
                context_extra = {
                    "upload_id": upload.id,
                    "keep_id": upload.keep_id,
                    "temp_file_path": temp_path,
                }
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                        logger.info(
                            "Removed temporary file for failed upload",
                            extra={"event": "keeps.media.cleanup_file_removed", "extra": context_extra},
                        )
                    except OSError:
                        logger.exception(
                            "Failed to remove temporary file for failed upload",
                            extra={"event": "keeps.media.cleanup_file_failed", "extra": context_extra},
                        )

            upload.delete()
            removed_count += 1

        logger.info(
            "Completed cleanup of failed uploads",
            extra={"event": "keeps.media.cleanup_summary", "extra": {"removed_count": removed_count}},
        )


@shared_task
def validate_media_file(upload_id: str):
    """Validate uploaded media file."""
    with project_logging.log_context(task="keeps.validate_media_file", upload_id=upload_id):
        try:
            upload = MediaUpload.objects.get(id=upload_id)
        except MediaUpload.DoesNotExist:
            logger.warning(
                "Media upload missing during validation",
                extra={"event": "keeps.media.validation_missing_upload", "extra": {"upload_id": upload_id}},
            )
            return False

        with project_logging.log_context(keep_id=upload.keep_id, media_type=upload.media_type):
            try:
                if not os.path.exists(upload.temp_file_path):
                    raise ValueError("Temporary file not found")

                file_size = os.path.getsize(upload.temp_file_path)
                max_size = max_upload_size(upload.media_type)
                if file_size > max_size:
                    raise ValueError(f"File size {file_size} exceeds maximum allowed size {max_size}")

                if upload.media_type == "photo":
                    try:
                        with Image.open(upload.temp_file_path) as image:
                            image.verify()
                    except Exception as exc:
                        raise ValueError("Invalid image file") from exc

                if upload.poster_temp_path:
                    try:
                        with Image.open(upload.poster_temp_path) as image:
                            image.verify()
                    except Exception as exc:
                        raise ValueError("Invalid poster image") from exc

                logger.info(
                    "Media file validation passed",
                    extra={
                        "event": "keeps.media.validation_success",
                        "extra": {
                            "upload_id": upload_id,
                            "keep_id": upload.keep_id,
                            "file_size": file_size,
                            "media_type": upload.media_type,
                        },
                    },
                )

                process_media_upload.delay(upload_id)
                return True
            except Exception as exc:  # noqa: BLE001 - surface specific validation causes
                logger.exception(
                    "Media file validation failed",
                    extra={
                        "event": "keeps.media.validation_failure",
                        "extra": {"upload_id": upload_id},
                    },
                )

                try:
                    upload.status = MediaUploadStatus.FAILED
                    upload.error_message = f"Validation failed: {exc}"
                    upload.save(update_fields=["status", "error_message"])
                except MediaUpload.DoesNotExist:
                    logger.warning(
                        "Media upload missing when recording validation failure",
                        extra={"event": "keeps.media.validation_missing_on_failure"},
                    )

                raise


@shared_task
def send_activity_notifications(event: str, object_id: str):
    """Notify circle members about a new post, comment, reply or like."""
    with project_logging.log_context(task="keeps.send_activity_notifications", event=event, object_id=object_id):
        send_activity(event, object_id)


@shared_task
def send_new_post_digests():
    """Queue the daily new-post digest for everyone who opted in (run by beat)."""
    with project_logging.log_context(task="keeps.send_new_post_digests"):
        user_ids = digest_recipient_ids()
        for user_id in user_ids:
            send_new_post_digest.delay(user_id)
        logger.info("Queued new-post digests for %s users", len(user_ids))


@shared_task
def send_new_post_digest(user_id: int):
    """Email one user the posts that are new in their circles since their last digest."""
    with project_logging.log_context(task="keeps.send_new_post_digest", user_id=user_id):
        send_digest(user_id)
