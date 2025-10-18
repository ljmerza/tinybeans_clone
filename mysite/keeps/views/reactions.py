"""Views for Keep reactions."""
from rest_framework import generics, permissions
from drf_spectacular.utils import extend_schema, OpenApiResponse

from mysite.users.models import Circle
from ..models import KeepReaction
from ..serializers import KeepReactionSerializer
from .permissions import IsCircleMember, IsCircleAdminOrOwner, is_circle_admin


class KeepReactionListCreateView(generics.ListCreateAPIView):
    """List and create reactions to keeps."""
    
    serializer_class = KeepReactionSerializer
    permission_classes = [IsCircleMember]
    
    def get_queryset(self):
        """Return reactions for keeps the user can access."""
        # Avoid queryset evaluation during schema generation
        if getattr(self, 'swagger_fake_view', False):
            return KeepReaction.objects.none()
            
        if not self.request.user.is_authenticated:
            return KeepReaction.objects.none()
            
        user_circles = Circle.objects.filter(
            memberships__user=self.request.user
        )
        
        return KeepReaction.objects.filter(
            keep__circle__in=user_circles
        ).select_related('user', 'keep')
    
    def perform_create(self, serializer):
        """Set the user when creating a reaction."""
        serializer.save(user=self.request.user)
    
    @extend_schema(
        summary="List keep reactions",
        description="List all reactions to keeps that the user can access in their circles.",
        responses={
            200: OpenApiResponse(
                response=KeepReactionSerializer(many=True),
                description="List of reactions to keeps"
            )
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        summary="Create a reaction",
        description="Add a reaction (like, love, laugh, wow, celebrate) to a keep. "
                   "Each user can only have one reaction per keep.",
        request=KeepReactionSerializer,
        responses={
            201: OpenApiResponse(
                response=KeepReactionSerializer,
                description="Reaction created successfully"
            ),
            400: OpenApiResponse(
                description="Validation error or duplicate reaction"
            )
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class KeepReactionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a reaction."""
    
    serializer_class = KeepReactionSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'reaction_id'
    
    def get_permissions(self):
        """Return appropriate permissions based on action."""
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            permission_classes = [IsCircleAdminOrOwner]
        else:
            permission_classes = [IsCircleMember]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Return reactions for keeps the user can access."""
        # Avoid queryset evaluation during schema generation
        if getattr(self, 'swagger_fake_view', False):
            return KeepReaction.objects.none()
            
        if not self.request.user.is_authenticated:
            return KeepReaction.objects.none()
            
        user_circles = Circle.objects.filter(
            memberships__user=self.request.user
        )
        
        return KeepReaction.objects.filter(
            keep__circle__in=user_circles
        ).select_related('user', 'keep')
    
    def perform_update(self, serializer):
        """Allow creators and circle admins to update reactions."""
        reaction = serializer.instance
        user = self.request.user
        
        # Check if user is creator or circle admin
        if reaction.user != user and not is_circle_admin(user, reaction.keep.circle):
            raise permissions.PermissionDenied(
                "You can only update your own reactions or as a circle admin."
            )
        serializer.save()
    
    def perform_destroy(self, instance):
        """Allow creators and circle admins to delete reactions."""
        user = self.request.user
        
        # Check if user is creator or circle admin
        if instance.user != user and not is_circle_admin(user, instance.keep.circle):
            raise permissions.PermissionDenied(
                "You can only delete your own reactions or as a circle admin."
            )
        instance.delete()
    
    @extend_schema(
        summary="Retrieve a reaction",
        description="Get details of a specific reaction to a keep.",
        responses={
            200: OpenApiResponse(
                response=KeepReactionSerializer,
                description="Reaction details"
            ),
            404: OpenApiResponse(
                description="Reaction not found or not accessible"
            )
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        summary="Update a reaction",
        description="Update a reaction to a keep. Only the reaction creator or circle admins can update reactions.",
        request=KeepReactionSerializer,
        responses={
            200: OpenApiResponse(
                response=KeepReactionSerializer,
                description="Reaction updated successfully"
            ),
            403: OpenApiResponse(
                description="Permission denied - only creators or circle admins can update"
            )
        }
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
    
    @extend_schema(
        summary="Partially update a reaction",
        description="Partially update a reaction to a keep. Only the reaction creator or circle admins can update reactions.",
        request=KeepReactionSerializer,
        responses={
            200: OpenApiResponse(
                response=KeepReactionSerializer,
                description="Reaction updated successfully"
            ),
            403: OpenApiResponse(
                description="Permission denied - only creators or circle admins can update"
            )
        }
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)
    
    @extend_schema(
        summary="Delete a reaction",
        description="Delete a reaction to a keep. Only the reaction creator or circle admins can delete reactions.",
        responses={
            204: OpenApiResponse(
                description="Reaction deleted successfully"
            ),
            403: OpenApiResponse(
                description="Permission denied - only creators or circle admins can delete"
            )
        }
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)
