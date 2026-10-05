"""Serializers for notification delivery: the phone texts go to and push devices."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from django.conf import settings
from rest_framework import serializers

from mysite.notification_utils import create_message

E164_PATTERN = re.compile(r"^\+[1-9]\d{6,14}$")
# Spacing and punctuation people type in phone numbers.
PHONE_SEPARATORS = re.compile(r"[\s().-]")


class NotificationPhoneSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=30)

    def validate_phone_number(self, value):
        number = PHONE_SEPARATORS.sub("", value)
        if not E164_PATTERN.match(number):
            raise serializers.ValidationError(create_message("errors.notification_phone_invalid"))
        allowed = settings.NOTIFICATIONS_SMS_ALLOWED_PREFIXES
        if allowed and not any(number.startswith(prefix) for prefix in allowed):
            raise serializers.ValidationError(create_message("errors.notification_phone_country_unsupported"))
        return number


class NotificationPhoneVerifySerializer(serializers.Serializer):
    code = serializers.RegexField(r"^\d{6}$")


class PushSubscriptionKeysSerializer(serializers.Serializer):
    p256dh = serializers.CharField(max_length=200)
    auth = serializers.CharField(max_length=100)


class PushSubscriptionSerializer(serializers.Serializer):
    """A browser's ``PushSubscription.toJSON()``; other fields it sends are ignored."""

    endpoint = serializers.URLField(max_length=1000)
    keys = PushSubscriptionKeysSerializer()

    def validate_endpoint(self, value):
        # The server POSTs to this URL, so only known push services are accepted.
        parsed = urlparse(value)
        host = (parsed.hostname or "").lower()
        allowed = settings.PUSH_ALLOWED_ENDPOINT_HOSTS
        if parsed.scheme != "https" or not any(host == suffix or host.endswith(f".{suffix}") for suffix in allowed):
            raise serializers.ValidationError(create_message("errors.push_endpoint_unsupported"))
        return value


class PushUnsubscribeSerializer(serializers.Serializer):
    endpoint = serializers.URLField(max_length=1000)


__all__ = [
    "NotificationPhoneSerializer",
    "NotificationPhoneVerifySerializer",
    "PushSubscriptionSerializer",
    "PushUnsubscribeSerializer",
]
