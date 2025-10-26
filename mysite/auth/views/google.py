"""Google OAuth API Views.

This module re-exports all Google OAuth views for backward compatibility.
The views have been split into specialized modules in the google_oauth/ subdirectory:
- initiate.py: OAuth flow initiation
- callback.py: OAuth callback handling
- linking.py: Account linking and unlinking
- helpers.py: Shared utility functions

All views are imported from their respective modules below.
"""
from mysite.auth.views.google_oauth import (
    GoogleOAuthInitiateView,
    GoogleOAuthCallbackView,
    GoogleOAuthLinkView,
    GoogleOAuthUnlinkView,
)

__all__ = [
    'GoogleOAuthInitiateView',
    'GoogleOAuthCallbackView',
    'GoogleOAuthLinkView',
    'GoogleOAuthUnlinkView',
]
