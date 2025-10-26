"""Invitee-facing circle invitation views (list, respond, accept, finalize)."""
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiResponse, OpenApiTypes, extend_schema
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView

from mysite.auth.permissions import IsEmailVerified
from mysite.auth.token_utils import pop_token, store_token
from mysite.emails.tasks import send_email_task
from mysite.emails.templates import CIRCLE_INVITATION_ACCEPTED_TEMPLATE
from mysite.notification_utils import (
    create_message,
    error_response,
    success_response,
)

from ...models import (
    CircleInvitation,
    CircleInvitationStatus,
    CircleMembership,
)
from ...serializers import (
    CircleInvitationFinalizeSerializer,
    CircleInvitationOnboardingStartSerializer,
    CircleInvitationResponseSerializer,
    CircleInvitationSerializer,
    CircleMembershipSerializer,
    CircleSerializer,
    UserSerializer,
)


class CircleInvitationListView(APIView):
    """List pending invitations for the authenticated user."""

    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]
    serializer_class = CircleInvitationSerializer

    @extend_schema(
        description='Return pending circle invitations for the authenticated user.',
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='Pending invitations for the authenticated user.',
            )
        }
    )
    def get(self, request):
        """List pending invitations for the current user."""
        invitations = CircleInvitation.objects.filter(
            email__iexact=request.user.email,
            status=CircleInvitationStatus.PENDING,
        ).select_related('circle')

        data = CircleInvitationSerializer(invitations, many=True).data
        return success_response({'invitations': data})


class CircleInvitationRespondView(APIView):
    """Accept or decline a pending invitation."""

    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]
    serializer_class = CircleInvitationResponseSerializer

    @extend_schema(
        description='Accept or decline a pending invitation that belongs to the authenticated user.',
        request=CircleInvitationResponseSerializer,
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='Invitation response processed for authenticated user.',
            )
        },
    )
    def post(self, request, invitation_id):
        """Accept or decline an invitation."""
        invitation = get_object_or_404(CircleInvitation, id=invitation_id)

        if invitation.email.lower() != request.user.email.lower():
            raise PermissionDenied(_('Invitation does not belong to this user'))

        serializer = CircleInvitationResponseSerializer(data=request.data, context={'invitation': invitation})
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data['action']

        if invitation.status != CircleInvitationStatus.PENDING:
            return error_response(
                'invitation_not_pending',
                [create_message('errors.invitation_not_pending')],
                status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            if action == 'accept':
                membership, created = CircleMembership.objects.get_or_create(
                    user=request.user,
                    circle=invitation.circle,
                    defaults={'role': invitation.role, 'invited_by': invitation.invited_by},
                )
                if not created and membership.role != invitation.role:
                    membership.role = invitation.role
                    membership.save(update_fields=['role'])

                invitation.status = CircleInvitationStatus.ACCEPTED
                if invitation.invited_user_id != request.user.id:
                    invitation.invited_user = request.user
                invitation.archived_at = timezone.now()
                invitation.archived_reason = "accepted"
                message_key = 'notifications.circle.invitation_accepted'
            else:
                invitation.status = CircleInvitationStatus.DECLINED
                message_key = 'notifications.circle.invitation_declined'

            invitation.responded_at = timezone.now()
            update_fields = ['status', 'responded_at']
            if invitation.invited_user_id == request.user.id:
                update_fields.append('invited_user')
            invitation.save(update_fields=update_fields)

        return success_response(
            {'circle': CircleSerializer(invitation.circle).data},
            messages=[create_message(message_key)],
            status_code=status.HTTP_200_OK
        )


class CircleInvitationAcceptView(APIView):
    """Begin onboarding flow for a circle invitation (token-based, public)."""

    permission_classes = [permissions.AllowAny]
    serializer_class = CircleInvitationOnboardingStartSerializer

    @extend_schema(
        description='Begin onboarding for a circle invitation using the one-time link token. Returns metadata and an onboarding token for account creation.',
        request=CircleInvitationOnboardingStartSerializer,
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='Invitation onboarding initialized. Returns onboarding token and invitation context.',
            )
        },
    )
    def post(self, request):
        """Start onboarding flow with invitation token."""
        serializer = CircleInvitationOnboardingStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Consume the one-time invitation token
        payload = pop_token('circle-invite', serializer.validated_data['token'])
        if not payload:
            return error_response(
                'token_invalid_expired',
                [create_message('errors.token_invalid_expired')],
                status.HTTP_400_BAD_REQUEST
            )

        # Verify invitation exists and is pending
        invitation = CircleInvitation.objects.filter(
            id=payload['invitation_id'],
            status=CircleInvitationStatus.PENDING,
        ).select_related('circle', 'invited_by').first()

        if not invitation:
            return error_response(
                'invitation_not_found',
                [create_message('errors.invitation_not_found')],
                status.HTTP_404_NOT_FOUND
            )

        # Verify email matches
        if invitation.email.lower() != payload.get('email', '').lower():
            return error_response(
                'invitation_mismatch',
                [create_message('errors.invitation_mismatch')],
                status.HTTP_400_BAD_REQUEST
            )

        # Create onboarding token with extended TTL
        onboarding_payload = {
            'invitation_id': str(invitation.id),
            'circle_id': invitation.circle_id,
            'email': invitation.email,
            'role': invitation.role,
            'existing_user': bool(invitation.invited_user_id or payload.get('existing_user')),
            'invited_user_id': invitation.invited_user_id,
            'issued_at': timezone.now().isoformat(),
            'invited_by_id': invitation.invited_by_id,
        }

        ttl_minutes = getattr(settings, 'CIRCLE_INVITE_ONBOARDING_TTL_MINUTES', 60)
        onboarding_token = store_token(
            'circle-invite-onboarding',
            onboarding_payload,
            ttl=max(60, ttl_minutes * 60),
        )

        # Prepare response
        circle_data = CircleSerializer(invitation.circle).data
        inviter = UserSerializer(invitation.invited_by).data if invitation.invited_by_id else None

        response_payload = {
            'onboarding_token': onboarding_token,
            'expires_in_minutes': ttl_minutes,
            'invitation': {
                'id': str(invitation.id),
                'email': invitation.email,
                'existing_user': onboarding_payload['existing_user'],
                'role': invitation.role,
                'circle': circle_data,
                'invited_user_id': invitation.invited_user_id,
                'invited_by': inviter,
                'reminder_scheduled_at': invitation.created_at,
            },
        }

        return success_response(
            response_payload,
            messages=[create_message('notifications.circle.invitation_onboarding_ready')],
            status_code=status.HTTP_200_OK,
        )


class CircleInvitationFinalizeView(APIView):
    """Finalize circle invitation onboarding (authenticated).

    Note: Does not require IsEmailVerified because the onboarding token proves
    email ownership (user clicked link from inbox). Email is auto-verified during finalization.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CircleInvitationFinalizeSerializer

    @extend_schema(
        description='Finalize circle invitation onboarding using an onboarding token once the invitee is authenticated.',
        request=CircleInvitationFinalizeSerializer,
        responses={
            201: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='Invitation accepted and membership created.',
            )
        },
    )
    def post(self, request):
        """Complete onboarding and create membership."""
        serializer = CircleInvitationFinalizeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Consume onboarding token
        payload = pop_token('circle-invite-onboarding', serializer.validated_data['onboarding_token'])
        if not payload:
            return error_response(
                'token_invalid_expired',
                [create_message('errors.token_invalid_expired')],
                status.HTTP_400_BAD_REQUEST
            )

        # Verify invitation exists and is pending
        invitation = CircleInvitation.objects.filter(
            id=payload['invitation_id'],
            status=CircleInvitationStatus.PENDING,
        ).select_related('circle', 'invited_by').first()

        if not invitation:
            return error_response(
                'invitation_not_found',
                [create_message('errors.invitation_not_found')],
                status.HTTP_404_NOT_FOUND
            )

        # Verify user matches invitation
        user = request.user
        email_match = user.email and user.email.lower() == invitation.email.lower()
        invited_match = invitation.invited_user_id == user.id

        if not email_match and not invited_match:
            return error_response(
                'invitation_mismatch',
                [create_message('errors.invitation_mismatch')],
                status.HTTP_403_FORBIDDEN
            )

        # Create membership and update invitation
        with transaction.atomic():
            # Auto-verify email since they proved ownership by clicking invite link
            if not user.email_verified:
                user.email_verified = True
                user.save(update_fields=['email_verified'])

            membership, created = CircleMembership.objects.get_or_create(
                user=user,
                circle=invitation.circle,
                defaults={'role': invitation.role, 'invited_by': invitation.invited_by},
            )

            if not created and membership.role != invitation.role:
                membership.role = invitation.role
                membership.invited_by = membership.invited_by or invitation.invited_by
                membership.save(update_fields=['role', 'invited_by'])

            invitation.status = CircleInvitationStatus.ACCEPTED
            invitation.responded_at = timezone.now()
            invitation.archived_at = timezone.now()
            invitation.archived_reason = "accepted"

            if invitation.invited_user_id != user.id:
                invitation.invited_user = user

            update_fields = ['status', 'responded_at', 'invited_user', 'archived_at', 'archived_reason']
            invitation.save(update_fields=update_fields)

        # Notify inviter
        if invitation.invited_by_id:
            base_url = getattr(settings, 'ACCOUNT_FRONTEND_BASE_URL', 'http://localhost:3000').rstrip('/')
            send_email_task.delay(
                to_email=invitation.invited_by.email,
                template_id=CIRCLE_INVITATION_ACCEPTED_TEMPLATE,
                context={
                    'circle_name': invitation.circle.name,
                    'invited_by': invitation.invited_by.display_name,
                    'invitee_name': user.display_name,
                    'circle_admin_link': f"{base_url}/circles/{invitation.circle.id}",
                },
            )

        return success_response(
            {
                'circle': CircleSerializer(invitation.circle).data,
                'membership': CircleMembershipSerializer(membership).data,
            },
            messages=[create_message('notifications.circle.invitation_accepted')],
            status_code=status.HTTP_201_CREATED,
        )
