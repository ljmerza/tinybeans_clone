"""Views for Keep CRUD operations."""
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiTypes, OpenApiParameter

from mysite.notification_utils import create_message, error_response, success_response
from mysite.users.models import Circle
from ..models import Keep, KeepType
from ..serializers import (
    KeepSerializer,
    KeepCreateSerializer,
    KeepDetailSerializer,
)
from .permissions import IsCircleMember, IsCircleAdminOrOwner, is_circle_admin


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
        from rest_framework import permissions
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
        from rest_framework import permissions
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
            return error_response(
                messages=[create_message('errors.circle_not_found')],
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        keeps = Keep.objects.filter(circle=circle).select_related(
            'circle', 'created_by'
        ).prefetch_related(
            'media_files', 'reactions', 'comments'
        ).order_by('-date_of_memory', '-created_at')
        
        serializer = KeepSerializer(keeps, many=True)
        return success_response(serializer.data)


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
            return error_response(
                messages=[create_message('errors.invalid_keep_type')],
                status_code=status.HTTP_400_BAD_REQUEST
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
        return success_response(serializer.data)
