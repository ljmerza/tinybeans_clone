"""The agent API: whoami, posts, one post, and proposing a milestone. Token only (see ``AgentAPIView``)."""

from __future__ import annotations

import uuid

from django.http import Http404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from mysite.albums import milestones
from mysite.albums.models import MilestoneSuggestion
from mysite.keeps.person_stats import age_on
from mysite.keeps.views.feed import parse_day
from mysite.users.models import ChildProfile

from .. import hygiene, queries
from ..pagination import ORDERS, AgentPostPagination
from ..permissions import CanSuggest, IsApiToken
from ..serializers import MilestoneSuggestionCreateSerializer
from ..throttling import AgentReadThrottle, AgentSuggestThrottle
from .base import AgentAPIView

Status = MilestoneSuggestion.Status

MILESTONE_FILTERS = ("any", "unreviewed", "in_album", "pending")
SEARCH_MAX_LENGTH = 200
SEARCH_MAX_TERMS = 10


def _day_bounds(params, name):
    """``parse_day`` for one query parameter, with errors keyed by that parameter."""
    value = params.get(name)
    if not value:
        return None
    try:
        return parse_day(value)
    except ValidationError:
        raise ValidationError({name: "Use YYYY-MM-DD."}) from None


def _search_terms(value):
    if not value:
        return []
    if len(value) > SEARCH_MAX_LENGTH:
        raise ValidationError({"q": f"Use at most {SEARCH_MAX_LENGTH} characters."})
    terms = [term.strip() for term in value.split(",") if term.strip()]
    if len(terms) > SEARCH_MAX_TERMS:
        raise ValidationError({"q": f"Use at most {SEARCH_MAX_TERMS} comma-separated terms."})
    return terms


def _choice(params, name, choices):
    value = params.get(name) or choices[0]
    if value not in choices:
        raise ValidationError({name: f"Use one of: {', '.join(choices)}."})
    return value


def _page_size(params):
    value = params.get("page_size")
    if value is None:
        return
    try:
        size = int(value)
    except ValueError:
        size = 0
    if size < 1:
        raise ValidationError({"page_size": f"Use 1 to {AgentPostPagination.max_page_size}."})
    # Larger sizes are capped by the paginator.


@extend_schema(exclude=True)
class AgentWhoAmIView(AgentAPIView):
    """The token's circle: its children's ages, Milestones album size and counts."""

    def get(self, request):
        token = request.auth
        circle_id = token.circle_id
        today = timezone.now().date()
        posts = queries.agent_posts(circle_id)
        album_exists = hasattr(token.circle, "milestone_album")
        children = ChildProfile.objects.filter(circle_id=circle_id).order_by("display_name", "id")
        return Response(
            {
                "circle": {"name": hygiene.strip_hidden(token.circle.name)},
                "token": {
                    "name": hygiene.strip_hidden(token.name),
                    "prefix": token.display_prefix,
                    "expires_at": token.expires_at,
                    "can_suggest": token.can_suggest,
                },
                "children": [
                    {
                        "id": str(child.id),
                        "name": hygiene.strip_hidden(child.display_name),
                        "age_today": age_on(child.birthdate, today) if child.birthdate else None,
                    }
                    for child in children
                ],
                "milestones_album": {
                    "exists": album_exists,
                    "post_count": posts.filter(in_milestones_album=True).count() if album_exists else 0,
                },
                "counts": {
                    "posts": posts.count(),
                    "pending_suggestions": milestones.pending_suggestions(circle_id).count(),
                },
                "server_date": today.isoformat(),
            }
        )


@extend_schema(exclude=True)
class AgentPostListView(AgentAPIView):
    """The circle's posts, oldest first, filtered by date, text, child and milestone state."""

    def get(self, request):
        circle_id = request.auth.circle_id
        params = request.query_params
        start = _day_bounds(params, "from")
        end = _day_bounds(params, "to")
        terms = _search_terms(params.get("q"))
        milestone = _choice(params, "milestone", MILESTONE_FILTERS)
        _choice(params, "order", ORDERS)
        _page_size(params)

        posts = queries.agent_posts(circle_id)
        if start:
            posts = posts.filter(date_of_memory__gte=start[0])
        if end:
            posts = posts.filter(date_of_memory__lt=end[1])
        if terms:
            posts = posts.filter(queries.search_q(terms))
        child_id = params.get("child")
        if child_id:
            try:
                child_id = uuid.UUID(child_id)
            except ValueError:
                raise ValidationError({"child": "Not a valid child id."}) from None
            if not ChildProfile.objects.filter(pk=child_id, circle_id=circle_id).exists():
                raise Http404
            posts = posts.filter(queries.child_q(child_id))
        if milestone == "in_album":
            posts = posts.filter(in_milestones_album=True)
        elif milestone == "pending":
            posts = posts.filter(in_milestones_album=False, suggestion_status=Status.PENDING)
        elif milestone == "unreviewed":
            posts = posts.filter(queries.unreviewed_q())

        paginator = AgentPostPagination()
        page = paginator.paginate_queryset(posts, request, view=self)
        return Response(
            {
                "posts": [queries.compact_post(keep) for keep in page],
                "next_cursor": paginator.get_next_cursor(),
            }
        )


@extend_schema(exclude=True)
class AgentPostDetailView(AgentAPIView):
    """One post, with its latest comments."""

    def get(self, request, post_id):
        circle_id = request.auth.circle_id
        keep = queries.agent_posts(circle_id).filter(pk=post_id).first()
        if keep is None:
            raise Http404
        return Response(queries.post_detail(keep, circle_id))


@extend_schema(exclude=True)
class AgentMilestoneSuggestionView(AgentAPIView):
    """Propose one post as a milestone (tokens created with ``can_suggest`` only)."""

    permission_classes = [IsApiToken, CanSuggest]
    throttle_classes = [AgentReadThrottle, AgentSuggestThrottle]

    def post(self, request):
        token = request.auth
        serializer = MilestoneSuggestionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        keep = queries.agent_posts(token.circle_id).filter(pk=data["post_id"]).first()
        if keep is None:
            raise Http404
        result = milestones.propose(
            circle_id=token.circle_id,
            keep=keep,
            source=MilestoneSuggestion.Source.AGENT,
            label=data["label"],
            reason=data["reason"],
            token_prefix=token.display_prefix,
        )
        if result.outcome == milestones.BIRTHDAY:
            return Response({"code": "birthday"}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        if result.outcome == milestones.PENDING_CAP:
            return Response({"code": "pending_cap"}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        return Response(
            {"status": result.outcome, "created": result.created},
            status=status.HTTP_201_CREATED if result.created else status.HTTP_200_OK,
        )
