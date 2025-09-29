"""Views for Keep comments."""
from rest_framework import generics, permissions
from drf_spectacular.utils import extend_schema, OpenApiResponse

from users.models import Circle
from ..models import KeepComment
from ..serializers import KeepCommentSerializer
from .permissions import IsCircleMember, IsCircleAdminOrOwner, is_circle_admin


class KeepCommentListCreateView(generics.ListCreateAPIView):
    """List and create comments on keeps."""
    
    serializer_class = KeepCommentSerializer
    permission_classes = [IsCircleMember]
    
    def get_queryset(self):
        """Return comments for keeps the user can access."""
        # Avoid queryset evaluation during schema generation
        if getattr(self, 'swagger_fake_view', False):
            return KeepComment.objects.none()
            
        if not self.request.user.is_authenticated:
            return KeepComment.objects.none()
            
        user_circles = Circle.objects.filter(
            memberships__user=self.request.user
        )
        
        return KeepComment.objects.filter(
            keep__circle__in=user_circles
        ).select_related('user', 'keep')
    
    def perform_create(self, serializer):
        """Set the user when creating a comment."""
        serializer.save(user=self.request.user)
    
    @extend_schema(
        summary="List keep comments",
        description="List all comments on keeps that the user can access in their circles.",
        responses={
            200: OpenApiResponse(
                response=KeepCommentSerializer(many=True),
                description="List of comments on keeps"
            )
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        summary="Create a comment",
        description="Add a comment to a keep. All circle members can comment on keeps in their circles.",
        request=KeepCommentSerializer,
        responses={
            201: OpenApiResponse(
                response=KeepCommentSerializer,
                description="Comment created successfully"
            ),
            400: OpenApiResponse(
                description="Validation error"
            )
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class KeepCommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a comment."""
    
    serializer_class = KeepCommentSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'comment_id'
    
    def get_permissions(self):
        """Return appropriate permissions based on action."""
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            permission_classes = [IsCircleAdminOrOwner]
        else:
            permission_classes = [IsCircleMember]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Return comments for keeps the user can access."""
        # Avoid queryset evaluation during schema generation
        if getattr(self, 'swagger_fake_view', False):
            return KeepComment.objects.none()
            
        if not self.request.user.is_authenticated:
            return KeepComment.objects.none()
            
        user_circles = Circle.objects.filter(
            memberships__user=self.request.user
        )
        
        return KeepComment.objects.filter(
            keep__circle__in=user_circles
        ).select_related('user', 'keep')
    
    def perform_update(self, serializer):
        """Allow creators and circle admins to update comments."""
        comment = serializer.instance
        user = self.request.user
        
        # Check if user is creator or circle admin
        if comment.user != user and not is_circle_admin(user, comment.keep.circle):
            raise permissions.PermissionDenied(
                "You can only update your own comments or as a circle admin."
            )
        serializer.save()
    
    def perform_destroy(self, instance):
        """Allow creators and circle admins to delete comments."""
        user = self.request.user
        
        # Check if user is creator or circle admin
        if instance.user != user and not is_circle_admin(user, instance.keep.circle):
            raise permissions.PermissionDenied(
                "You can only delete your own comments or as a circle admin."
            )
        instance.delete()
    
    @extend_schema(
        summary="Retrieve a comment",
        description="Get details of a specific comment on a keep.",
        responses={
            200: OpenApiResponse(
                response=KeepCommentSerializer,
                description="Comment details"
            ),
            404: OpenApiResponse(
                description="Comment not found or not accessible"
            )
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        summary="Update a comment",
        description="Update a comment on a keep. Only the comment creator or circle admins can update comments.",
        request=KeepCommentSerializer,
        responses={
            200: OpenApiResponse(
                response=KeepCommentSerializer,
                description="Comment updated successfully"
            ),
            403: OpenApiResponse(
                description="Permission denied - only creators or circle admins can update"
            )
        }
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
    
    @extend_schema(
        summary="Partially update a comment",
        description="Partially update a comment on a keep. Only the comment creator or circle admins can update comments.",
        request=KeepCommentSerializer,
        responses={
            200: OpenApiResponse(
                response=KeepCommentSerializer,
                description="Comment updated successfully"
            ),
            403: OpenApiResponse(
                description="Permission denied - only creators or circle admins can update"
            )
        }
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)
    
    @extend_schema(
        summary="Delete a comment",
        description="Delete a comment on a keep. Only the comment creator or circle admins can delete comments.",
        responses={
            204: OpenApiResponse(
                description="Comment deleted successfully"
            ),
            403: OpenApiResponse(
                description="Permission denied - only creators or circle admins can delete"
            )
        }
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)
