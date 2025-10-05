"""Google OAuth API Views.

This module implements all Google OAuth 2.0 endpoints:
- POST /api/auth/google/initiate/ - Start OAuth flow
- POST /api/auth/google/callback/ - Handle OAuth callback
- POST /api/auth/google/link/ - Link Google to existing account
- DELETE /api/auth/google/unlink/ - Unlink Google account
"""
import logging

from django.conf import settings
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from auth.services.google_oauth_service import (
    GoogleOAuthService,
    InvalidRedirectURIError,
    InvalidStateError,
    OAuthError,
    UnverifiedAccountError,
    GoogleAccountAlreadyLinkedError,
)
from auth.serializers import (
    OAuthInitiateRequestSerializer,
    OAuthInitiateResponseSerializer,
    OAuthCallbackRequestSerializer,
    OAuthCallbackResponseSerializer,
    OAuthLinkRequestSerializer,
    OAuthLinkResponseSerializer,
    OAuthUnlinkRequestSerializer,
    OAuthUnlinkResponseSerializer,
    OAuthErrorSerializer,
)
from auth.token_utils import get_tokens_for_user, set_refresh_cookie
from auth.response_utils import rate_limit_response
from users.serializers import UserSerializer
from mysite.notification_utils import error_response, success_response, validation_error_response, create_message

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class GoogleOAuthInitiateView(APIView):
    """Initiate Google OAuth flow.
    
    Generates OAuth URL with state token and PKCE for frontend to redirect to.
    Rate limited to prevent abuse.
    """
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        request=OAuthInitiateRequestSerializer,
        responses={
            200: OAuthInitiateResponseSerializer,
            400: OAuthErrorSerializer,
            429: OpenApiResponse(description='Rate limit exceeded'),
        },
        description="Initiate Google OAuth flow. Returns OAuth URL for frontend to redirect to.",
        tags=['OAuth']
    )
    @method_decorator(ratelimit(
        key='ip',
        rate=f'{settings.OAUTH_RATE_LIMIT_MAX_ATTEMPTS}/{settings.OAUTH_RATE_LIMIT_WINDOW}s',
        block=True
    ))
    def post(self, request):
        """POST /api/auth/google/initiate/"""
        # Check rate limit
        was_limited = getattr(request, 'limited', False)
        if was_limited:
            return rate_limit_response()
        
        # Validate request
        serializer = OAuthInitiateRequestSerializer(data=request.data)
        if not serializer.is_valid():
            errors = []
            for field, field_errors in serializer.errors.items():
                for error_msg in field_errors:
                    errors.append(create_message('errors.validation_error', {
                        'field': field,
                        'message': str(error_msg)
                    }))
            return validation_error_response(errors)
        
        redirect_uri = serializer.validated_data['redirect_uri']
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        try:
            oauth_service = GoogleOAuthService()
            result = oauth_service.generate_auth_url(
                redirect_uri=redirect_uri,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            response_serializer = OAuthInitiateResponseSerializer(data={
                'google_oauth_url': result['url'],
                'state': result['state'],
                'expires_in': result['expires_in']
            })
            response_serializer.is_valid(raise_exception=True)
            
            return success_response(response_serializer.data)
            
        except InvalidRedirectURIError as e:
            logger.warning(f"Invalid redirect URI: {redirect_uri}", extra={'ip': ip_address})
            return error_response(
                'invalid_redirect_uri',
                [create_message('errors.oauth.invalid_redirect_uri', {'uri': redirect_uri})],
                status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"OAuth initiate failed: {str(e)}", exc_info=True)
            return error_response(
                'oauth_initiate_failed',
                [create_message('errors.oauth.initiate_failed', {})],
                status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
        was_limited = getattr(request, 'limited', False)
        if was_limited:
            return rate_limit_response()
        
        # Validate request
        serializer = OAuthCallbackRequestSerializer(data=request.data)
        if not serializer.is_valid():
            errors = []
            for field, field_errors in serializer.errors.items():
                for error_msg in field_errors:
                    errors.append(create_message('errors.validation_error', {
                        'field': field,
                        'message': str(error_msg)
                    }))
            return validation_error_response(errors)
        
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
                    'access': str(tokens['access']),
                    'refresh': str(tokens['refresh'])
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


class GoogleOAuthLinkView(APIView):
    """Link Google account to authenticated user.
    
    Requires authentication. Links Google account to the current user.
    """
    permission_classes = [permissions.IsAuthenticated]
    
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
        was_limited = getattr(request, 'limited', False)
        if was_limited:
            return rate_limit_response()
        
        # Validate request
        serializer = OAuthLinkRequestSerializer(data=request.data)
        if not serializer.is_valid():
            errors = []
            for field, field_errors in serializer.errors.items():
                for error_msg in field_errors:
                    errors.append(create_message('errors.validation_error', {
                        'field': field,
                        'message': str(error_msg)
                    }))
            return validation_error_response(errors)
        
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
    permission_classes = [permissions.IsAuthenticated]
    
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
        was_limited = getattr(request, 'limited', False)
        if was_limited:
            return rate_limit_response()
        
        # Validate request
        serializer = OAuthUnlinkRequestSerializer(data=request.data)
        if not serializer.is_valid():
            errors = []
            for field, field_errors in serializer.errors.items():
                for error_msg in field_errors:
                    errors.append(create_message('errors.validation_error', {
                        'field': field,
                        'message': str(error_msg)
                    }))
            return validation_error_response(errors)
        
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
