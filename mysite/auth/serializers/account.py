"""Account and password lifecycle serializers."""

from __future__ import annotations

from django.contrib.auth import authenticate
from rest_framework import serializers

from mysite.notification_utils import create_message
from mysite.users.models import User
from mysite.users.models.user import Language


class PreferredLanguageField(serializers.CharField):
    """Optional UI language for a new account.

    Unsupported codes become ``None`` rather than a validation error, so the
    caller can drop the value and let the model default apply.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("required", False)
        kwargs.setdefault("allow_null", True)
        kwargs.setdefault("allow_blank", True)
        kwargs.setdefault("write_only", True)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        return value if value in Language.values else None


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    language = PreferredLanguageField(help_text="Preferred UI language; unsupported values use the default.")

    class Meta:
        model = User
        fields = ["email", "password", "first_name", "last_name", "language"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        if not validated_data.get("language"):
            validated_data.pop("language", None)
        user = User.objects.create_user(password=password, **validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs["email"], password=attrs["password"])
        if not user:
            raise serializers.ValidationError(create_message("errors.invalid_credentials"))
        if not user.is_active:
            raise serializers.ValidationError(create_message("errors.account_inactive"))
        attrs["user"] = user
        return attrs


class EmailVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, attrs):
        email = attrs["email"]
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise serializers.ValidationError(create_message("errors.user_not_found"))
        attrs["user"] = user
        return attrs


class EmailVerificationConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, attrs):
        email = attrs["email"]
        user = User.objects.filter(email__iexact=email).first()
        attrs["user"] = user
        return attrs


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": create_message("errors.password_mismatch")})
        return attrs


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError({"current_password": create_message("errors.auth.invalid_password")})
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": create_message("errors.password_mismatch")})
        return attrs


__all__ = [
    "PreferredLanguageField",
    "SignupSerializer",
    "LoginSerializer",
    "EmailVerificationSerializer",
    "EmailVerificationConfirmSerializer",
    "PasswordResetRequestSerializer",
    "PasswordResetConfirmSerializer",
    "PasswordChangeSerializer",
]
