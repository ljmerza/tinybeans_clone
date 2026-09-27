"""Home-screen photo feed across all of the user's circles."""

from django.db.models import Count, Exists, IntegerField, OuterRef, Prefetch, Q, Subquery
from django.db.models.functions import Coalesce
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, OpenApiTypes, extend_schema
from rest_framework import generics
from rest_framework.pagination import CursorPagination

from ..models import Keep, KeepComment, KeepMedia, KeepReaction
from ..serializers.feed import KeepFeedSerializer

RECENT_COMMENT_COUNT = 2


class KeepFeedPagination(CursorPagination):
    """Cursor pagination keeps infinite scroll stable while new keeps arrive."""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 30
    # date_of_memory positions the cursor; the rest break ties between keeps
    # imported with the same timestamp.
    ordering = ("-date_of_memory", "-created_at", "-id")


def _count_subquery(model):
    counts = model.objects.filter(keep=OuterRef("pk")).values("keep").annotate(total=Count("id")).values("total")
    return Coalesce(Subquery(counts, output_field=IntegerField()), 0)


def feed_queryset(user):
    """Keeps with at least one displayable photo/video in the user's circles."""
    displayable_media = KeepMedia.objects.filter(keep=OuterRef("pk")).filter(
        Q(media_type="photo") | Q(media_type="video", thumbnails_generated=True)
    )

    return (
        Keep.objects.filter(circle__memberships__user=user)
        .filter(Exists(displayable_media))
        .annotate(
            reaction_count=_count_subquery(KeepReaction),
            comment_count=_count_subquery(KeepComment),
        )
        .select_related("circle", "created_by")
        .prefetch_related(
            Prefetch("media_files", queryset=KeepMedia.objects.order_by("upload_order", "id")),
            Prefetch("reactions", queryset=KeepReaction.objects.filter(user=user), to_attr="viewer_reactions"),
            Prefetch(
                "comments",
                queryset=KeepComment.objects.select_related("user").order_by("-created_at", "-id")[
                    :RECENT_COMMENT_COUNT
                ],
                to_attr="recent_comments_desc",
            ),
        )
    )


class KeepFeedView(generics.ListAPIView):
    """Newest-first photo feed across every circle the user belongs to."""

    serializer_class = KeepFeedSerializer
    pagination_class = KeepFeedPagination

    def get_queryset(self):
        # Avoid queryset evaluation during schema generation
        if getattr(self, "swagger_fake_view", False):
            return Keep.objects.none()
        return feed_queryset(self.request.user)

    @extend_schema(
        summary="Photo feed",
        description="Keeps with photos (or videos with a poster frame) from every circle the user "
        "belongs to, newest memory first. Cursor-paginated: follow `next` for older posts.",
        parameters=[
            OpenApiParameter(
                name="page_size",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Posts per page (default 10, max 30)",
            ),
        ],
        responses={200: OpenApiResponse(response=KeepFeedSerializer(many=True), description="A page of feed posts")},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class KeepFeedItemView(generics.RetrieveAPIView):
    """A single keep in feed shape, for shared links."""

    serializer_class = KeepFeedSerializer
    lookup_url_kwarg = "keep_id"

    def get_queryset(self):
        # Avoid queryset evaluation during schema generation
        if getattr(self, "swagger_fake_view", False):
            return Keep.objects.none()
        return feed_queryset(self.request.user)

    @extend_schema(
        summary="Photo feed post",
        description="One keep in the same shape as the feed. 404 unless the user belongs to its circle "
        "and it has a displayable photo or video.",
        responses={
            200: OpenApiResponse(response=KeepFeedSerializer, description="The feed post"),
            404: OpenApiResponse(description="Not found or not visible to the user"),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
