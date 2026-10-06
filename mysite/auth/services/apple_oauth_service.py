"""Sign in with Apple service.

Apple requires ``response_mode=form_post`` when the name/email scopes are
requested, so the flow has one more hop than Google's:

1. Initiate: store an ``AppleOAuthState`` and return Apple's authorize URL.
2. Apple POSTs ``code``/``state`` (plus, on the first authorization only, the
   user's name) to ``APPLE_OAUTH_REDIRECT_URI``. ``AppleOAuthReturnView`` parks
   the name on the state and 303s the browser to the SPA with ``code``/``state``
   in the URL fragment.
3. The SPA posts ``code``/``state`` to the callback (or link) endpoint, which
   claims the state, exchanges the code using a client secret JWT signed with
   the Apple key, and verifies the ID token against Apple's public keys.

Apple's token endpoint takes no PKCE verifier; the single-use state, the
nonce checked in the ID token and the signed client secret stand in for it.
"""

from __future__ import annotations

import json
import logging
import secrets
import time
from datetime import timedelta
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode

import jwt
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from mysite.auth.log_utils import mask_email, mask_id
from mysite.auth.models import AppleOAuthState
from mysite.auth.services.oauth.account_linking_service import OAuthError, UnverifiedAccountError
from mysite.auth.services.oauth.pkce_state_service import InvalidRedirectURIError, InvalidStateError

User = get_user_model()
logger = logging.getLogger(__name__)

APPLE_ISSUER = "https://appleid.apple.com"
APPLE_AUTHORIZE_URL = "https://appleid.apple.com/auth/authorize"
APPLE_TOKEN_URL = "https://appleid.apple.com/auth/token"
APPLE_KEYS_URL = "https://appleid.apple.com/auth/keys"
APPLE_SCOPES = "name email"
# Apple allows up to six months; the secret is minted per exchange, so keep it short.
CLIENT_SECRET_TTL_SECONDS = 300
ID_TOKEN_ALGORITHMS = {"RS256", "ES256"}
REQUEST_TIMEOUT_SECONDS = 10

__all__ = [
    "AppleAccountAlreadyLinkedError",
    "AppleOAuthNotConfiguredError",
    "AppleOAuthService",
    "InvalidRedirectURIError",
    "InvalidStateError",
    "OAuthError",
    "UnverifiedAccountError",
]


class AppleOAuthNotConfiguredError(Exception):
    """Apple credentials are not set, so Sign in with Apple is disabled."""


class AppleAccountAlreadyLinkedError(OAuthError):
    """The Apple account is already linked to a different user."""


_jwks_client: Optional[jwt.PyJWKClient] = None


def _get_jwks_client() -> jwt.PyJWKClient:
    """Shared client so Apple's key set is cached across requests."""
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = jwt.PyJWKClient(APPLE_KEYS_URL, lifespan=3600, timeout=REQUEST_TIMEOUT_SECONDS)
    return _jwks_client


def _claim_is_true(value: Any) -> bool:
    """Apple sends boolean claims as either booleans or "true"/"false" strings."""
    return value is True or (isinstance(value, str) and value.lower() == "true")


class AppleOAuthService:
    """Service for Sign in with Apple (REST / web flow)."""

    def __init__(self):
        if not self.is_configured():
            raise AppleOAuthNotConfiguredError("Sign in with Apple credentials not configured")
        self.client_id = settings.APPLE_OAUTH_CLIENT_ID
        self.team_id = settings.APPLE_OAUTH_TEAM_ID
        self.key_id = settings.APPLE_OAUTH_KEY_ID
        self.private_key = settings.APPLE_OAUTH_PRIVATE_KEY
        self.redirect_uri = settings.APPLE_OAUTH_REDIRECT_URI
        self.allowed_return_uris = getattr(settings, "APPLE_OAUTH_ALLOWED_RETURN_URIS", [])
        self.state_expiration = settings.OAUTH_STATE_EXPIRATION

    @staticmethod
    def is_configured() -> bool:
        """True once every Apple credential, the return URL and an allowed SPA return URI are set."""
        return all(
            getattr(settings, name, "")
            for name in (
                "APPLE_OAUTH_CLIENT_ID",
                "APPLE_OAUTH_TEAM_ID",
                "APPLE_OAUTH_KEY_ID",
                "APPLE_OAUTH_PRIVATE_KEY",
                "APPLE_OAUTH_REDIRECT_URI",
                "APPLE_OAUTH_ALLOWED_RETURN_URIS",
            )
        )

    # -- State -----------------------------------------------------------------

    def generate_auth_url(self, return_uri: str, ip_address: str, user_agent: str) -> Dict[str, Any]:
        """Create a state and build Apple's authorize URL.

        Raises:
            InvalidRedirectURIError: If ``return_uri`` is not allowlisted
        """
        if return_uri not in self.allowed_return_uris:
            logger.warning("Invalid Apple return URI attempted", extra={"return_uri": return_uri})
            raise InvalidRedirectURIError(f"Return URI not in whitelist: {return_uri}")

        state_token = secrets.token_urlsafe(96)
        nonce = secrets.token_urlsafe(48)
        AppleOAuthState.objects.create(
            state_token=state_token,
            nonce=nonce,
            return_uri=return_uri,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=timezone.now() + timedelta(seconds=self.state_expiration),
        )

        params = {
            "response_type": "code",
            "response_mode": "form_post",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": APPLE_SCOPES,
            "state": state_token,
            "nonce": nonce,
        }
        logger.info("Apple OAuth flow initiated", extra={"state": state_token[:8] + "...", "ip": ip_address})
        return {
            "url": f"{APPLE_AUTHORIZE_URL}?{urlencode(params)}",
            "state": state_token,
            "expires_in": self.state_expiration,
        }

    @staticmethod
    def find_pending_state(state_token: str) -> Optional[AppleOAuthState]:
        """Unused, unexpired state for Apple's form POST, or None."""
        if not state_token:
            return None
        oauth_state = AppleOAuthState.objects.filter(state_token=state_token[:128]).first()
        if oauth_state is None or not oauth_state.is_valid():
            return None
        return oauth_state

    @staticmethod
    def record_authorization_user(oauth_state: AppleOAuthState, user_json: Optional[str]) -> None:
        """Keep the name Apple sends only on a user's first authorization.

        ``user_json`` is the form field ``user``:
        ``{"name": {"firstName": "...", "lastName": "..."}, "email": "..."}``.
        The email is ignored; the verified one comes from the ID token.
        """
        if not user_json:
            return
        try:
            payload = json.loads(user_json)
        except (TypeError, ValueError):
            logger.warning("Ignoring malformed Apple user payload")
            return
        name = payload.get("name") if isinstance(payload, dict) else None
        if not isinstance(name, dict):
            return

        def clean(value: Any) -> str:
            return value.strip()[:150] if isinstance(value, str) else ""

        oauth_state.first_name = clean(name.get("firstName"))
        oauth_state.last_name = clean(name.get("lastName"))
        oauth_state.save(update_fields=["first_name", "last_name"])

    @staticmethod
    def validate_state_token(state_token: str, ip_address: Optional[str] = None) -> AppleOAuthState:
        """Validate a state token from the SPA.

        Raises:
            InvalidStateError: If state is unknown, used or expired
        """
        try:
            oauth_state = AppleOAuthState.objects.get(state_token=state_token)
        except AppleOAuthState.DoesNotExist:
            logger.warning(
                "Invalid Apple OAuth state token", extra={"state": state_token[:8] + "...", "ip": ip_address}
            )
            raise InvalidStateError("State token not found") from None

        if oauth_state.used_at:
            logger.warning(
                "Apple OAuth state token replay attempted", extra={"state": state_token[:8] + "...", "ip": ip_address}
            )
            raise InvalidStateError("State token already used")

        if not oauth_state.is_valid():
            raise InvalidStateError("State token expired")

        if ip_address and oauth_state.ip_address != ip_address:
            # Logged, not enforced: mobile clients change IPs mid-flow.
            logger.warning(
                "Apple OAuth state IP mismatch",
                extra={
                    "state": state_token[:8] + "...",
                    "original_ip": oauth_state.ip_address,
                    "current_ip": ip_address,
                },
            )

        return oauth_state

    # -- Apple API ---------------------------------------------------------------

    def build_client_secret(self) -> str:
        """ES256 client secret JWT, as specified by Apple."""
        now = int(time.time())
        return jwt.encode(
            {
                "iss": self.team_id,
                "iat": now,
                "exp": now + CLIENT_SECRET_TTL_SECONDS,
                "aud": APPLE_ISSUER,
                "sub": self.client_id,
            },
            self.private_key,
            algorithm="ES256",
            headers={"kid": self.key_id},
        )

    def exchange_code_for_identity(self, authorization_code: str, oauth_state: AppleOAuthState) -> Dict[str, Any]:
        """Redeem the code and return the verified identity.

        Raises:
            OAuthError: If Apple rejects the code or the ID token fails verification
        """
        try:
            response = requests.post(
                APPLE_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.build_client_secret(),
                    "code": authorization_code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.redirect_uri,
                },
                headers={"Accept": "application/json"},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as e:
            raise OAuthError(f"Apple token request failed: {e}") from e

        try:
            body = response.json()
        except ValueError:
            body = {}
        if response.status_code != 200:
            raise OAuthError(f"Apple token exchange failed: HTTP {response.status_code} {body.get('error', '')}")

        id_token = body.get("id_token")
        if not id_token:
            raise OAuthError("Apple token response had no id_token")

        claims = self.verify_id_token(id_token, oauth_state.nonce)
        logger.info(
            "Apple token exchange successful",
            extra={"apple_id": mask_id(claims.get("sub")), "email": mask_email(claims.get("email"))},
        )
        return {
            "sub": claims["sub"],
            "email": claims.get("email") or "",
            "email_verified": _claim_is_true(claims.get("email_verified")),
            "is_private_email": _claim_is_true(claims.get("is_private_email")),
            "first_name": oauth_state.first_name,
            "last_name": oauth_state.last_name,
        }

    def verify_id_token(self, id_token: str, nonce: str) -> Dict[str, Any]:
        """Check signature, issuer, audience, expiry and nonce of Apple's ID token.

        Raises:
            OAuthError: If any check fails
        """
        try:
            signing_key = _get_jwks_client().get_signing_key_from_jwt(id_token)
            algorithm = signing_key.algorithm_name
            if algorithm not in ID_TOKEN_ALGORITHMS:
                raise OAuthError(f"Unexpected Apple ID token algorithm: {algorithm}")
            claims = jwt.decode(
                id_token,
                signing_key.key,
                algorithms=[algorithm],
                audience=self.client_id,
                issuer=APPLE_ISSUER,
                options={"require": ["iss", "aud", "exp", "iat", "sub"]},
            )
        except jwt.PyJWTError as e:
            raise OAuthError(f"Apple ID token verification failed: {e}") from e

        if not secrets.compare_digest(str(claims.get("nonce", "")), nonce):
            raise OAuthError("Nonce mismatch")
        return claims

    # -- Accounts ----------------------------------------------------------------

    @staticmethod
    def _provider_after_link(user: User) -> str:
        if user.password_login_enabled:
            return "hybrid"
        return user.auth_provider if user.google_id else "apple"

    @transaction.atomic
    def get_or_create_user(self, identity: Dict[str, Any], language: Optional[str] = None) -> Tuple[User, str]:
        """Log in, link by verified email, or create, mirroring the Google rules (ADR-010).

        Returns:
            Tuple of (User, action) where action is 'created', 'linked', or 'login'

        Raises:
            UnverifiedAccountError: If an unverified account owns the email
            OAuthError: If Apple shared no verified email for a new user
        """
        apple_id = identity["sub"]
        email = identity["email"]

        existing_user = User.objects.filter(apple_id=apple_id).first()
        if existing_user:
            logger.info(
                "Apple login - existing user", extra={"user_id": existing_user.id, "apple_id": mask_id(apple_id)}
            )
            return existing_user, "login"

        # Apple at Work & School accounts may omit the email.
        if not email or not identity["email_verified"]:
            raise OAuthError("Apple did not share a verified email address")

        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            # CRITICAL SECURITY CHECK: Prevent account takeover
            if not existing_user.email_verified:
                logger.warning(
                    "Apple OAuth blocked - unverified account exists",
                    extra={"email": mask_email(email), "apple_id": mask_id(apple_id)},
                )
                raise UnverifiedAccountError(email)

            existing_user.apple_id = apple_id
            existing_user.apple_email = email
            existing_user.apple_linked_at = timezone.now()
            existing_user.auth_provider = self._provider_after_link(existing_user)
            existing_user.save()
            logger.info("Apple account linked", extra={"user_id": existing_user.id, "apple_id": mask_id(apple_id)})
            return existing_user, "linked"

        new_user = User.objects.create(
            email=email,
            apple_id=apple_id,
            apple_email=email,
            first_name=identity.get("first_name", ""),
            last_name=identity.get("last_name", ""),
            email_verified=True,  # Apple verifies emails, relay addresses included
            auth_provider="apple",
            password_login_enabled=False,
            apple_linked_at=timezone.now(),
            **({"language": language} if language else {}),
        )
        new_user.set_unusable_password()
        new_user.save()
        logger.info(
            "Apple user created",
            extra={"user_id": new_user.id, "apple_id": mask_id(apple_id), "email": mask_email(email)},
        )
        return new_user, "created"

    @transaction.atomic
    def link_apple_account(self, user: User, identity: Dict[str, Any]) -> User:
        """Link Apple to the signed-in user.

        Unlike Google, the Apple email need not match the account email: with
        "Hide My Email" Apple only ever shares a relay address.

        Raises:
            AppleAccountAlreadyLinkedError: If another user has this Apple ID
        """
        apple_id = identity["sub"]
        if User.objects.filter(apple_id=apple_id).exclude(id=user.id).exists():
            raise AppleAccountAlreadyLinkedError("This Apple account is already linked to another user")

        user.apple_id = apple_id
        user.apple_email = identity["email"] or None
        user.apple_linked_at = timezone.now()
        user.auth_provider = self._provider_after_link(user)
        user.save()
        logger.info("Apple account linked to user", extra={"user_id": user.id, "apple_id": mask_id(apple_id)})
        return user

    @staticmethod
    @transaction.atomic
    def unlink_apple_account(user: User) -> User:
        """Unlink Apple from the user.

        Raises:
            OAuthError: If the user has no password to fall back on
        """
        if not user.password_login_enabled:
            raise OAuthError("Cannot unlink Apple account without setting a password first")

        user.apple_id = None
        user.apple_email = None
        user.apple_linked_at = None
        user.auth_provider = "hybrid" if user.google_id else "manual"
        user.save()
        logger.info("Apple account unlinked", extra={"user_id": user.id})
        return user
