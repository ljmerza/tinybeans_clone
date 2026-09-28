"""Serializers for Keep comments."""

from rest_framework import serializers

from mysite.circles.models import CircleMembership
from mysite.notification_utils import create_message
from mysite.users.models import UserRole

from ..models import Keep, KeepComment


def can_delete_comment(comment, context):
    """Whether the requesting user may delete `comment`: its author or an admin of its circle.

    Mirrors ``KeepCommentDetailView.perform_destroy``. The viewer's admin circles
    are looked up once and cached in the serializer context, which nested and
    list serializers share, so a page of comments costs one extra query.
    """
    request = context.get("request")
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return False
    if comment.user_id == user.id:
        return True
    if "admin_circle_ids" not in context:
        context["admin_circle_ids"] = set(
            CircleMembership.objects.filter(user=user, role=UserRole.CIRCLE_ADMIN).values_list("circle_id", flat=True)
        )
    return comment.keep.circle_id in context["admin_circle_ids"]


class KeepCommentSerializer(serializers.ModelSerializer):
    """Serializer for keep comments."""

    user_display_name = serializers.CharField(source="user.display_name", read_only=True)
    can_delete = serializers.SerializerMethodField()
    keep = serializers.PrimaryKeyRelatedField(queryset=Keep.objects.all())
    parent = serializers.PrimaryKeyRelatedField(
        queryset=KeepComment.objects.all(),
        required=False,
        allow_null=True,
        help_text="Id of the comment this one replies to; omit for a top-level comment",
    )

    class Meta:
        model = KeepComment
        fields = [
            "id",
            "keep",
            "user",
            "user_display_name",
            "parent",
            "comment",
            "can_delete",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "can_delete", "created_at", "updated_at"]

    def get_can_delete(self, obj) -> bool:
        return can_delete_comment(obj, self.context)

    def validate_keep(self, keep):
        user = self.context["request"].user
        if not CircleMembership.objects.filter(user=user, circle=keep.circle).exists():
            raise serializers.ValidationError(create_message("errors.circle_membership_required"))
        return keep

    def validate(self, attrs):
        parent = attrs.get("parent")
        keep = attrs.get("keep") or getattr(self.instance, "keep", None)
        if parent is not None and keep is not None and parent.keep_id != keep.id:
            raise serializers.ValidationError({"parent": "Reply must be on the same keep as its parent."})
        if parent is not None:
            # Threads are one level deep: a reply to a reply joins its top-level comment.
            while parent.parent_id is not None:
                parent = parent.parent
            attrs["parent"] = parent
        return attrs
