"""Authentication and account lifecycle serializers."""
from __future__ import annotations

from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from users.models import User


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs['username'], password=attrs['password'])
        if not user:
            raise serializers.ValidationError(_('Invalid username or password'))
        if not user.is_active:
            raise serializers.ValidationError(_('User account is inactive'))
        attrs['user'] = user
        return attrs


class EmailVerificationSerializer(serializers.Serializer):
    identifier = serializers.CharField()

    def validate(self, attrs):
        identifier = attrs['identifier']
        try:
            user = User.objects.get(username=identifier)
        except User.DoesNotExist:
            user = User.objects.filter(email__iexact=identifier).first()
        if not user:
            raise serializers.ValidationError(_('User not found'))
        attrs['user'] = user
        return attrs


class EmailVerificationConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()


class PasswordResetRequestSerializer(serializers.Serializer):
    identifier = serializers.CharField()

    def validate(self, attrs):
        identifier = attrs['identifier']
        user = User.objects.filter(username=identifier).first()
        if not user:
            user = User.objects.filter(email__iexact=identifier).first()
        attrs['user'] = user
        return attrs


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': _('Passwords do not match')})
        return attrs


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        user = self.context['request'].user
        if not user.check_password(attrs['current_password']):
            raise serializers.ValidationError({'current_password': _('Current password is incorrect')})
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': _('Passwords do not match')})
        return attrs


class MagicLoginRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, attrs):
        email = attrs['email']
        user = User.objects.filter(email__iexact=email).first()
        attrs['user'] = user
        return attrs


class MagicLoginVerifySerializer(serializers.Serializer):
    token = serializers.CharField()


# Google OAuth Serializers

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
        help_text="JWT refresh token (long-lived)"
    )


class OAuthCallbackResponseSerializer(serializers.Serializer):
    """Response serializer for OAuth callback."""
    from users.serializers import UserSerializer
    
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
    from users.serializers import UserSerializer
    
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
    from users.serializers import UserSerializer
    
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
    'SignupSerializer',
    'LoginSerializer',
    'EmailVerificationSerializer',
    'EmailVerificationConfirmSerializer',
    'PasswordResetRequestSerializer',
    'PasswordResetConfirmSerializer',
    'PasswordChangeSerializer',
    'MagicLoginRequestSerializer',
    'MagicLoginVerifySerializer',
    # OAuth serializers
    'OAuthInitiateRequestSerializer',
    'OAuthInitiateResponseSerializer',
    'OAuthCallbackRequestSerializer',
    'OAuthCallbackResponseSerializer',
    'OAuthLinkRequestSerializer',
    'OAuthLinkResponseSerializer',
    'OAuthUnlinkRequestSerializer',
    'OAuthUnlinkResponseSerializer',
    'OAuthErrorSerializer',
    'JWTTokenSerializer',
]
