"""A child's growth log on the person page.

Everyone in the person's circle can read it; only the circle's admins can add,
change or delete measurements (the same rule as albums). Only child-kind
people have a growth log; for anyone else, and for people outside the
viewer's circles, it is 404.
"""

from django.http import Http404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from mysite.circles.models import CircleMembership
from mysite.users.models import UserRole

from ..models import GrowthMeasurement, Person
from ..serializers.growth import GrowthMeasurementSerializer

# The list is returned whole, for the charts; this keeps it bounded.
GROWTH_MEASUREMENT_LIMIT = 1000

ADMIN_ONLY_MESSAGE = "Only circle admins can add or change growth measurements."


def get_child_person_or_404(user, person_id):
    """A child's person in one of the user's circles, with the child loaded; 404 otherwise."""
    person = (
        Person.objects.filter(id=person_id, circle__memberships__user=user, child__isnull=False)
        .select_related("child")
        .first()
    )
    if person is None:
        raise Http404
    return person


def can_edit_growth(user, person):
    return CircleMembership.objects.filter(circle_id=person.circle_id, user=user, role=UserRole.CIRCLE_ADMIN).exists()


def require_growth_admin(user, person):
    if not can_edit_growth(user, person):
        raise PermissionDenied(ADMIN_ONLY_MESSAGE)


class PersonGrowthView(APIView):
    """A child's measurements (GET, any member) or a new one (POST, circle admins)."""

    @extend_schema(
        summary="Growth log",
        description="Every measurement of a child, oldest first, with the child's birthdate (for age) and "
        "whether the viewer may change the log (circle admins). Heights are in cm and weights in kg. "
        "404 unless the person is a child in one of the viewer's circles.",
        responses={
            200: OpenApiResponse(description="`{can_edit, birthdate, measurements: [...]}`"),
            404: OpenApiResponse(description="Not found, not a child, or not in one of the user's circles"),
        },
    )
    def get(self, request, person_id):
        person = get_child_person_or_404(request.user, person_id)
        measurements = GrowthMeasurement.objects.filter(person=person)
        return Response(
            {
                "can_edit": can_edit_growth(request.user, person),
                "birthdate": person.child.birthdate,
                "measurements": GrowthMeasurementSerializer(measurements, many=True).data,
            }
        )

    @extend_schema(
        summary="Log a measurement",
        description="Circle admins can log a height (cm), a weight (kg) or both for a date. Values are "
        "rounded to 0.1 cm and 1 g. The date can't be in the future or before the child's birthdate.",
        request=GrowthMeasurementSerializer,
        responses={
            201: OpenApiResponse(response=GrowthMeasurementSerializer, description="The new measurement"),
            400: OpenApiResponse(description="Invalid input, or neither height nor weight"),
            403: OpenApiResponse(description="Not an admin of the circle"),
            404: OpenApiResponse(description="Not found, not a child, or not in one of the user's circles"),
        },
    )
    def post(self, request, person_id):
        person = get_child_person_or_404(request.user, person_id)
        require_growth_admin(request.user, person)
        if GrowthMeasurement.objects.filter(person=person).count() >= GROWTH_MEASUREMENT_LIMIT:
            raise ValidationError({"detail": "This growth log is full."})
        serializer = GrowthMeasurementSerializer(data=request.data, context={"person": person})
        serializer.is_valid(raise_exception=True)
        measurement = serializer.save(person=person, created_by=request.user)
        return Response(GrowthMeasurementSerializer(measurement).data, status=status.HTTP_201_CREATED)


class PersonGrowthDetailView(APIView):
    """Change (PATCH) or delete (DELETE) one measurement. Circle admins only."""

    def _measurement_for_edit(self, request, person_id, measurement_id):
        person = get_child_person_or_404(request.user, person_id)
        measurement = GrowthMeasurement.objects.filter(id=measurement_id, person=person).first()
        if measurement is None:
            raise Http404
        require_growth_admin(request.user, person)
        measurement.person = person
        return measurement

    @extend_schema(
        summary="Change a measurement",
        description="Circle admins can change the date, height, weight or note. Send only what changed; "
        "a height or weight set to null is cleared, as long as the other remains.",
        request=GrowthMeasurementSerializer,
        responses={
            200: OpenApiResponse(response=GrowthMeasurementSerializer, description="The measurement"),
            400: OpenApiResponse(description="Invalid input, or neither height nor weight left"),
            403: OpenApiResponse(description="Not an admin of the circle"),
            404: OpenApiResponse(description="Not found or not visible to the user"),
        },
    )
    def patch(self, request, person_id, measurement_id):
        measurement = self._measurement_for_edit(request, person_id, measurement_id)
        serializer = GrowthMeasurementSerializer(
            measurement, data=request.data, partial=True, context={"person": measurement.person}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(
        summary="Delete a measurement",
        responses={
            204: OpenApiResponse(description="Deleted"),
            403: OpenApiResponse(description="Not an admin of the circle"),
            404: OpenApiResponse(description="Not found or not visible to the user"),
        },
    )
    def delete(self, request, person_id, measurement_id):
        measurement = self._measurement_for_edit(request, person_id, measurement_id)
        measurement.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
