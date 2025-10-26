"""Email verification views."""
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
from mysite.emails.templates import EMAIL_VERIFICATION_TEMPLATE
from mysite.notification_utils import create_message, error_response, rate_limit_response, success_response
from mysite.users.models import User
from mysite.users.serializers import PublicUserSerializer

from ..serializers import EmailVerificationConfirmSerializer
from ..services import EmailVerificationError, EmailVerificationService
from ..token_utils import pop_token, set_refresh_cookie, store_token
from .constants import (
    EMAIL_VERIFICATION_CONFIRM_RATE,
    EMAIL_VERIFICATION_RESEND_RATE,
    EMAIL_VERIFICATION_TOKEN_TTL_SECONDS,
)

logger = logging.getLogger(__name__)


class EmailVerificationResendView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        description='Request that a new email verification message be sent to the authenticated user.',
        responses={202: OpenApiResponse(response=OpenApiTypes.OBJECT, description='Verification email scheduled')},
    )
    @method_decorator(ratelimit(
        key='ip',
        rate=EMAIL_VERIFICATION_RESEND_RATE,
        method='POST',
        block=False,
    ))
    @method_decorator(ratelimit(
        key='user',
        rate=EMAIL_VERIFICATION_RESEND_RATE,
        method='POST',
        block=False,
    ))
    def post(self, request):
        if getattr(request, 'limited', False):
            return rate_limit_response('errors.rate_limit')
        user = request.user
        if user.email_verified:
            return success_response(
                {},
                messages=[create_message('notifications.auth.email_verification_sent')],
                status_code=status.HTTP_200_OK,
            )
        token = store_token(
            'verify-email',
            {'user_id': user.id, 'issued_at': timezone.now().isoformat()},
            ttl=EMAIL_VERIFICATION_TOKEN_TTL_SECONDS,
        )
        base_url = (getattr(settings, 'ACCOUNT_FRONTEND_BASE_URL', 'http://localhost:3000') or 'http://localhost:3000').rstrip('/')
        verification_link = f"{base_url}/verify-email?{urlencode({'token': token})}"
        expires_in_minutes = max(1, math.ceil(EMAIL_VERIFICATION_TOKEN_TTL_SECONDS / 60))

        send_email_task.delay(
            to_email=user.email,
            template_id=EMAIL_VERIFICATION_TEMPLATE,
            context={
                'token': token,
                'email': user.email,
                'full_name': user.display_name,
                'verification_link': verification_link,
                'verification_expires_in_minutes': expires_in_minutes,
            },
        )
        with project_logging.log_context(user_id=user.id):
            logger.info(
                'Email verification message scheduled',
                extra={
                    'event': 'auth.email_verification.resent',
                    'extra': {'user_id': user.id},
                },
            )
            log_security_event(
                'user.email_verification.resent',
                actor_id=str(user.id),
                status='pending',
                severity='notice',
                metadata={'delivery_method': 'email'},
            )
        return success_response(
            {},
            messages=[create_message('notifications.auth.email_verification_sent')],
            status_code=status.HTTP_202_ACCEPTED
        )


class EmailVerificationConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = EmailVerificationConfirmSerializer
    service_class = EmailVerificationService
    redirect_path = '/circles/onboarding'

    @extend_schema(
        description='Confirm email ownership using a verification token.',
        request=EmailVerificationConfirmSerializer,
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT, description='Email successfully verified')},
    )
    @method_decorator(ratelimit(
        key='ip',
        rate=EMAIL_VERIFICATION_CONFIRM_RATE,
        method='POST',
        block=False,
    ))
    @method_decorator(ratelimit(
        key='post:token',
        rate=EMAIL_VERIFICATION_CONFIRM_RATE,
        method='POST',
        block=False,
    ))
    def post(self, request):
        if getattr(request, 'limited', False):
            return rate_limit_response('errors.rate_limit')
        serializer = EmailVerificationConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = pop_token('verify-email', serializer.validated_data['token'])
        if not payload:
            logger.warning(
                'Email verification token invalid or expired',
                extra={'event': 'auth.email_verification.invalid_token'},
            )
            return error_response(
                'invalid_token',
                [create_message('errors.token_invalid_expired')],
                status.HTTP_400_BAD_REQUEST
            )
        user = User.objects.filter(id=payload['user_id']).first()
        if not user:
            logger.warning(
                'Email verification target user missing',
                extra={
                    'event': 'auth.email_verification.user_missing',
                    'extra': {'user_id': payload.get('user_id')},
                },
            )
            return error_response(
                'user_not_found',
                [create_message('errors.user_not_found')],
                status.HTTP_404_NOT_FOUND
            )
        service = self.service_class()
        try:
            access_token, refresh_token = service.verify_and_login(user)
        except EmailVerificationError as exc:
            logger.warning(
                'Email verification validation failed',
                extra={'event': 'auth.email_verification.failed', 'extra': {'user_id': user.id}},
            )
            return error_response(
                'email_verification_failed',
                [create_message('errors.email_verification_failed', {'message': str(exc)})],
                status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            logger.error(
                'Email verification service error',
                extra={'event': 'auth.email_verification.error', 'extra': {'user_id': user.id}},
                exc_info=True,
            )
            return error_response(
                'email_verification_failed',
                [create_message('errors.email_verification_failed')],
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        client_ip = self._get_client_ip(request)
        with project_logging.log_context(user_id=user.id):
            logger.info(
                'Email verification confirmed with auto-login',
                extra={'event': 'auth.email_verification.confirmed', 'extra': {'user_id': user.id, 'ip': client_ip}},
            )
            log_audit_event(
                AuditEvent(
                    action='user.email_verified',
                    actor_id=str(user.id),
                    target_id=str(user.id),
                    status='success',
                    severity='info',
                    metadata={'auto_login': True, 'ip': client_ip},
                )
            )

        response = success_response(
            {
                'user': PublicUserSerializer(user).data,
                'access_token': access_token,
                'redirect_url': self.redirect_path,
            },
            messages=[create_message('notifications.auth.email_verified')]
        )
        set_refresh_cookie(response, refresh_token)
        return response

    @staticmethod
    def _get_client_ip(request):
        forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
