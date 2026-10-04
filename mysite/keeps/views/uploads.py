"""Views for handling media uploads and processing."""

import os
import uuid

from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView

from mysite.notification_utils import create_message, error_response, success_response

from ..models import Keep, MediaUpload, MediaUploadStatus
from ..serializers import MediaUploadSerializer, MediaUploadStatusSerializer
from ..tasks import max_upload_size, validate_media_file
from .permissions import IsCircleMember

# A browser-captured poster frame is one JPEG; anything near this is not one.
MAX_POSTER_SIZE = 10 * 1024 * 1024
# Room for the multipart boundaries and the form fields next to the files.
MULTIPART_OVERHEAD = 1024 * 1024


def max_upload_request_size() -> int:
    """Largest upload request body the app accepts, in bytes.

    The biggest allowed file plus a poster frame and multipart overhead. A
    reverse proxy in front of Django must allow at least this much, or it
    rejects files the app would take and answers before the app can explain.
    """
    return max(settings.MAX_UPLOAD_SIZE, settings.MAX_VIDEO_UPLOAD_SIZE) + MAX_POSTER_SIZE + MULTIPART_OVERHEAD


def _park_file(uploaded_file, suffix):
    """Copy an uploaded file into the shared upload dir and return its path."""
    os.makedirs(settings.UPLOAD_TEMP_DIR, exist_ok=True)
    path = os.path.join(settings.UPLOAD_TEMP_DIR, f"upload_{uuid.uuid4()}{suffix}")
    with open(path, "wb") as temp_file:
        for chunk in uploaded_file.chunks():
            temp_file.write(chunk)
    return path


class MediaUploadView(APIView):
    """Handle media file uploads for keeps."""

    permission_classes = [IsCircleMember]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        summary="Upload media file",
        description="Upload a media file (photo or video) for a keep. The file will be processed asynchronously. "
        "A video may include a `poster` image (e.g. a frame captured in the browser); the feed only shows "
        "videos that have one.",
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "keep_id": {"type": "string", "format": "uuid"},
                    "media_type": {"type": "string", "enum": ["photo", "video"]},
                    "file": {"type": "string", "format": "binary"},
                    "caption": {"type": "string", "maxLength": 500},
                    "upload_order": {"type": "integer", "minimum": 0},
                    "poster": {"type": "string", "format": "binary"},
                },
            }
        },
        responses={
            202: OpenApiResponse(
                response=MediaUploadSerializer, description="Upload initiated successfully, processing in background"
            ),
            400: OpenApiResponse(description="Invalid file or parameters"),
            413: OpenApiResponse(description="File too large"),
        },
    )
    def post(self, request):
        """Handle media file upload."""
        # Get parameters
        keep_id = request.data.get("keep_id")
        media_type = request.data.get("media_type")
        uploaded_file = request.FILES.get("file")
        poster_file = request.FILES.get("poster") if media_type == "video" else None
        caption = request.data.get("caption", "")
        upload_order = int(request.data.get("upload_order", 0))

        # Validate parameters
        if not keep_id or not media_type or not uploaded_file:
            return error_response(
                "required_fields_missing",
                messages=[create_message("errors.required_fields_missing")],
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if media_type not in ["photo", "video"]:
            return error_response(
                "invalid_media_type",
                messages=[create_message("errors.invalid_media_type")],
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Get keep and verify access
        try:
            keep = Keep.objects.get(id=keep_id)
        except Keep.DoesNotExist:
            return error_response(
                "keep_not_found",
                messages=[create_message("errors.keep_not_found")],
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # Verify user has access to the keep's circle
        if not keep.circle.memberships.filter(user=request.user).exists():
            return error_response(
                "access_denied",
                messages=[create_message("errors.access_denied")],
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # Validate file size
        max_size = max_upload_size(media_type)
        if uploaded_file.size > max_size:
            return error_response(
                "file_too_large",
                messages=[create_message("errors.file_too_large", {"maxSize": max_size})],
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        # Validate file type
        allowed_types = settings.ALLOWED_IMAGE_TYPES if media_type == "photo" else settings.ALLOWED_VIDEO_TYPES

        if uploaded_file.content_type not in allowed_types:
            return error_response(
                "invalid_file_type",
                messages=[create_message("errors.invalid_file_type", {"allowedTypes": ", ".join(allowed_types)})],
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if poster_file and (
            poster_file.content_type not in settings.ALLOWED_IMAGE_TYPES or poster_file.size > MAX_POSTER_SIZE
        ):
            return error_response(
                "invalid_file_type",
                messages=[
                    create_message(
                        "errors.invalid_file_type", {"allowedTypes": ", ".join(settings.ALLOWED_IMAGE_TYPES)}
                    )
                ],
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        temp_file_path = ""
        poster_temp_path = ""

        try:
            # Park the files where the Celery worker can read them
            temp_file_path = _park_file(uploaded_file, os.path.splitext(uploaded_file.name)[1])
            if poster_file:
                poster_temp_path = _park_file(poster_file, ".poster")

            # Create upload record
            upload = MediaUpload.objects.create(
                keep=keep,
                media_type=media_type,
                original_filename=uploaded_file.name,
                content_type=uploaded_file.content_type,
                file_size=uploaded_file.size,
                caption=caption,
                upload_order=upload_order,
                temp_file_path=temp_file_path,
                poster_temp_path=poster_temp_path,
                status=MediaUploadStatus.PENDING,
            )

            # Start validation and processing
            validate_media_file.delay(str(upload.id))

            # Return upload info
            serializer = MediaUploadSerializer(upload)
            return success_response(
                serializer.data,
                messages=[create_message("notifications.media.upload_initiated")],
                status_code=status.HTTP_202_ACCEPTED,
            )

        except Exception:
            # Clean up temporary files on error
            for path in (temp_file_path, poster_temp_path):
                if path and os.path.exists(path):
                    os.remove(path)

            return error_response(
                "upload_failed",
                messages=[create_message("errors.upload_failed")],
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MediaUploadLimitsView(APIView):
    """The largest photo and video an upload accepts, so the client can check first."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Upload limits",
        description="Largest accepted photo and video, in bytes (MAX_UPLOAD_SIZE / MAX_VIDEO_UPLOAD_SIZE).",
        responses={200: OpenApiResponse(description="`{max_photo_bytes, max_video_bytes}`")},
    )
    def get(self, request):
        return success_response(
            {
                "max_photo_bytes": max_upload_size("photo"),
                "max_video_bytes": max_upload_size("video"),
            }
        )


class MediaUploadStatusView(APIView):
    """Check the status of a media upload."""

    permission_classes = [IsCircleMember]

    @extend_schema(
        summary="Check upload status",
        description="Check the processing status of a media upload.",
        responses={
            200: OpenApiResponse(response=MediaUploadStatusSerializer, description="Upload status information"),
            404: OpenApiResponse(description="Upload not found"),
        },
    )
    def get(self, request, upload_id):
        """Get upload status."""
        try:
            upload = MediaUpload.objects.select_related("keep__circle", "media_file").get(id=upload_id)
        except MediaUpload.DoesNotExist:
            return error_response(
                "upload_not_found", [create_message("errors.upload_not_found")], status.HTTP_404_NOT_FOUND
            )

        # Verify user has access to the keep's circle
        if not upload.keep.circle.memberships.filter(user=request.user).exists():
            return error_response("access_denied", [create_message("errors.access_denied")], status.HTTP_403_FORBIDDEN)

        serializer = MediaUploadStatusSerializer(upload)
        return success_response(serializer.data)
