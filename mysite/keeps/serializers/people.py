"""Serializers for the people who can be tagged on posts."""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from ..models import PERSON_NAME_MAX_LENGTH, Person, PersonKind


class PersonSerializer(serializers.ModelSerializer):
    """A taggable person: who they are, never the linked profile's private details."""

    kind = serializers.ChoiceField(choices=PersonKind.choices, read_only=True)

    class Meta:
        model = Person
        fields = ["id", "name", "kind"]
        read_only_fields = fields


class PersonDetailSerializer(PersonSerializer):
    """A person with their circle, for the person page."""

    circle = serializers.SerializerMethodField()

    class Meta(PersonSerializer.Meta):
        fields = PersonSerializer.Meta.fields + ["circle"]
        read_only_fields = fields

    @extend_schema_field(
        {
            "type": "object",
            "properties": {"id": {"type": "integer"}, "name": {"type": "string"}, "slug": {"type": "string"}},
        }
    )
    def get_circle(self, obj):
        return {"id": obj.circle.id, "name": obj.circle.name, "slug": obj.circle.slug}


class PersonCreateSerializer(serializers.Serializer):
    """A free-text person, e.g. "Grandma Jo"."""

    name = serializers.CharField(max_length=PERSON_NAME_MAX_LENGTH, trim_whitespace=True)

    def validate_name(self, value):
        circle = self.context["circle"]
        taken = Person.objects.filter(
            circle=circle, child__isnull=True, user__isnull=True, pet__isnull=True, name__iexact=value
        ).exists()
        if taken:
            raise serializers.ValidationError("Someone with this name is already in the circle.")
        return value


class KeepPeopleUpdateSerializer(serializers.Serializer):
    """The full new list of people tagged on a post."""

    people = serializers.ListField(child=serializers.UUIDField(), allow_empty=True, max_length=200)
