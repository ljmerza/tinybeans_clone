"""Serializers for circle management workflows."""
from __future__ import annotations

from rest_framework import serializers

from mysite.notification_utils import create_message
from mysite.users.models import User, UserRole
from mysite.users.serializers.core import CircleSerializer, UserSerializer

from ..models import (
    Circle,
    CircleInvitation,
    CircleInvitationStatus,
    CircleMembership,
)


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
    invited_user = UserSerializer(read_only=True)
    existing_user = serializers.SerializerMethodField()

    class Meta:
        model = CircleInvitation
        fields = [
            'id',
            'circle',
            'email',
            'invited_user',
            'existing_user',
            'role',
            'status',
            'created_at',
            'responded_at',
            'reminder_sent_at',
            'archived_at',
            'archived_reason',
        ]
        read_only_fields = [
            'id',
            'circle',
            'invited_user',
            'existing_user',
            'status',
            'created_at',
            'responded_at',
            'reminder_sent_at',
            'archived_at',
            'archived_reason',
        ]

    def get_existing_user(self, obj: CircleInvitation) -> bool:
        if obj.invited_user_id:
            return True
        return User.objects.filter(email__iexact=obj.email).exists()


class CircleInvitationCreateSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    username = serializers.CharField(required=False, allow_blank=False)
    role = serializers.ChoiceField(choices=UserRole.choices, required=False)

    def validate(self, attrs):
        circle = self.context['circle']
        email = attrs.get('email')
        username = attrs.get('username')

        if not email and not username:
            raise serializers.ValidationError(
                {'identifier': create_message('errors.invitation_identifier_required')}
            )
        if email and username:
            raise serializers.ValidationError(
                {'identifier': create_message('errors.invitation_identifier_conflict')}
            )

        invited_user = None
        identifier_field = 'email'

        if username:
            try:
                invited_user = User.objects.get(username__iexact=username)
            except User.DoesNotExist:
                raise serializers.ValidationError({'username': create_message('errors.user_not_found')})
            if not invited_user.email:
                raise serializers.ValidationError({'username': create_message('errors.user_missing_email')})
            email = invited_user.email
            identifier_field = 'username'

        email = email.lower()
        if invited_user is None:
            invited_user = User.objects.filter(email__iexact=email).first()

        membership_exists = False
        if invited_user:
            membership_exists = CircleMembership.objects.filter(circle=circle, user=invited_user).exists()
        if not membership_exists:
            membership_exists = CircleMembership.objects.filter(circle=circle, user__email__iexact=email).exists()
        if membership_exists:
            raise serializers.ValidationError(
                {
                    identifier_field: create_message('errors.circle_member_exists')
                }
            )

        if CircleInvitation.objects.filter(
            circle=circle,
            status=CircleInvitationStatus.PENDING,
            email__iexact=email,
        ).exists():
            raise serializers.ValidationError(
                {
                    identifier_field: create_message('errors.invitation_pending_for_email')
                }
            )
        if invited_user and CircleInvitation.objects.filter(
            circle=circle,
            status=CircleInvitationStatus.PENDING,
            invited_user=invited_user,
        ).exists():
            raise serializers.ValidationError(
                {
                    identifier_field: create_message('errors.invitation_pending_for_email')
                }
            )

        attrs['email'] = email
        attrs['role'] = attrs.get('role') or UserRole.CIRCLE_MEMBER
        if invited_user:
            attrs['invited_user'] = invited_user
        return attrs


class CircleInvitationResponseSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['accept', 'decline'])

    def validate(self, attrs):
        invitation = self.context['invitation']
        if invitation.status != CircleInvitationStatus.PENDING:
            raise serializers.ValidationError(create_message('errors.invitation_not_pending'))
        attrs['action'] = attrs['action'].lower()
        return attrs


class CircleInvitationOnboardingStartSerializer(serializers.Serializer):
    token = serializers.CharField()


class CircleInvitationFinalizeSerializer(serializers.Serializer):
    onboarding_token = serializers.CharField()


__all__ = [
    'CircleMembershipSerializer',
    'CircleMemberSerializer',
    'CircleCreateSerializer',
    'CircleMemberAddSerializer',
    'CircleInvitationSerializer',
    'CircleInvitationCreateSerializer',
    'CircleInvitationResponseSerializer',
    'CircleInvitationOnboardingStartSerializer',
    'CircleInvitationFinalizeSerializer',
]

