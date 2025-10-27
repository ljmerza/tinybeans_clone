"""Google OAuth Callback View.

This module handles the OAuth callback from Google.
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
    InvalidStateError,
    OAuthError,
    UnverifiedAccountError,
)
from mysite.auth.serializers import (
    OAuthCallbackRequestSerializer,
    OAuthCallbackResponseSerializer,
    OAuthErrorSerializer,
)
from mysite.auth.token_utils import get_tokens_for_user, set_refresh_cookie
from mysite.users.serializers import UserSerializer
from mysite.notification_utils import error_response, success_response, create_message
from mysite.auth.views.google_oauth.helpers import (
    get_client_ip,
    check_rate_limit,
    handle_validation_errors
)

logger = logging.getLogger(__name__)


class GoogleOAuthCallbackView(APIView):
    """Handle Google OAuth callback.

    Exchanges authorization code for tokens, creates or links user account,
    and issues JWT tokens.
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=OAuthCallbackRequestSerializer,
        responses={
            200: OAuthCallbackResponseSerializer,
            400: OAuthErrorSerializer,
            403: OAuthErrorSerializer,
            500: OAuthErrorSerializer,
        },
        description="""Handle Google OAuth callback.

        Validates state token, exchanges authorization code, and either:
        - Creates new user account (if new email)
        - Links Google to existing verified account
        - Blocks if unverified account exists
        - Logs in if Google ID already linked
        """,
        tags=['OAuth']
    )
    @method_decorator(ratelimit(
        key='ip',
        rate=f'{settings.OAUTH_RATE_LIMIT_MAX_ATTEMPTS}/{settings.OAUTH_RATE_LIMIT_WINDOW}s',
        block=True
    ))
    def post(self, request):
        """POST /api/auth/google/callback/"""
        # Check rate limit
        rate_limit_response = check_rate_limit(request)
        if rate_limit_response:
            return rate_limit_response

        # Validate request
        serializer = OAuthCallbackRequestSerializer(data=request.data)
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

            # Get or create user
            user, account_action = oauth_service.get_or_create_user(
                token_result['user_info']
            )

            # Mark state as used
            oauth_state.mark_as_used()

            # Generate JWT tokens
            tokens = get_tokens_for_user(user)

            # Prepare response
            response_data = {
                'user': UserSerializer(user).data,
                'tokens': {
                    'access': str(tokens['access'])
                },
                'account_action': account_action
            }

            response_serializer = OAuthCallbackResponseSerializer(data=response_data)
            response_serializer.is_valid(raise_exception=True)

            # Create response with refresh token cookie
            response = success_response(response_serializer.data)
            set_refresh_cookie(response, tokens['refresh'])

            logger.info(
                f"OAuth callback successful - {account_action}",
                extra={
                    'user_id': user.id,
                    'action': account_action,
                    'ip': ip_address
                }
            )

            return response

        except InvalidStateError as e:
            logger.warning(f"Invalid OAuth state: {str(e)}", extra={'ip': ip_address})
            return error_response(
                'invalid_state_token',
                [create_message('errors.oauth.invalid_state', {})],
                status.HTTP_400_BAD_REQUEST
            )

        except UnverifiedAccountError as e:
            logger.warning(
                f"OAuth blocked - unverified account: {e.email}",
                extra={'email': e.email, 'ip': ip_address}
            )
            return error_response(
                'unverified_account_exists',
                [create_message('errors.oauth.unverified_account_exists', {
                    'email': e.email,
                    'help_url': '/help/verify-email'
                })],
                status.HTTP_403_FORBIDDEN
            )

        except OAuthError as e:
            logger.error(f"OAuth error: {str(e)}", exc_info=True)
            return error_response(
                'oauth_error',
                [create_message('errors.oauth.authentication_failed', {})],
                status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            logger.error(f"OAuth callback failed: {str(e)}", exc_info=True)
            return error_response(
                'oauth_callback_failed',
                [create_message('errors.oauth.callback_failed', {})],
                status.HTTP_500_INTERNAL_SERVER_ERROR
            )
