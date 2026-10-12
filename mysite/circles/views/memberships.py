"""Circle membership management views."""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiResponse, OpenApiTypes, extend_schema
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView

from mysite.auth.permissions import IsEmailVerified
from mysite.notification_utils import create_message, error_response, success_response
from mysite.users.models import UserRole

from ..models import Circle, CircleMembership
from ..serializers import (
    CircleMemberAddSerializer,
    CircleMemberSerializer,
    CircleMembershipSerializer,
    CircleMembershipSettingsSerializer,
    CircleSerializer,
)


class CircleMemberListView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]
    serializer_class = CircleMemberSerializer

    @extend_schema(
        description="List members of a circle including their roles.",
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="Members of the requested circle with roles.",
            )
        },
    )
    def get(self, request, circle_id):
        circle = get_object_or_404(Circle, id=circle_id)
        membership = CircleMembership.objects.filter(circle=circle, user=request.user).first()
        if not (request.user.is_superuser or (membership and membership.role == UserRole.CIRCLE_ADMIN)):
            raise PermissionDenied(_("Only circle admins can view members"))

        memberships = CircleMembership.objects.filter(circle=circle).select_related("user").order_by("user__email")
        serializer = CircleMemberSerializer(memberships, many=True)
        return success_response({"circle": CircleSerializer(circle).data, "members": serializer.data})

    @extend_schema(
        description="Add an existing user to a circle with an optional role override.",
        request=CircleMemberAddSerializer,
        responses={
            201: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="Membership created for user in circle.",
            )
        },
    )
    def post(self, request, circle_id):
        circle = get_object_or_404(Circle, id=circle_id)
        membership = CircleMembership.objects.filter(circle=circle, user=request.user).first()
        if not (request.user.is_superuser or (membership and membership.role == UserRole.CIRCLE_ADMIN)):
            raise PermissionDenied(_("Only circle admins can add members"))

        serializer = CircleMemberAddSerializer(
            data=request.data,
            context={"circle": circle, "invited_by": request.user},
        )
        serializer.is_valid(raise_exception=True)
        membership = serializer.save()

        return success_response(
            {"membership": CircleMemberSerializer(membership).data},
            messages=[create_message("notifications.circle.member_added")],
            status_code=status.HTTP_201_CREATED,
        )


class CircleMyMembershipView(APIView):
    """The viewer's own membership in a circle, and the settings they can change on it."""

    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]
    serializer_class = CircleMembershipSettingsSerializer

    def get_membership(self, request, circle_id):
        return get_object_or_404(
            CircleMembership.objects.select_related("circle"), circle_id=circle_id, user=request.user
        )

    @extend_schema(
        description="The viewer's membership in this circle, including their own settings for it.",
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="`{membership}`")},
    )
    def get(self, request, circle_id):
        membership = self.get_membership(request, circle_id)
        return success_response({"membership": CircleMembershipSerializer(membership).data})

    @extend_schema(
        description="Change the viewer's own settings for this circle, e.g. how often its "
        '"On this day" memories show in their home feed. Any member may change their own.',
        request=CircleMembershipSettingsSerializer,
        responses={
            200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="`{membership}`"),
            404: OpenApiResponse(description="Not a member of this circle"),
        },
    )
    def patch(self, request, circle_id):
        membership = self.get_membership(request, circle_id)
        serializer = CircleMembershipSettingsSerializer(membership, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response({"membership": CircleMembershipSerializer(membership).data})


class CircleMemberRemoveView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]
    serializer_class = CircleMemberSerializer

    @extend_schema(
        description="Remove a member (or yourself) from a circle. Circle owners cannot be removed.",
        responses={
            204: OpenApiResponse(description="Membership removed."),
            403: OpenApiResponse(description="Cannot remove circle owner."),
            404: OpenApiResponse(description="Membership not found."),
        },
    )
    def delete(self, request, circle_id, user_id):
        circle = get_object_or_404(Circle, id=circle_id)
        membership_to_remove = (
            CircleMembership.objects.filter(circle=circle, user_id=user_id).select_related("user").first()
        )
        if not membership_to_remove:
            return error_response(
                "membership_not_found", [create_message("errors.membership_not_found")], status.HTTP_404_NOT_FOUND
            )

        # Prevent owner removal (most important check - do this first)
        if membership_to_remove.is_owner:
            return error_response(
                "cannot_remove_owner", [create_message("errors.circle.cannot_remove_owner")], status.HTTP_403_FORBIDDEN
            )

        requester_membership = CircleMembership.objects.filter(circle=circle, user=request.user).first()
        removing_self = request.user.id == user_id

        if not removing_self:
            if not (
                request.user.is_superuser
                or (requester_membership and requester_membership.role == UserRole.CIRCLE_ADMIN)
            ):
                raise PermissionDenied(_("Only circle admins can remove other members"))
        else:
            if not requester_membership and not request.user.is_superuser:
                raise PermissionDenied(_("Not a member of this circle"))

        membership_to_remove.delete()
        return success_response({}, status_code=status.HTTP_204_NO_CONTENT)


__all__ = [
    "CircleMemberListView",
    "CircleMemberRemoveView",
]
