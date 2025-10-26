"""Google OAuth Linking Views.

This module handles linking and unlinking Google accounts.
"""
import logging

from django.conf import settings
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import permissions, status
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from mysite.auth.services.google_oauth_service import (
    GoogleOAuthService,
    OAuthError,
    GoogleAccountAlreadyLinkedError,
)
from mysite.auth.serializers import (
    OAuthLinkRequestSerializer,
    OAuthLinkResponseSerializer,
    OAuthUnlinkRequestSerializer,
    OAuthUnlinkResponseSerializer,
    OAuthErrorSerializer,
)
from mysite.auth.permissions import IsEmailVerified
from mysite.users.serializers import UserSerializer
from mysite.notification_utils import error_response, success_response, create_message
from mysite.auth.views.google_oauth.helpers import (
    get_client_ip,
    check_rate_limit,
    handle_validation_errors
)

logger = logging.getLogger(__name__)


class GoogleOAuthLinkView(APIView):
    """Link Google account to authenticated user.

    Requires authentication. Links Google account to the current user.
    """
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]

    @extend_schema(
        request=OAuthLinkRequestSerializer,
        responses={
            200: OAuthLinkResponseSerializer,
            400: OAuthErrorSerializer,
            409: OAuthErrorSerializer,
        },
        description="Link Google account to authenticated user. Requires JWT authentication.",
        tags=['OAuth']
    )
    @method_decorator(ratelimit(
        key='user',
        rate=f'{settings.OAUTH_RATE_LIMIT_MAX_ATTEMPTS}/{settings.OAUTH_RATE_LIMIT_WINDOW}s',
        block=True
    ))
    def post(self, request):
        """POST /api/auth/google/link/"""
        # Check rate limit
        rate_limit_response = check_rate_limit(request)
        if rate_limit_response:
            return rate_limit_response

        # Validate request
        serializer = OAuthLinkRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return handle_validation_errors(serializer)

        authorization_code = serializer.validated_data['code']
        state_token = serializer.validated_data['state']
        ip_address = get_client_ip(request)

        try:
            oauth_service = GoogleOAuthService()

            # Validate state token
            oauth_state = oauth_service.validate_state_token(state_token, ip_address)

            # Exchange code for token
            token_result = oauth_service.exchange_code_for_token(
                authorization_code,
                oauth_state
            )

            # Link Google account
            updated_user = oauth_service.link_google_account(
                request.user,
                token_result['user_info']
            )

            # Mark state as used
            oauth_state.mark_as_used()

            response_data = {
                'message': 'Google account linked successfully',
                'user': UserSerializer(updated_user).data
            }

            response_serializer = OAuthLinkResponseSerializer(data=response_data)
            response_serializer.is_valid(raise_exception=True)

            logger.info(
                "Google account linked",
                extra={'user_id': request.user.id, 'ip': ip_address}
            )

            return success_response(
                response_serializer.data,
                messages=[create_message('notifications.oauth.account_linked', {})]
            )

        except GoogleAccountAlreadyLinkedError as e:
            return error_response(
                'google_account_already_linked',
                [create_message('errors.oauth.account_already_linked', {})],
                status.HTTP_409_CONFLICT
            )

        except OAuthError as e:
            logger.error(f"Link Google account failed: {str(e)}", exc_info=True)
            return error_response(
                'oauth_link_failed',
                [create_message('errors.oauth.link_failed', {})],
                status.HTTP_400_BAD_REQUEST
            )


class GoogleOAuthUnlinkView(APIView):
    """Unlink Google account from authenticated user.

    Requires authentication and password verification.
    """
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]

    @extend_schema(
        request=OAuthUnlinkRequestSerializer,
        responses={
            200: OAuthUnlinkResponseSerializer,
            400: OAuthErrorSerializer,
        },
        description="Unlink Google account from authenticated user. Requires password verification.",
        tags=['OAuth']
    )
    @method_decorator(ratelimit(
        key='user',
        rate='3/15m',
        block=True
    ))
    def delete(self, request):
        """DELETE /api/auth/google/unlink/"""
        # Check rate limit
        rate_limit_response = check_rate_limit(request)
        if rate_limit_response:
            return rate_limit_response

        # Validate request
        serializer = OAuthUnlinkRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return handle_validation_errors(serializer)

        password = serializer.validated_data['password']

        # Verify password
        if not request.user.check_password(password):
            logger.warning(
                "Invalid password for OAuth unlink",
                extra={'user_id': request.user.id}
            )
            return error_response(
                'invalid_password',
                [create_message('errors.auth.invalid_password', {'field': 'password'})],
                status.HTTP_400_BAD_REQUEST
            )

        try:
            oauth_service = GoogleOAuthService()
            updated_user = oauth_service.unlink_google_account(request.user)

            response_data = {
                'message': 'Google account unlinked successfully',
                'user': UserSerializer(updated_user).data
            }

            response_serializer = OAuthUnlinkResponseSerializer(data=response_data)
            response_serializer.is_valid(raise_exception=True)

            logger.info(
                "Google account unlinked",
                extra={'user_id': request.user.id}
            )

            return success_response(
                response_serializer.data,
                messages=[create_message('notifications.oauth.account_unlinked', {})]
            )

        except OAuthError as e:
            return error_response(
                'cannot_unlink_without_password',
                [create_message('errors.oauth.cannot_unlink_without_password', {
                    'help_url': '/help/set-password'
                })],
                status.HTTP_400_BAD_REQUEST
            )
