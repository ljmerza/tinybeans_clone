"""Circle lifecycle views (list, detail, activity)."""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiResponse, OpenApiTypes, extend_schema
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView

from mysite.albums.birthdays import queue_sync as queue_birthday_album_sync
from mysite.audit import AuditEvent, log_audit_event
from mysite.auth.permissions import IsEmailVerified
from mysite.notification_utils import create_message, success_response
from mysite.users.models import UserRole

from ..models import Circle, CircleMembership
from ..serializers import (
    CircleCreateSerializer,
    CircleMembershipSerializer,
    CircleSerializer,
    UserSerializer,
)

# Circle settings for the AI milestone features; changes are audit-logged.
AI_SETTING_FIELDS = ("review_ai_milestones",)


class UserCircleListView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]
    serializer_class = CircleMembershipSerializer

    @extend_schema(
        description="List all circles the authenticated user belongs to, including membership roles.",
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="List of circle memberships for the authenticated user.",
            )
        },
    )
    def get(self, request):
        memberships = (
            CircleMembership.objects.filter(user=request.user).select_related("circle").order_by("circle__name")
        )
        serializer = CircleMembershipSerializer(memberships, many=True)
        return success_response({"circles": serializer.data})

    @extend_schema(
        description="Create a new circle owned by the authenticated user. Email verification is required.",
        request=CircleCreateSerializer,
        responses={
            201: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="Circle created and returned with metadata.",
            ),
            400: OpenApiResponse(
                description="Email verification required or validation error.",
            ),
        },
    )
    def post(self, request):
        serializer = CircleCreateSerializer(data=request.data, context={"user": request.user})
        serializer.is_valid(raise_exception=True)
        circle = serializer.save()
        return success_response(
            {"circle": CircleSerializer(circle).data},
            messages=[create_message("notifications.circle.created")],
            status_code=status.HTTP_201_CREATED,
        )


class CircleDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]
    serializer_class = CircleCreateSerializer

    @extend_schema(
        description="Update circle metadata (name, slug) or the monthly recap, On this day, Birthdays album and "
        "AI milestone review settings for an owned circle. Turning the Birthdays album on fills it in the "
        "background.",
        request=CircleCreateSerializer,
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="Circle details updated successfully.",
            )
        },
    )
    def patch(self, request, circle_id):
        circle = get_object_or_404(Circle, id=circle_id)
        membership = CircleMembership.objects.filter(circle=circle, user=request.user).first()
        if not (request.user.is_superuser or (membership and membership.role == UserRole.CIRCLE_ADMIN)):
            raise PermissionDenied(_("Only circle admins can update circle details"))

        serializer = CircleCreateSerializer(circle, data=request.data, partial=True, context={"user": request.user})
        serializer.is_valid(raise_exception=True)
        was_birthday_album_enabled = circle.birthday_album_enabled
        ai_settings_before = {field: getattr(circle, field) for field in AI_SETTING_FIELDS}
        serializer.save()
        if circle.birthday_album_enabled and not was_birthday_album_enabled:
            # Fill the Birthdays album now rather than at the next nightly run.
            queue_birthday_album_sync(circle.id)
        changed_ai_settings = [
            field for field in AI_SETTING_FIELDS if getattr(circle, field) != ai_settings_before[field]
        ]
        if changed_ai_settings:
            log_audit_event(
                AuditEvent(
                    action="circle.ai_settings.update",
                    actor_type="user",
                    actor_id=str(request.user.pk),
                    target_type="circle",
                    target_id=str(circle.id),
                    # Field names only, never values.
                    metadata={"fields": changed_ai_settings},
                )
            )
        return success_response(
            {"circle": CircleSerializer(circle).data},
            messages=[create_message("notifications.circle.updated")],
            status_code=status.HTTP_200_OK,
        )


class CircleActivityView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]
    serializer_class = CircleSerializer

    @extend_schema(
        description="View recent membership and invitation events for a circle.",
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="Aggregation of circle membership and invitation events.",
            )
        },
    )
    def get(self, request, circle_id):
        circle = get_object_or_404(Circle, id=circle_id)
        membership = CircleMembership.objects.filter(circle=circle, user=request.user).first()
        if not (request.user.is_superuser or (membership and membership.role == UserRole.CIRCLE_ADMIN)):
            raise PermissionDenied(_("Only circle admins can view activity"))

        events = []
        memberships = circle.memberships.select_related("user").order_by("-created_at")
        for member in memberships:
            events.append(
                {
                    "type": "member_joined",
                    "created_at": member.created_at,
                    "user": UserSerializer(member.user).data,
                    "role": member.role,
                }
            )

        invitations = circle.invitations.select_related("invited_user").order_by("-created_at")
        for invitation in invitations:
            events.append(
                {
                    "type": "invitation",
                    "created_at": invitation.created_at,
                    "email": invitation.email,
                    "existing_user": bool(invitation.invited_user_id),
                    "invited_user": (
                        UserSerializer(invitation.invited_user).data if invitation.invited_user_id else None
                    ),
                    "role": invitation.role,
                    "status": invitation.status,
                    "responded_at": invitation.responded_at,
                }
            )

        events.sort(key=lambda item: item["created_at"] or timezone.now(), reverse=True)
        return success_response({"circle": CircleSerializer(circle).data, "events": events})


__all__ = [
    "UserCircleListView",
    "CircleDetailView",
    "CircleActivityView",
]
