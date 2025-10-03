"""Google OAuth Service for handling OAuth 2.0 authentication flow.

This service encapsulates all Google OAuth logic including:
- OAuth URL generation with PKCE
- State token validation
- Authorization code exchange
- User information retrieval
- Account linking logic
"""
import secrets
import hashlib
import base64
import logging
from datetime import timedelta
from typing import Dict, Tuple, Optional
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google_auth_oauthlib.flow import Flow

from auth.models import GoogleOAuthState

User = get_user_model()
logger = logging.getLogger(__name__)


class OAuthError(Exception):
    """Base exception for OAuth errors."""
    pass


class InvalidStateError(OAuthError):
    """OAuth state token is invalid or expired."""
    pass


class InvalidRedirectURIError(OAuthError):
    """Redirect URI is not in the whitelist."""
    pass


class UnverifiedAccountError(OAuthError):
    """Account with this email exists but is unverified."""
    def __init__(self, email: str):
        self.email = email
        super().__init__(f"Unverified account exists: {email}")


class GoogleAccountAlreadyLinkedError(OAuthError):
    """Google account is already linked to a different user."""
    pass


class GoogleOAuthService:
    """Service for handling Google OAuth 2.0 authentication."""
    
    def __init__(self):
        self.client_id = settings.GOOGLE_OAUTH_CLIENT_ID
        self.client_secret = settings.GOOGLE_OAUTH_CLIENT_SECRET
        self.scopes = settings.GOOGLE_OAUTH_SCOPES
        self.allowed_redirect_uris = settings.OAUTH_ALLOWED_REDIRECT_URIS
        self.state_expiration = settings.OAUTH_STATE_EXPIRATION
        
        if not self.client_id or not self.client_secret:
            raise ValueError("Google OAuth credentials not configured")
    
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
        self.validate_redirect_uri(redirect_uri)
        
        # Generate PKCE pair
        code_verifier, code_challenge = self.generate_pkce_pair()
        
        # Generate state token
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
        
        # Build OAuth URL
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
        
        google_oauth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(auth_params)}"
        
        logger.info(
            "OAuth flow initiated",
            extra={
                'state': state_token[:8] + '...',
                'ip': ip_address,
                'redirect_uri': redirect_uri
            }
        )
        
        return {
            'url': google_oauth_url,
            'state': state_token,
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
            flow.code_verifier = oauth_state.code_verifier
            
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
    
    @transaction.atomic
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
        google_id = google_user_info['sub']
        google_email = google_user_info['email']
        email_verified = google_user_info.get('email_verified', False)
        
        # Check if Google ID already exists
        try:
            existing_user = User.objects.get(google_id=google_id)
            logger.info(
                "OAuth login - existing Google user",
                extra={'user_id': existing_user.id, 'google_id': google_id}
            )
            return existing_user, 'login'
        except User.DoesNotExist:
            pass
        
        # Check if email exists
        try:
            existing_user = User.objects.get(email=google_email)
            
            # CRITICAL SECURITY CHECK: Prevent account takeover
            if not existing_user.email_verified:
                logger.warning(
                    "OAuth blocked - unverified account exists",
                    extra={'email': google_email, 'google_id': google_id}
                )
                raise UnverifiedAccountError(google_email)
            
            # Verified account - link Google ID
            existing_user.google_id = google_id
            existing_user.google_email = google_email
            existing_user.auth_provider = 'hybrid'
            existing_user.google_linked_at = timezone.now()
            existing_user.last_google_sync = timezone.now()
            existing_user.email_verified = True  # Ensure verified
            existing_user.save()
            
            logger.info(
                "OAuth account linked",
                extra={'user_id': existing_user.id, 'google_id': google_id}
            )
            
            return existing_user, 'linked'
            
        except User.DoesNotExist:
            pass
        
        # Create new Google-only user
        username = self._generate_username_from_email(google_email)
        
        new_user = User.objects.create(
            username=username,
            email=google_email,
            google_id=google_id,
            google_email=google_email,
            first_name=google_user_info.get('given_name', ''),
            last_name=google_user_info.get('family_name', ''),
            email_verified=True,  # Google verifies emails
            auth_provider='google',
            has_usable_password=False,  # No password set
            google_linked_at=timezone.now(),
            last_google_sync=timezone.now()
        )
        
        # Set unusable password (prevents password login)
        new_user.set_unusable_password()
        new_user.save()
        
        logger.info(
            "OAuth user created",
            extra={'user_id': new_user.id, 'google_id': google_id, 'email': google_email}
        )
        
        return new_user, 'created'
    
    def _generate_username_from_email(self, email: str) -> str:
        """Generate unique username from email.
        
        Args:
            email: Email address
            
        Returns:
            Unique username
        """
        base_username = email.split('@')[0]
        # Remove special characters
        base_username = ''.join(c for c in base_username if c.isalnum() or c == '_')
        
        # Ensure uniqueness
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1
        
        return username
    
    @transaction.atomic
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
        google_id = google_user_info['sub']
        google_email = google_user_info['email']
        
        # Verify email matches
        if user.email != google_email:
            raise OAuthError(
                f"Google email ({google_email}) doesn't match user email ({user.email})"
            )
        
        # Check if Google ID already linked to different user
        if User.objects.filter(google_id=google_id).exclude(id=user.id).exists():
            raise GoogleAccountAlreadyLinkedError(
                "This Google account is already linked to another user"
            )
        
        # Link Google account
        user.google_id = google_id
        user.google_email = google_email
        user.auth_provider = 'hybrid' if user.has_usable_password else 'google'
        user.google_linked_at = timezone.now()
        user.last_google_sync = timezone.now()
        user.email_verified = True
        user.save()
        
        logger.info(
            "Google account linked to user",
            extra={'user_id': user.id, 'google_id': google_id}
        )
        
        return user
    
    @transaction.atomic
    def unlink_google_account(self, user: User) -> User:
        """Unlink Google account from user.
        
        Args:
            user: User to unlink from
            
        Returns:
            Updated user
            
        Raises:
            OAuthError: If user has no password and can't unlink
        """
        if not user.has_usable_password:
            raise OAuthError(
                "Cannot unlink Google account without setting a password first"
            )
        
        user.google_id = None
        user.google_email = None
        user.auth_provider = 'manual'
        user.google_linked_at = None
        user.save()
        
        logger.info(
            "Google account unlinked",
            extra={'user_id': user.id}
        )
        
        return user
