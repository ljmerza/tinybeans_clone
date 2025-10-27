"""Google OAuth serializers."""
from __future__ import annotations

from rest_framework import serializers

from mysite.users.serializers import UserSerializer


class OAuthInitiateRequestSerializer(serializers.Serializer):
    """Request serializer for OAuth initiation."""
    redirect_uri = serializers.URLField(
        required=True,
        help_text="The URI to redirect to after OAuth completes"
    )


class OAuthInitiateResponseSerializer(serializers.Serializer):
    """Response serializer for OAuth initiation."""
    google_oauth_url = serializers.URLField(
        help_text="The Google OAuth URL to redirect the user to"
    )
    state = serializers.CharField(
        help_text="OAuth state token for CSRF protection"
    )
    expires_in = serializers.IntegerField(
        help_text="Seconds until state token expires"
    )


class OAuthCallbackRequestSerializer(serializers.Serializer):
    """Request serializer for OAuth callback."""
    code = serializers.CharField(
        required=True,
        max_length=512,
        help_text="Authorization code from Google"
    )
    state = serializers.CharField(
        required=True,
        max_length=512,
        help_text="OAuth state token"
    )


class JWTTokenSerializer(serializers.Serializer):
    """JWT token pair serializer."""
    access = serializers.CharField(
        help_text="JWT access token (short-lived)"
    )
    refresh = serializers.CharField(
        help_text="JWT refresh token (long-lived)",
        required=False,
        allow_blank=True
    )


class OAuthCallbackResponseSerializer(serializers.Serializer):
    """Response serializer for OAuth callback."""

    user = UserSerializer(
        help_text="User information"
    )
    tokens = JWTTokenSerializer(
        help_text="JWT authentication tokens"
    )
    account_action = serializers.ChoiceField(
        choices=['created', 'linked', 'login'],
        help_text="Action taken: created new account, linked existing, or logged in"
    )


class OAuthLinkRequestSerializer(serializers.Serializer):
    """Request serializer for linking Google account."""
    code = serializers.CharField(
        required=True,
        max_length=512,
        help_text="Authorization code from Google"
    )
    state = serializers.CharField(
        required=True,
        max_length=512,
        help_text="OAuth state token"
    )


class OAuthLinkResponseSerializer(serializers.Serializer):
    """Response serializer for linking Google account."""

    message = serializers.CharField(
        help_text="Success message"
    )
    user = UserSerializer(
        help_text="Updated user information"
    )


class OAuthUnlinkRequestSerializer(serializers.Serializer):
    """Request serializer for unlinking Google account."""
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        help_text="User's password for verification"
    )


class OAuthUnlinkResponseSerializer(serializers.Serializer):
    """Response serializer for unlinking Google account."""

    message = serializers.CharField(
        help_text="Success message"
    )
    user = UserSerializer(
        help_text="Updated user information"
    )


class OAuthErrorSerializer(serializers.Serializer):
    """Error response serializer."""
    error = serializers.DictField(
        child=serializers.CharField(),
        help_text="Error details"
    )


__all__ = [
    'JWTTokenSerializer',
    'OAuthCallbackRequestSerializer',
    'OAuthCallbackResponseSerializer',
    'OAuthErrorSerializer',
    'OAuthInitiateRequestSerializer',
    'OAuthInitiateResponseSerializer',
    'OAuthLinkRequestSerializer',
    'OAuthLinkResponseSerializer',
    'OAuthUnlinkRequestSerializer',
    'OAuthUnlinkResponseSerializer',
]
