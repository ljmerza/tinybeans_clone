"""Authentication and account lifecycle views."""
from __future__ import annotations

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

from users.models import User
from users.serializers import UserSerializer
from users.tasks import (
    EMAIL_VERIFICATION_TEMPLATE,
    PASSWORD_RESET_TEMPLATE,
    send_email_task,
)
from .serializers import (
    EmailVerificationConfirmSerializer,
    EmailVerificationSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    SignupSerializer,
    MagicLoginRequestSerializer,
    MagicLoginVerifySerializer,
)
from .token_utils import (
    REFRESH_COOKIE_NAME,
    TOKEN_TTL_SECONDS,
    clear_refresh_cookie,
    get_tokens_for_user,
    set_refresh_cookie,
    pop_token,
    store_token,
    generate_partial_token,
)
from mysite.notification_utils import create_message, success_response, error_response, rate_limit_response


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
            ttl=TOKEN_TTL_SECONDS,
        )

        base_url = (getattr(settings, 'ACCOUNT_FRONTEND_BASE_URL', 'http://localhost:3000') or 'http://localhost:3000').rstrip('/')
        verification_link = f"{base_url}/verify-email?{urlencode({'token': verification_token})}"
        expires_in_minutes = max(1, math.ceil(TOKEN_TTL_SECONDS / 60))

        send_email_task.delay(
            to_email=user.email,
            template_id=EMAIL_VERIFICATION_TEMPLATE,
            context={
                'token': verification_token,
                'email': user.email,
                'username': user.username,
                'verification_link': verification_link,
                'verification_expires_in_minutes': expires_in_minutes,
            },
        )

        tokens = get_tokens_for_user(user)
        user_data = UserSerializer(user).data
        user_data['tokens'] = {'access': tokens['access']}
        
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
        description='Authenticate with username/password and receive an access token (refresh token stored in HTTP-only cookie). If 2FA is enabled, returns requires_2fa flag and partial token.',
        request=LoginSerializer,
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT, description='JWT tokens and user payload or 2FA required response')},
    )
    @method_decorator(ratelimit(key='ip', rate='10/h', method='POST', block=True))
    @method_decorator(ratelimit(key='post:username', rate='5/h', method='POST', block=True))
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        # Check if 2FA is enabled for this user
        try:
            from .models import TwoFactorSettings
            from .services.twofa_service import TwoFactorService
            from .services.trusted_device_service import TrustedDeviceService
            
            twofa_settings = user.twofa_settings
            
            if twofa_settings.is_enabled:
                # Check if account is locked
                if twofa_settings.is_locked():
                    return error_response(
                        'account_locked',
                        [create_message('errors.account_locked_2fa', {
                            'retry_after': 'later'
                        })],
                        status.HTTP_429_TOO_MANY_REQUESTS
                    )
                
                # Check if device is trusted (Remember Me feature)
                device_id = TrustedDeviceService.get_device_id_from_request(request)
                
                if device_id and TrustedDeviceService.is_trusted_device(user, device_id):
                    # Trusted device - skip 2FA and proceed with normal login
                    tokens = get_tokens_for_user(user)
                    user_data = UserSerializer(user).data
                    user_data['tokens'] = {'access': tokens['access']}
                    user_data['trusted_device'] = True
                    
                    response_data = success_response(
                        user_data,
                        messages=[create_message('notifications.auth.login_success')]
                    )
                    set_refresh_cookie(response_data, tokens['refresh'])
                    return response_data
                
                # 2FA required - check rate limiting
                if TwoFactorService.is_rate_limited(user):
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
                
                # Generate partial token with IP binding for 2FA verification
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
        
        # Normal login flow (no 2FA or 2FA not enabled)
        tokens = get_tokens_for_user(user)
        user_data = UserSerializer(user).data
        user_data['tokens'] = {'access': tokens['access']}
        
        response_data = success_response(
            user_data,
            messages=[create_message('notifications.auth.login_success')]
        )
        set_refresh_cookie(response_data, tokens['refresh'])
        return response_data


class EmailVerificationResendView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = EmailVerificationSerializer

    @extend_schema(
        description='Request that a new email verification message be sent to a user.',
        request=EmailVerificationSerializer,
        responses={202: OpenApiResponse(response=OpenApiTypes.OBJECT, description='Verification email scheduled')},
    )
    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token = store_token(
            'verify-email',
            {'user_id': user.id, 'issued_at': timezone.now().isoformat()},
            ttl=TOKEN_TTL_SECONDS,
        )
        base_url = (getattr(settings, 'ACCOUNT_FRONTEND_BASE_URL', 'http://localhost:3000') or 'http://localhost:3000').rstrip('/')
        verification_link = f"{base_url}/verify-email?{urlencode({'token': token})}"
        expires_in_minutes = max(1, math.ceil(TOKEN_TTL_SECONDS / 60))

        send_email_task.delay(
            to_email=user.email,
            template_id=EMAIL_VERIFICATION_TEMPLATE,
            context={
                'token': token,
                'email': user.email,
                'username': user.username,
                'verification_link': verification_link,
                'verification_expires_in_minutes': expires_in_minutes,
            },
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
            return error_response(
                'refresh_token_missing',
                [create_message('errors.token_invalid_expired', {})],
                status.HTTP_401_UNAUTHORIZED
            )

        serializer = TokenRefreshSerializer(data={'refresh': refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError:
            response = error_response(
                'invalid_refresh_token',
                [create_message('errors.token_invalid_expired', {})],
                status.HTTP_401_UNAUTHORIZED
            )
            clear_refresh_cookie(response)
            return response

        data = serializer.validated_data
        access_token = data['access']
        new_refresh = data.get('refresh', refresh_token)

        response = success_response({'access': access_token})
        set_refresh_cookie(response, new_refresh)
        return response


class EmailVerificationConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = EmailVerificationConfirmSerializer

    @extend_schema(
        description='Confirm email ownership using a verification token.',
        request=EmailVerificationConfirmSerializer,
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT, description='Email successfully verified')},
    )
    def post(self, request):
        serializer = EmailVerificationConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = pop_token('verify-email', serializer.validated_data['token'])
        if not payload:
            return error_response(
                'invalid_token',
                [create_message('errors.token_invalid_expired')],
                status.HTTP_400_BAD_REQUEST
            )
        user = User.objects.filter(id=payload['user_id']).first()
        if not user:
            return error_response(
                'user_not_found',
                [create_message('errors.user_not_found')],
                status.HTTP_404_NOT_FOUND
            )
        if not user.email_verified:
            user.email_verified = True
            user.save(update_fields=['email_verified'])
        return success_response(
            {},
            messages=[create_message('notifications.auth.email_verified')]
        )


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetRequestSerializer

    @extend_schema(
        description='Initiate the password reset flow for a user by email or username.',
        request=PasswordResetRequestSerializer,
        responses={202: OpenApiResponse(response=OpenApiTypes.OBJECT, description='Password reset email scheduled')},
    )
    def post(self, request):
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
                    'username': user.username,
                    'reset_link': reset_link,
                    'expires_in_minutes': expires_in_minutes,
                },
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
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = pop_token('password-reset', serializer.validated_data['token'])
        if not payload:
            return error_response(
                'invalid_token',
                [create_message('errors.token_invalid_expired')],
                status.HTTP_400_BAD_REQUEST
            )
        user = User.objects.filter(id=payload['user_id']).first()
        if not user:
            return error_response(
                'user_not_found',
                [create_message('errors.user_not_found')],
                status.HTTP_404_NOT_FOUND
            )
        user.set_password(serializer.validated_data['password'])
        user.save(update_fields=['password'])
        return success_response(
            {},
            messages=[create_message('notifications.auth.password_updated')]
        )


class PasswordChangeView(APIView):
    permission_classes = [permissions.IsAuthenticated]
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
            
            # Create magic login token with 15-minute expiry
            magic_token = MagicLoginToken.objects.create(
                user=user,
                token=token,
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
                    'username': user.username,
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
        
        try:
            magic_token = MagicLoginToken.objects.select_related('user').get(token=token_value)
            
            if not magic_token.is_valid():
                return error_response(
                    messages=[create_message('errors.magic_link_expired')],
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Mark token as used
            magic_token.mark_as_used()
            
            user = magic_token.user
            
            # Check if user account is active
            if not user.is_active:
                return error_response(
                    messages=[create_message('errors.account_inactive')],
                    status_code=status.HTTP_403_FORBIDDEN
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
                    device_id = TrustedDeviceService.get_device_id_from_request(request)
                    
                    if device_id and TrustedDeviceService.is_trusted_device(user, device_id):
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
                messages=[create_message('errors.magic_link_invalid')],
                status_code=status.HTTP_400_BAD_REQUEST
            )
