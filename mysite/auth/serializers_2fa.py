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
    has_email = serializers.SerializerMethodField()
    preferred_method = serializers.SerializerMethodField()
    email_address = serializers.SerializerMethodField()

    class Meta:
        model = TwoFactorSettings
        fields = [
            'is_enabled',
            'preferred_method',
            'phone_number',
            'backup_email',
            'email_address',
            'created_at',
            'updated_at',
            'has_totp',
            'has_sms',
            'has_email',
            'sms_verified',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_has_totp(self, obj):
        # Consider TOTP configured only after verification
        return bool(getattr(obj, '_totp_secret_encrypted', None)) and bool(obj.totp_verified)

    def get_has_sms(self, obj):
        # Consider SMS configured only after phone number verification
        return bool(obj.phone_number) and bool(obj.sms_verified)

    def get_has_email(self, obj):
        # Consider email configured only after verification
        return bool(obj.email_verified)

    def get_preferred_method(self, obj):
        # If no methods are enabled, return None
        has_any_method = (
            self.get_has_totp(obj) or 
            self.get_has_sms(obj) or 
            self.get_has_email(obj)
        )
        if not has_any_method:
            return None
        return obj.preferred_method

    def get_email_address(self, obj):
        # Prefer backup email when present, otherwise fall back to primary account email
        if obj.backup_email:
            return obj.backup_email
        return getattr(obj.user, 'email', None)


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
