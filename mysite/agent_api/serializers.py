"""Serializers for token management and the agent API's one write."""

from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from .hygiene import strip_hidden
from .models import CircleApiToken

# A token must last at least this long, so a typo can't make one that is dead on arrival.
MIN_LIFETIME = timedelta(hours=1)


class ApiTokenSerializer(serializers.ModelSerializer):
    """A token as admins see it: never the hash, never the plaintext."""

    status = serializers.CharField(read_only=True)
    created_by = serializers.SerializerMethodField()

    class Meta:
        model = CircleApiToken
        fields = [
            "id",
            "name",
            "display_prefix",
            "can_suggest",
            "status",
            "created_by",
            "created_at",
            "expires_at",
            "last_used_at",
            "last_used_ip",
            "revoked_at",
            "revoked_reason",
        ]
        read_only_fields = fields

    def get_created_by(self, token):
        return {"id": token.created_by_id, "display_name": token.created_by.display_name}


class ApiTokenCreateSerializer(serializers.Serializer):
    # Lengths match the model columns (a test checks): SQLite in tests doesn't enforce them, Postgres does.
    name = serializers.CharField(max_length=100)
    can_suggest = serializers.BooleanField(default=False)
    expires_at = serializers.DateTimeField(allow_null=True)
    code = serializers.CharField(max_length=32, write_only=True)

    def validate_expires_at(self, value):
        if value is not None and value <= timezone.now() + MIN_LIFETIME:
            raise serializers.ValidationError("Choose a time at least an hour from now, or no expiry.")
        return value


class MilestoneSuggestionCreateSerializer(serializers.Serializer):
    post_id = serializers.UUIDField()
    # Lengths match MilestoneSuggestion's columns (a test checks).
    label = serializers.CharField(max_length=80)
    reason = serializers.CharField(max_length=500)

    def _visible(self, value):
        value = strip_hidden(value).strip()
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate_label(self, value):
        return self._visible(value)

    def validate_reason(self, value):
        return self._visible(value)
