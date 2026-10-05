"""Serializers for albums."""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from mysite.circles.models import Circle
from mysite.keeps.models import Keep
from mysite.keeps.serializers.feed import FEED_URL_EXPIRES_IN

from .models import Album, AlbumKeep


def cover_url(media):
    """The cover rendition: a photo's gallery size (or original), a video's poster frame."""
    if media.media_type == "video":
        return media.get_url("gallery", FEED_URL_EXPIRES_IN)
    return media.get_url("gallery" if media.thumbnails_generated else "original", FEED_URL_EXPIRES_IN)


class AlbumSerializer(serializers.ModelSerializer):
    """An album card: name, cover and how many posts it holds.

    ``post_count``, ``can_edit``, ``cover_media_id``, ``recap_month`` and (when
    filtering by a keep) ``has_keep`` are annotated by ``views.visible_albums``,
    and the cover media rows are attached in bulk, so a page costs a fixed
    number of queries.
    """

    circle = serializers.SerializerMethodField()
    created_by_display_name = serializers.SerializerMethodField()
    cover = serializers.SerializerMethodField()
    post_count = serializers.IntegerField(read_only=True, help_text="Posts in the album the viewer can see")
    can_edit = serializers.BooleanField(
        read_only=True, help_text="Whether the viewer may rename or delete it: its creator or a circle admin"
    )
    has_keep = serializers.SerializerMethodField()
    recap_month = serializers.DateField(
        read_only=True, allow_null=True, help_text="First day of the month a monthly recap covers; null otherwise"
    )

    class Meta:
        model = Album
        fields = [
            "id",
            "circle",
            "name",
            "description",
            "created_by",
            "created_by_display_name",
            "cover_keep",
            "cover",
            "post_count",
            "can_edit",
            "has_keep",
            "recap_month",
            "created_at",
            "updated_at",
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

    def get_created_by_display_name(self, obj) -> str | None:
        return obj.created_by.display_name if obj.created_by else None

    @extend_schema_field(
        {
            "type": "object",
            "nullable": True,
            "properties": {
                "keep_id": {"type": "string", "format": "uuid"},
                "media_type": {"type": "string", "enum": ["photo", "video"]},
                "url": {"type": "string"},
            },
        }
    )
    def get_cover(self, obj):
        media = getattr(obj, "cover_media", None)
        if media is None:
            return None
        return {"keep_id": str(media.keep_id), "media_type": media.media_type, "url": cover_url(media)}

    @extend_schema_field(
        {
            "type": "boolean",
            "nullable": True,
            "description": "With `?keep=`: whether that keep is in the album; otherwise null",
        }
    )
    def get_has_keep(self, obj):
        return getattr(obj, "has_keep", None)


class AlbumCreateSerializer(serializers.ModelSerializer):
    """Create an album in one of the viewer's circles, optionally with a first post."""

    circle = serializers.PrimaryKeyRelatedField(queryset=Circle.objects.none())
    keep = serializers.PrimaryKeyRelatedField(
        queryset=Keep.objects.none(),
        required=False,
        write_only=True,
        help_text="Optional post to add straight away; must be in the same circle",
    )

    class Meta:
        model = Album
        fields = ["circle", "name", "description", "keep"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request is not None and request.user.is_authenticated:
            self.fields["circle"].queryset = Circle.objects.filter(memberships__user=request.user)
            self.fields["keep"].queryset = Keep.objects.filter(circle__memberships__user=request.user)

    def validate(self, attrs):
        keep = attrs.get("keep")
        if keep is not None and keep.circle_id != attrs["circle"].id:
            raise serializers.ValidationError({"keep": "Only posts from the album's circle can be added."})
        return attrs

    def create(self, validated_data):
        keep = validated_data.pop("keep", None)
        user = self.context["request"].user
        album = Album.objects.create(created_by=user, **validated_data)
        if keep is not None:
            AlbumKeep.objects.create(album=album, keep=keep, added_by=user)
        return album


class AlbumUpdateSerializer(serializers.ModelSerializer):
    """Rename an album, change its description or pick its cover post."""

    cover_keep = serializers.PrimaryKeyRelatedField(
        queryset=Keep.objects.all(),
        required=False,
        allow_null=True,
        help_text="A post in the album whose first photo is the cover; null for the default",
    )

    class Meta:
        model = Album
        fields = ["name", "description", "cover_keep"]

    def validate_cover_keep(self, keep):
        if keep is not None and not AlbumKeep.objects.filter(album=self.instance, keep=keep).exists():
            raise serializers.ValidationError("The cover must be a post in the album.")
        return keep

    def update(self, instance, validated_data):
        album = super().update(instance, validated_data)
        album.touch()
        return album
