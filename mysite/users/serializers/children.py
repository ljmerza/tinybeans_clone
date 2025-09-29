"""Serializers for child profile upgrade flows."""
from __future__ import annotations

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..models import (
    ChildProfile,
    ChildProfileUpgradeStatus,
    GuardianConsentMethod,
    User,
)


class ChildProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChildProfile
        fields = [
            'id',
            'display_name',
            'birthdate',
            'avatar_url',
            'pronouns',
            'upgrade_status',
            'pending_invite_email',
            'linked_user',
        ]
        read_only_fields = ['upgrade_status', 'pending_invite_email', 'linked_user']


class ChildProfileUpgradeRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    username = serializers.CharField(required=False)
    guardian_name = serializers.CharField()
    guardian_relationship = serializers.CharField()
    consent_method = serializers.ChoiceField(
        choices=GuardianConsentMethod.choices,
        required=False,
        default=GuardianConsentMethod.DIGITAL_SIGNATURE,
    )
    agreement_reference = serializers.CharField(required=False, allow_blank=True)
    consent_metadata = serializers.JSONField(required=False)

    def validate(self, attrs):
        child = self.context['child']
        if child.upgrade_status == ChildProfileUpgradeStatus.LINKED:
            raise serializers.ValidationError(_('Child profile already linked'))
        attrs['email'] = attrs['email'].lower()
        if User.objects.filter(email__iexact=attrs['email']).exists():
            raise serializers.ValidationError({'email': _('A user with this email already exists. Ask them to log in.')})
        username = attrs.get('username')
        if username and User.objects.filter(username=username).exists():
            raise serializers.ValidationError({'username': _('Username is already taken')})
        if 'consent_metadata' not in attrs or attrs['consent_metadata'] is None:
            attrs['consent_metadata'] = {}
        return attrs


class ChildProfileUpgradeConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': _('Passwords do not match')})
        if User.objects.filter(username=attrs['username']).exists():
            raise serializers.ValidationError({'username': _('Username is already taken')})
        return attrs


__all__ = [
    'ChildProfileSerializer',
    'ChildProfileUpgradeRequestSerializer',
    'ChildProfileUpgradeConfirmSerializer',
]
