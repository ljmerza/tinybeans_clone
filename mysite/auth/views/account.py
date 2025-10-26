"""Account creation, session management, and CSRF helpers."""
from __future__ import annotations

import logging
import math
from urllib.parse import urlencode

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import OpenApiResponse, OpenApiTypes, extend_schema
from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

from mysite import project_logging
from mysite.audit import AuditEvent, log_audit_event, log_security_event
from mysite.emails.tasks import send_email_task
from mysite.emails.templates import EMAIL_VERIFICATION_TEMPLATE
from mysite.notification_utils import create_message, error_response, rate_limit_response, success_response
from mysite.users.serializers import UserSerializer

from ..serializers import LoginSerializer, SignupSerializer
from ..token_utils import (
    REFRESH_COOKIE_NAME,
    clear_refresh_cookie,
    get_tokens_for_user,
    set_refresh_cookie,
    store_token,
)
from .constants import EMAIL_VERIFICATION_TOKEN_TTL_SECONDS

logger = logging.getLogger(__name__)


class SignupView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = SignupSerializer

    @extend_schema(
        description='Register a new account and receive an access token (refresh token stored as an HTTP-only cookie). Email verification is required before creating circles.',
        request=SignupSerializer,
        responses={
            201: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='Signup successful; returns created user, tokens, and verification token.',
            )
        },
    )
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        verification_token = store_token(
            'verify-email',
            {'user_id': user.id, 'issued_at': timezone.now().isoformat()},
            ttl=EMAIL_VERIFICATION_TOKEN_TTL_SECONDS,
        )

        base_url = (getattr(settings, 'ACCOUNT_FRONTEND_BASE_URL', 'http://localhost:3000') or 'http://localhost:3000').rstrip('/')
        verification_link = f"{base_url}/verify-email?{urlencode({'token': verification_token})}"
        expires_in_minutes = max(1, math.ceil(EMAIL_VERIFICATION_TOKEN_TTL_SECONDS / 60))

        send_email_task.delay(
            to_email=user.email,
            template_id=EMAIL_VERIFICATION_TEMPLATE,
            context={
                'token': verification_token,
                'email': user.email,
                'full_name': user.display_name,
                'verification_link': verification_link,
                'verification_expires_in_minutes': expires_in_minutes,
            },
        )

        tokens = get_tokens_for_user(user)
        user_data = UserSerializer(user).data
        user_data['tokens'] = {'access': tokens['access']}

        with project_logging.log_context(user_id=user.id):
            logger.info(
                'User signup completed',
                extra={
                    'event': 'auth.signup.success',
                    'extra': {
                        'user_id': user.id,
                        'email_domain': user.email.split('@')[-1] if user.email and '@' in user.email else None,
                    },
                },
            )
            log_audit_event(
                AuditEvent(
                    action='user.signup',
                    actor_id=str(user.id),
                    target_id=str(user.id),
                    severity='info',
                    metadata={'has_verified_email': False},
                )
            )

        response_data = success_response(
            user_data,
            messages=[create_message('notifications.auth.signup_success')],
            status_code=status.HTTP_201_CREATED
        )
        set_refresh_cookie(response_data, tokens['refresh'])
        return response_data


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    @extend_schema(
        description='Authenticate with email/password and receive an access token (refresh token stored in HTTP-only cookie). If 2FA is enabled, returns requires_2fa flag and partial token.',
        request=LoginSerializer,
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT, description='JWT tokens and user payload or 2FA required response')},
    )
    @method_decorator(ratelimit(key='ip', rate='10/h', method='POST', block=True))
    @method_decorator(ratelimit(key='post:email', rate='5/h', method='POST', block=True))
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        with project_logging.log_context(user_id=user.id):
            logger.info(
                'Credentials validated for login request',
                extra={
                    'event': 'auth.login.credentials_valid',
                    'extra': {'user_id': user.id},
                },
            )

            # Check if 2FA is enabled for this user
            try:
                from ..models import TwoFactorSettings
                from ..services.twofa_service import TwoFactorService
                from ..services.trusted_device_service import TrustedDeviceService

                twofa_settings = user.twofa_settings

                if twofa_settings.is_enabled:
                    # Check if account is locked
                    if twofa_settings.is_locked():
                        log_security_event(
                            'user.login.locked',
                            actor_id=str(user.id),
                            status='denied',
                            severity='warning',
                            metadata={'reason': 'twofa_locked'},
                        )
                        return error_response(
                            'account_locked',
                            [create_message('errors.account_locked_2fa', {
                                'retry_after': 'later'
                            })],
                            status.HTTP_429_TOO_MANY_REQUESTS
                        )

                    # Check if device is trusted (Remember Me feature)
                    device_token = TrustedDeviceService.get_device_id_from_request(request)

                    is_trusted, rotated_token = TrustedDeviceService.is_trusted_device(
                        user,
                        device_token,
                        request,
                    ) if device_token else (False, None)

                    if is_trusted:
                        tokens = get_tokens_for_user(user)
                        user_data = UserSerializer(user).data
                        user_data['tokens'] = {'access': tokens['access']}
                        user_data['trusted_device'] = True

                        log_audit_event(
                            AuditEvent(
                                action='user.login',
                                actor_id=str(user.id),
                                target_id=str(user.id),
                                status='success',
                                severity='info',
                                metadata={'trusted_device': True},
                            )
                        )
                        log_security_event(
                            'user.login.success',
                            actor_id=str(user.id),
                            status='success',
                            severity='info',
                            metadata={'trusted_device': True},
                        )
                        with project_logging.log_context(trusted_device=True):
                            logger.info(
                                'Login succeeded via trusted device',
                                extra={
                                    'event': 'auth.login.trusted_device',
                                    'extra': {'user_id': user.id},
                                },
                            )

                        response_data = success_response(
                            user_data,
                            messages=[create_message('notifications.auth.login_success')]
                        )
                        set_refresh_cookie(response_data, tokens['refresh'])
                        if rotated_token:
                            TrustedDeviceService.set_trusted_device_cookie(response_data, rotated_token)
                        return response_data

                    # 2FA required
                    if TwoFactorService.is_rate_limited(user):
                        return rate_limit_response('errors.rate_limit_2fa')

                    if twofa_settings.preferred_method in ['email', 'sms']:
                        TwoFactorService.send_otp(
                            user,
                            method=twofa_settings.preferred_method,
                            purpose='login'
                        )

                    from ..token_utils import generate_partial_token
                    partial_token = generate_partial_token(user, request)

                    message_key = 'notifications.twofa.code_sent' if twofa_settings.preferred_method != 'totp' else 'notifications.twofa.enter_authenticator_code'
                    return success_response(
                        {
                            'requires_2fa': True,
                            'method': twofa_settings.preferred_method,
                            'partial_token': partial_token,
                        },
                        messages=[create_message(message_key, {'method': twofa_settings.preferred_method})]
                    )

            except TwoFactorSettings.DoesNotExist:
                logger.info(
                    'Two-factor settings not found; continuing without 2FA enforcement',
                    extra={'event': 'auth.login.twofa_not_configured', 'extra': {'user_id': user.id}},
                )

        tokens = get_tokens_for_user(user)
        user_data = UserSerializer(user).data
        user_data['tokens'] = {'access': tokens['access']}

        log_audit_event(
            AuditEvent(
                action='user.login',
                actor_id=str(user.id),
                target_id=str(user.id),
                status='success',
                severity='info',
                metadata={'twofa_enforced': False},
            )
        )
        log_security_event(
            'user.login.success',
            actor_id=str(user.id),
            status='success',
            severity='info',
            metadata={'twofa_enforced': False},
        )
        logger.info(
            'Login succeeded',
            extra={
                'event': 'auth.login.success',
                'extra': {'user_id': user.id, 'twofa_enforced': False},
            },
        )

        response_data = success_response(
            user_data,
            messages=[create_message('notifications.auth.login_success')]
        )
        set_refresh_cookie(response_data, tokens['refresh'])
        return response_data


class TokenRefreshCookieView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        description='Obtain a new access token using the refresh token stored in the HTTP-only cookie.',
        request=None,
        responses={
            200: OpenApiResponse(response=OpenApiTypes.OBJECT, description='New access token issued.'),
            401: OpenApiResponse(description='Missing or invalid refresh token cookie.'),
        },
    )
    def post(self, request):
        refresh_token = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if not refresh_token:
            logger.warning(
                'Refresh token cookie missing for refresh request',
                extra={'event': 'auth.token_refresh.missing_cookie'},
            )
            return error_response(
                'refresh_token_missing',
                [create_message('errors.token_invalid_expired', {})],
                status.HTTP_401_UNAUTHORIZED
            )

        serializer = TokenRefreshSerializer(data={'refresh': refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError:
            logger.warning(
                'Refresh token invalid or expired',
                extra={'event': 'auth.token_refresh.invalid_token'},
            )
            response = error_response(
                'invalid_refresh_token',
                [create_message('errors.token_invalid_expired', {})],
                status.HTTP_401_UNAUTHORIZED
            )
            clear_refresh_cookie(response)
            return response
        except Exception as e:
            from mysite.users.models import User
            if isinstance(e.__cause__, User.DoesNotExist):
                logger.warning(
                    'Refresh token belongs to deleted user',
                    extra={'event': 'auth.token_refresh.user_deleted'},
                )
                response = error_response(
                    'invalid_refresh_token',
                    [create_message('errors.token_invalid_expired', {})],
                    status.HTTP_401_UNAUTHORIZED
                )
                clear_refresh_cookie(response)
                return response
            raise

        data = serializer.validated_data
        access_token = data['access']
        new_refresh = data.get('refresh', refresh_token)

        response = success_response({'access': access_token})
        set_refresh_cookie(response, new_refresh)
        logger.info('Refresh token rotated', extra={'event': 'auth.token_refresh.success'})
        return response


class LogoutView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        description='Clear the refresh token cookie to log out the user.',
        request=None,
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT, description='Logged out successfully')},
    )
    def post(self, request):
        response = success_response(
            {},
            messages=[create_message('notifications.auth.logout_success')],
            status_code=status.HTTP_200_OK
        )
        clear_refresh_cookie(response)
        user_id = getattr(getattr(request, 'user', None), 'id', None)
        with project_logging.log_context(user_id=user_id):
            logger.info(
                'User logged out',
                extra={
                    'event': 'auth.logout.success',
                    'extra': {'user_id': user_id},
                },
            )
            if user_id is not None:
                log_audit_event(
                    AuditEvent(
                        action='user.logout',
                        actor_id=str(user_id),
                        target_id=str(user_id),
                        status='success',
                        severity='info',
                    )
                )
        return response


@ensure_csrf_cookie
def get_csrf_token(request):
    """
    Endpoint to set CSRF cookie for the frontend.
    Call this endpoint before making any POST requests to get the CSRF token.
    """
    return JsonResponse({'detail': 'CSRF cookie set'})
