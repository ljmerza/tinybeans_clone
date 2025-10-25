"""Invitation lifecycle views for circles."""
from __future__ import annotations
from datetime import timedelta
from uuid import UUID
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django_ratelimit.decorators import ratelimit
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiResponse, OpenApiTypes, extend_schema
from mysite.auth.token_utils import (
    TOKEN_TTL_SECONDS,
    pop_token,
    store_token,
)
from mysite.auth.permissions import IsEmailVerified
from mysite.notification_utils import (
    create_message,
    error_response,
    rate_limit_response,
    success_response,
)
from mysite.emails.tasks import send_email_task
from mysite.emails.templates import (
    CIRCLE_INVITATION_ACCEPTED_TEMPLATE,
    CIRCLE_INVITATION_TEMPLATE,
)
from ..models import (
    Circle,
    CircleInvitation,
    CircleInvitationStatus,
    CircleMembership,
)
from mysite.users.models import UserRole
from ..serializers import (
    CircleInvitationCreateSerializer,
    CircleInvitationFinalizeSerializer,
    CircleInvitationOnboardingStartSerializer,
    CircleInvitationResponseSerializer,
    CircleInvitationSerializer,
    CircleMembershipSerializer,
    CircleSerializer,
    UserSerializer,
)
class CircleInvitationCreateView(APIView):
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
        circle = get_object_or_404(Circle, id=circle_id)
        membership = CircleMembership.objects.filter(circle=circle, user=request.user).first()
        if not membership or membership.role != UserRole.CIRCLE_ADMIN:
            raise PermissionDenied(_('Only circle admins can view invitations'))
        include_archived = request.query_params.get('include') == 'archived'
        base_qs = circle.invitations.select_related('invited_user').order_by('-created_at')
        if not include_archived:
            base_qs = base_qs.filter(status=CircleInvitationStatus.PENDING)
        invitations = base_qs
        data = CircleInvitationSerializer(invitations, many=True).data
        return success_response({'invitations': data})
    @extend_schema(
        description='Invite a new member to join a circle via username or email. Existing users receive a pending invitation and must accept before joining.',
        request=CircleInvitationCreateSerializer,
        responses={
            202: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='Invitation created and notification queued.',
            )
        },
    )
    def post(self, request, circle_id):
        circle = get_object_or_404(Circle, id=circle_id)
        membership = CircleMembership.objects.filter(circle=circle, user=request.user).first()
        if not membership or membership.role != UserRole.CIRCLE_ADMIN:
            raise PermissionDenied(_('Only circle admins can invite members'))
        serializer = CircleInvitationCreateSerializer(data=request.data, context={'circle': circle})
        serializer.is_valid(raise_exception=True)
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
        invitation = CircleInvitation.objects.create(
            circle=circle,
            email=serializer.validated_data['email'],
            invited_by=request.user,
            invited_user=serializer.validated_data.get('invited_user'),
            role=serializer.validated_data['role'],
        )
        token = store_token(
            'circle-invite',
            {
                'invitation_id': str(invitation.id),
                'circle_id': circle.id,
                'email': invitation.email,
                'role': invitation.role,
                'issued_at': timezone.now().isoformat(),
                'existing_user': bool(invitation.invited_user_id),
                'invited_user_id': invitation.invited_user_id,
            },
            ttl=TOKEN_TTL_SECONDS,
        )
        send_email_task.delay(
            to_email=invitation.email,
            template_id=CIRCLE_INVITATION_TEMPLATE,
            context={
                'token': token,
                'email': invitation.email,
                'circle_name': circle.name,
                'invited_by': request.user.username,
                'invitation_link': self._build_invitation_link(token),
            },
        )
        data = CircleInvitationSerializer(invitation).data
        return success_response(
            {'invitation': data},
            messages=[create_message('notifications.circle.invitation_sent')],
            status_code=status.HTTP_202_ACCEPTED
        )
    @staticmethod
    def _build_invitation_link(token: str) -> str:
        base_url = getattr(settings, 'ACCOUNT_FRONTEND_BASE_URL', 'http://localhost:3000') or 'http://localhost:3000'
        base_url = base_url.rstrip('/')
        return f"{base_url}/invitations/accept?token={token}"
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
        circle = get_object_or_404(Circle, id=circle_id)
        membership = CircleMembership.objects.filter(circle=circle, user=request.user).first()
        if not membership or membership.role != UserRole.CIRCLE_ADMIN:
            raise PermissionDenied(_('Only circle admins can manage invitations'))
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
        circle = get_object_or_404(Circle, id=circle_id)
        membership = CircleMembership.objects.filter(circle=circle, user=request.user).first()
        if not membership or membership.role != UserRole.CIRCLE_ADMIN:
            raise PermissionDenied(_('Only circle admins can manage invitations'))
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
        token = store_token(
            'circle-invite',
            {
                'invitation_id': str(invitation.id),
                'circle_id': circle.id,
                'email': invitation.email,
                'role': invitation.role,
                'issued_at': timezone.now().isoformat(),
                'existing_user': bool(invitation.invited_user_id),
                'invited_user_id': invitation.invited_user_id,
            },
            ttl=TOKEN_TTL_SECONDS,
        )
        invitation_link = CircleInvitationCreateView._build_invitation_link(token)
        base_context = {
            'circle_name': circle.name,
            'invited_by': invitation.invited_by.username if invitation.invited_by_id else request.user.username,
            'invitation_link': invitation_link,
        }
        send_email_task.delay(
            to_email=invitation.email,
            template_id=CIRCLE_INVITATION_TEMPLATE,
            context={**base_context, 'token': token, 'email': invitation.email},
        )
        invitation.reminder_sent_at = timezone.now()
        invitation.save(update_fields=['reminder_sent_at'])
        data = CircleInvitationSerializer(invitation).data
        return success_response(
            {'invitation': data},
            messages=[create_message('notifications.circle.invitation_sent')],
            status_code=status.HTTP_202_ACCEPTED,
        )
    if getattr(settings, 'RATELIMIT_ENABLE', True):
        post = method_decorator(
            ratelimit(
                key='user',
                rate=getattr(settings, 'CIRCLE_INVITE_RESEND_RATELIMIT', '5/15m'),
                method='POST',
                block=True,
            )
        )(post)
class CircleInvitationListView(APIView):
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
        invitations = CircleInvitation.objects.filter(
            email__iexact=request.user.email,
            status=CircleInvitationStatus.PENDING,
        ).select_related('circle')
        data = CircleInvitationSerializer(invitations, many=True).data
        return success_response({'invitations': data})
class CircleInvitationRespondView(APIView):
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
        serializer = CircleInvitationOnboardingStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = pop_token('circle-invite', serializer.validated_data['token'])
        if not payload:
            return error_response(
                'token_invalid_expired',
                [create_message('errors.token_invalid_expired')],
                status.HTTP_400_BAD_REQUEST
            )
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
        if invitation.email.lower() != payload.get('email', '').lower():
            return error_response(
                'invitation_mismatch',
                [create_message('errors.invitation_mismatch')],
                status.HTTP_400_BAD_REQUEST
            )
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
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]
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
        serializer = CircleInvitationFinalizeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = pop_token('circle-invite-onboarding', serializer.validated_data['onboarding_token'])
        if not payload:
            return error_response(
                'token_invalid_expired',
                [create_message('errors.token_invalid_expired')],
                status.HTTP_400_BAD_REQUEST
            )
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
        user = request.user
        email_match = user.email and user.email.lower() == invitation.email.lower()
        invited_match = invitation.invited_user_id == user.id
        if not email_match and not invited_match:
            return error_response(
                'invitation_mismatch',
                [create_message('errors.invitation_mismatch')],
                status.HTTP_403_FORBIDDEN
            )
        with transaction.atomic():
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
        if invitation.invited_by_id:
            base_url = getattr(settings, 'ACCOUNT_FRONTEND_BASE_URL', 'http://localhost:3000').rstrip('/')
            send_email_task.delay(
                to_email=invitation.invited_by.email,
                template_id=CIRCLE_INVITATION_ACCEPTED_TEMPLATE,
                context={
                    'circle_name': invitation.circle.name,
                    'invited_by': invitation.invited_by.username,
                    'invitee_name': user.username,
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
__all__ = [
    'CircleInvitationCreateView',
    'CircleInvitationCancelView',
    'CircleInvitationResendView',
    'CircleInvitationListView',
    'CircleInvitationRespondView',
    'CircleInvitationAcceptView',
    'CircleInvitationFinalizeView',
]
