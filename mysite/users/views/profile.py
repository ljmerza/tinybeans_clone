"""Profile and preference management views."""

from __future__ import annotations

import logging

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, OpenApiTypes, extend_schema
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView

from mysite import project_logging
from mysite.auth.permissions import IsEmailVerified
from mysite.notification_utils import create_message, error_response, success_response

from ..models import Circle, CircleMembership, UserNotificationPreferences
from ..serializers import EmailPreferencesSerializer, UserProfileSerializer

logger = logging.getLogger(__name__)


class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserProfileSerializer

    @extend_schema(
        description="Retrieve profile metadata for the authenticated user.",
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT, description="Authenticated user profile data")},
    )
    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return success_response({"user": serializer.data})

    @extend_schema(
        description="Update selected profile fields (name, etc.) for the authenticated user.",
        request=UserProfileSerializer,
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT)},
    )
    def patch(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        updated_fields = sorted(serializer.validated_data.keys())
        with project_logging.log_context(user_id=request.user.id):
            logger.info(
                "User profile updated",
                extra={
                    "event": "users.profile.updated",
                    "extra": {"updated_fields": updated_fields},
                },
            )
        return success_response(
            {"user": serializer.data},
            messages=[create_message("notifications.profile.updated")],
            status_code=status.HTTP_200_OK,
        )


class EmailPreferencesView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]
    serializer_class = EmailPreferencesSerializer

    def get_circle(self, request):
        circle_id = request.query_params.get("circle_id")
        if not circle_id:
            return None
        circle = get_object_or_404(Circle, id=circle_id)
        if not CircleMembership.objects.filter(circle=circle, user=request.user).exists():
            raise PermissionDenied(_("Not a member of this circle"))
        return circle

    def get_object(self, request):
        """Return the row to edit, creating it if needed.

        A new circle override starts as a copy of the user's current global
        preferences, so changing one setting doesn't reset the others.
        """
        circle = self.get_circle(request)
        if circle is None:
            prefs, _created = UserNotificationPreferences.objects.get_or_create(user=request.user, circle=None)
            return prefs
        prefs = UserNotificationPreferences.effective_for(request.user, circle)
        if prefs.circle_id is None:
            prefs.pk = None
            prefs.circle = circle
            prefs.save()
        return prefs

    @extend_schema(
        description="Fetch the notification preferences in effect, optionally for a specific circle. "
        "A circle without its own override returns the user's global preferences.",
        parameters=[
            OpenApiParameter(
                name="circle_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Optional circle context to fetch per-circle overrides.",
                required=False,
            )
        ],
        responses=EmailPreferencesSerializer,
    )
    def get(self, request):
        prefs = UserNotificationPreferences.effective_for(request.user, self.get_circle(request))
        return success_response(EmailPreferencesSerializer(prefs).data)

    @extend_schema(
        description="Update notification preferences globally or for a specific circle.",
        parameters=[
            OpenApiParameter(
                name="circle_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Optional circle context when updating per-circle overrides.",
                required=False,
            )
        ],
        request=EmailPreferencesSerializer,
        responses=EmailPreferencesSerializer,
    )
    def patch(self, request):
        prefs = self.get_object(request)
        serializer = EmailPreferencesSerializer(prefs, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        circle_id = getattr(prefs.circle, "id", None)
        with project_logging.log_context(user_id=request.user.id, circle_id=circle_id):
            logger.info(
                "Notification preferences updated",
                extra={
                    "event": "users.preferences.updated",
                    "extra": {
                        "circle_id": circle_id,
                        "updated_fields": sorted(serializer.validated_data.keys()),
                    },
                },
            )
        return success_response(
            serializer.data,
            messages=[create_message("notifications.preferences.updated")],
            status_code=status.HTTP_200_OK,
        )

    @extend_schema(
        description="Remove a circle's notification override so the global preferences apply again.",
        parameters=[
            OpenApiParameter(
                name="circle_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Circle whose override should be removed.",
                required=True,
            )
        ],
        responses=EmailPreferencesSerializer,
    )
    def delete(self, request):
        circle = self.get_circle(request)
        if circle is None:
            return error_response(
                "circle_required",
                [create_message("errors.notification_circle_required")],
                status.HTTP_400_BAD_REQUEST,
            )
        UserNotificationPreferences.objects.filter(user=request.user, circle=circle).delete()
        prefs = UserNotificationPreferences.effective_for(request.user, circle)
        return success_response(
            EmailPreferencesSerializer(prefs).data,
            messages=[create_message("notifications.preferences.updated")],
            status_code=status.HTTP_200_OK,
        )
