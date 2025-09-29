"""Views for Keep models and related functionality.

This module provides API views for managing family memories (keeps)
with proper permissions and filtering within family circles.
"""
from rest_framework import permissions, status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Prefetch
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiTypes, OpenApiParameter

from users.models import Circle, CircleMembership, UserRole
from ..models import (
    Keep,
    KeepMedia,
    KeepReaction,
    KeepComment,
    KeepType,
)
from ..serializers import (
    KeepSerializer,
    KeepCreateSerializer,
    KeepDetailSerializer,
    KeepMediaSerializer,
    KeepReactionSerializer,
    KeepCommentSerializer,
)


class IsCircleMember(permissions.BasePermission):
    """Permission to check if user is a member of the circle."""
    
    def has_permission(self, request, view):
        """Check if user is authenticated."""
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """Check if user is a member of the circle containing the object."""
        # For Keep objects
        if hasattr(obj, 'circle'):
            circle = obj.circle
        # For related objects (comments, reactions, etc.)
        elif hasattr(obj, 'keep'):
            circle = obj.keep.circle
        else:
            return False
        
        return CircleMembership.objects.filter(
            user=request.user,
            circle=circle
        ).exists()


class IsCircleAdminOrOwner(permissions.BasePermission):
    """Permission to check if user is circle admin or owner of the object."""
    
    def has_permission(self, request, view):
        """Check if user is authenticated."""
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """Check if user can modify this object."""
        # For Keep objects
        if hasattr(obj, 'circle'):
            circle = obj.circle
            owner_field = 'created_by'
        # For related objects (comments, reactions, etc.)
        elif hasattr(obj, 'keep'):
            circle = obj.keep.circle
            owner_field = 'user'
        else:
            return False
        
        # First check if user is a member of the circle
        try:
            membership = CircleMembership.objects.get(
                user=request.user,
                circle=circle
            )
        except CircleMembership.DoesNotExist:
            return False
        
        # Allow if user is circle admin
        if membership.role == UserRole.CIRCLE_ADMIN:
            return True
        
        # Allow if user is the owner of the object
        owner = getattr(obj, owner_field, None)
        return owner == request.user


def is_circle_admin(user, circle):
    """Check if user is an admin of the given circle."""
    try:
        membership = CircleMembership.objects.get(user=user, circle=circle)
        return membership.role == UserRole.CIRCLE_ADMIN
    except CircleMembership.DoesNotExist:
        return False


def can_user_post_in_circle(user, circle):
    """Check if user can post keeps in the given circle (member or admin)."""
    return CircleMembership.objects.filter(
        user=user,
        circle=circle
    ).exists()


class KeepListCreateView(generics.ListCreateAPIView):
    """List and create family memories (keeps)."""
    
    permission_classes = [IsCircleMember]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['keep_type', 'circle', 'created_by', 'is_public']
    search_fields = ['title', 'description', 'tags']
    ordering_fields = ['date_of_memory', 'created_at', 'updated_at']
    ordering = ['-date_of_memory', '-created_at']
    
    def get_queryset(self):
        """Return keeps from circles the user belongs to."""
        # Avoid queryset evaluation during schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Keep.objects.none()
            
        if not self.request.user.is_authenticated:
            return Keep.objects.none()
            
        user_circles = Circle.objects.filter(
            memberships__user=self.request.user
        )
        
        queryset = Keep.objects.filter(
            circle__in=user_circles
        ).select_related(
            'circle',
            'created_by',
            'milestone',
            'milestone__child_profile'
        ).prefetch_related(
            'media_files',
            'reactions__user',
            'comments__user'
        )
        
        # Filter by circle if specified
        circle_slug = self.request.query_params.get('circle_slug')
        if circle_slug:
            queryset = queryset.filter(circle__slug=circle_slug)
        
        # Filter by tag if specified
        tag = self.request.query_params.get('tag')
        if tag:
            queryset = queryset.filter(
                tags__icontains=tag
            )
        
        return queryset
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.request.method == 'POST':
            return KeepCreateSerializer
        return KeepSerializer
    
    def perform_create(self, serializer):
        """Set the creator when creating a new keep."""
        serializer.save(created_by=self.request.user)
    
    @extend_schema(
        summary="List keeps in user's circles",
        description="Retrieve a paginated list of family memories from circles the user belongs to. "
                   "Supports filtering by type, circle, creator, tags, and full-text search.",
        parameters=[
            OpenApiParameter(
                name='keep_type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by keep type',
                enum=['note', 'media', 'milestone']
            ),
            OpenApiParameter(
                name='circle',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                description='Filter by circle ID'
            ),
            OpenApiParameter(
                name='circle_slug',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by circle slug'
            ),
            OpenApiParameter(
                name='tag',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by tag (partial match)'
            ),
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Search in title, description, and tags'
            ),
            OpenApiParameter(
                name='ordering',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Order by field. Prefix with - for descending.',
                enum=['date_of_memory', '-date_of_memory', 'created_at', '-created_at']
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=KeepSerializer(many=True),
                description="Paginated list of keeps from user's circles"
            )
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        summary="Create a new keep",
        description="Create a new family memory (keep) with optional media files and milestone data. "
                   "The user must be a member of the specified circle.",
        request=KeepCreateSerializer,
        responses={
            201: OpenApiResponse(
                response=KeepSerializer,
                description="Keep created successfully"
            ),
            400: OpenApiResponse(
                description="Validation error or circle membership required"
            ),
            403: OpenApiResponse(
                description="Not a member of the specified circle"
            )
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class KeepDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a specific keep."""
    
    lookup_field = 'id'
    lookup_url_kwarg = 'keep_id'
    
    def get_permissions(self):
        """Return appropriate permissions based on action."""
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            permission_classes = [IsCircleAdminOrOwner]
        else:
            permission_classes = [IsCircleMember]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Return keeps from circles the user belongs to."""
        # Avoid queryset evaluation during schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Keep.objects.none()
            
        if not self.request.user.is_authenticated:
            return Keep.objects.none()
            
        user_circles = Circle.objects.filter(
            memberships__user=self.request.user
        )
        
        return Keep.objects.filter(
            circle__in=user_circles
        ).select_related(
            'circle',
            'created_by',
            'milestone',
            'milestone__child_profile'
        ).prefetch_related(
            'media_files',
            'reactions__user',
            'comments__user'
        )
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.request.method == 'GET':
            return KeepDetailSerializer
        return KeepSerializer
    
    def perform_update(self, serializer):
        """Allow creators and circle admins to update keeps."""
        keep = serializer.instance
        user = self.request.user
        
        # Check if user is creator or circle admin
        if keep.created_by != user and not is_circle_admin(user, keep.circle):
            raise permissions.PermissionDenied(
                "You can only update keeps you created or as a circle admin."
            )
        serializer.save()
    
    def perform_destroy(self, instance):
        """Allow creators and circle admins to delete keeps."""
        user = self.request.user
        
        # Check if user is creator or circle admin
        if instance.created_by != user and not is_circle_admin(user, instance.circle):
            raise permissions.PermissionDenied(
                "You can only delete keeps you created or as a circle admin."
            )
        instance.delete()
    
    @extend_schema(
        summary="Retrieve a keep",
        description="Get detailed information about a specific family memory including "
                   "all media files, milestone data, reactions, and comments.",
        responses={
            200: OpenApiResponse(
                response=KeepDetailSerializer,
                description="Detailed keep information with all related data"
            ),
            404: OpenApiResponse(
                description="Keep not found or not accessible"
            )
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        summary="Update a keep",
        description="Update a family memory. Only the keep creator or circle admins can update keeps.",
        request=KeepSerializer,
        responses={
            200: OpenApiResponse(
                response=KeepSerializer,
                description="Keep updated successfully"
            ),
            403: OpenApiResponse(
                description="Permission denied - only creators or circle admins can update"
            ),
            404: OpenApiResponse(
                description="Keep not found or not accessible"
            )
        }
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
    
    @extend_schema(
        summary="Partially update a keep",
        description="Partially update a family memory. Only the keep creator or circle admins can update keeps.",
        request=KeepSerializer,
        responses={
            200: OpenApiResponse(
                response=KeepSerializer,
                description="Keep updated successfully"
            ),
            403: OpenApiResponse(
                description="Permission denied - only creators or circle admins can update"
            ),
            404: OpenApiResponse(
                description="Keep not found or not accessible"
            )
        }
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)
    
    @extend_schema(
        summary="Delete a keep",
        description="Delete a family memory. Only the keep creator or circle admins can delete keeps.",
        responses={
            204: OpenApiResponse(
                description="Keep deleted successfully"
            ),
            403: OpenApiResponse(
                description="Permission denied - only creators or circle admins can delete"
            ),
            404: OpenApiResponse(
                description="Keep not found or not accessible"
            )
        }
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class KeepByCircleView(APIView):
    """Get keeps for a specific circle."""
    
    permission_classes = [IsCircleMember]
    
    @extend_schema(
        summary="Get keeps by circle",
        description="Retrieve all keeps for a specific circle using the circle slug. "
                   "Only circle members can access keeps from their circles.",
        parameters=[
            OpenApiParameter(
                name='circle_slug',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='Unique slug identifier for the circle',
                required=True
            )
        ],
        responses={
            200: OpenApiResponse(
                response=KeepSerializer(many=True),
                description="List of keeps for the specified circle"
            ),
            404: OpenApiResponse(
                description="Circle not found or user is not a member"
            )
        }
    )
    def get(self, request, circle_slug):
        """Get keeps for a specific circle."""
        try:
            circle = Circle.objects.get(
                slug=circle_slug,
                memberships__user=request.user
            )
        except Circle.DoesNotExist:
            return Response(
                {'error': 'Circle not found or you are not a member.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        keeps = Keep.objects.filter(circle=circle).select_related(
            'circle', 'created_by'
        ).prefetch_related(
            'media_files', 'reactions', 'comments'
        ).order_by('-date_of_memory', '-created_at')
        
        serializer = KeepSerializer(keeps, many=True)
        return Response(serializer.data)


class KeepByTypeView(APIView):
    """Filter keeps by type."""
    
    permission_classes = [IsCircleMember]
    
    @extend_schema(
        summary="Get keeps by type",
        description="Filter keeps by type (note, media, or milestone) from all circles the user belongs to.",
        parameters=[
            OpenApiParameter(
                name='type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Type of keep to filter by',
                required=True,
                enum=['note', 'media', 'milestone']
            )
        ],
        responses={
            200: OpenApiResponse(
                response=KeepSerializer(many=True),
                description="List of keeps of the specified type"
            ),
            400: OpenApiResponse(
                description="Invalid or missing keep type parameter"
            )
        }
    )
    def get(self, request):
        """Filter keeps by type."""
        keep_type = request.query_params.get('type')
        if not keep_type or keep_type not in [choice[0] for choice in KeepType.choices]:
            return Response(
                {'error': 'Valid keep type required. Options: note, media, milestone'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user_circles = Circle.objects.filter(
            memberships__user=request.user
        )
        
        keeps = Keep.objects.filter(
            circle__in=user_circles,
            keep_type=keep_type
        ).select_related(
            'circle', 'created_by'
        ).prefetch_related(
            'media_files', 'reactions', 'comments'
        ).order_by('-date_of_memory', '-created_at')
        
        serializer = KeepSerializer(keeps, many=True)
        return Response(serializer.data)


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