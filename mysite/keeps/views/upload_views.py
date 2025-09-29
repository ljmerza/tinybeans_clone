"""Views for handling media uploads and processing."""
import os
import tempfile
import uuid
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema, OpenApiResponse

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from ..models import Keep, MediaUpload, MediaUploadStatus
from ..tasks import validate_media_file
from ..serializers import MediaUploadSerializer, MediaUploadStatusSerializer
from .keep_views import IsCircleMember


class MediaUploadView(APIView):
    """Handle media file uploads for keeps."""
    
    permission_classes = [IsCircleMember]
    parser_classes = [MultiPartParser, FormParser]
    
    @extend_schema(
        summary="Upload media file",
        description="Upload a media file (photo or video) for a keep. The file will be processed asynchronously.",
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'keep_id': {'type': 'string', 'format': 'uuid'},
                    'media_type': {'type': 'string', 'enum': ['photo', 'video']},
                    'file': {'type': 'string', 'format': 'binary'},
                    'caption': {'type': 'string', 'maxLength': 500},
                    'upload_order': {'type': 'integer', 'minimum': 0},
                }
            }
        },
        responses={
            202: OpenApiResponse(
                response=MediaUploadSerializer,
                description="Upload initiated successfully, processing in background"
            ),
            400: OpenApiResponse(
                description="Invalid file or parameters"
            ),
            413: OpenApiResponse(
                description="File too large"
            )
        }
    )
    def post(self, request):
        """Handle media file upload."""
        # Get parameters
        keep_id = request.data.get('keep_id')
        media_type = request.data.get('media_type')
        uploaded_file = request.FILES.get('file')
        caption = request.data.get('caption', '')
        upload_order = int(request.data.get('upload_order', 0))
        
        # Validate parameters
        if not keep_id or not media_type or not uploaded_file:
            return Response(
                {'error': 'keep_id, media_type, and file are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if media_type not in ['photo', 'video']:
            return Response(
                {'error': 'media_type must be photo or video'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get keep and verify access
        try:
            keep = Keep.objects.get(id=keep_id)
        except Keep.DoesNotExist:
            return Response(
                {'error': 'Keep not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verify user has access to the keep's circle
        if not keep.circle.memberships.filter(user=request.user).exists():
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate file size
        if uploaded_file.size > settings.MAX_UPLOAD_SIZE:
            return Response(
                {'error': f'File size exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE} bytes'},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            )
        
        # Validate file type
        allowed_types = (
            settings.ALLOWED_IMAGE_TYPES if media_type == 'photo' 
            else settings.ALLOWED_VIDEO_TYPES
        )
        
        if uploaded_file.content_type not in allowed_types:
            return Response(
                {'error': f'File type {uploaded_file.content_type} not allowed for {media_type}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create temporary file
        temp_dir = tempfile.gettempdir()
        temp_filename = f"upload_{uuid.uuid4()}{os.path.splitext(uploaded_file.name)[1]}"
        temp_file_path = os.path.join(temp_dir, temp_filename)
        
        try:
            # Save uploaded file to temporary location
            with open(temp_file_path, 'wb') as temp_file:
                for chunk in uploaded_file.chunks():
                    temp_file.write(chunk)
            
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
                status=MediaUploadStatus.PENDING
            )
            
            # Start validation and processing
            validate_media_file.delay(str(upload.id))
            
            # Return upload info
            serializer = MediaUploadSerializer(upload)
            return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            # Clean up temporary file on error
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            
            return Response(
                {'error': f'Upload failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MediaUploadStatusView(APIView):
    """Check the status of a media upload."""
    
    permission_classes = [IsCircleMember]
    
    @extend_schema(
        summary="Check upload status",
        description="Check the processing status of a media upload.",
        responses={
            200: OpenApiResponse(
                response=MediaUploadStatusSerializer,
                description="Upload status information"
            ),
            404: OpenApiResponse(
                description="Upload not found"
            )
        }
    )
    def get(self, request, upload_id):
        """Get upload status."""
        try:
            upload = MediaUpload.objects.select_related(
                'keep__circle', 'media_file'
            ).get(id=upload_id)
        except MediaUpload.DoesNotExist:
            return Response(
                {'error': 'Upload not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verify user has access to the keep's circle
        if not upload.keep.circle.memberships.filter(user=request.user).exists():
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = MediaUploadStatusSerializer(upload)
        return Response(serializer.data)