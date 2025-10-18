"""Profile and preference management views."""
from __future__ import annotations

import logging

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, OpenApiTypes, extend_schema

from mysite import project_logging
from mysite.notification_utils import create_message, success_response
from ..models import Circle, CircleMembership, UserNotificationPreferences
from ..serializers import EmailPreferencesSerializer, UserProfileSerializer

logger = logging.getLogger(__name__)


class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserProfileSerializer

    @extend_schema(
        description='Retrieve profile metadata for the authenticated user.',
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT, description='Authenticated user profile data')},
    )
    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return success_response({'user': serializer.data})

    @extend_schema(
        description='Update selected profile fields (name, etc.) for the authenticated user.',
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
                'User profile updated',
                extra={
                    'event': 'users.profile.updated',
                    'extra': {'updated_fields': updated_fields},
                },
            )
        return success_response(
            {'user': serializer.data},
            messages=[create_message('notifications.profile.updated')],
            status_code=status.HTTP_200_OK
        )


class EmailPreferencesView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmailPreferencesSerializer

    def get_object(self, request):
        circle_id = request.query_params.get('circle_id')
        circle = None
        if circle_id:
            circle = get_object_or_404(Circle, id=circle_id)
            if not CircleMembership.objects.filter(circle=circle, user=request.user).exists():
                raise PermissionDenied(_('Not a member of this circle'))
        prefs, _ = UserNotificationPreferences.objects.get_or_create(user=request.user, circle=circle)
        return prefs

    @extend_schema(
        description='Fetch notification preferences, optionally scoped to a specific circle.',
        parameters=[
            OpenApiParameter(
                name='circle_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Optional circle context to fetch per-circle overrides.',
                required=False,
            )
        ],
        responses=EmailPreferencesSerializer,
    )
    def get(self, request):
        prefs = self.get_object(request)
        return success_response(EmailPreferencesSerializer(prefs).data)

    @extend_schema(
        description='Update notification preferences globally or for a specific circle.',
        parameters=[
            OpenApiParameter(
                name='circle_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Optional circle context when updating per-circle overrides.',
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
        circle_id = getattr(prefs.circle, 'id', None)
        with project_logging.log_context(user_id=request.user.id, circle_id=circle_id):
            logger.info(
                'Notification preferences updated',
                extra={
                    'event': 'users.preferences.updated',
                    'extra': {
                        'circle_id': circle_id,
                        'updated_fields': sorted(serializer.validated_data.keys()),
                    },
                },
            )
        return success_response(
            serializer.data,
            messages=[create_message('notifications.preferences.updated')],
            status_code=status.HTTP_200_OK
        )
