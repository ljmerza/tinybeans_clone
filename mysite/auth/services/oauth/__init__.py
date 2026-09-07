"""OAuth sub-services for Google authentication.

This package contains specialized services for handling OAuth operations:
- PKCEStateService: PKCE and state management
- GoogleAPIService: Google API interactions
- AccountLinkingService: Account linking/unlinking operations
"""

from mysite.auth.services.oauth.account_linking_service import (
    AccountLinkingService,
    GoogleAccountAlreadyLinkedError,
    UnverifiedAccountError,
)
from mysite.auth.services.oauth.google_api_service import GoogleAPIService, OAuthError
from mysite.auth.services.oauth.pkce_state_service import InvalidRedirectURIError, InvalidStateError, PKCEStateService

__all__ = [
    "PKCEStateService",
    "GoogleAPIService",
    "AccountLinkingService",
    "OAuthError",
    "InvalidStateError",
    "InvalidRedirectURIError",
    "UnverifiedAccountError",
    "GoogleAccountAlreadyLinkedError",
]
