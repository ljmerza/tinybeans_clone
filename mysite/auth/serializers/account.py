"""Account and password lifecycle serializers."""
from __future__ import annotations

from django.contrib.auth import authenticate
from rest_framework import serializers

from mysite.notification_utils import create_message
from mysite.users.models import User


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)

    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs['email'], password=attrs['password'])
        if not user:
            raise serializers.ValidationError(create_message('errors.invalid_credentials'))
        if not user.is_active:
            raise serializers.ValidationError(create_message('errors.account_inactive'))
        attrs['user'] = user
        return attrs


class EmailVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, attrs):
        email = attrs['email']
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise serializers.ValidationError(create_message('errors.user_not_found'))
        attrs['user'] = user
        return attrs


class EmailVerificationConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, attrs):
        email = attrs['email']
        user = User.objects.filter(email__iexact=email).first()
        attrs['user'] = user
        return attrs


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': create_message('errors.password_mismatch')})
        return attrs


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        user = self.context['request'].user
        if not user.check_password(attrs['current_password']):
            raise serializers.ValidationError({'current_password': create_message('errors.auth.invalid_password')})
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': create_message('errors.password_mismatch')})
        return attrs


__all__ = [
    'SignupSerializer',
    'LoginSerializer',
    'EmailVerificationSerializer',
    'EmailVerificationConfirmSerializer',
    'PasswordResetRequestSerializer',
    'PasswordResetConfirmSerializer',
    'PasswordChangeSerializer',
]
