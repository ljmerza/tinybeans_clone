"""Two-Factor Authentication Serializers"""
from rest_framework import serializers
from .models import TwoFactorSettings, RecoveryCode, TrustedDevice


class TwoFactorSetupSerializer(serializers.Serializer):
    """Serializer for initiating 2FA setup"""
    method = serializers.ChoiceField(
        choices=['totp', 'email', 'sms'],
        required=True,
        help_text="2FA method to set up"
    )
    phone_number = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        help_text="Phone number in E.164 format (required for SMS)"
    )


class TwoFactorVerifySetupSerializer(serializers.Serializer):
    """Serializer for verifying 2FA setup"""
    code = serializers.CharField(
        min_length=6,
        max_length=6,
        required=True,
        help_text="6-digit verification code"
    )


class TwoFactorVerifySerializer(serializers.Serializer):
    """Serializer for verifying 2FA code during login"""
    code = serializers.CharField(
        min_length=6,
        max_length=6,
        required=True,
        help_text="6-digit verification code or recovery code"
    )
    remember_me = serializers.BooleanField(
        default=False,
        required=False,
        help_text="Trust this device for 30 days"
    )


class TwoFactorStatusSerializer(serializers.ModelSerializer):
    """Serializer for 2FA settings status"""

    has_totp = serializers.SerializerMethodField()
    has_sms = serializers.SerializerMethodField()

    class Meta:
        model = TwoFactorSettings
        fields = [
            'is_enabled',
            'preferred_method',
            'phone_number',
            'backup_email',
            'created_at',
            'updated_at',
            'has_totp',
            'has_sms',
            'sms_verified',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_has_totp(self, obj):
        # Consider TOTP configured only after full verification (i.e., 2FA is enabled)
        return bool(getattr(obj, '_totp_secret_encrypted', None)) and bool(obj.is_enabled)

    def get_has_sms(self, obj):
        # Consider SMS configured only after phone number verification
        return bool(obj.phone_number) and bool(obj.sms_verified)


class RecoveryCodeSerializer(serializers.ModelSerializer):
    """Serializer for recovery codes"""
    class Meta:
        model = RecoveryCode
        fields = ['code', 'is_used', 'created_at']
        read_only_fields = ['code', 'is_used', 'created_at']


class TrustedDeviceSerializer(serializers.ModelSerializer):
    """Serializer for trusted devices"""
    class Meta:
        model = TrustedDevice
        fields = [
            'device_id',
            'device_name',
            'ip_address',
            'last_used_at',
            'expires_at',
            'created_at'
        ]
        read_only_fields = fields


class TwoFactorDisableSerializer(serializers.Serializer):
    """Serializer for disabling 2FA"""
    code = serializers.CharField(
        min_length=6,
        max_length=6,
        required=True,
        help_text="Current 2FA code to confirm disable"
    )


class TwoFactorVerifyLoginSerializer(serializers.Serializer):
    """Serializer for verifying 2FA during login"""
    code = serializers.CharField(
        required=True,
        help_text="6-digit verification code or recovery code (XXXX-XXXX-XXXX)"
    )
    partial_token = serializers.CharField(
        required=True,
        help_text="Partial token received from login"
    )
    remember_me = serializers.BooleanField(
        default=False,
        required=False,
        help_text="Trust this device for 30 days"
    )


class TwoFactorPreferredMethodSerializer(serializers.Serializer):
    """Serializer for updating the preferred 2FA method"""

    method = serializers.ChoiceField(
        choices=['totp', 'email', 'sms'],
        required=True,
        help_text="Method to make the default for future verifications",
    )


class TwoFactorMethodRemoveSerializer(serializers.Serializer):
    """Serializer for validating removable 2FA method names"""

    method = serializers.ChoiceField(
        choices=['totp', 'sms', 'email'],
        required=True,
        help_text="2FA method to remove",
    )
