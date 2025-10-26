"""Google OAuth views package.

This package contains all Google OAuth-related views split into modules:
- initiate.py: OAuth flow initiation
- callback.py: OAuth callback handling
- linking.py: Account linking and unlinking
- helpers.py: Shared utility functions
"""
from mysite.auth.views.google_oauth.initiate import GoogleOAuthInitiateView
from mysite.auth.views.google_oauth.callback import GoogleOAuthCallbackView
from mysite.auth.views.google_oauth.linking import (
    GoogleOAuthLinkView,
    GoogleOAuthUnlinkView
)

__all__ = [
    'GoogleOAuthInitiateView',
    'GoogleOAuthCallbackView',
    'GoogleOAuthLinkView',
    'GoogleOAuthUnlinkView',
]
