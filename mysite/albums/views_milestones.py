"""Milestone suggestion review API: circle admins list, approve and dismiss AI / API token picks.

Mounted under ``/api/users/circles/<circle_id>/milestone-suggestions/`` with the
other per-circle admin APIs. JWT only, and only real circle admins: superusers
act through Django admin. Anything from another circle is a 404.
"""

from django.db.models import Exists, OuterRef, Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, OpenApiTypes, extend_schema
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from mysite.circles.models import CircleMembership
from mysite.keeps.models import KeepType
from mysite.keeps.serializers.feed import KeepFeedSerializer
from mysite.keeps.views.feed import feed_queryset

from . import milestones
from .models import MilestoneSuggestion
from .serializers import MilestoneSuggestionSerializer
from .views import _displayable_media, is_circle_admin

Status = MilestoneSuggestion.Status

LISTABLE_STATUSES = (Status.PENDING, Status.DISMISSED)


def require_milestone_admin(user, circle_id):
    """404 outside the circle, 403 for members who aren't its admins."""
    if not CircleMembership.objects.filter(circle_id=circle_id, user=user).exists():
        raise Http404
    if not is_circle_admin(user, circle_id):
        raise PermissionDenied("Only circle admins can review milestone suggestions.")


class MilestoneSuggestionPagination(LimitOffsetPagination):
    default_limit = 20
    max_limit = 100


class MilestoneSuggestionListView(APIView):
    """The circle's pending (or dismissed) milestone suggestions, each with its post in feed shape."""

    authentication_classes = [JWTAuthentication]

    @extend_schema(
        summary="Milestone suggestions",
        description="The circle's milestone suggestions, newest first, each with its post in the feed's shape "
        "(`keep`). `pending` leaves out posts already in the Milestones album, and posts the feed would not "
        "show. Circle admins only. Limit/offset paginated.",
        parameters=[
            OpenApiParameter(
                name="status",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                enum=[str(status) for status in LISTABLE_STATUSES],
                description="Which suggestions (default `pending`)",
            ),
            OpenApiParameter(
                name="limit",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Suggestions per page (default 20, max 100)",
            ),
            OpenApiParameter(
                name="offset", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, description="Suggestions to skip"
            ),
        ],
        responses={
            200: OpenApiResponse(description="`{count, next, previous, results: [{...suggestion, keep}]}`"),
            400: OpenApiResponse(description="Unknown `status`"),
            403: OpenApiResponse(description="Not an admin of the circle"),
            404: OpenApiResponse(description="Not a member of the circle"),
        },
    )
    def get(self, request, circle_id):
        require_milestone_admin(request.user, circle_id)
        status = request.query_params.get("status") or Status.PENDING
        if status not in LISTABLE_STATUSES:
            raise ValidationError({"status": "Use pending or dismissed."})

        if status == Status.PENDING:
            suggestions = milestones.pending_suggestions(circle_id)
        else:
            suggestions = MilestoneSuggestion.objects.filter(circle_id=circle_id, status=status)
        # Only posts the feed shows, so every item has a post to render.
        displayable = _displayable_media().filter(keep=OuterRef("keep"))
        suggestions = suggestions.filter(Q(keep__keep_type=KeepType.NOTE) | Exists(displayable)).order_by(
            "-created_at", "-id"
        )

        paginator = MilestoneSuggestionPagination()
        page = paginator.paginate_queryset(suggestions, request, view=self)
        keeps = feed_queryset(request.user).filter(pk__in=[suggestion.keep_id for suggestion in page])
        posts = {post["id"]: post for post in KeepFeedSerializer(keeps, many=True, context={"request": request}).data}
        results = [
            {**MilestoneSuggestionSerializer(suggestion).data, "keep": posts.get(str(suggestion.keep_id))}
            for suggestion in page
        ]
        return paginator.get_paginated_response(results)


class MilestoneSuggestionActionView(APIView):
    """Approve or dismiss one suggestion."""

    authentication_classes = [JWTAuthentication]
    decision = None

    def _suggestion(self, request, circle_id, suggestion_id):
        require_milestone_admin(request.user, circle_id)
        return get_object_or_404(MilestoneSuggestion, pk=suggestion_id, circle_id=circle_id)

    def post(self, request, circle_id, suggestion_id):
        suggestion = self._suggestion(request, circle_id, suggestion_id)
        if self.decision == "approve":
            suggestion, album = milestones.approve(suggestion, request.user)
            return Response({"suggestion": MilestoneSuggestionSerializer(suggestion).data, "album_id": album.pk})
        suggestion = milestones.dismiss(suggestion, request.user)
        return Response({"suggestion": MilestoneSuggestionSerializer(suggestion).data})


class MilestoneSuggestionApproveView(MilestoneSuggestionActionView):
    decision = "approve"

    @extend_schema(
        summary="Approve a milestone suggestion",
        description="Adds the post to the circle's Milestones album, making the album if there is none. Works on "
        "pending and dismissed suggestions (undoing a dismiss); approving twice is a no-op. Circle admins only.",
        request=None,
        responses={
            200: OpenApiResponse(description="`{suggestion, album_id}`"),
            400: OpenApiResponse(description="The suggestion can't be approved (e.g. it was added automatically)"),
            403: OpenApiResponse(description="Not an admin of the circle"),
            404: OpenApiResponse(description="Not found in this circle"),
        },
    )
    def post(self, request, circle_id, suggestion_id):
        return super().post(request, circle_id, suggestion_id)


class MilestoneSuggestionDismissView(MilestoneSuggestionActionView):
    decision = "dismiss"

    @extend_schema(
        summary="Dismiss a milestone suggestion",
        description="Turns a pending suggestion down; the post is not suggested again. Dismissing twice is a "
        "no-op. Circle admins only.",
        request=None,
        responses={
            200: OpenApiResponse(description="`{suggestion}`"),
            400: OpenApiResponse(description="The suggestion isn't pending"),
            403: OpenApiResponse(description="Not an admin of the circle"),
            404: OpenApiResponse(description="Not found in this circle"),
        },
    )
    def post(self, request, circle_id, suggestion_id):
        return super().post(request, circle_id, suggestion_id)
