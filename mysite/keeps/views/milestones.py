"""Milestones: list them in feed shape, set or clear one on a keep, and the children to pick from."""

import uuid

from django.db import transaction
from django.db.models import Count
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, OpenApiTypes, extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from mysite.users.models.child_profile import ChildProfile

from ..models import Keep, KeepType, Milestone
from ..serializers.feed import KeepFeedSerializer
from ..serializers.milestones import (
    FEED_MILESTONE_SCHEMA,
    KeepChildSummarySerializer,
    MilestoneWriteSerializer,
    feed_milestone,
)
from .feed import DAY_PARAMETERS, KeepFeedPagination, feed_queryset, filter_by_circle, get_visible_keep_or_404
from .permissions import is_circle_admin


class MilestonePagination(KeepFeedPagination):
    # Oldest first: a child's milestones read as a timeline.
    ordering = ("date_of_memory", "created_at", "id")


def parse_child_id(value):
    try:
        return uuid.UUID(value)
    except ValueError:
        raise ValidationError({"child": "Use a child profile id."}) from None


class KeepFeedMilestonesView(generics.ListAPIView):
    """Milestone keeps in feed shape, oldest first, optionally for one child."""

    serializer_class = KeepFeedSerializer
    pagination_class = MilestonePagination

    def get_queryset(self):
        # Avoid queryset evaluation during schema generation
        if getattr(self, "swagger_fake_view", False):
            return Keep.objects.none()
        # Built on the feed, so circle membership and media visibility match it.
        queryset = feed_queryset(self.request.user).filter(milestone__isnull=False)
        child = self.request.query_params.get("child")
        if child:
            queryset = queryset.filter(milestone__child_profile_id=parse_child_id(child))
        return filter_by_circle(queryset, self.request.query_params.get("circle_slug"))

    @extend_schema(
        summary="Milestone feed posts",
        description="Keeps marked as milestones, in the same shape as the feed, from every circle the user "
        "belongs to, oldest memory first. Cursor-paginated: follow `next` for later milestones.",
        parameters=[
            OpenApiParameter(
                name="child",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                description="Only this child's milestones",
            ),
            DAY_PARAMETERS[1],
            OpenApiParameter(
                name="page_size",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Posts per page (default 10, max 30)",
            ),
        ],
        responses={
            200: OpenApiResponse(response=KeepFeedSerializer(many=True), description="A page of milestones"),
            400: OpenApiResponse(description="Invalid child id"),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class KeepMilestoneView(APIView):
    """Mark a keep as a milestone (PUT) or unmark it (DELETE)."""

    def get_keep(self, request, keep_id):
        """A keep the user may change: its creator or a circle admin, like deleting it."""
        keep = get_visible_keep_or_404(request.user, keep_id)
        if keep.created_by_id != request.user.id and not is_circle_admin(request.user, keep.circle):
            raise PermissionDenied("You can only change keeps you created or as a circle admin.")
        return keep

    @extend_schema(
        summary="Set a keep's milestone",
        description="Mark a keep as a milestone, or change its milestone type or child. The child must belong "
        "to the keep's circle. Only the keep's creator or a circle admin may. 404 unless the user belongs "
        "to the keep's circle.",
        request=MilestoneWriteSerializer,
        responses={
            200: OpenApiResponse(response=FEED_MILESTONE_SCHEMA, description="The milestone, as feed posts show it"),
            400: OpenApiResponse(description="Invalid type, or a child from another circle"),
            403: OpenApiResponse(description="Not the creator or a circle admin"),
            404: OpenApiResponse(description="Not found or not visible to the user"),
        },
    )
    def put(self, request, keep_id):
        keep = self.get_keep(request, keep_id)
        existing = Milestone.objects.filter(keep=keep).first()
        serializer = MilestoneWriteSerializer(existing, data=request.data, context={"keep": keep})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            serializer.save(keep=keep)
            if keep.keep_type != KeepType.MILESTONE:
                keep.keep_type = KeepType.MILESTONE
                keep.save(update_fields=["keep_type", "updated_at"])
        keep = Keep.objects.select_related("milestone__child_profile").get(pk=keep.pk)
        return Response(feed_milestone(keep))

    @extend_schema(
        summary="Clear a keep's milestone",
        description="Stop showing a keep as a milestone; it goes back to a photo/video or text post. Clearing a "
        "keep that isn't a milestone is a no-op. Only the keep's creator or a circle admin may.",
        request=None,
        responses={
            204: OpenApiResponse(description="Not a milestone (any more)"),
            403: OpenApiResponse(description="Not the creator or a circle admin"),
            404: OpenApiResponse(description="Not found or not visible to the user"),
        },
    )
    def delete(self, request, keep_id):
        keep = self.get_keep(request, keep_id)
        with transaction.atomic():
            Milestone.objects.filter(keep=keep).delete()
            if keep.keep_type == KeepType.MILESTONE:
                keep.keep_type = KeepType.MEDIA if keep.media_files.exists() else KeepType.NOTE
                keep.save(update_fields=["keep_type", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class KeepChildrenView(generics.ListAPIView):
    """Children in the user's circles, with how many milestones each has."""

    serializer_class = KeepChildSummarySerializer
    pagination_class = None

    def get_queryset(self):
        # Avoid queryset evaluation during schema generation
        if getattr(self, "swagger_fake_view", False):
            return ChildProfile.objects.none()
        return (
            ChildProfile.objects.filter(circle__memberships__user=self.request.user)
            .select_related("circle")
            .annotate(milestone_count=Count("milestones", distinct=True))
            .order_by("circle__name", "display_name", "id")
        )

    @extend_schema(
        summary="Children in the user's circles",
        description="Every child profile in a circle the user belongs to, with its circle and milestone count, "
        "for tagging and filtering milestones. Not paginated.",
        responses={200: OpenApiResponse(response=KeepChildSummarySerializer(many=True), description="Children")},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
