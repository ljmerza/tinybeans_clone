"""Magic login serializers."""
from __future__ import annotations

from rest_framework import serializers

from mysite.users.models import User


class MagicLoginRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, attrs):
        email = attrs['email']
        user = User.objects.filter(email__iexact=email).first()
        attrs['user'] = user
        return attrs


class MagicLoginVerifySerializer(serializers.Serializer):
    token = serializers.CharField()


__all__ = [
    'MagicLoginRequestSerializer',
    'MagicLoginVerifySerializer',
]
