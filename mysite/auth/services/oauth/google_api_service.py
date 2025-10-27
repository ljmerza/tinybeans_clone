"""Google API Interaction Service.

This service handles:
- OAuth URL generation
- Token exchange with Google
- ID token verification
"""
import logging
from typing import Dict
from urllib.parse import urlencode

from django.conf import settings

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google_auth_oauthlib.flow import Flow

from mysite.auth.models import GoogleOAuthState

logger = logging.getLogger(__name__)


class OAuthError(Exception):
    """Base exception for OAuth errors."""
    pass


class GoogleAPIService:
    """Service for interacting with Google OAuth APIs."""

    def __init__(self):
        self.client_id = settings.GOOGLE_OAUTH_CLIENT_ID
        self.client_secret = settings.GOOGLE_OAUTH_CLIENT_SECRET
        self.scopes = settings.GOOGLE_OAUTH_SCOPES

        if not self.client_id or not self.client_secret:
            raise ValueError("Google OAuth credentials not configured")

    def build_auth_url(
        self,
        redirect_uri: str,
        state_token: str,
        code_challenge: str,
        nonce: str
    ) -> str:
        """Build Google OAuth authorization URL.

        Args:
            redirect_uri: OAuth redirect URI
            state_token: State token for CSRF protection
            code_challenge: PKCE code challenge
            nonce: Nonce for ID token validation

        Returns:
            Complete Google OAuth URL
        """
        auth_params = {
            'client_id': self.client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(self.scopes),
            'state': state_token,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'access_type': 'offline',
            'prompt': 'consent',
            'nonce': nonce,
        }

        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(auth_params)}"

    def exchange_code_for_token(
        self,
        authorization_code: str,
        oauth_state: GoogleOAuthState,
        code_verifier: str
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
        try:
            # Create Flow for token exchange
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                    }
                },
                scopes=self.scopes,
                redirect_uri=oauth_state.redirect_uri
            )

            # Set code verifier for PKCE
            flow.code_verifier = code_verifier

            # Exchange code for token
            flow.fetch_token(code=authorization_code)

            # Get credentials
            credentials = flow.credentials

            # Verify ID token
            id_info = id_token.verify_oauth2_token(
                credentials.id_token,
                google_requests.Request(),
                self.client_id
            )

            # Verify nonce
            if id_info.get('nonce') != oauth_state.nonce:
                raise OAuthError("Nonce mismatch")

            logger.info(
                "OAuth token exchange successful",
                extra={
                    'google_id': id_info.get('sub'),
                    'email': id_info.get('email')
                }
            )

            return {
                'access_token': credentials.token,
                'id_token': credentials.id_token,
                'user_info': id_info
            }

        except Exception as e:
            logger.error(
                f"OAuth token exchange failed: {str(e)}",
                extra={'error': str(e)},
                exc_info=True
            )
            raise OAuthError(f"Token exchange failed: {str(e)}")
