"""Views for Keep media files."""
from rest_framework import generics, permissions
from drf_spectacular.utils import extend_schema, OpenApiResponse

from mysite.circles.models import Circle
from ..models import KeepMedia
from ..serializers import KeepMediaSerializer
from .permissions import IsCircleMember, IsCircleAdminOrOwner, is_circle_admin


class KeepMediaListCreateView(generics.ListCreateAPIView):
    """List and create media files for keeps."""
    
    serializer_class = KeepMediaSerializer
    permission_classes = [IsCircleMember]
    
    def get_queryset(self):
        """Return media for keeps the user can access."""
        # Avoid queryset evaluation during schema generation
        if getattr(self, 'swagger_fake_view', False):
            return KeepMedia.objects.none()
            
        if not self.request.user.is_authenticated:
            return KeepMedia.objects.none()
            
        user_circles = Circle.objects.filter(
            memberships__user=self.request.user
        )
        
        return KeepMedia.objects.filter(
            keep__circle__in=user_circles
        ).select_related('keep')
    
    @extend_schema(
        summary="List keep media files",
        description="List all media files (photos and videos) attached to keeps in user's circles.",
        responses={
            200: OpenApiResponse(
                response=KeepMediaSerializer(many=True),
                description="List of media files"
            )
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        summary="Upload media file",
        description="Upload a new media file (photo or video) and attach it to a keep.",
        request=KeepMediaSerializer,
        responses={
            201: OpenApiResponse(
                response=KeepMediaSerializer,
                description="Media file uploaded successfully"
            ),
            400: OpenApiResponse(
                description="Validation error or unsupported file type"
            )
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class KeepMediaDetailView(generics.RetrieveDestroyAPIView):
    """Retrieve or delete media files."""
    
    serializer_class = KeepMediaSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'media_id'
    
    def get_permissions(self):
        """Return appropriate permissions based on action."""
        if self.request.method == 'DELETE':
            permission_classes = [IsCircleAdminOrOwner]
        else:
            permission_classes = [IsCircleMember]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Return media for keeps the user can access."""
        # Avoid queryset evaluation during schema generation
        if getattr(self, 'swagger_fake_view', False):
            return KeepMedia.objects.none()
            
        if not self.request.user.is_authenticated:
            return KeepMedia.objects.none()
            
        user_circles = Circle.objects.filter(
            memberships__user=self.request.user
        )
        
        return KeepMedia.objects.filter(
            keep__circle__in=user_circles
        ).select_related('keep')
    
    def perform_destroy(self, instance):
        """Allow keep creators and circle admins to delete media."""
        user = self.request.user
        
        # Check if user is keep creator or circle admin
        if instance.keep.created_by != user and not is_circle_admin(user, instance.keep.circle):
            raise permissions.PermissionDenied(
                "You can only delete media from keeps you created or as a circle admin."
            )
        instance.delete()
    
    @extend_schema(
        summary="Retrieve media file",
        description="Get details of a specific media file attached to a keep.",
        responses={
            200: OpenApiResponse(
                response=KeepMediaSerializer,
                description="Media file details"
            ),
            404: OpenApiResponse(
                description="Media file not found or not accessible"
            )
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        summary="Delete media file",
        description="Delete a media file from a keep. Only the keep creator or circle admins can delete media files.",
        responses={
            204: OpenApiResponse(
                description="Media file deleted successfully"
            ),
            403: OpenApiResponse(
                description="Permission denied - only keep creators or circle admins can delete"
            ),
            404: OpenApiResponse(
                description="Media file not found or not accessible"
            )
        }
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)
