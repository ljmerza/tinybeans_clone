"""Serializers for Keep comments."""

from django.db import transaction
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from mysite.circles.models import CircleMembership
from mysite.notification_utils import create_message
from mysite.users.models import UserRole

from ..models import Keep, KeepComment, KeepCommentMention

# More than anyone would mention in one family comment; bounds the write.
MAX_MENTIONS = 50

MENTIONS_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {"id": {"type": "integer"}, "display_name": {"type": "string"}},
    },
}


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


def comment_mentions(comment):
    """The members `comment` @mentions, as `{id, display_name}`, in the order they were added.

    Prefetch ``mentions__user`` when serializing many comments.
    """
    return [{"id": mention.user_id, "display_name": mention.user.display_name} for mention in comment.mentions.all()]


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
    mentions = serializers.SerializerMethodField()
    mention_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        max_length=MAX_MENTIONS,
        help_text="User ids of the circle members the comment @mentions. Anyone outside the keep's circle is "
        "dropped rather than rejected. On an update, omit it to keep the current mentions.",
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
            "mentions",
            "mention_ids",
            "can_delete",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "mentions", "can_delete", "created_at", "updated_at"]

    def get_can_delete(self, obj) -> bool:
        return can_delete_comment(obj, self.context)

    @extend_schema_field(MENTIONS_SCHEMA)
    def get_mentions(self, obj):
        return comment_mentions(obj)

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
        mention_ids = attrs.get("mention_ids")
        if mention_ids is not None and keep is not None:
            # Drop non-members instead of failing the comment: someone may have
            # left the circle after the composer listed them.
            member_ids = set(
                CircleMembership.objects.filter(circle=keep.circle, user_id__in=mention_ids).values_list(
                    "user_id", flat=True
                )
            )
            attrs["mention_ids"] = [user_id for user_id in dict.fromkeys(mention_ids) if user_id in member_ids]
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        mention_ids = validated_data.pop("mention_ids", [])
        comment = super().create(validated_data)
        KeepCommentMention.objects.bulk_create(
            [KeepCommentMention(comment=comment, user_id=user_id) for user_id in mention_ids]
        )
        return comment

    @transaction.atomic
    def update(self, instance, validated_data):
        mention_ids = validated_data.pop("mention_ids", None)
        comment = super().update(instance, validated_data)
        if mention_ids is not None:
            # Keep the rows of members still mentioned, so their notification
            # isn't sent again (see ``KeepCommentDetailView.perform_update``).
            comment.mentions.exclude(user_id__in=mention_ids).delete()
            KeepCommentMention.objects.bulk_create(
                [KeepCommentMention(comment=comment, user_id=user_id) for user_id in mention_ids],
                ignore_conflicts=True,
            )
        return comment
