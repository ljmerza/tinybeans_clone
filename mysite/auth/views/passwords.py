"""Password lifecycle views."""
from __future__ import annotations

import logging
import math
from urllib.parse import urlencode

from django.conf import settings
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import OpenApiResponse, OpenApiTypes, extend_schema
from rest_framework import permissions, status
from rest_framework.views import APIView

from mysite import project_logging
from mysite.audit import AuditEvent, log_audit_event, log_security_event
from mysite.emails.tasks import send_email_task
from mysite.emails.templates import PASSWORD_RESET_TEMPLATE
from mysite.notification_utils import create_message, error_response, rate_limit_response, success_response
from mysite.users.models import User

from ..permissions import IsEmailVerified
from ..serializers import (
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
)
from ..token_utils import (
    TOKEN_TTL_SECONDS,
    get_tokens_for_user,
    pop_token,
    set_refresh_cookie,
    store_token,
)
from .constants import PASSWORD_RESET_CONFIRM_RATE, PASSWORD_RESET_RATE

logger = logging.getLogger(__name__)


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetRequestSerializer

    @extend_schema(
        description='Initiate the password reset flow for a user by email.',
        request=PasswordResetRequestSerializer,
        responses={202: OpenApiResponse(response=OpenApiTypes.OBJECT, description='Password reset email scheduled')},
    )
    @method_decorator(ratelimit(
        key='ip',
        rate=PASSWORD_RESET_RATE,
        method='POST',
        block=False,
    ))
    @method_decorator(ratelimit(
        key='post:identifier',
        rate=PASSWORD_RESET_RATE,
        method='POST',
        block=False,
    ))
    def post(self, request):
        if getattr(request, 'limited', False):
            logger.warning(
                'Password reset request rate limited',
                extra={'event': 'auth.password_reset.rate_limited'},
            )
            return rate_limit_response('errors.rate_limit')
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        if user:
            token = store_token(
                'password-reset',
                {'user_id': user.id, 'issued_at': timezone.now().isoformat()},
                ttl=TOKEN_TTL_SECONDS,
            )
            base_url = (getattr(settings, 'ACCOUNT_FRONTEND_BASE_URL', 'http://localhost:3000') or 'http://localhost:3000').rstrip('/')
            reset_link = f"{base_url}/password/reset/confirm?{urlencode({'token': token})}"
            expires_in_minutes = max(1, math.ceil(TOKEN_TTL_SECONDS / 60))
            send_email_task.delay(
                to_email=user.email,
                template_id=PASSWORD_RESET_TEMPLATE,
                context={
                    'token': token,
                    'email': user.email,
                    'full_name': user.display_name,
                    'reset_link': reset_link,
                    'expires_in_minutes': expires_in_minutes,
                },
            )
            with project_logging.log_context(user_id=user.id):
                logger.info(
                    'Password reset email scheduled',
                    extra={
                        'event': 'auth.password_reset.requested',
                        'extra': {'user_id': user.id},
                    },
                )
                log_security_event(
                    'user.password_reset.requested',
                    actor_id=str(user.id),
                    status='pending',
                    severity='warning',
                )
        else:
            logger.info(
                'Password reset requested for unknown identifier',
                extra={'event': 'auth.password_reset.unknown_user'},
            )
        return success_response(
            {},
            messages=[create_message('notifications.auth.password_reset')],
            status_code=status.HTTP_202_ACCEPTED
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    @extend_schema(
        description='Complete a password reset using a valid reset token.',
        request=PasswordResetConfirmSerializer,
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT, description='Password reset completed')},
    )
    @method_decorator(ratelimit(
        key='ip',
        rate=PASSWORD_RESET_CONFIRM_RATE,
        method='POST',
        block=False,
    ))
    @method_decorator(ratelimit(
        key='post:token',
        rate=PASSWORD_RESET_CONFIRM_RATE,
        method='POST',
        block=False,
    ))
    def post(self, request):
        if getattr(request, 'limited', False):
            logger.warning(
                'Password reset confirmation rate limited',
                extra={'event': 'auth.password_reset_confirm.rate_limited'},
            )
            return rate_limit_response('errors.rate_limit')
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = pop_token('password-reset', serializer.validated_data['token'])
        if not payload:
            logger.warning(
                'Password reset token invalid or expired',
                extra={'event': 'auth.password_reset.invalid_token'},
            )
            return error_response(
                'invalid_token',
                [create_message('errors.token_invalid_expired')],
                status.HTTP_400_BAD_REQUEST
            )
        user = User.objects.filter(id=payload['user_id']).first()
        if not user:
            logger.warning(
                'Password reset target user missing',
                extra={
                    'event': 'auth.password_reset.user_missing',
                    'extra': {'user_id': payload.get('user_id')},
                },
            )
            return error_response(
                'user_not_found',
                [create_message('errors.user_not_found')],
                status.HTTP_404_NOT_FOUND
            )
        user.set_password(serializer.validated_data['password'])
        user.save(update_fields=['password'])
        with project_logging.log_context(user_id=user.id):
            logger.info(
                'Password reset completed',
                extra={
                    'event': 'auth.password_reset.success',
                    'extra': {'user_id': user.id},
                },
            )
            log_audit_event(
                AuditEvent(
                    action='user.password_reset',
                    actor_id=str(user.id),
                    target_id=str(user.id),
                    status='success',
                    severity='warning',
                )
            )
            log_security_event(
                'user.password_reset.success',
                actor_id=str(user.id),
                status='success',
                severity='warning',
            )
        return success_response(
            {},
            messages=[create_message('notifications.auth.password_updated')]
        )


class PasswordChangeView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]
    serializer_class = PasswordChangeSerializer

    @extend_schema(
        description='Allow an authenticated user to change their password and rotate tokens (refresh token stored in HTTP-only cookie).',
        request=PasswordChangeSerializer,
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT, description='Password changed successfully with new tokens')},
    )
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data['password'])
        user.save(update_fields=['password'])
        tokens = get_tokens_for_user(user)

        with project_logging.log_context(user_id=user.id):
            logger.info(
                'Password changed by authenticated user',
                extra={
                    'event': 'auth.password_change.success',
                    'extra': {'user_id': user.id},
                },
            )
            log_audit_event(
                AuditEvent(
                    action='user.password_change',
                    actor_id=str(user.id),
                    target_id=str(user.id),
                    status='success',
                    severity='info',
                )
            )
            log_security_event(
                'user.password_change.success',
                actor_id=str(user.id),
                status='success',
                severity='info',
            )

        data = {'tokens': {'access': tokens['access']}}
        response = success_response(
            data,
            messages=[create_message('notifications.auth.password_updated')],
            status_code=status.HTTP_200_OK
        )
        set_refresh_cookie(response, tokens['refresh'])
        return response
