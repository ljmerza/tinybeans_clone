"""Authentication and account lifecycle serializers."""
from __future__ import annotations

from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..models import Circle, CircleMembership, User, UserRole
from .core import CircleSerializer, UserSerializer


class SignupSerializer(serializers.ModelSerializer):
    circle_name = serializers.CharField(required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=UserRole.choices, required=False)
    password = serializers.CharField(write_only=True, min_length=8)
    create_circle = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'circle_name', 'role', 'create_circle']

    def validate_role(self, value):
        if value == UserRole.CIRCLE_ADMIN:
            return value
        return value or UserRole.CIRCLE_MEMBER

    def validate(self, attrs):
        attrs = super().validate(attrs)
        create_circle = attrs.get('create_circle', False)
        circle_name = (attrs.get('circle_name') or '').strip()
        attrs['circle_name'] = circle_name

        if not create_circle:
            if circle_name:
                raise serializers.ValidationError(
                    {'circle_name': _('Circle name can only be provided when create_circle is true.')}
                )
            if attrs.get('role') == UserRole.CIRCLE_ADMIN:
                raise serializers.ValidationError(
                    {'role': _('Circle admin role requires creating a circle during signup.')}
                )

        return attrs

    def create(self, validated_data):
        circle_name = validated_data.pop('circle_name', '')
        role = validated_data.pop('role', UserRole.CIRCLE_MEMBER)
        create_circle = validated_data.pop('create_circle', True)
        password = validated_data.pop('password')

        user = User.objects.create_user(password=password, role=role, **validated_data)

        circle = None
        if create_circle:
            if not circle_name:
                circle_name = f"{user.username}'s Circle"

            circle = Circle.objects.create(name=circle_name, created_by=user)
            CircleMembership.objects.create(user=user, circle=circle, role=UserRole.CIRCLE_ADMIN)
            if user.role != UserRole.CIRCLE_ADMIN:
                user.role = UserRole.CIRCLE_ADMIN
                user.save(update_fields=['role'])

        return user, circle

    def to_representation(self, instance_tuple):
        user, circle = instance_tuple
        data = UserSerializer(user).data
        data['circle'] = CircleSerializer(circle).data if circle else None
        data['pending_circle_setup'] = circle is None
        return data


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


__all__ = [
    'SignupSerializer',
    'LoginSerializer',
    'EmailVerificationSerializer',
    'EmailVerificationConfirmSerializer',
    'PasswordResetRequestSerializer',
    'PasswordResetConfirmSerializer',
    'PasswordChangeSerializer',
]
