"""Home-screen photo feed across all of the user's circles."""

import calendar
import re
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

from django.db.models import Count, Exists, IntegerField, OuterRef, Prefetch, Q, Subquery
from django.db.models.functions import Coalesce, ExtractDay, ExtractMonth
from django.http import Http404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, OpenApiTypes, extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import CursorPagination, LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from mysite.circles.models import CircleMembership
from mysite.users.models import UserRole

from ..models import Keep, KeepComment, KeepFavorite, KeepMedia, KeepReaction, KeepType
from ..serializers.feed import FeedLikerSerializer, KeepFeedSerializer

# Matches the web feed's initial comment count, so it needs no extra fetch.
RECENT_COMMENT_COUNT = 3
DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# "On this day" picks at most this many keeps, and this many from any one year.
ON_THIS_DAY_LIMIT = 12
ON_THIS_DAY_PER_YEAR = 3


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
    """Text posts, and keeps with at least one displayable photo/video, in the user's circles.

    A media keep stays hidden until a file is displayable, so a post whose
    uploads are still processing never shows up as an empty text post.
    """
    displayable_media = KeepMedia.objects.filter(keep=OuterRef("pk")).filter(
        Q(media_type="photo") | Q(media_type="video", thumbnails_generated=True)
    )
    # Mirrors ``KeepDetailView.perform_destroy``: the creator or a circle admin.
    circle_admin = CircleMembership.objects.filter(circle=OuterRef("circle"), user=user, role=UserRole.CIRCLE_ADMIN)

    return (
        Keep.objects.filter(circle__memberships__user=user)
        .filter(Q(keep_type=KeepType.NOTE) | Exists(displayable_media))
        .annotate(
            reaction_count=_count_subquery(KeepReaction),
            comment_count=_count_subquery(KeepComment),
            favorited=Exists(KeepFavorite.objects.filter(keep=OuterRef("pk"), user=user)),
            can_delete=Q(created_by=user) | Exists(circle_admin),
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


def parse_day(value):
    """UTC [start, end) bounds for a `YYYY-MM-DD` day, matching the calendar's UTC days."""
    try:
        if not DAY_RE.match(value):
            raise ValueError(value)
        start = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=dt_timezone.utc)
    except ValueError:
        raise ValidationError({"date": "Use YYYY-MM-DD."}) from None
    return start, start + timedelta(days=1)


def filter_by_circle(queryset, circle_slug):
    """Restrict to one circle; the queryset is already limited to the user's circles."""
    return queryset.filter(circle__slug=circle_slug) if circle_slug else queryset


DAY_PARAMETERS = [
    OpenApiParameter(
        name="date",
        type=OpenApiTypes.DATE,
        location=OpenApiParameter.QUERY,
        description="Only keeps whose memory falls on this UTC day (YYYY-MM-DD)",
    ),
    OpenApiParameter(
        name="circle_slug",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description="Only keeps from this circle",
    ),
]


class KeepFeedView(generics.ListAPIView):
    """Newest-first photo feed across every circle the user belongs to."""

    serializer_class = KeepFeedSerializer
    pagination_class = KeepFeedPagination

    def get_queryset(self):
        # Avoid queryset evaluation during schema generation
        if getattr(self, "swagger_fake_view", False):
            return Keep.objects.none()
        queryset = feed_queryset(self.request.user)
        day = self.request.query_params.get("date")
        if day:
            start, end = parse_day(day)
            queryset = queryset.filter(date_of_memory__gte=start, date_of_memory__lt=end)
        return filter_by_circle(queryset, self.request.query_params.get("circle_slug"))

    @extend_schema(
        summary="Photo feed",
        description="Text posts and keeps with photos (or videos with a poster frame) from every circle "
        "the user belongs to, newest memory first. Cursor-paginated: follow `next` for older posts.",
        parameters=[
            OpenApiParameter(
                name="page_size",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Posts per page (default 10, max 30)",
            ),
            *DAY_PARAMETERS,
        ],
        responses={
            200: OpenApiResponse(response=KeepFeedSerializer(many=True), description="A page of feed posts"),
            400: OpenApiResponse(description="Invalid date"),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class KeepFeedAdjacentDaysView(APIView):
    """The nearest earlier and later days that have feed posts, for day-to-day paging."""

    @extend_schema(
        summary="Adjacent photo days",
        description="For a UTC day, the closest earlier and later days (YYYY-MM-DD, or null) that have "
        "posts in the feed, optionally within one circle.",
        parameters=[
            OpenApiParameter(
                name="date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="The current UTC day (YYYY-MM-DD)",
                required=True,
            ),
            DAY_PARAMETERS[1],
        ],
        responses={
            200: OpenApiResponse(description="`{date, previous, next}`"),
            400: OpenApiResponse(description="Missing or invalid date"),
        },
    )
    def get(self, request):
        day = request.query_params.get("date", "")
        start, end = parse_day(day)
        keeps = filter_by_circle(feed_queryset(request.user), request.query_params.get("circle_slug"))
        dates = keeps.values_list("date_of_memory", flat=True)
        previous = dates.filter(date_of_memory__lt=start).order_by("-date_of_memory").first()
        following = dates.filter(date_of_memory__gte=end).order_by("date_of_memory").first()

        def as_day(moment):
            return moment.astimezone(dt_timezone.utc).date().isoformat() if moment else None

        return Response({"date": day, "previous": as_day(previous), "next": as_day(following)})


def on_this_day_ids(keeps, day):
    """Ids of `keeps` from earlier years on `day`'s month and day, newest first.

    Memories are matched on their UTC date, like the calendar. In a non-leap
    year, Feb 28 also brings back Feb 29 memories so they still come up once a
    year. Each year (newest first) contributes one keep per round, up to
    ON_THIS_DAY_PER_YEAR, until ON_THIS_DAY_LIMIT, so one busy year can't push
    out the others.
    """
    month_days = [(day.month, day.day)]
    if (day.month, day.day) == (2, 28) and not calendar.isleap(day.year):
        month_days.append((2, 29))
    same_day = Q()
    for month, day_of_month in month_days:
        same_day |= Q(memory_month=month, memory_day=day_of_month)
    candidates = (
        keeps.annotate(
            memory_month=ExtractMonth("date_of_memory", tzinfo=dt_timezone.utc),
            memory_day=ExtractDay("date_of_memory", tzinfo=dt_timezone.utc),
        )
        .filter(same_day, date_of_memory__lt=datetime(day.year, 1, 1, tzinfo=dt_timezone.utc))
        .order_by(*KeepFeedPagination.ordering)
        .values_list("id", "date_of_memory")
    )
    by_year = {}
    for keep_id, moment in candidates:
        by_year.setdefault(moment.astimezone(dt_timezone.utc).year, []).append(keep_id)
    chosen = []
    for rank in range(ON_THIS_DAY_PER_YEAR):
        for ids in by_year.values():
            if rank < len(ids) and len(chosen) < ON_THIS_DAY_LIMIT:
                chosen.append(ids[rank])
    return chosen


class KeepFeedOnThisDayView(generics.GenericAPIView):
    """Keeps from this month and day in earlier years, for the home feed's memories."""

    serializer_class = KeepFeedSerializer

    def get_queryset(self):
        # Avoid queryset evaluation during schema generation
        if getattr(self, "swagger_fake_view", False):
            return Keep.objects.none()
        return filter_by_circle(feed_queryset(self.request.user), self.request.query_params.get("circle_slug"))

    @extend_schema(
        summary="On this day",
        description="Feed posts whose memory (UTC date) falls on the same month and day as `date` in an "
        "earlier year, from every circle the user belongs to, newest first. `date` is the viewer's local "
        f"today. At most {ON_THIS_DAY_LIMIT} posts, up to {ON_THIS_DAY_PER_YEAR} from each year, spread "
        "across as many years as possible. In a non-leap year, Feb 28 also includes Feb 29 memories.",
        parameters=[
            OpenApiParameter(
                name="date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="The viewer's local today (YYYY-MM-DD)",
                required=True,
            ),
            DAY_PARAMETERS[1],
        ],
        responses={
            200: OpenApiResponse(
                response=KeepFeedSerializer(many=True), description="`{date, results}`: feed posts, newest first"
            ),
            400: OpenApiResponse(description="Missing or invalid date"),
        },
    )
    def get(self, request):
        day = request.query_params.get("date", "")
        start, _ = parse_day(day)
        keeps = self.get_queryset()
        ids = on_this_day_ids(keeps, start)
        results = keeps.filter(id__in=ids).order_by(*KeepFeedPagination.ordering) if ids else []
        return Response({"date": day, "results": self.get_serializer(results, many=True).data})


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
        "and it is a text post or has a displayable photo or video.",
        responses={
            200: OpenApiResponse(response=KeepFeedSerializer, description="The feed post"),
            404: OpenApiResponse(description="Not found or not visible to the user"),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class KeepLikersPagination(LimitOffsetPagination):
    default_limit = 50
    max_limit = 200


class KeepFeedLikersView(generics.ListAPIView):
    """Who liked a keep, newest first. Any reaction type counts as a like."""

    serializer_class = FeedLikerSerializer
    pagination_class = KeepLikersPagination

    def get_queryset(self):
        # Avoid queryset evaluation during schema generation
        if getattr(self, "swagger_fake_view", False):
            return KeepReaction.objects.none()
        keep_id = self.kwargs["keep_id"]
        if not Keep.objects.filter(id=keep_id, circle__memberships__user=self.request.user).exists():
            raise Http404
        return KeepReaction.objects.filter(keep_id=keep_id).select_related("user").order_by("-created_at", "-id")

    @extend_schema(
        summary="Photo feed post likers",
        description="Everyone who reacted to a keep (any reaction counts as a like), newest first. "
        "Limit/offset paginated. 404 unless the user belongs to the keep's circle.",
        parameters=[
            OpenApiParameter(
                name="limit",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Likers per page (default 50, max 200)",
            ),
            OpenApiParameter(
                name="offset",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="How many likers to skip",
            ),
        ],
        responses={
            200: OpenApiResponse(response=FeedLikerSerializer(many=True), description="A page of likers"),
            404: OpenApiResponse(description="Not found or not visible to the user"),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


def get_visible_keep_or_404(user, keep_id):
    """A keep in one of the user's circles; 404 otherwise, including once it is deleted."""
    keep = Keep.objects.filter(id=keep_id, circle__memberships__user=user).first()
    if keep is None:
        raise Http404
    return keep


class KeepFavoritesPagination(KeepFeedPagination):
    # Most recently favorited first; id breaks ties.
    ordering = ("-favorited_at", "-id")


class KeepFeedFavoritesView(generics.ListAPIView):
    """The user's own favorites, in feed shape, most recently favorited first."""

    serializer_class = KeepFeedSerializer
    pagination_class = KeepFavoritesPagination

    def get_queryset(self):
        # Avoid queryset evaluation during schema generation
        if getattr(self, "swagger_fake_view", False):
            return Keep.objects.none()
        user = self.request.user
        favorited_at = KeepFavorite.objects.filter(keep=OuterRef("pk"), user=user).values("created_at")[:1]
        # Built on the feed, so a keep drops off the list once it is deleted,
        # stops being displayable, or the user leaves its circle.
        return feed_queryset(user).filter(favorited=True).annotate(favorited_at=Subquery(favorited_at))

    @extend_schema(
        summary="Favorite feed posts",
        description="The keeps the user favorited, in the same shape as the feed, most recently favorited "
        "first. Only keeps still visible in the feed are listed. Cursor-paginated: follow `next`.",
        parameters=[
            OpenApiParameter(
                name="page_size",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Posts per page (default 10, max 30)",
            ),
        ],
        responses={
            200: OpenApiResponse(response=KeepFeedSerializer(many=True), description="A page of favorites"),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class KeepFeedFavoriteView(APIView):
    """Favorite (POST) or unfavorite (DELETE) a keep. Both are idempotent."""

    @extend_schema(
        summary="Favorite a feed post",
        description="Add a keep to the user's private favorites. Favoriting it again is a no-op. "
        "404 unless the user belongs to the keep's circle.",
        request=None,
        responses={
            200: OpenApiResponse(description="`{favorited: true}`, already a favorite"),
            201: OpenApiResponse(description="`{favorited: true}`, newly favorited"),
            404: OpenApiResponse(description="Not found (e.g. deleted) or not visible to the user"),
        },
    )
    def post(self, request, keep_id):
        keep = get_visible_keep_or_404(request.user, keep_id)
        _, created = KeepFavorite.objects.get_or_create(keep=keep, user=request.user)
        return Response({"favorited": True}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @extend_schema(
        summary="Unfavorite a feed post",
        description="Remove a keep from the user's favorites. Unfavoriting a keep that isn't a favorite is "
        "a no-op. 404 unless the user belongs to the keep's circle.",
        request=None,
        responses={
            204: OpenApiResponse(description="Not a favorite (any more)"),
            404: OpenApiResponse(description="Not found (e.g. deleted) or not visible to the user"),
        },
    )
    def delete(self, request, keep_id):
        # The row is the user's own, so drop it even when the keep is no
        # longer visible to them, then report whether the keep is still there.
        KeepFavorite.objects.filter(keep_id=keep_id, user=request.user).delete()
        get_visible_keep_or_404(request.user, keep_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
