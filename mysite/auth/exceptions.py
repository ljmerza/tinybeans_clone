"""Custom exceptions for authentication module."""


class OAuthError(Exception):
    """Base exception for OAuth errors."""
    pass


class InvalidStateTokenError(OAuthError):
    """OAuth state token is invalid or expired."""
    pass


class InvalidRedirectURIError(OAuthError):
    """Redirect URI is not in the whitelist."""
    pass


class UnverifiedAccountExistsError(OAuthError):
    """Account with this email exists but is unverified."""
    def __init__(self, email: str):
        self.email = email
        super().__init__(f"Unverified account exists: {email}")


class GoogleOAuthError(OAuthError):
    """General Google OAuth error."""
    pass


class GoogleAccountAlreadyLinkedError(OAuthError):
    """Google account is already linked to a different user."""
    pass


# Backwards compatibility aliases
InvalidStateError = InvalidStateTokenError
UnverifiedAccountError = UnverifiedAccountExistsError
