"""Google OAuth Service for handling OAuth 2.0 authentication flow.

This service orchestrates the OAuth flow by delegating to specialized sub-services:
- PKCEStateService: PKCE and state management
- GoogleAPIService: Google API interactions
- AccountLinkingService: Account linking/unlinking operations
"""
import logging
from typing import Dict, Tuple, Optional

from django.conf import settings
from django.contrib.auth import get_user_model

from mysite.auth.models import GoogleOAuthState
from mysite.auth.services.oauth.pkce_state_service import (
    PKCEStateService,
    InvalidStateError,
    InvalidRedirectURIError
)
from mysite.auth.services.oauth.google_api_service import (
    GoogleAPIService,
    OAuthError
)
from mysite.auth.services.oauth.account_linking_service import (
    AccountLinkingService,
    UnverifiedAccountError,
    GoogleAccountAlreadyLinkedError
)

User = get_user_model()
logger = logging.getLogger(__name__)

# Re-export exceptions for backward compatibility
__all__ = [
    'GoogleOAuthService',
    'OAuthError',
    'InvalidStateError',
    'InvalidRedirectURIError',
    'UnverifiedAccountError',
    'GoogleAccountAlreadyLinkedError',
]


class GoogleOAuthService:
    """Service for handling Google OAuth 2.0 authentication.

    This service orchestrates the OAuth flow by delegating to specialized services.
    """

    def __init__(self):
        self.pkce_state_service = PKCEStateService()
        self.google_api_service = GoogleAPIService()
        self.account_linking_service = AccountLinkingService()
        self.state_expiration = settings.OAUTH_STATE_EXPIRATION
    
    def generate_pkce_pair(self) -> Tuple[str, str]:
        """Generate PKCE code verifier and code challenge.

        Returns:
            Tuple of (code_verifier, code_challenge)
        """
        return self.pkce_state_service.generate_pkce_pair()

    def validate_redirect_uri(self, redirect_uri: str) -> None:
        """Validate redirect URI against whitelist.

        Args:
            redirect_uri: The redirect URI to validate

        Raises:
            InvalidRedirectURIError: If URI is not in whitelist
        """
        return self.pkce_state_service.validate_redirect_uri(redirect_uri)
    
    def generate_auth_url(
        self,
        redirect_uri: str,
        ip_address: str,
        user_agent: str
    ) -> Dict[str, str]:
        """Generate Google OAuth authorization URL with PKCE.

        Args:
            redirect_uri: Where Google should redirect after auth
            ip_address: Client IP address for security tracking
            user_agent: Client user agent for security tracking

        Returns:
            Dict with 'url', 'state', and 'expires_in'

        Raises:
            InvalidRedirectURIError: If redirect URI not in whitelist
        """
        # Validate redirect URI
        self.pkce_state_service.validate_redirect_uri(redirect_uri)

        # Generate PKCE pair
        code_verifier, code_challenge = self.pkce_state_service.generate_pkce_pair()

        # Create and store state
        oauth_state, nonce = self.pkce_state_service.create_state(
            code_verifier=code_verifier,
            redirect_uri=redirect_uri,
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Build OAuth URL
        google_oauth_url = self.google_api_service.build_auth_url(
            redirect_uri=redirect_uri,
            state_token=oauth_state.state_token,
            code_challenge=code_challenge,
            nonce=nonce
        )

        logger.info(
            "OAuth flow initiated",
            extra={
                'state': oauth_state.state_token[:8] + '...',
                'ip': ip_address,
                'redirect_uri': redirect_uri
            }
        )

        return {
            'url': google_oauth_url,
            'state': oauth_state.state_token,
            'expires_in': self.state_expiration
        }
    
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
        return self.pkce_state_service.validate_state_token(state_token, ip_address)
    
    def exchange_code_for_token(
        self,
        authorization_code: str,
        oauth_state: GoogleOAuthState
    ) -> Dict[str, any]:
        """Exchange authorization code for access token using PKCE.

        Args:
            authorization_code: The authorization code from Google
            oauth_state: Validated OAuth state object

        Returns:
            Dict with 'access_token', 'id_token', and user info

        Raises:
            OAuthError: If token exchange fails
        """
        code_verifier = self.pkce_state_service.pop_code_verifier(oauth_state)
        return self.google_api_service.exchange_code_for_token(
            authorization_code,
            oauth_state,
            code_verifier
        )
    
    def get_or_create_user(
        self,
        google_user_info: Dict[str, any]
    ) -> Tuple[User, str]:
        """Get existing user or create new user from Google info.

        Implements the 5 account scenarios from ADR-010:
        1. New user → Create account
        2. Existing verified user → Link Google ID
        3. Existing unverified user → BLOCK
        4. User with Google ID → Login
        5. Link to authenticated user

        Args:
            google_user_info: User info from Google ID token

        Returns:
            Tuple of (User, action) where action is 'created', 'linked', or 'login'

        Raises:
            UnverifiedAccountError: If unverified account exists
            GoogleAccountAlreadyLinkedError: If Google ID already linked
        """
        return self.account_linking_service.get_or_create_user(google_user_info)
    
    def link_google_account(
        self,
        user: User,
        google_user_info: Dict[str, any]
    ) -> User:
        """Link Google account to existing authenticated user.

        Args:
            user: Authenticated user
            google_user_info: User info from Google

        Returns:
            Updated user

        Raises:
            GoogleAccountAlreadyLinkedError: If Google ID already used
            OAuthError: If email doesn't match
        """
        return self.account_linking_service.link_google_account(user, google_user_info)

    def unlink_google_account(self, user: User) -> User:
        """Unlink Google account from user.

        Args:
            user: User to unlink from

        Returns:
            Updated user

        Raises:
            OAuthError: If user has no password and can't unlink
        """
        return self.account_linking_service.unlink_google_account(user)
