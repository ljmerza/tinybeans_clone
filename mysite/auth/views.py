"""Authentication and account lifecycle views."""
from __future__ import annotations

import logging
import math
from urllib.parse import urlencode

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from drf_spectacular.utils import OpenApiResponse, OpenApiTypes, extend_schema
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator

from mysite.users.models import User
from mysite.users.serializers import PublicUserSerializer, UserSerializer
from mysite.emails.tasks import send_email_task
from mysite.emails.templates import EMAIL_VERIFICATION_TEMPLATE, PASSWORD_RESET_TEMPLATE
from .token_utils import (
    REFRESH_COOKIE_NAME,
    TOKEN_TTL_SECONDS,
    clear_refresh_cookie,
    get_tokens_for_user,
    set_refresh_cookie,
    pop_token,
    store_token,
    generate_partial_token,
    hash_magic_login_token,
)
from mysite.auth.permissions import IsEmailVerified
from mysite.auth.services import EmailVerificationError, EmailVerificationService

from .serializers import (
    EmailVerificationConfirmSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    SignupSerializer,
    MagicLoginRequestSerializer,
    MagicLoginVerifySerializer,
)
from mysite import project_logging
from mysite.audit import AuditEvent, log_audit_event, log_security_event
from mysite.notification_utils import create_message, success_response, error_response, rate_limit_response


logger = logging.getLogger(__name__)


def _rate_from_settings(setting_name: str, default: str):
    def _rate(group, request):
        return getattr(settings, setting_name, default)
    return _rate


PASSWORD_RESET_RATE = _rate_from_settings('PASSWORD_RESET_RATELIMIT', '5/15m')
PASSWORD_RESET_CONFIRM_RATE = _rate_from_settings('PASSWORD_RESET_CONFIRM_RATELIMIT', '10/15m')
EMAIL_VERIFICATION_RESEND_RATE = _rate_from_settings('EMAIL_VERIFICATION_RESEND_RATELIMIT', '5/15m')
EMAIL_VERIFICATION_CONFIRM_RATE = _rate_from_settings('EMAIL_VERIFICATION_CONFIRM_RATELIMIT', '10/15m')
EMAIL_VERIFICATION_TOKEN_TTL_SECONDS = getattr(
    settings,
    'EMAIL_VERIFICATION_TOKEN_TTL_SECONDS',
    48 * 60 * 60,
)


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

        # Use new notification format per ADR-012
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
                from .models import TwoFactorSettings
                from .services.twofa_service import TwoFactorService
                from .services.trusted_device_service import TrustedDeviceService

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

                    # 2FA required - check rate limiting
                    if TwoFactorService.is_rate_limited(user):
                        log_security_event(
                            'user.login.rate_limited',
                            actor_id=str(user.id),
                            status='denied',
                            severity='warning',
                            metadata={'reason': 'twofa_rate_limit'},
                        )
                        return error_response(
                            'rate_limit_exceeded',
                            [create_message('errors.rate_limit_2fa')],
                            status.HTTP_429_TOO_MANY_REQUESTS
                        )

                    # Send 2FA code based on preferred method
                    if twofa_settings.preferred_method in ['email', 'sms']:
                        TwoFactorService.send_otp(
                            user,
                            method=twofa_settings.preferred_method,
                            purpose='login'
                        )
                        with project_logging.log_context(twofa_method=twofa_settings.preferred_method):
                            logger.info(
                                '2FA OTP sent for login',
                                extra={
                                    'event': 'auth.login.2fa_sent',
                                    'extra': {
                                        'user_id': user.id,
                                        'method': twofa_settings.preferred_method,
                                    },
                                },
                            )

                    partial_token = generate_partial_token(user, request)

                    log_security_event(
                        'user.login.challenge',
                        actor_id=str(user.id),
                        status='pending',
                        severity='notice',
                        metadata={'method': twofa_settings.preferred_method},
                    )
                    return success_response(
                        {
                            'requires_2fa': True,
                            'method': twofa_settings.preferred_method,
                            'partial_token': partial_token,
                        },
                        messages=[create_message(
                            'notifications.twofa.code_sent' if twofa_settings.preferred_method != 'totp' else 'notifications.twofa.enter_authenticator_code',
                            {'method': twofa_settings.preferred_method}
                        )]
                    )

            except TwoFactorSettings.DoesNotExist:
                # No 2FA configured - proceed with normal login
                pass

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
            # Handle case where user was deleted but token still exists
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
            # Re-raise if it's a different exception
            raise

        data = serializer.validated_data
        access_token = data['access']
        new_refresh = data.get('refresh', refresh_token)

        response = success_response({'access': access_token})
        set_refresh_cookie(response, new_refresh)
        logger.info('Refresh token rotated', extra={'event': 'auth.token_refresh.success'})
        return response


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
        except Exception as exc:
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
        # Always return success to prevent email enumeration
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


class MagicLoginRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = MagicLoginRequestSerializer

    @extend_schema(
        description='Request a magic login link to be sent via email.',
        request=MagicLoginRequestSerializer,
        responses={202: OpenApiResponse(response=OpenApiTypes.OBJECT, description='Magic login link email scheduled')},
    )
    @method_decorator(ratelimit(key='ip', rate='5/h', method='POST', block=True))
    def post(self, request):
        serializer = MagicLoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data.get('user')
        
        if user:
            import uuid
            from datetime import timedelta
            from .models import MagicLoginToken
            from .token_utils import get_client_ip
            
            # Generate unique token
            token = uuid.uuid4().hex
            token_hash = hash_magic_login_token(token)
            
            # Create magic login token with 15-minute expiry
            magic_token = MagicLoginToken.objects.create(
                user=user,
                token_hash=token_hash,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                expires_at=timezone.now() + timedelta(minutes=15)
            )
            
            # Send email with magic link
            base_url = (getattr(settings, 'ACCOUNT_FRONTEND_BASE_URL', 'http://localhost:3000') or 'http://localhost:3000').rstrip('/')
            magic_link = f"{base_url}/magic-login?{urlencode({'token': token})}"
            
            send_email_task.delay(
                to_email=user.email,
                template_id='users.magic.login',
                context={
                    'token': token,
                    'email': user.email,
                    'full_name': user.display_name,
                    'magic_link': magic_link,
                    'expires_in_minutes': 15,
                },
            )
        
        # Always return success to prevent email enumeration
        return success_response(
            {},
            messages=[create_message('notifications.auth.magic_link_sent')],
            status_code=status.HTTP_202_ACCEPTED
        )


class MagicLoginVerifyView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = MagicLoginVerifySerializer

    @extend_schema(
        description='Verify a magic login token and authenticate the user.',
        request=MagicLoginVerifySerializer,
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT, description='Login successful with JWT tokens')},
    )
    @method_decorator(ratelimit(key='ip', rate='10/h', method='POST', block=True))
    def post(self, request):
        serializer = MagicLoginVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        from .models import MagicLoginToken
        
        token_value = serializer.validated_data['token']
        
        token_hash = hash_magic_login_token(token_value)
        
        try:
            magic_token = MagicLoginToken.objects.select_related('user').get(token_hash=token_hash)
            
            if not magic_token.is_valid():
                return error_response(
                    'magic_link_expired',
                    [create_message('errors.magic_link_expired')],
                    status.HTTP_400_BAD_REQUEST
                )
            
            # Mark token as used
            magic_token.mark_as_used()
            
            user = magic_token.user
            
            # Check if user account is active
            if not user.is_active:
                return error_response(
                    'account_inactive',
                    [create_message('errors.account_inactive')],
                    status.HTTP_403_FORBIDDEN
                )
            
            # Check if 2FA is enabled for this user
            try:
                from .models import TwoFactorSettings
                from .services.twofa_service import TwoFactorService
                from .services.trusted_device_service import TrustedDeviceService
                
                twofa_settings = user.twofa_settings
                
                if twofa_settings.is_enabled:
                    # Check if account is locked
                    if twofa_settings.is_locked():
                        return rate_limit_response('errors.account_locked_2fa')
                    
                    # Check if device is trusted
                    device_token = TrustedDeviceService.get_device_id_from_request(request)
                    is_trusted, rotated_token = TrustedDeviceService.is_trusted_device(
                        user,
                        device_token,
                        request,
                    ) if device_token else (False, None)
                    
                    if is_trusted:
                        # Trusted device - proceed with login
                        tokens = get_tokens_for_user(user)
                        data = {
                            'user': UserSerializer(user).data,
                            'tokens': {'access': tokens['access']},
                            'trusted_device': True,
                        }
                        response = success_response(
                            data,
                            messages=[create_message('notifications.auth.magic_login_success')],
                            status_code=status.HTTP_200_OK
                        )
                        set_refresh_cookie(response, tokens['refresh'])
                        if rotated_token:
                            TrustedDeviceService.set_trusted_device_cookie(response, rotated_token)
                        return response
                    
                    # 2FA required - check rate limiting
                    if TwoFactorService.is_rate_limited(user):
                        return rate_limit_response('errors.rate_limit_2fa')
                    
                    # Send 2FA code based on preferred method
                    if twofa_settings.preferred_method in ['email', 'sms']:
                        TwoFactorService.send_otp(
                            user,
                            method=twofa_settings.preferred_method,
                            purpose='login'
                        )
                    
                    # Generate partial token for 2FA verification
                    from .token_utils import generate_partial_token
                    partial_token = generate_partial_token(user, request)
                    
                    # Return 2FA required response with i18n message
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
                # No 2FA configured - proceed with normal login
                pass
            
            # Generate JWT tokens and login
            tokens = get_tokens_for_user(user)
            data = {
                'user': UserSerializer(user).data,
                'tokens': {'access': tokens['access']},
            }
            response = success_response(
                data,
                messages=[create_message('notifications.auth.magic_login_success')],
                status_code=status.HTTP_200_OK
            )
            set_refresh_cookie(response, tokens['refresh'])
            return response
            
        except MagicLoginToken.DoesNotExist:
            return error_response(
                'magic_link_invalid',
                [create_message('errors.magic_link_invalid')],
                status.HTTP_400_BAD_REQUEST
            )
