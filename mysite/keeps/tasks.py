"""Celery tasks for media upload and processing."""
import os
from io import BytesIO
from PIL import Image, ImageOps
from django.conf import settings
from celery import shared_task
from celery.utils.log import get_task_logger

from mysite import project_logging

from .models import KeepMedia, MediaUpload, MediaUploadStatus
from .storage import get_storage_backend

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3)
def process_media_upload(self, upload_id: str):
    """Process a media upload asynchronously."""
    with project_logging.log_context(task='keeps.process_media_upload', upload_id=upload_id):
        try:
            upload = MediaUpload.objects.get(id=upload_id)
        except MediaUpload.DoesNotExist:
            logger.warning(
                'Media upload not found for processing',
                extra={'event': 'keeps.media.upload_missing', 'extra': {'upload_id': upload_id}},
            )
            return False

        with project_logging.log_context(keep_id=upload.keep_id, media_type=upload.media_type):
            try:
                upload.status = MediaUploadStatus.PROCESSING
                upload.save(update_fields=['status'])

                logger.info(
                    'Processing media upload',
                    extra={
                        'event': 'keeps.media.process_start',
                        'extra': {
                            'upload_id': upload_id,
                            'keep_id': upload.keep_id,
                            'media_type': upload.media_type,
                            'content_type': upload.content_type,
                        },
                    },
                )

                with open(upload.temp_file_path, 'rb') as file_handle:
                    file_content = file_handle.read()

                storage = get_storage_backend()
                storage_key_original = storage.save(
                    file_content=file_content,
                    filename=upload.original_filename,
                    content_type=upload.content_type
                )

                metadata = storage.get_metadata(storage_key_original)
                file_size = metadata.get('size', len(file_content))

                media = KeepMedia.objects.create(
                    keep=upload.keep,
                    media_type=upload.media_type,
                    caption=upload.caption,
                    upload_order=upload.upload_order,
                    storage_key_original=storage_key_original,
                    file_size=file_size,
                    original_filename=upload.original_filename,
                    content_type=upload.content_type
                )

                if upload.media_type == 'photo':
                    generate_image_sizes.delay(media.id)
                    logger.info(
                        'Queued image resize task',
                        extra={
                            'event': 'keeps.media.image_resize_queued',
                            'extra': {'media_id': media.id},
                        },
                    )

                upload.status = MediaUploadStatus.COMPLETED
                upload.media_file = media
                upload.error_message = ''
                upload.save(update_fields=['status', 'media_file', 'error_message'])

                if os.path.exists(upload.temp_file_path):
                    os.remove(upload.temp_file_path)

                logger.info(
                    'Successfully processed media upload',
                    extra={
                        'event': 'keeps.media.process_success',
                        'extra': {
                            'upload_id': upload_id,
                            'media_id': media.id,
                            'keep_id': upload.keep_id,
                        },
                    },
                )
                return True
            except Exception as exc:  # noqa: BLE001 - ensure we capture and persist failure details
                logger.exception(
                    'Failed to process media upload',
                    extra={
                        'event': 'keeps.media.process_failure',
                        'extra': {'upload_id': upload_id},
                    },
                )

                try:
                    upload.status = MediaUploadStatus.FAILED
                    upload.error_message = str(exc)
                    upload.save(update_fields=['status', 'error_message'])
                except MediaUpload.DoesNotExist:
                    logger.warning(
                        'Media upload missing during failure handling',
                        extra={'event': 'keeps.media.upload_missing_on_failure'},
                    )

                if self.request.retries < self.max_retries:
                    attempt = self.request.retries + 1
                    logger.info(
                        'Retrying media upload processing',
                        extra={
                            'event': 'keeps.media.retry_scheduled',
                            'extra': {'upload_id': upload_id, 'attempt': attempt},
                        },
                    )
                    raise self.retry(countdown=60 * (2 ** self.request.retries))

                raise


@shared_task(bind=True, max_retries=3)
def generate_image_sizes(self, media_id: int):
    """Generate thumbnail and gallery size images."""
    with project_logging.log_context(task='keeps.generate_image_sizes', media_id=media_id):
        try:
            media = KeepMedia.objects.get(id=media_id)
        except KeepMedia.DoesNotExist:
            logger.warning(
                'Media record not found for image sizing',
                extra={'event': 'keeps.media.image_sizes_missing', 'extra': {'media_id': media_id}},
            )
            return False

        with project_logging.log_context(keep_id=media.keep_id, media_type=media.media_type):
            if media.media_type != 'photo':
                logger.info(
                    'Skipping image processing for non-photo media',
                    extra={
                        'event': 'keeps.media.image_sizes_skipped',
                        'extra': {'media_id': media_id, 'media_type': media.media_type},
                    },
                )
                return False

            try:
                storage = get_storage_backend()
                image_data = storage.get_file_content(media.storage_key_original)
                image = Image.open(BytesIO(image_data))
                image = ImageOps.exif_transpose(image)
                media.width, media.height = image.size

                thumbnail_image = image.copy()
                thumbnail_image.thumbnail((150, 150), Image.Resampling.LANCZOS)
                thumbnail_io = BytesIO()
                thumbnail_image.save(thumbnail_io, format='JPEG', quality=85, optimize=True)
                thumbnail_data = thumbnail_io.getvalue()
                media.storage_key_thumbnail = storage.save(
                    file_content=thumbnail_data,
                    filename='thumbnail.jpg',
                    content_type='image/jpeg'
                )

                gallery_image = image.copy()
                gallery_image.thumbnail((800, 600), Image.Resampling.LANCZOS)
                gallery_io = BytesIO()
                gallery_image.save(gallery_io, format='JPEG', quality=90, optimize=True)
                gallery_data = gallery_io.getvalue()
                media.storage_key_gallery = storage.save(
                    file_content=gallery_data,
                    filename='gallery.jpg',
                    content_type='image/jpeg'
                )

                media.thumbnails_generated = True
                media.save(update_fields=[
                    'width',
                    'height',
                    'storage_key_thumbnail',
                    'storage_key_gallery',
                    'thumbnails_generated',
                ])

                logger.info(
                    'Successfully generated image sizes',
                    extra={
                        'event': 'keeps.media.image_sizes_success',
                        'extra': {
                            'media_id': media_id,
                            'keep_id': media.keep_id,
                            'width': media.width,
                            'height': media.height,
                        },
                    },
                )
                return True
            except Exception:
                logger.exception(
                    'Failed to generate image sizes',
                    extra={
                        'event': 'keeps.media.image_sizes_failure',
                        'extra': {'media_id': media_id},
                    },
                )

                if self.request.retries < self.max_retries:
                    attempt = self.request.retries + 1
                    logger.info(
                        'Retrying image processing',
                        extra={
                            'event': 'keeps.media.image_sizes_retry',
                            'extra': {'media_id': media_id, 'attempt': attempt},
                        },
                    )
                    raise self.retry(countdown=60 * (2 ** self.request.retries))

                raise


@shared_task
def cleanup_failed_uploads():
    """Clean up failed upload temporary files."""
    from datetime import timedelta
    from django.utils import timezone

    with project_logging.log_context(task='keeps.cleanup_failed_uploads'):
        cutoff = timezone.now() - timedelta(hours=1)
        failed_uploads = MediaUpload.objects.filter(
            status=MediaUploadStatus.FAILED,
            created_at__lt=cutoff
        )

        removed_count = 0
        for upload in failed_uploads:
            context_extra = {
                'upload_id': upload.id,
                'keep_id': upload.keep_id,
                'temp_file_path': upload.temp_file_path,
            }
            if upload.temp_file_path and os.path.exists(upload.temp_file_path):
                try:
                    os.remove(upload.temp_file_path)
                    logger.info(
                        'Removed temporary file for failed upload',
                        extra={'event': 'keeps.media.cleanup_file_removed', 'extra': context_extra},
                    )
                except OSError:
                    logger.exception(
                        'Failed to remove temporary file for failed upload',
                        extra={'event': 'keeps.media.cleanup_file_failed', 'extra': context_extra},
                    )

            upload.delete()
            removed_count += 1

        logger.info(
            'Completed cleanup of failed uploads',
            extra={'event': 'keeps.media.cleanup_summary', 'extra': {'removed_count': removed_count}},
        )


@shared_task
def validate_media_file(upload_id: str):
    """Validate uploaded media file."""
    with project_logging.log_context(task='keeps.validate_media_file', upload_id=upload_id):
        try:
            upload = MediaUpload.objects.get(id=upload_id)
        except MediaUpload.DoesNotExist:
            logger.warning(
                'Media upload missing during validation',
                extra={'event': 'keeps.media.validation_missing_upload', 'extra': {'upload_id': upload_id}},
            )
            return False

        with project_logging.log_context(keep_id=upload.keep_id, media_type=upload.media_type):
            try:
                if not os.path.exists(upload.temp_file_path):
                    raise ValueError('Temporary file not found')

                file_size = os.path.getsize(upload.temp_file_path)
                max_size = settings.MAX_UPLOAD_SIZE
                if file_size > max_size:
                    raise ValueError(f'File size {file_size} exceeds maximum allowed size {max_size}')

                if upload.media_type == 'photo':
                    try:
                        with Image.open(upload.temp_file_path) as image:
                            image.verify()
                    except Exception as exc:
                        raise ValueError('Invalid image file') from exc

                logger.info(
                    'Media file validation passed',
                    extra={
                        'event': 'keeps.media.validation_success',
                        'extra': {
                            'upload_id': upload_id,
                            'keep_id': upload.keep_id,
                            'file_size': file_size,
                            'media_type': upload.media_type,
                        },
                    },
                )

                process_media_upload.delay(upload_id)
                return True
            except Exception as exc:  # noqa: BLE001 - surface specific validation causes
                logger.exception(
                    'Media file validation failed',
                    extra={
                        'event': 'keeps.media.validation_failure',
                        'extra': {'upload_id': upload_id},
                    },
                )

                try:
                    upload.status = MediaUploadStatus.FAILED
                    upload.error_message = f'Validation failed: {exc}'
                    upload.save(update_fields=['status', 'error_message'])
                except MediaUpload.DoesNotExist:
                    logger.warning(
                        'Media upload missing when recording validation failure',
                        extra={'event': 'keeps.media.validation_missing_on_failure'},
                    )

                raise
