"""Authentication and account lifecycle views."""
from __future__ import annotations

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from drf_spectacular.utils import OpenApiResponse, OpenApiTypes, extend_schema

from ..models import User
from ..serializers import (
    EmailVerificationConfirmSerializer,
    EmailVerificationSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    SignupSerializer,
    UserSerializer,
)
from ..tasks import (
    EMAIL_VERIFICATION_TEMPLATE,
    PASSWORD_RESET_TEMPLATE,
    send_email_task,
)
from ..token_utils import pop_token, store_token
from .utils import (
    REFRESH_COOKIE_NAME,
    TOKEN_TTL_SECONDS,
    _clear_refresh_cookie,
    _get_tokens_for_user,
    _set_refresh_cookie,
)


class SignupView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = SignupSerializer

    @extend_schema(
        description='Register a new account, optionally defer circle creation, and receive an access token (refresh token stored as an HTTP-only cookie).',
        request=SignupSerializer,
        responses={
            201: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='Signup successful; returns created user, circle (if created), tokens, and verification token.',
            )
        },
    )
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, circle = serializer.save()

        verification_token = store_token(
            'verify-email',
            {'user_id': user.id, 'issued_at': timezone.now().isoformat()},
            ttl=TOKEN_TTL_SECONDS,
        )

        send_email_task.delay(
            to_email=user.email,
            template_id=EMAIL_VERIFICATION_TEMPLATE,
            context={
                'token': verification_token,
                'email': user.email,
                'username': user.username,
            },
        )

        tokens = _get_tokens_for_user(user)
        data = serializer.to_representation((user, circle))
        data['tokens'] = {'access': tokens['access']}
        data['verification_token'] = verification_token
        response = Response(data, status=status.HTTP_201_CREATED)
        _set_refresh_cookie(response, tokens['refresh'])
        return response


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    @extend_schema(
        description='Authenticate with username/password and receive an access token (refresh token stored in HTTP-only cookie).',
        request=LoginSerializer,
        responses={200: OpenApiResponse(response=OpenApiTypes.OBJECT, description='JWT tokens and user payload')},
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        tokens = _get_tokens_for_user(user)
        data = {
            'user': UserSerializer(user).data,
            'tokens': {'access': tokens['access']},
        }
        response = Response(data)
        _set_refresh_cookie(response, tokens['refresh'])
        return response


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
        send_email_task.delay(
            to_email=user.email,
            template_id=EMAIL_VERIFICATION_TEMPLATE,
            context={
                'token': token,
                'email': user.email,
                'username': user.username,
            },
        )
        return Response({'message': _('Verification email reissued'), 'token': token}, status=status.HTTP_202_ACCEPTED)


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
            return Response({'detail': _('Refresh token cookie missing.')}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = TokenRefreshSerializer(data={'refresh': refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError:
            response = Response({'detail': _('Invalid or expired refresh token.')}, status=status.HTTP_401_UNAUTHORIZED)
            _clear_refresh_cookie(response)
            return response

        data = serializer.validated_data
        access_token = data['access']
        new_refresh = data.get('refresh', refresh_token)

        response = Response({'access': access_token})
        _set_refresh_cookie(response, new_refresh)
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
            return Response({'detail': _('Invalid or expired token')}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.filter(id=payload['user_id']).first()
        if not user:
            return Response({'detail': _('User not found')}, status=status.HTTP_404_NOT_FOUND)
        if not user.email_verified:
            user.email_verified = True
            user.save(update_fields=['email_verified'])
        return Response({'detail': _('Email verified successfully')})


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
            send_email_task.delay(
                to_email=user.email,
                template_id=PASSWORD_RESET_TEMPLATE,
                context={
                    'token': token,
                    'email': user.email,
                    'username': user.username,
                },
            )
            return Response({'message': _('Password reset sent'), 'token': token}, status=status.HTTP_202_ACCEPTED)
        return Response({'message': _('Password reset sent')}, status=status.HTTP_202_ACCEPTED)


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
            return Response({'detail': _('Invalid or expired token')}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.filter(id=payload['user_id']).first()
        if not user:
            return Response({'detail': _('User not found')}, status=status.HTTP_404_NOT_FOUND)
        user.set_password(serializer.validated_data['password'])
        user.save(update_fields=['password'])
        return Response({'detail': _('Password updated')})


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
        tokens = _get_tokens_for_user(user)
        response = Response({'detail': _('Password changed'), 'tokens': {'access': tokens['access']}})
        _set_refresh_cookie(response, tokens['refresh'])
        return response
