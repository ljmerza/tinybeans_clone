"""PKCE and OAuth State Management Service.

This service handles:
- PKCE code verifier and challenge generation
- OAuth state token generation and validation
- Redirect URI validation
"""
import secrets
import hashlib
import base64
import logging
from datetime import timedelta
from typing import Tuple, Optional

from django.conf import settings
from django.utils import timezone

from mysite.auth.models import GoogleOAuthState

logger = logging.getLogger(__name__)


class InvalidStateError(Exception):
    """OAuth state token is invalid or expired."""
    pass


class InvalidRedirectURIError(Exception):
    """Redirect URI is not in the whitelist."""
    pass


class PKCEStateService:
    """Service for managing PKCE and OAuth state tokens."""

    def __init__(self):
        self.allowed_redirect_uris = settings.OAUTH_ALLOWED_REDIRECT_URIS
        self.state_expiration = settings.OAUTH_STATE_EXPIRATION

    def generate_pkce_pair(self) -> Tuple[str, str]:
        """Generate PKCE code verifier and code challenge.

        Returns:
            Tuple of (code_verifier, code_challenge)
        """
        # Generate code verifier (43-128 characters)
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8')
        code_verifier = code_verifier.rstrip('=')  # Remove padding

        # Generate code challenge using S256
        code_challenge = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        code_challenge = base64.urlsafe_b64encode(code_challenge).decode('utf-8')
        code_challenge = code_challenge.rstrip('=')  # Remove padding

        return code_verifier, code_challenge

    def validate_redirect_uri(self, redirect_uri: str) -> None:
        """Validate redirect URI against whitelist.

        Args:
            redirect_uri: The redirect URI to validate

        Raises:
            InvalidRedirectURIError: If URI is not in whitelist
        """
        if redirect_uri not in self.allowed_redirect_uris:
            logger.warning(
                f"Invalid redirect URI attempted: {redirect_uri}",
                extra={'redirect_uri': redirect_uri}
            )
            raise InvalidRedirectURIError(f"Redirect URI not in whitelist: {redirect_uri}")

    def create_state(
        self,
        code_verifier: str,
        redirect_uri: str,
        ip_address: str,
        user_agent: str
    ) -> Tuple[GoogleOAuthState, str]:
        """Create and store OAuth state.

        Args:
            code_verifier: PKCE code verifier
            redirect_uri: OAuth redirect URI
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Tuple of (GoogleOAuthState object, nonce)
        """
        # Generate state token and nonce
        state_token = secrets.token_urlsafe(96)  # 128 characters
        nonce = secrets.token_urlsafe(48)  # 64 characters

        # Calculate expiration
        expires_at = timezone.now() + timedelta(seconds=self.state_expiration)

        # Store state in database
        oauth_state = GoogleOAuthState.objects.create(
            state_token=state_token,
            code_verifier=code_verifier,
            redirect_uri=redirect_uri,
            nonce=nonce,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at
        )

        logger.info(
            "OAuth state created",
            extra={
                'state': state_token[:8] + '...',
                'ip': ip_address,
                'redirect_uri': redirect_uri
            }
        )

        return oauth_state, nonce

    def validate_state_token(
        self,
        state_token: str,
        ip_address: Optional[str] = None
    ) -> GoogleOAuthState:
        """Validate OAuth state token.

        Args:
            state_token: The state token to validate
            ip_address: Client IP to verify (optional but recommended)

        Returns:
            GoogleOAuthState object if valid

        Raises:
            InvalidStateError: If state is invalid, expired, or used
        """
        try:
            oauth_state = GoogleOAuthState.objects.get(state_token=state_token)
        except GoogleOAuthState.DoesNotExist:
            logger.warning(
                "Invalid OAuth state token",
                extra={'state': state_token[:8] + '...', 'ip': ip_address}
            )
            raise InvalidStateError("State token not found")

        # Check if already used
        if oauth_state.used_at:
            logger.warning(
                "OAuth state token replay attempted",
                extra={'state': state_token[:8] + '...', 'ip': ip_address}
            )
            raise InvalidStateError("State token already used")

        # Check expiration
        if not oauth_state.is_valid():
            logger.warning(
                "Expired OAuth state token",
                extra={'state': state_token[:8] + '...', 'ip': ip_address}
            )
            raise InvalidStateError("State token expired")

        # Optional: Verify IP address matches
        if ip_address and oauth_state.ip_address != ip_address:
            logger.warning(
                "OAuth state IP mismatch",
                extra={
                    'state': state_token[:8] + '...',
                    'original_ip': oauth_state.ip_address,
                    'current_ip': ip_address
                }
            )
            # Don't fail on IP mismatch (mobile users may change IPs)
            # but log it for security monitoring

        return oauth_state
