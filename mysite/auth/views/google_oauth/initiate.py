"""Google OAuth Initiate View.

This module handles initiating the Google OAuth flow.
"""
import logging

from django.conf import settings
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import permissions, status
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from mysite.auth.services.google_oauth_service import (
    GoogleOAuthService,
    InvalidRedirectURIError,
)
from mysite.auth.serializers import (
    OAuthInitiateRequestSerializer,
    OAuthInitiateResponseSerializer,
    OAuthErrorSerializer,
)
from mysite.notification_utils import error_response, success_response, create_message
from mysite.auth.views.google_oauth.helpers import (
    get_client_ip,
    check_rate_limit,
    handle_validation_errors
)

logger = logging.getLogger(__name__)


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
        rate_limit_response = check_rate_limit(request)
        if rate_limit_response:
            return rate_limit_response

        # Validate request
        serializer = OAuthInitiateRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return handle_validation_errors(serializer)

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
