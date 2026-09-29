"""Serializers for the photo feed.

Feed items are shaped for the home-screen feed: the media to show, the
viewer's own reaction and favorite, counts, and a short comment preview. Counts are
annotated and the preview is a sliced prefetch (see ``views.feed``), so a page
costs a fixed number of queries regardless of how many reactions or comments
each keep has.
"""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from ..models import Keep, KeepComment, KeepReaction
from .comments import can_delete_comment

# Presign for a day (instead of the 1h default). The virtualized feed remounts
# images as they scroll back into view, so short-lived URLs would break on a
# tab left open for a while.
FEED_URL_EXPIRES_IN = 86400


def is_displayable(media):
    """Photos always show; videos only once a poster frame exists."""
    return media.media_type == "photo" or (media.media_type == "video" and media.thumbnails_generated)


class FeedCommentSerializer(serializers.ModelSerializer):
    """A comment in a feed item's preview."""

    user_display_name = serializers.CharField(source="user.display_name", read_only=True)
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = KeepComment
        fields = ["id", "user", "user_display_name", "parent", "comment", "can_delete", "created_at"]
        read_only_fields = fields

    def get_can_delete(self, obj) -> bool:
        return can_delete_comment(obj, self.context)


class FeedLikerSerializer(serializers.ModelSerializer):
    """Someone who reacted to a keep; any reaction type counts as a like."""

    user_display_name = serializers.CharField(source="user.display_name", read_only=True)

    class Meta:
        model = KeepReaction
        fields = ["id", "user", "user_display_name", "reaction_type", "created_at"]
        read_only_fields = fields


class KeepFeedSerializer(serializers.ModelSerializer):
    """One keep as a feed post."""

    circle = serializers.SerializerMethodField()
    created_by_display_name = serializers.CharField(source="created_by.display_name", read_only=True)
    media = serializers.SerializerMethodField()
    reaction_count = serializers.IntegerField(read_only=True)
    comment_count = serializers.IntegerField(read_only=True)
    viewer_reaction = serializers.SerializerMethodField()
    favorited = serializers.BooleanField(read_only=True, help_text="Whether the viewer favorited this keep")
    recent_comments = serializers.SerializerMethodField()

    class Meta:
        model = Keep
        fields = [
            "id",
            "circle",
            "created_by",
            "created_by_display_name",
            "title",
            "description",
            "date_of_memory",
            "created_at",
            "media",
            "reaction_count",
            "comment_count",
            "viewer_reaction",
            "favorited",
            "recent_comments",
        ]
        read_only_fields = fields

    @extend_schema_field(
        {
            "type": "object",
            "properties": {"id": {"type": "integer"}, "name": {"type": "string"}, "slug": {"type": "string"}},
        }
    )
    def get_circle(self, obj):
        return {"id": obj.circle.id, "name": obj.circle.name, "slug": obj.circle.slug}

    @extend_schema_field(
        {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "media_type": {"type": "string", "enum": ["photo", "video"]},
                    "url": {"type": "string"},
                    "poster_url": {"type": "string", "nullable": True},
                    "width": {"type": "integer", "nullable": True},
                    "height": {"type": "integer", "nullable": True},
                    "caption": {"type": "string"},
                },
            },
        }
    )
    def get_media(self, obj):
        items = []
        for media in obj.media_files.all():
            if not is_displayable(media):
                continue
            if media.media_type == "video":
                url = media.get_url("original", FEED_URL_EXPIRES_IN)
                poster_url = media.get_url("gallery", FEED_URL_EXPIRES_IN)
            else:
                # The gallery rendition keeps the original's aspect ratio, so the
                # original width/height still describe its shape.
                size = "gallery" if media.thumbnails_generated else "original"
                url = media.get_url(size, FEED_URL_EXPIRES_IN)
                poster_url = None
            items.append(
                {
                    "id": media.id,
                    "media_type": media.media_type,
                    "url": url,
                    "poster_url": poster_url,
                    "width": media.width,
                    "height": media.height,
                    "caption": media.caption,
                }
            )
        return items

    @extend_schema_field(
        {
            "type": "object",
            "nullable": True,
            "properties": {"id": {"type": "integer"}, "reaction_type": {"type": "string"}},
        }
    )
    def get_viewer_reaction(self, obj):
        reactions = getattr(obj, "viewer_reactions", None)
        if not reactions:
            return None
        reaction = reactions[0]
        return {"id": reaction.id, "reaction_type": reaction.reaction_type}

    @extend_schema_field(FeedCommentSerializer(many=True))
    def get_recent_comments(self, obj):
        # Prefetched newest-first so the slice keeps the latest ones; show them
        # in reading order.
        newest_first = getattr(obj, "recent_comments_desc", [])
        return FeedCommentSerializer(list(reversed(newest_first)), many=True, context=self.context).data
