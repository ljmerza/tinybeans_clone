"""Celery tasks for media upload and processing."""
import os
from io import BytesIO
from PIL import Image, ImageOps
from django.conf import settings
from celery import shared_task
from celery.utils.log import get_task_logger

from .models import KeepMedia, MediaUpload, MediaUploadStatus
from .storage import get_storage_backend

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3)
def process_media_upload(self, upload_id: str):
    """Process a media upload asynchronously."""
    try:
        # Get upload record
        upload = MediaUpload.objects.get(id=upload_id)
        upload.status = MediaUploadStatus.PROCESSING
        upload.save()
        
        logger.info(f"Processing media upload {upload_id}")
        
        # Read the temporary file
        with open(upload.temp_file_path, 'rb') as f:
            file_content = f.read()
        
        # Get storage backend
        storage = get_storage_backend()
        
        # Save original file to storage
        storage_key_original = storage.save(
            file_content=file_content,
            filename=upload.original_filename,
            content_type=upload.content_type
        )
        
        # Get file metadata
        metadata = storage.get_metadata(storage_key_original)
        
        # Create KeepMedia record
        media = KeepMedia.objects.create(
            keep=upload.keep,
            media_type=upload.media_type,
            caption=upload.caption,
            upload_order=upload.upload_order,
            storage_key_original=storage_key_original,
            file_size=metadata.get('size', len(file_content)),
            original_filename=upload.original_filename,
            content_type=upload.content_type
        )
        
        # Process images for thumbnails and gallery versions
        if upload.media_type == 'photo':
            generate_image_sizes.delay(media.id)
        
        # Update upload status
        upload.status = MediaUploadStatus.COMPLETED
        upload.media_file = media
        upload.save()
        
        # Clean up temporary file
        if os.path.exists(upload.temp_file_path):
            os.remove(upload.temp_file_path)
        
        logger.info(f"Successfully processed media upload {upload_id}")
        
    except Exception as exc:
        logger.error(f"Failed to process media upload {upload_id}: {exc}")
        
        # Update upload status
        try:
            upload = MediaUpload.objects.get(id=upload_id)
            upload.status = MediaUploadStatus.FAILED
            upload.error_message = str(exc)
            upload.save()
        except MediaUpload.DoesNotExist:
            pass
        
        # Retry task
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying media upload {upload_id} (attempt {self.request.retries + 1})")
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        
        raise exc


@shared_task(bind=True, max_retries=3)
def generate_image_sizes(self, media_id: int):
    """Generate thumbnail and gallery size images."""
    try:
        media = KeepMedia.objects.get(id=media_id)
        
        if media.media_type != 'photo':
            logger.warning(f"Skipping image processing for non-photo media {media_id}")
            return
        
        logger.info(f"Generating image sizes for media {media_id}")
        
        storage = get_storage_backend()
        
        # Get the original image
        image_data = storage.get_file_content(media.storage_key_original)
        
        # Create PIL Image
        image = Image.open(BytesIO(image_data))
        
        # Fix orientation based on EXIF data
        image = ImageOps.exif_transpose(image)
        
        # Store original dimensions
        media.width, media.height = image.size
        
        # Generate thumbnail (150x150)
        thumbnail_image = image.copy()
        thumbnail_image.thumbnail((150, 150), Image.Resampling.LANCZOS)
        
        # Save thumbnail
        thumbnail_io = BytesIO()
        thumbnail_image.save(thumbnail_io, format='JPEG', quality=85, optimize=True)
        thumbnail_data = thumbnail_io.getvalue()
        
        # Save thumbnail to storage and capture returned key
        media.storage_key_thumbnail = storage.save(
            file_content=thumbnail_data,
            filename="thumbnail.jpg",
            content_type="image/jpeg"
        )
        
        # Generate gallery size (800x600 max, maintain aspect ratio)
        gallery_image = image.copy()
        gallery_image.thumbnail((800, 600), Image.Resampling.LANCZOS)
        
        # Save gallery version
        gallery_io = BytesIO()
        gallery_image.save(gallery_io, format='JPEG', quality=90, optimize=True)
        gallery_data = gallery_io.getvalue()
        
        # Save gallery version to storage
        media.storage_key_gallery = storage.save(
            file_content=gallery_data,
            filename="gallery.jpg",
            content_type="image/jpeg"
        )
        
        media.thumbnails_generated = True
        media.save()
        
        logger.info(f"Successfully generated image sizes for media {media_id}")
        
    except Exception as exc:
        logger.error(f"Failed to generate image sizes for media {media_id}: {exc}")
        
        # Retry task
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying image processing for media {media_id} (attempt {self.request.retries + 1})")
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        
        raise exc


@shared_task
def cleanup_failed_uploads():
    """Clean up failed upload temporary files."""
    from datetime import timedelta
    from django.utils import timezone
    
    # Find failed uploads older than 1 hour
    cutoff = timezone.now() - timedelta(hours=1)
    failed_uploads = MediaUpload.objects.filter(
        status=MediaUploadStatus.FAILED,
        created_at__lt=cutoff
    )
    
    removed_count = 0
    for upload in failed_uploads:
        # Remove temporary file
        if upload.temp_file_path and os.path.exists(upload.temp_file_path):
            try:
                os.remove(upload.temp_file_path)
                logger.info(f"Cleaned up temporary file: {upload.temp_file_path}")
            except OSError as e:
                logger.error(f"Failed to remove temporary file {upload.temp_file_path}: {e}")
        
        # Delete upload record
        upload.delete()
        removed_count += 1
    
    logger.info(f"Cleaned up {removed_count} failed uploads")


@shared_task
def validate_media_file(upload_id: str):
    """Validate uploaded media file."""
    try:
        upload = MediaUpload.objects.get(id=upload_id)
        
        # Basic file validation
        if not os.path.exists(upload.temp_file_path):
            raise ValueError("Temporary file not found")
        
        file_size = os.path.getsize(upload.temp_file_path)
        
        # Check file size limits
        max_size = settings.MAX_UPLOAD_SIZE
        if file_size > max_size:
            raise ValueError(f"File size {file_size} exceeds maximum allowed size {max_size}")
        
        # Validate file type
        if upload.media_type == 'photo':
            try:
                with Image.open(upload.temp_file_path) as img:
                    # Verify it's a valid image
                    img.verify()
            except Exception:
                raise ValueError("Invalid image file")
        
        # TODO: Add video validation for video files
        # TODO: Add virus scanning
        # TODO: Add content analysis
        
        logger.info(f"Media file validation passed for upload {upload_id}")
        
        # Proceed to processing
        process_media_upload.delay(upload_id)
        
    except Exception as exc:
        logger.error(f"Media file validation failed for upload {upload_id}: {exc}")
        
        # Update upload status
        try:
            upload = MediaUpload.objects.get(id=upload_id)
            upload.status = MediaUploadStatus.FAILED
            upload.error_message = f"Validation failed: {exc}"
            upload.save()
        except MediaUpload.DoesNotExist:
            pass
        
        raise exc
