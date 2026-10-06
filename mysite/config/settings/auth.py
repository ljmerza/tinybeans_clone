"""Authentication, 2FA, OAuth, and JWT settings"""

import base64
import hashlib
import os
import warnings
from datetime import timedelta

from django.core.exceptions import ImproperlyConfigured


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return int(value)


def _validate_fernet_key(candidate: str):
    import binascii

    clean = (candidate or "").strip()
    if not clean:
        return None

    padded = clean + "=" * (-len(clean) % 4)
    try:
        decoded = base64.urlsafe_b64decode(padded.encode("utf-8"))
    except (binascii.Error, ValueError):
        return None

    if len(decoded) != 32:
        return None

    # Return a normalized base64 string to guarantee padding is present.
    return base64.urlsafe_b64encode(decoded).decode("utf-8")


# Custom User Model
AUTH_USER_MODEL = "users.User"

# JWT Configuration
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    # Rotate the refresh token on every refresh and blacklist the previous one
    # (ADR-015). This bounds the lifetime of a stolen refresh token to a single
    # use and enables explicit revocation on logout. Requires
    # 'rest_framework_simplejwt.token_blacklist' in INSTALLED_APPS so the
    # OutstandingToken / BlacklistedToken tables exist.
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

# 2FA Settings
TWOFA_ENABLED = _env_flag("TWOFA_ENABLED", default=True)
TWOFA_CODE_LENGTH = 6
TWOFA_CODE_EXPIRY_MINUTES = 10
TWOFA_MAX_ATTEMPTS = 5
TWOFA_RATE_LIMIT_WINDOW = int(os.environ.get("TWOFA_RATE_LIMIT_WINDOW", 900))
TWOFA_RATE_LIMIT_MAX = int(os.environ.get("TWOFA_RATE_LIMIT_MAX", 3))
TWOFA_RECOVERY_CODE_COUNT = 10
TWOFA_ISSUER_NAME = os.environ.get("TWOFA_ISSUER_NAME", "Circles")


# 2FA Security - Encryption Key for TOTP Secrets
# SECURITY WARNING: Keep this secret! Generate with:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
def _get_twofa_encryption_key(debug: bool, secret_key: str) -> str:
    _raw_twofa_key = os.environ.get("TWOFA_ENCRYPTION_KEY")
    _normalized_twofa_key = _validate_fernet_key(_raw_twofa_key)
    if _normalized_twofa_key:
        return _normalized_twofa_key
    else:
        if debug:
            # Derive a deterministic development key from SECRET_KEY so local setups work out of the box.
            _derived_key = base64.urlsafe_b64encode(hashlib.sha256(secret_key.encode("utf-8")).digest()).decode("utf-8")
            if _raw_twofa_key:
                warnings.warn(
                    "TWOFA_ENCRYPTION_KEY is not a valid Fernet key; "
                    "using key derived from SECRET_KEY (development only).",
                    RuntimeWarning,
                    stacklevel=2,
                )
            return _derived_key
        else:
            raise ImproperlyConfigured(
                "TWOFA_ENCRYPTION_KEY must be set to a Fernet-compatible key when DEBUG is False"
            )


# This will be set by base.py after DEBUG and SECRET_KEY are available
# TWOFA_ENCRYPTION_KEY = _get_twofa_encryption_key(DEBUG, SECRET_KEY)

# 2FA Account Lockout
TWOFA_LOCKOUT_ENABLED = _env_flag("TWOFA_LOCKOUT_ENABLED", default=True)
TWOFA_LOCKOUT_DURATION_MINUTES = int(os.environ.get("TWOFA_LOCKOUT_DURATION_MINUTES", 30))
TWOFA_LOCKOUT_THRESHOLD = int(os.environ.get("TWOFA_LOCKOUT_THRESHOLD", 5))

# Trusted Devices (Remember Me)
TWOFA_TRUSTED_DEVICE_ENABLED = _env_flag("TWOFA_TRUSTED_DEVICE_ENABLED", default=True)
TWOFA_TRUSTED_DEVICE_MAX_AGE_DAYS = int(os.environ.get("TWOFA_TRUSTED_DEVICE_MAX_AGE_DAYS", 30))
TWOFA_TRUSTED_DEVICE_MAX_COUNT = int(os.environ.get("TWOFA_TRUSTED_DEVICE_MAX_COUNT", 5))
TWOFA_TRUSTED_DEVICE_ROTATION_DAYS = int(os.environ.get("TWOFA_TRUSTED_DEVICE_ROTATION_DAYS", 15))

# Google OAuth Configuration
GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
GOOGLE_OAUTH_REDIRECT_URI = os.environ.get("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:3000/auth/google/callback")

# Security: Allowed redirect URIs (whitelist), exact match. Prevents open
# redirects. The SPA sends `<browser origin>/auth/google-callback`, so list one
# entry per origin the app is served from, e.g.
#   OAUTH_ALLOWED_REDIRECT_URIS=https://app.example.com/auth/google-callback
# Each entry must also be an authorized redirect URI on the Google OAuth client.
_DEV_OAUTH_REDIRECT_URIS = [
    "http://localhost:3053/auth/google-callback",
    "http://127.0.0.1:3053/auth/google-callback",
    "http://localhost:3000/auth/google-callback",
]


def _get_oauth_allowed_redirect_uris(debug: bool) -> list:
    """Comma-separated OAUTH_ALLOWED_REDIRECT_URIS; localhost defaults only when DEBUG."""
    value = os.environ.get("OAUTH_ALLOWED_REDIRECT_URIS")
    if not value:
        return list(_DEV_OAUTH_REDIRECT_URIS) if debug else []
    return [item.strip() for item in value.split(",") if item.strip()]


# This will be set by base.py after DEBUG is available
# OAUTH_ALLOWED_REDIRECT_URIS = _get_oauth_allowed_redirect_uris(DEBUG)

# OAuth state expiration (seconds)
# State tokens expire after 10 minutes to prevent stale requests
OAUTH_STATE_EXPIRATION = int(os.environ.get("OAUTH_STATE_EXPIRATION", 600))

# OAuth rate limiting
# Prevent abuse of OAuth endpoints
OAUTH_RATE_LIMIT_MAX_ATTEMPTS = int(os.environ.get("OAUTH_RATE_LIMIT_MAX_ATTEMPTS", 5))
OAUTH_RATE_LIMIT_WINDOW = int(os.environ.get("OAUTH_RATE_LIMIT_WINDOW", 900))  # 15 minutes

# Google OAuth scopes
# Minimum required scopes for authentication
GOOGLE_OAUTH_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

# Sign in with Apple Configuration
# All four credentials come from the Apple Developer account: the Services ID
# (client id), the 10-character Team ID, and the ID + PEM contents of a
# "Sign in with Apple" private key (.p8). Newlines in the key may be written as
# literal "\n". Apple sign-in stays disabled, and the button hidden, until all
# four are set and APPLE_OAUTH_REDIRECT_URI is set.
APPLE_OAUTH_CLIENT_ID = os.environ.get("APPLE_OAUTH_CLIENT_ID", "")
APPLE_OAUTH_TEAM_ID = os.environ.get("APPLE_OAUTH_TEAM_ID", "")
APPLE_OAUTH_KEY_ID = os.environ.get("APPLE_OAUTH_KEY_ID", "")
APPLE_OAUTH_PRIVATE_KEY = os.environ.get("APPLE_OAUTH_PRIVATE_KEY", "").replace("\\n", "\n")

# Apple POSTs the authorization response (response_mode=form_post), so it goes
# to the API, not the SPA: https://<host>/api/auth/apple/return/. It must be
# HTTPS on a real domain and registered as a Return URL on the Services ID.
APPLE_OAUTH_REDIRECT_URI = os.environ.get("APPLE_OAUTH_REDIRECT_URI", "")

# Where the API sends the browser after Apple's POST: the SPA's
# `<browser origin>/auth/apple-callback`. Exact match, one entry per origin.
_DEV_APPLE_OAUTH_RETURN_URIS = [
    "http://localhost:3053/auth/apple-callback",
    "http://127.0.0.1:3053/auth/apple-callback",
    "http://localhost:3000/auth/apple-callback",
]


def _get_apple_oauth_allowed_return_uris(debug: bool) -> list:
    """Comma-separated APPLE_OAUTH_ALLOWED_RETURN_URIS; localhost defaults only when DEBUG."""
    value = os.environ.get("APPLE_OAUTH_ALLOWED_RETURN_URIS")
    if not value:
        return list(_DEV_APPLE_OAUTH_RETURN_URIS) if debug else []
    return [item.strip() for item in value.split(",") if item.strip()]


# This will be set by base.py after DEBUG is available
# APPLE_OAUTH_ALLOWED_RETURN_URIS = _get_apple_oauth_allowed_return_uris(DEBUG)


# Rate limiting (django-ratelimit)
def _get_ratelimit_enable(debug: bool) -> bool:
    return _env_flag("RATELIMIT_ENABLE", default=not debug)


# This will be set by base.py after DEBUG is available
# RATELIMIT_ENABLE = _get_ratelimit_enable(DEBUG)

# django-ratelimit `key="ip"` resolves the client through the proxy-aware
# resolver (TRUST_FORWARDED_FOR / TRUSTED_PROXY_IPS) instead of REMOTE_ADDR,
# which is the in-image nginx (127.0.0.1) in production.
RATELIMIT_IP_META_KEY = "mysite.security.ip_utils.ratelimit_client_ip"

PASSWORD_RESET_RATELIMIT = os.environ.get("PASSWORD_RESET_RATELIMIT", "5/15m")
PASSWORD_RESET_CONFIRM_RATELIMIT = os.environ.get("PASSWORD_RESET_CONFIRM_RATELIMIT", "10/15m")
# Applied per user and per client IP; every attempt counts, so it also caps
# current-password guessing from a stolen session.
PASSWORD_CHANGE_RATELIMIT = os.environ.get("PASSWORD_CHANGE_RATELIMIT", "5/15m")
EMAIL_VERIFICATION_RESEND_RATELIMIT = os.environ.get("EMAIL_VERIFICATION_RESEND_RATELIMIT", "5/15m")
EMAIL_VERIFICATION_CONFIRM_RATELIMIT = os.environ.get("EMAIL_VERIFICATION_CONFIRM_RATELIMIT", "10/15m")
CIRCLE_INVITE_RATELIMIT = os.environ.get("CIRCLE_INVITE_RATELIMIT", "10/15m")
CIRCLE_INVITE_RESEND_RATELIMIT = os.environ.get("CIRCLE_INVITE_RESEND_RATELIMIT", "5/15m")
CIRCLE_INVITE_CIRCLE_LIMIT = _env_int("CIRCLE_INVITE_CIRCLE_LIMIT", 25)
CIRCLE_INVITE_CIRCLE_LIMIT_WINDOW_MINUTES = _env_int("CIRCLE_INVITE_CIRCLE_LIMIT_WINDOW_MINUTES", 60)
CIRCLE_INVITE_REMINDER_DELAY_MINUTES = _env_int("CIRCLE_INVITE_REMINDER_DELAY_MINUTES", 1440)
CIRCLE_INVITE_REMINDER_COOLDOWN_MINUTES = _env_int("CIRCLE_INVITE_REMINDER_COOLDOWN_MINUTES", 1440)
CIRCLE_INVITE_REMINDER_BATCH_SIZE = _env_int("CIRCLE_INVITE_REMINDER_BATCH_SIZE", 100)
CIRCLE_INVITE_ONBOARDING_TTL_MINUTES = _env_int("CIRCLE_INVITE_ONBOARDING_TTL_MINUTES", 60)

# Email verification token expiry (defaults to 48 hours for local/dev)
EMAIL_VERIFICATION_TOKEN_TTL_HOURS = _env_int("EMAIL_VERIFICATION_TOKEN_TTL_HOURS", 48)
EMAIL_VERIFICATION_TOKEN_TTL_SECONDS = EMAIL_VERIFICATION_TOKEN_TTL_HOURS * 60 * 60
EMAIL_VERIFICATION_ENFORCED = _env_flag("EMAIL_VERIFICATION_ENFORCED", default=True)
