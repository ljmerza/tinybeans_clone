"""Sign in with Apple views.

See ``mysite/auth/services/apple_oauth_service.py`` for the flow. Every
endpoint answers "disabled" until the Apple credentials are configured, and
``OAuthProvidersView`` tells the SPA whether to show the Apple button at all.
"""

import logging
from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.views import APIView

from mysite.auth.log_utils import mask_email
from mysite.auth.permissions import IsEmailVerified
from mysite.auth.serializers import (
    AppleOAuthInitiateResponseSerializer,
    OAuthCallbackRequestSerializer,
    OAuthCallbackResponseSerializer,
    OAuthErrorSerializer,
    OAuthInitiateRequestSerializer,
    OAuthLinkRequestSerializer,
    OAuthLinkResponseSerializer,
    OAuthProvidersResponseSerializer,
    OAuthUnlinkRequestSerializer,
    OAuthUnlinkResponseSerializer,
)
from mysite.auth.services.apple_oauth_service import (
    AppleAccountAlreadyLinkedError,
    AppleOAuthNotConfiguredError,
    AppleOAuthService,
    InvalidRedirectURIError,
    InvalidStateError,
    OAuthError,
    UnverifiedAccountError,
)
from mysite.auth.token_utils import get_tokens_for_user, set_refresh_cookie
from mysite.auth.views.google_oauth.helpers import check_rate_limit, get_client_ip, handle_validation_errors
from mysite.notification_utils import create_message, error_response, success_response
from mysite.users.serializers import UserSerializer

logger = logging.getLogger(__name__)

OAUTH_RATE = f"{settings.OAUTH_RATE_LIMIT_MAX_ATTEMPTS}/{settings.OAUTH_RATE_LIMIT_WINDOW}s"
# Used when Apple's POST has no usable state, so there is no stored return URI.
FALLBACK_RETURN_PATH = "/auth/apple-callback"


def _disabled_response():
    return error_response(
        "apple_oauth_disabled", [create_message("errors.oauth.apple_disabled", {})], status.HTTP_404_NOT_FOUND
    )


def _invalid_state_response():
    return error_response(
        "invalid_state_token", [create_message("errors.oauth.invalid_state", {})], status.HTTP_400_BAD_REQUEST
    )


def google_oauth_configured() -> bool:
    """Google sign-in works only with the client credentials and an allowed redirect URI."""
    return bool(
        getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
        and getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "")
        and getattr(settings, "OAUTH_ALLOWED_REDIRECT_URIS", [])
    )


class OAuthProvidersView(APIView):
    """Report which social sign-in providers are configured; the SPA hides the rest."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(responses={200: OAuthProvidersResponseSerializer}, tags=["OAuth"])
    def get(self, request):
        """GET /api/auth/providers/"""
        return success_response(
            {
                "google": google_oauth_configured(),
                "apple": AppleOAuthService.is_configured(),
            }
        )


class AppleOAuthInitiateView(APIView):
    """Start Sign in with Apple; returns Apple's authorize URL."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=OAuthInitiateRequestSerializer,
        responses={
            200: AppleOAuthInitiateResponseSerializer,
            400: OAuthErrorSerializer,
            404: OAuthErrorSerializer,
            429: OpenApiResponse(description="Rate limit exceeded"),
        },
        description=(
            "Initiate Sign in with Apple. `redirect_uri` is the SPA page "
            "(`<origin>/auth/apple-callback`) the browser lands on after Apple's POST."
        ),
        tags=["OAuth"],
    )
    @method_decorator(ratelimit(key="ip", rate=OAUTH_RATE, block=True))
    def post(self, request):
        """POST /api/auth/apple/initiate/"""
        rate_limit_response = check_rate_limit(request)
        if rate_limit_response:
            return rate_limit_response

        serializer = OAuthInitiateRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return handle_validation_errors(serializer)

        return_uri = serializer.validated_data["redirect_uri"]
        ip_address = get_client_ip(request)

        try:
            result = AppleOAuthService().generate_auth_url(
                return_uri=return_uri, ip_address=ip_address, user_agent=request.META.get("HTTP_USER_AGENT", "")
            )
        except AppleOAuthNotConfiguredError:
            return _disabled_response()
        except InvalidRedirectURIError:
            logger.warning(f"Invalid Apple return URI: {return_uri}", extra={"ip": ip_address})
            return error_response(
                "invalid_redirect_uri",
                [create_message("errors.oauth.invalid_redirect_uri", {"uri": return_uri})],
                status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Apple OAuth initiate failed: {str(e)}", exc_info=True)
            return error_response(
                "oauth_initiate_failed",
                [create_message("errors.oauth.initiate_failed", {})],
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return success_response(
            {"apple_oauth_url": result["url"], "state": result["state"], "expires_in": result["expires_in"]}
        )


def _redirect_to_spa(return_uri: str, params: dict) -> HttpResponseRedirect:
    """303 to the SPA with the result in the fragment.

    A fragment never reaches a server, so the code stays out of access logs and
    Referer headers; the SPA strips it from the address bar on load.
    """
    response = HttpResponseRedirect(f"{return_uri}#{urlencode(params)}")
    response.status_code = 303
    response["Cache-Control"] = "no-store"
    response["Referrer-Policy"] = "no-referrer"
    return response


@csrf_exempt  # Apple's cross-site form POST; the state token is the CSRF guard.
@require_POST
@ratelimit(key="ip", rate=OAUTH_RATE, block=False)
def apple_oauth_return(request):
    """POST /api/auth/apple/return/ - Apple's ``form_post`` target (APPLE_OAUTH_REDIRECT_URI)."""
    if not AppleOAuthService.is_configured():
        return _redirect_to_spa(FALLBACK_RETURN_PATH, {"error": "apple_disabled"})

    state_token = request.POST.get("state", "")
    oauth_state = AppleOAuthService.find_pending_state(state_token)
    if oauth_state is None:
        logger.warning("Apple return with unknown or expired state", extra={"ip": get_client_ip(request)})
        return _redirect_to_spa(FALLBACK_RETURN_PATH, {"error": "invalid_state"})

    if getattr(request, "limited", False):
        return _redirect_to_spa(oauth_state.return_uri, {"error": "rate_limited", "state": state_token})

    # e.g. "user_cancelled_authorize"
    apple_error = request.POST.get("error")
    if apple_error:
        return _redirect_to_spa(oauth_state.return_uri, {"error": apple_error[:64], "state": state_token})

    code = request.POST.get("code", "")
    if not code:
        return _redirect_to_spa(oauth_state.return_uri, {"error": "invalid_callback", "state": state_token})

    AppleOAuthService.record_authorization_user(oauth_state, request.POST.get("user"))
    return _redirect_to_spa(oauth_state.return_uri, {"code": code, "state": state_token})


class AppleOAuthCallbackView(APIView):
    """Finish Sign in with Apple: verify, then create, link or log in the user."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=OAuthCallbackRequestSerializer,
        responses={
            200: OAuthCallbackResponseSerializer,
            400: OAuthErrorSerializer,
            403: OAuthErrorSerializer,
            404: OAuthErrorSerializer,
            500: OAuthErrorSerializer,
        },
        description="Complete Sign in with Apple with the code and state from the SPA callback page.",
        tags=["OAuth"],
    )
    @method_decorator(ratelimit(key="ip", rate=OAUTH_RATE, block=True))
    def post(self, request):
        """POST /api/auth/apple/callback/"""
        rate_limit_response = check_rate_limit(request)
        if rate_limit_response:
            return rate_limit_response

        serializer = OAuthCallbackRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return handle_validation_errors(serializer)

        ip_address = get_client_ip(request)

        try:
            oauth_service = AppleOAuthService()
            oauth_state = oauth_service.validate_state_token(serializer.validated_data["state"], ip_address)
            # Claim before the token exchange so concurrent callbacks can't both proceed (ADR-015).
            if not oauth_state.mark_as_used():
                raise InvalidStateError("State token already used")

            identity = oauth_service.exchange_code_for_identity(serializer.validated_data["code"], oauth_state)
            user, account_action = oauth_service.get_or_create_user(
                identity, language=serializer.validated_data.get("language")
            )
            tokens = get_tokens_for_user(user)

            # Already serialized; don't validate it as input (see google_oauth/callback.py).
            response = success_response(
                {
                    "user": UserSerializer(user).data,
                    "tokens": {"access": str(tokens["access"])},
                    "account_action": account_action,
                }
            )
            set_refresh_cookie(response, tokens["refresh"])
            logger.info(
                f"Apple OAuth callback successful - {account_action}",
                extra={"user_id": user.id, "action": account_action, "ip": ip_address},
            )
            return response

        except AppleOAuthNotConfiguredError:
            return _disabled_response()

        except InvalidStateError as e:
            logger.warning(f"Invalid Apple OAuth state: {str(e)}", extra={"ip": ip_address})
            return _invalid_state_response()

        except UnverifiedAccountError as e:
            logger.warning(
                "Apple OAuth blocked - unverified account", extra={"email": mask_email(e.email), "ip": ip_address}
            )
            return error_response(
                "unverified_account_exists",
                [
                    create_message(
                        "errors.oauth.unverified_account_exists", {"email": e.email, "help_url": "/help/verify-email"}
                    )
                ],
                status.HTTP_403_FORBIDDEN,
            )

        except OAuthError as e:
            logger.error(f"Apple OAuth error: {str(e)}", exc_info=True)
            return error_response(
                "oauth_error", [create_message("errors.oauth.authentication_failed", {})], status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            logger.error(f"Apple OAuth callback failed: {str(e)}", exc_info=True)
            return error_response(
                "oauth_callback_failed",
                [create_message("errors.oauth.callback_failed", {})],
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AppleOAuthLinkView(APIView):
    """Link an Apple account to the signed-in user."""

    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]

    @extend_schema(
        request=OAuthLinkRequestSerializer,
        responses={
            200: OAuthLinkResponseSerializer,
            400: OAuthErrorSerializer,
            404: OAuthErrorSerializer,
            409: OAuthErrorSerializer,
        },
        description="Link an Apple account to the authenticated user. Requires JWT authentication.",
        tags=["OAuth"],
    )
    @method_decorator(ratelimit(key="user", rate=OAUTH_RATE, block=True))
    def post(self, request):
        """POST /api/auth/apple/link/"""
        rate_limit_response = check_rate_limit(request)
        if rate_limit_response:
            return rate_limit_response

        serializer = OAuthLinkRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return handle_validation_errors(serializer)

        ip_address = get_client_ip(request)

        try:
            oauth_service = AppleOAuthService()
            oauth_state = oauth_service.validate_state_token(serializer.validated_data["state"], ip_address)
            if not oauth_state.mark_as_used():
                raise InvalidStateError("State token already used")

            identity = oauth_service.exchange_code_for_identity(serializer.validated_data["code"], oauth_state)
            updated_user = oauth_service.link_apple_account(request.user, identity)
            logger.info("Apple account linked", extra={"user_id": request.user.id, "ip": ip_address})
            return success_response(
                {"message": "Apple account linked successfully", "user": UserSerializer(updated_user).data},
                messages=[create_message("notifications.oauth.apple_account_linked", {})],
            )

        except AppleOAuthNotConfiguredError:
            return _disabled_response()

        except InvalidStateError:
            logger.warning(
                "Invalid Apple OAuth state token for link operation",
                extra={"user_id": request.user.id, "ip": ip_address},
            )
            return _invalid_state_response()

        except AppleAccountAlreadyLinkedError:
            return error_response(
                "apple_account_already_linked",
                [create_message("errors.oauth.apple_account_already_linked", {})],
                status.HTTP_409_CONFLICT,
            )

        except OAuthError as e:
            logger.error(f"Link Apple account failed: {str(e)}", exc_info=True)
            return error_response(
                "oauth_link_failed", [create_message("errors.oauth.apple_link_failed", {})], status.HTTP_400_BAD_REQUEST
            )


class AppleOAuthUnlinkView(APIView):
    """Unlink Apple from the signed-in user; requires their password."""

    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]

    @extend_schema(
        request=OAuthUnlinkRequestSerializer,
        responses={200: OAuthUnlinkResponseSerializer, 400: OAuthErrorSerializer},
        description="Unlink the Apple account from the authenticated user. Requires password verification.",
        tags=["OAuth"],
    )
    @method_decorator(ratelimit(key="user", rate="3/15m", block=True))
    def delete(self, request):
        """DELETE /api/auth/apple/unlink/"""
        rate_limit_response = check_rate_limit(request)
        if rate_limit_response:
            return rate_limit_response

        serializer = OAuthUnlinkRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return handle_validation_errors(serializer)

        if not request.user.check_password(serializer.validated_data["password"]):
            logger.warning("Invalid password for Apple unlink", extra={"user_id": request.user.id})
            return error_response(
                "invalid_password",
                [create_message("errors.auth.invalid_password", {"field": "password"})],
                status.HTTP_400_BAD_REQUEST,
            )

        try:
            updated_user = AppleOAuthService.unlink_apple_account(request.user)
        except OAuthError:
            return error_response(
                "cannot_unlink_without_password",
                [
                    create_message(
                        "errors.oauth.apple_cannot_unlink_without_password", {"help_url": "/help/set-password"}
                    )
                ],
                status.HTTP_400_BAD_REQUEST,
            )

        logger.info("Apple account unlinked", extra={"user_id": request.user.id})
        return success_response(
            {"message": "Apple account unlinked successfully", "user": UserSerializer(updated_user).data},
            messages=[create_message("notifications.oauth.apple_account_unlinked", {})],
        )
