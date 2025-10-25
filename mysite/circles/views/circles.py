"""Circle lifecycle views (list, detail, activity)."""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiResponse, OpenApiTypes, extend_schema

from mysite.auth.permissions import IsEmailVerified
from mysite.notification_utils import create_message, success_response

from ..models import Circle, CircleInvitation, CircleMembership
from mysite.users.models import UserRole
from ..serializers import (
    CircleCreateSerializer,
    CircleMemberSerializer,
    CircleMembershipSerializer,
    CircleSerializer,
    UserSerializer,
)


class UserCircleListView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]
    serializer_class = CircleMembershipSerializer

    @extend_schema(
        description='List all circles the authenticated user belongs to, including membership roles.',
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='List of circle memberships for the authenticated user.',
            )
        }
    )
    def get(self, request):
        memberships = (
            CircleMembership.objects.filter(user=request.user)
            .select_related('circle')
            .order_by('circle__name')
        )
        serializer = CircleMembershipSerializer(memberships, many=True)
        return success_response({'circles': serializer.data})

    @extend_schema(
        description='Create a new circle owned by the authenticated user. Email verification is required.',
        request=CircleCreateSerializer,
        responses={
            201: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='Circle created and returned with metadata.',
            ),
            400: OpenApiResponse(
                description='Email verification required or validation error.',
            )
        },
    )
    def post(self, request):
        serializer = CircleCreateSerializer(data=request.data, context={'user': request.user})
        serializer.is_valid(raise_exception=True)
        circle = serializer.save()
        return success_response(
            {'circle': CircleSerializer(circle).data},
            messages=[create_message('notifications.circle.created')],
            status_code=status.HTTP_201_CREATED
        )


class CircleDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]
    serializer_class = CircleCreateSerializer

    @extend_schema(
        description='Update circle metadata (name, slug) for an owned circle.',
        request=CircleCreateSerializer,
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='Circle details updated successfully.',
            )
        },
    )
    def patch(self, request, circle_id):
        circle = get_object_or_404(Circle, id=circle_id)
        membership = CircleMembership.objects.filter(circle=circle, user=request.user).first()
        if not (request.user.is_superuser or (membership and membership.role == UserRole.CIRCLE_ADMIN)):
            raise PermissionDenied(_('Only circle admins can update circle details'))

        serializer = CircleCreateSerializer(circle, data=request.data, partial=True, context={'user': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            {'circle': CircleSerializer(circle).data},
            messages=[create_message('notifications.circle.updated')],
            status_code=status.HTTP_200_OK
        )


class CircleActivityView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]
    serializer_class = CircleSerializer

    @extend_schema(
        description='View recent membership and invitation events for a circle.',
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='Aggregation of circle membership and invitation events.',
            )
        }
    )
    def get(self, request, circle_id):
        circle = get_object_or_404(Circle, id=circle_id)
        membership = CircleMembership.objects.filter(circle=circle, user=request.user).first()
        if not (request.user.is_superuser or (membership and membership.role == UserRole.CIRCLE_ADMIN)):
            raise PermissionDenied(_('Only circle admins can view activity'))

        events = []
        memberships = circle.memberships.select_related('user').order_by('-created_at')
        for member in memberships:
            events.append(
                {
                    'type': 'member_joined',
                    'created_at': member.created_at,
                    'user': UserSerializer(member.user).data,
                    'role': member.role,
                }
            )

        invitations = circle.invitations.select_related('invited_user').order_by('-created_at')
        for invitation in invitations:
            events.append(
                {
                    'type': 'invitation',
                    'created_at': invitation.created_at,
                    'email': invitation.email,
                    'existing_user': bool(invitation.invited_user_id),
                    'invited_user': (
                        UserSerializer(invitation.invited_user).data
                        if invitation.invited_user_id else None
                    ),
                    'role': invitation.role,
                    'status': invitation.status,
                    'responded_at': invitation.responded_at,
                }
            )

        events.sort(key=lambda item: item['created_at'] or timezone.now(), reverse=True)
        return success_response({'circle': CircleSerializer(circle).data, 'events': events})


__all__ = [
    'UserCircleListView',
    'CircleDetailView',
    'CircleActivityView',
]
