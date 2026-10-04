"""People tagging: a circle's taggable people, one person, and setting a post's people.

Any member of a circle may tag anyone on any of its posts, like commenting.
Everything here is 404 for people outside the circle.
"""

from django.db.models.functions import Lower
from django.http import Http404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from mysite.circles.models import Circle

from ..models import Person
from ..people import ensure_circle_people, resolve_circle_people, set_keep_people
from ..serializers.people import (
    KeepPeopleUpdateSerializer,
    PersonCreateSerializer,
    PersonDetailSerializer,
    PersonSerializer,
)
from .feed import get_visible_keep_or_404


def get_member_circle_or_404(user, circle_id):
    circle = Circle.objects.filter(id=circle_id, memberships__user=user).first()
    if circle is None:
        raise Http404
    return circle


def tagged_people(keep):
    """A post's people as the feed shows them: `{id, name}`, in name order."""
    people = keep.people.order_by(Lower("name"), "id")
    return [{"id": str(person.id), "name": person.name} for person in people]


class CirclePeopleView(APIView):
    """A circle's taggable people (GET), or a new free-text person (POST)."""

    @extend_schema(
        summary="Circle people",
        description="Everyone who can be tagged on the circle's posts, in name order: its child profiles, "
        "members and pets (each given a person the first time this is listed) and the free-text people "
        "members added. `kind` is `child`, `member`, `pet` or `other`. 404 unless the user is a member.",
        responses={
            200: OpenApiResponse(response=PersonSerializer(many=True), description="The circle's people"),
            404: OpenApiResponse(description="Not found or not a member"),
        },
    )
    def get(self, request, circle_id):
        circle = get_member_circle_or_404(request.user, circle_id)
        ensure_circle_people(circle)
        people = Person.objects.filter(circle=circle).order_by(Lower("name"), "id")
        return Response(PersonSerializer(people, many=True).data)

    @extend_schema(
        summary="Add a person",
        description='Any member can add someone who has no profile, e.g. "Grandma Jo", so they can be '
        "tagged. The name is trimmed; another free-text person in the circle with the same name (ignoring "
        "case) is rejected.",
        request=PersonCreateSerializer,
        responses={
            201: OpenApiResponse(response=PersonSerializer, description="The new person"),
            400: OpenApiResponse(description="Missing, too long or duplicate name"),
            404: OpenApiResponse(description="Not found or not a member"),
        },
    )
    def post(self, request, circle_id):
        circle = get_member_circle_or_404(request.user, circle_id)
        serializer = PersonCreateSerializer(data=request.data, context={"circle": circle})
        serializer.is_valid(raise_exception=True)
        person = Person.objects.create(circle=circle, name=serializer.validated_data["name"], created_by=request.user)
        return Response(PersonSerializer(person).data, status=status.HTTP_201_CREATED)


class PersonDetailView(APIView):
    """One person, with their circle, for the person page."""

    @extend_schema(
        summary="Person",
        responses={
            200: OpenApiResponse(response=PersonDetailSerializer, description="The person"),
            404: OpenApiResponse(description="Not found or not in one of the user's circles"),
        },
    )
    def get(self, request, person_id):
        person = (
            Person.objects.filter(id=person_id, circle__memberships__user=request.user).select_related("circle").first()
        )
        if person is None:
            raise Http404
        return Response(PersonDetailSerializer(person).data)


class KeepFeedPeopleView(APIView):
    """Set who is tagged on a post."""

    @extend_schema(
        summary="Tag people on a post",
        description="Replaces the post's people with `people` (person ids, all from the post's circle; an "
        "empty list untags everyone). Any member of the circle may. Returns the post's people as the feed "
        "shows them, in name order.",
        request=KeepPeopleUpdateSerializer,
        responses={
            200: OpenApiResponse(description="`{people: [{id, name}]}`"),
            400: OpenApiResponse(description="Invalid ids, or a person from another circle"),
            404: OpenApiResponse(description="Not found or not visible to the user"),
        },
    )
    def patch(self, request, keep_id):
        keep = get_visible_keep_or_404(request.user, keep_id)
        serializer = KeepPeopleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        people = resolve_circle_people(keep.circle_id, serializer.validated_data["people"])
        set_keep_people(keep, people, request.user)
        return Response({"people": tagged_people(keep)})
