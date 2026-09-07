"""Serializers for Keep reactions."""

from rest_framework import serializers

from mysite.circles.models import CircleMembership
from mysite.notification_utils import create_message

from ..models import Keep, KeepReaction


class KeepReactionSerializer(serializers.ModelSerializer):
    """Serializer for keep reactions."""

    user_display_name = serializers.CharField(source="user.display_name", read_only=True)
    keep = serializers.PrimaryKeyRelatedField(queryset=Keep.objects.all())

    class Meta:
        model = KeepReaction
        fields = [
            "id",
            "keep",
            "user",
            "user_display_name",
            "reaction_type",
            "created_at",
        ]
        read_only_fields = ["id", "user", "created_at"]

    def validate_keep(self, keep):
        user = self.context["request"].user
        if not CircleMembership.objects.filter(user=user, circle=keep.circle).exists():
            raise serializers.ValidationError(create_message("errors.circle_membership_required"))
        return keep

    def validate(self, attrs):
        # One reaction per user per keep (model unique_together); DRF only adds
        # that validator when both fields are writable, and `user` is not.
        keep = attrs.get("keep")
        if self.instance is None and keep is not None:
            user = self.context["request"].user
            if KeepReaction.objects.filter(keep=keep, user=user).exists():
                raise serializers.ValidationError({"keep": create_message("errors.reaction_exists")})
        return attrs
