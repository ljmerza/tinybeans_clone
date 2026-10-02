"""Milestones as the web client shows them: on feed posts, in the composer and the milestones view."""

import calendar
from datetime import date
from datetime import timezone as dt_timezone

from rest_framework import serializers

from mysite.notification_utils import create_message
from mysite.users.models.child_profile import ChildProfile

from ..models import Milestone, MilestoneType

FEED_MILESTONE_SCHEMA = {
    "type": "object",
    "nullable": True,
    "properties": {
        "milestone_type": {"type": "string", "enum": list(MilestoneType.values)},
        "child": {
            "type": "object",
            "nullable": True,
            "properties": {"id": {"type": "string", "format": "uuid"}, "display_name": {"type": "string"}},
        },
        "child_age": {
            "type": "object",
            "nullable": True,
            "description": "The child's age on the memory's (UTC) date, when their birthdate is known",
            "properties": {
                "years": {"type": "integer"},
                "months": {"type": "integer"},
                "days": {"type": "integer"},
            },
        },
        "age_at_milestone": {"type": "string", "description": "Age as entered by hand, if any"},
    },
}


def age_on(birthdate, day):
    """Whole years, months and days from `birthdate` to `day`; None when unknown or before birth.

    A birthday on the 31st falls on the last day of shorter months.
    """
    if birthdate is None or day < birthdate:
        return None
    months = (day.year - birthdate.year) * 12 + day.month - birthdate.month
    if day.day < min(birthdate.day, calendar.monthrange(day.year, day.month)[1]):
        months -= 1
    year, month_index = divmod(birthdate.month - 1 + months, 12)
    year += birthdate.year
    month = month_index + 1
    anchor = date(year, month, min(birthdate.day, calendar.monthrange(year, month)[1]))
    return {"years": months // 12, "months": months % 12, "days": (day - anchor).days}


def feed_milestone(keep):
    """The keep's milestone as feed posts carry it, or None."""
    milestone = getattr(keep, "milestone", None)
    if milestone is None:
        return None
    child = milestone.child_profile
    memory_day = keep.date_of_memory.astimezone(dt_timezone.utc).date()
    return {
        "milestone_type": milestone.milestone_type,
        "child": {"id": str(child.id), "display_name": child.display_name} if child else None,
        "child_age": age_on(child.birthdate, memory_day) if child else None,
        "age_at_milestone": milestone.age_at_milestone,
    }


def validate_child_in_circle(child, circle):
    """A milestone's child must belong to the keep's circle."""
    if child is not None and circle is not None and child.circle_id != circle.id:
        raise serializers.ValidationError({"child_profile": create_message("errors.milestone_child_not_in_circle")})


class MilestoneWriteSerializer(serializers.ModelSerializer):
    """Set a keep's milestone: its type and, optionally, which child it is for."""

    child_profile = serializers.PrimaryKeyRelatedField(
        queryset=ChildProfile.objects.all(), allow_null=True, required=False
    )

    class Meta:
        model = Milestone
        fields = ["milestone_type", "child_profile"]
        extra_kwargs = {"milestone_type": {"required": True}}

    def validate(self, data):
        # A PUT replaces the milestone, so leaving the child out clears it.
        data.setdefault("child_profile", None)
        validate_child_in_circle(data.get("child_profile"), self.context["keep"].circle)
        return data


class KeepChildSummarySerializer(serializers.ModelSerializer):
    """A child in one of the viewer's circles, for picking or filtering milestones."""

    circle = serializers.SerializerMethodField()
    milestone_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ChildProfile
        fields = ["id", "display_name", "circle", "milestone_count"]
        read_only_fields = fields

    def get_circle(self, obj) -> dict:
        return {"id": obj.circle.id, "name": obj.circle.name, "slug": obj.circle.slug}
