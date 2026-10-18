"""Serializers for child profile upgrade flows."""

from __future__ import annotations

from django.utils import timezone
from rest_framework import serializers

from mysite.notification_utils import create_message

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
            "id",
            "display_name",
            "birthdate",
            "avatar_url",
            "pronouns",
            "upgrade_status",
            "pending_invite_email",
            "linked_user",
        ]
        read_only_fields = ["upgrade_status", "pending_invite_email", "linked_user"]


class ChildBirthdateSerializer(serializers.ModelSerializer):
    """A child's name and birthdate, for the circle settings page; only the birthdate can be changed."""

    class Meta:
        model = ChildProfile
        fields = ["id", "display_name", "birthdate"]
        read_only_fields = ["id", "display_name"]

    def validate_birthdate(self, value):
        if value and value > timezone.localdate():
            raise serializers.ValidationError(create_message("errors.birthdate_in_future"))
        return value


class ChildProfileUpgradeRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
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
        child = self.context["child"]
        if child.upgrade_status == ChildProfileUpgradeStatus.LINKED:
            raise serializers.ValidationError(create_message("errors.child_already_linked"))
        attrs["email"] = attrs["email"].lower()
        if User.objects.filter(email__iexact=attrs["email"]).exists():
            raise serializers.ValidationError({"email": create_message("errors.email_already_registered")})
        if "consent_metadata" not in attrs or attrs["consent_metadata"] is None:
            attrs["consent_metadata"] = {}
        return attrs


class ChildProfileUpgradeConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": create_message("errors.password_mismatch")})
        return attrs


__all__ = [
    "ChildBirthdateSerializer",
    "ChildProfileSerializer",
    "ChildProfileUpgradeRequestSerializer",
    "ChildProfileUpgradeConfirmSerializer",
]
