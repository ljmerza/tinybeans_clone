"""Serializers for circle management workflows."""
from __future__ import annotations

from rest_framework import serializers

from mysite.notification_utils import create_message
from ..models import (
    Circle,
    CircleInvitation,
    CircleInvitationStatus,
    CircleMembership,
    User,
    UserRole,
)
from .core import CircleSerializer, UserSerializer


class CircleMembershipSerializer(serializers.ModelSerializer):
    membership_id = serializers.IntegerField(source='id', read_only=True)
    circle = CircleSerializer()

    class Meta:
        model = CircleMembership
        fields = ['membership_id', 'circle', 'role', 'created_at']


class CircleMemberSerializer(serializers.ModelSerializer):
    membership_id = serializers.IntegerField(source='id', read_only=True)
    user = UserSerializer()

    class Meta:
        model = CircleMembership
        fields = ['membership_id', 'user', 'role', 'created_at']


class CircleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Circle
        fields = ['id', 'name', 'slug', 'created_at']
        read_only_fields = ['id', 'slug', 'created_at']

    def validate(self, attrs):
        user = self.context['user']
        if not user.email_verified:
            raise serializers.ValidationError(create_message('errors.email_verification_required'))
        return attrs

    def create(self, validated_data):
        user = self.context['user']
        circle = Circle.objects.create(created_by=user, **validated_data)
        CircleMembership.objects.create(user=user, circle=circle, role=UserRole.CIRCLE_ADMIN)
        return circle


class CircleMemberAddSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    role = serializers.ChoiceField(choices=UserRole.choices, required=False)

    def validate(self, attrs):
        circle = self.context['circle']
        try:
            user = User.objects.get(id=attrs['user_id'])
        except User.DoesNotExist:
            raise serializers.ValidationError({'user_id': create_message('errors.user_not_found')})

        if CircleMembership.objects.filter(circle=circle, user=user).exists():
            raise serializers.ValidationError({'user_id': create_message('errors.circle_member_exists')})

        attrs['user'] = user
        attrs['role'] = attrs.get('role') or UserRole.CIRCLE_MEMBER
        return attrs

    def create(self, validated_data):
        circle = self.context['circle']
        invited_by = self.context.get('invited_by')
        membership = CircleMembership.objects.create(
            circle=circle,
            user=validated_data['user'],
            role=validated_data['role'],
            invited_by=invited_by,
        )
        return membership


class CircleInvitationSerializer(serializers.ModelSerializer):
    circle = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = CircleInvitation
        fields = ['id', 'circle', 'email', 'role', 'status', 'created_at', 'responded_at']
        read_only_fields = ['id', 'circle', 'status', 'created_at', 'responded_at']


class CircleInvitationCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=UserRole.choices, required=False)

    def validate(self, attrs):
        circle = self.context['circle']
        email = attrs['email'].lower()
        if CircleMembership.objects.filter(circle=circle, user__email__iexact=email).exists():
            raise serializers.ValidationError({'email': create_message('errors.circle_member_exists')})
        if CircleInvitation.objects.filter(
            circle=circle,
            email__iexact=email,
            status=CircleInvitationStatus.PENDING,
        ).exists():
            raise serializers.ValidationError({'email': create_message('errors.invitation_pending_for_email')})
        attrs['email'] = email
        attrs['role'] = attrs.get('role') or UserRole.CIRCLE_MEMBER
        return attrs


class CircleInvitationResponseSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['accept', 'decline'])

    def validate(self, attrs):
        invitation = self.context['invitation']
        if invitation.status != CircleInvitationStatus.PENDING:
            raise serializers.ValidationError(create_message('errors.invitation_not_pending'))
        attrs['action'] = attrs['action'].lower()
        return attrs


class CircleInvitationAcceptSerializer(serializers.Serializer):
    token = serializers.CharField()
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': create_message('errors.password_mismatch')})
        if User.objects.filter(username=attrs['username']).exists():
            raise serializers.ValidationError({'username': create_message('errors.username_taken')})
        return attrs


__all__ = [
    'CircleMembershipSerializer',
    'CircleMemberSerializer',
    'CircleCreateSerializer',
    'CircleMemberAddSerializer',
    'CircleInvitationSerializer',
    'CircleInvitationCreateSerializer',
    'CircleInvitationResponseSerializer',
    'CircleInvitationAcceptSerializer',
]
