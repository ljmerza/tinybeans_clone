"""Admin-facing circle invitation views (create, list, cancel, resend)."""
from datetime import timedelta
from uuid import UUID

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import OpenApiResponse, OpenApiTypes, extend_schema
from rest_framework import permissions, status
from rest_framework.views import APIView

from mysite.auth.permissions import IsEmailVerified
from mysite.notification_utils import (
    create_message,
    error_response,
    rate_limit_response,
    success_response,
)

from ...models import Circle, CircleInvitation, CircleInvitationStatus
from ...serializers import (
    CircleInvitationCreateSerializer,
    CircleInvitationSerializer,
)
from ...services.invitation_service import (
    check_admin_permission,
    send_invitation_email,
)


class CircleInvitationCreateView(APIView):
    """Create and list invitations for a circle (admin only)."""

    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]
    serializer_class = CircleInvitationCreateSerializer

    @extend_schema(
        description='List invitations for a circle. Only admins can access this endpoint.',
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='Invitations for the specified circle.',
            )
        },
    )
    def get(self, request, circle_id):
        """List invitations for a circle."""
        circle = get_object_or_404(Circle, id=circle_id)
        check_admin_permission(request.user, circle)

        include_archived = request.query_params.get('include') == 'archived'
        base_qs = circle.invitations.select_related('invited_user').order_by('-created_at')

        if not include_archived:
            base_qs = base_qs.filter(status=CircleInvitationStatus.PENDING)

        invitations = base_qs
        data = CircleInvitationSerializer(invitations, many=True).data
        return success_response({'invitations': data})

    @extend_schema(
        description='Invite a new member to join a circle via email. Existing users receive a pending invitation and must accept before joining.',
        request=CircleInvitationCreateSerializer,
        responses={
            202: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='Invitation created and notification queued.',
            )
        },
    )
    def post(self, request, circle_id):
        """Create a new invitation."""
        circle = get_object_or_404(Circle, id=circle_id)
        check_admin_permission(request.user, circle)

        serializer = CircleInvitationCreateSerializer(data=request.data, context={'circle': circle})
        serializer.is_valid(raise_exception=True)

        # Check circle-level rate limiting
        if getattr(settings, 'RATELIMIT_ENABLE', True):
            circle_limit = getattr(settings, 'CIRCLE_INVITE_CIRCLE_LIMIT', 0)
            if circle_limit:
                minutes = getattr(settings, 'CIRCLE_INVITE_CIRCLE_LIMIT_WINDOW_MINUTES', 60)
                window_start = timezone.now() - timedelta(minutes=minutes)
                invite_count = circle.invitations.filter(created_at__gte=window_start).count()

                if invite_count >= circle_limit:
                    return rate_limit_response(
                        context={'scope': 'circle', 'limit': circle_limit, 'windowMinutes': minutes}
                    )

        # Create invitation
        invitation = CircleInvitation.objects.create(
            circle=circle,
            email=serializer.validated_data['email'],
            invited_by=request.user,
            invited_user=serializer.validated_data.get('invited_user'),
            role=serializer.validated_data['role'],
        )

        # Send invitation email
        send_invitation_email(invitation, request.user.display_name)

        data = CircleInvitationSerializer(invitation).data
        return success_response(
            {'invitation': data},
            messages=[create_message('notifications.circle.invitation_sent')],
            status_code=status.HTTP_202_ACCEPTED
        )

    # Apply user-level rate limiting to POST
    if getattr(settings, 'RATELIMIT_ENABLE', True):
        post = method_decorator(
            ratelimit(
                key='user',
                rate=getattr(settings, 'CIRCLE_INVITE_RATELIMIT', '10/15m'),
                method='POST',
                block=True,
            )
        )(post)


class CircleInvitationCancelView(APIView):
    """Cancel a pending invitation (admin only)."""

    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]
    serializer_class = CircleInvitationSerializer

    @extend_schema(
        description='Cancel a pending invitation for the specified circle.',
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='Invitation cancelled successfully.',
            )
        },
    )
    def post(self, request, circle_id, invitation_id):
        """Cancel a pending invitation."""
        circle = get_object_or_404(Circle, id=circle_id)
        check_admin_permission(request.user, circle)

        try:
            invitation_uuid = UUID(str(invitation_id))
        except ValueError:
            return error_response(
                'invitation_invalid',
                [create_message('errors.invitation_not_found')],
                status.HTTP_404_NOT_FOUND,
            )

        invitation = CircleInvitation.objects.filter(
            id=invitation_uuid,
            circle=circle,
        ).first()

        if not invitation:
            return error_response(
                'invitation_not_found',
                [create_message('errors.invitation_not_found')],
                status.HTTP_404_NOT_FOUND,
            )

        if invitation.status != CircleInvitationStatus.PENDING:
            return error_response(
                'invitation_not_pending',
                [create_message('errors.invitation_not_pending')],
                status.HTTP_400_BAD_REQUEST,
            )

        invitation.delete()

        return success_response(
            {
                'invitation_id': str(invitation.id),
            },
            status_code=status.HTTP_200_OK,
        )


class CircleInvitationResendView(APIView):
    """Resend a pending invitation email (admin only)."""

    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]
    serializer_class = CircleInvitationSerializer

    @extend_schema(
        description='Resend a pending invitation email for the specified circle.',
        responses={
            202: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='Invitation resend accepted and email re-queued.',
            )
        },
    )
    def post(self, request, circle_id, invitation_id):
        """Resend invitation email."""
        circle = get_object_or_404(Circle, id=circle_id)
        check_admin_permission(request.user, circle)

        try:
            invitation_uuid = UUID(str(invitation_id))
        except ValueError:
            return error_response(
                'invitation_invalid',
                [create_message('errors.invitation_not_found')],
                status.HTTP_404_NOT_FOUND,
            )

        invitation = CircleInvitation.objects.filter(
            id=invitation_uuid,
            circle=circle,
        ).select_related('invited_user').first()

        if not invitation:
            return error_response(
                'invitation_not_found',
                [create_message('errors.invitation_not_found')],
                status.HTTP_404_NOT_FOUND,
            )

        if invitation.status != CircleInvitationStatus.PENDING:
            return error_response(
                'invitation_not_pending',
                [create_message('errors.invitation_not_pending')],
                status.HTTP_400_BAD_REQUEST,
            )

        # Send invitation email
        invited_by_name = invitation.invited_by.display_name if invitation.invited_by_id else request.user.display_name
        send_invitation_email(invitation, invited_by_name)

        # Update reminder timestamp
        invitation.reminder_sent_at = timezone.now()
        invitation.save(update_fields=['reminder_sent_at'])

        data = CircleInvitationSerializer(invitation).data
        return success_response(
            {'invitation': data},
            messages=[create_message('notifications.circle.invitation_sent')],
            status_code=status.HTTP_202_ACCEPTED,
        )

    # Apply user-level rate limiting to POST
    if getattr(settings, 'RATELIMIT_ENABLE', True):
        post = method_decorator(
            ratelimit(
                key='user',
                rate=getattr(settings, 'CIRCLE_INVITE_RESEND_RATELIMIT', '5/15m'),
                method='POST',
                block=True,
            )
        )(post)
