"""Views for Keep comments."""

import uuid

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, OpenApiTypes, extend_schema
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from mysite.circles.models import Circle
from mysite.users.models import User

from ..models import KeepComment
from ..notifications import notify_new_comment, notify_new_mentions
from ..serializers import KeepCommentSerializer
from ..serializers.comments import MENTIONS_SCHEMA
from .people import get_member_circle_or_404
from .permissions import IsCircleAdminOrOwner, IsCircleMember, is_circle_admin


class KeepCommentListCreateView(generics.ListCreateAPIView):
    """List and create comments on keeps."""

    serializer_class = KeepCommentSerializer
    permission_classes = [IsCircleMember]

    def get_queryset(self):
        """Return comments for keeps the user can access."""
        # Avoid queryset evaluation during schema generation
        if getattr(self, "swagger_fake_view", False):
            return KeepComment.objects.none()

        if not self.request.user.is_authenticated:
            return KeepComment.objects.none()

        user_circles = Circle.objects.filter(memberships__user=self.request.user)

        queryset = (
            KeepComment.objects.filter(keep__circle__in=user_circles)
            .select_related("user", "keep")
            .prefetch_related("mentions__user")
        )

        # Filter to one keep's thread if specified
        keep_id = self.request.query_params.get("keep")
        if keep_id:
            try:
                queryset = queryset.filter(keep_id=uuid.UUID(keep_id))
            except ValueError:
                return KeepComment.objects.none()

        return queryset

    def perform_create(self, serializer):
        """Set the user when creating a comment."""
        comment = serializer.save(user=self.request.user)
        notify_new_comment(comment)

    @extend_schema(
        summary="List keep comments",
        description="List all comments on keeps that the user can access in their circles.",
        parameters=[
            OpenApiParameter(
                name="keep",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                description="Only return comments on this keep",
            ),
        ],
        responses={
            200: OpenApiResponse(response=KeepCommentSerializer(many=True), description="List of comments on keeps")
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create a comment",
        description="Add a comment to a keep. All circle members can comment on keeps in their circles.",
        request=KeepCommentSerializer,
        responses={
            201: OpenApiResponse(response=KeepCommentSerializer, description="Comment created successfully"),
            400: OpenApiResponse(description="Validation error"),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class KeepCommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a comment."""

    serializer_class = KeepCommentSerializer
    lookup_field = "id"
    lookup_url_kwarg = "comment_id"

    def get_permissions(self):
        """Return appropriate permissions based on action."""
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            permission_classes = [IsCircleAdminOrOwner]
        else:
            permission_classes = [IsCircleMember]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """Return comments for keeps the user can access."""
        # Avoid queryset evaluation during schema generation
        if getattr(self, "swagger_fake_view", False):
            return KeepComment.objects.none()

        if not self.request.user.is_authenticated:
            return KeepComment.objects.none()

        user_circles = Circle.objects.filter(memberships__user=self.request.user)

        return (
            KeepComment.objects.filter(keep__circle__in=user_circles)
            .select_related("user", "keep")
            .prefetch_related("mentions__user")
        )

    def perform_update(self, serializer):
        """Allow creators and circle admins to update comments."""
        comment = serializer.instance
        user = self.request.user

        # Check if user is creator or circle admin
        if comment.user != user and not is_circle_admin(user, comment.keep.circle):
            raise permissions.PermissionDenied("You can only update your own comments or as a circle admin.")
        # Only members the edit newly mentions hear about it.
        mentioned_before = set(comment.mentions.values_list("user_id", flat=True))
        comment = serializer.save()
        notify_new_mentions(comment.mentions.exclude(user_id__in=mentioned_before))

    def perform_destroy(self, instance):
        """Allow creators and circle admins to delete comments."""
        user = self.request.user

        # Check if user is creator or circle admin
        if instance.user != user and not is_circle_admin(user, instance.keep.circle):
            raise permissions.PermissionDenied("You can only delete your own comments or as a circle admin.")
        instance.delete()

    @extend_schema(
        summary="Retrieve a comment",
        description="Get details of a specific comment on a keep.",
        responses={
            200: OpenApiResponse(response=KeepCommentSerializer, description="Comment details"),
            404: OpenApiResponse(description="Comment not found or not accessible"),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update a comment",
        description="Update a comment on a keep. Only the comment creator or circle admins can update comments.",
        request=KeepCommentSerializer,
        responses={
            200: OpenApiResponse(response=KeepCommentSerializer, description="Comment updated successfully"),
            403: OpenApiResponse(description="Permission denied - only creators or circle admins can update"),
        },
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a comment",
        description=(
            "Partially update a comment on a keep. Only the comment creator or circle admins can update comments."
        ),
        request=KeepCommentSerializer,
        responses={
            200: OpenApiResponse(response=KeepCommentSerializer, description="Comment updated successfully"),
            403: OpenApiResponse(description="Permission denied - only creators or circle admins can update"),
        },
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a comment",
        description="Delete a comment on a keep. Only the comment creator or circle admins can delete comments.",
        responses={
            204: OpenApiResponse(description="Comment deleted successfully"),
            403: OpenApiResponse(description="Permission denied - only creators or circle admins can delete"),
        },
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class CircleMentionableView(APIView):
    """Circle members the viewer can @mention in comments."""

    @extend_schema(
        summary="Mentionable members",
        description="The circle's members other than the viewer, as `{id, display_name}` in name order, for "
        "the comment composer's @mention suggestions. Only members, since they're who can be notified; child "
        "profiles and other tagged people aren't included. 404 unless the user is a member.",
        responses={
            200: OpenApiResponse(response=MENTIONS_SCHEMA, description="The circle's other members"),
            404: OpenApiResponse(description="Not found or not a member"),
        },
    )
    def get(self, request, circle_id):
        circle = get_member_circle_or_404(request.user, circle_id)
        users = User.objects.filter(circle_memberships__circle=circle, is_active=True).exclude(id=request.user.id)
        members = [{"id": user.id, "display_name": user.display_name} for user in users]
        members.sort(key=lambda member: (member["display_name"].casefold(), member["id"]))
        return Response(members)
