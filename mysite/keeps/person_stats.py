"""Stats for the person page: age, how many posts and photos they're in, and highlights.

Computed in a fixed handful of queries however many posts the person is in.
Only posts the person's feed would show count (text posts, and keeps with a
displayable photo or video), so the numbers match the page below them.
Months are UTC calendar months, like the calendar.
"""

from datetime import date, datetime
from datetime import timezone as dt_timezone

from django.db.models import Count, Exists, OuterRef, Prefetch, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone

from .models import Keep, KeepMedia, KeepPerson, KeepType
from .serializers.feed import FEED_URL_EXPIRES_IN, is_displayable

# Posts per month covers this many months, ending with the current one.
POSTS_PER_MONTH_SPAN = 12


def age_on(birthdate: date, today: date) -> dict | None:
    """Whole years, months and days from ``birthdate`` to ``today``; None if not born yet."""
    if birthdate > today:
        return None
    months = (today.year - birthdate.year) * 12 + today.month - birthdate.month
    if today.day < birthdate.day:
        months -= 1
    # The day this month count was last reached; clamp for e.g. a 31st birthday.
    anniversary_year = birthdate.year + (birthdate.month - 1 + months) // 12
    anniversary_month = (birthdate.month - 1 + months) % 12 + 1
    anniversary_day = min(birthdate.day, _days_in_month(anniversary_year, anniversary_month))
    days = (today - date(anniversary_year, anniversary_month, anniversary_day)).days
    return {"years": months // 12, "months": months % 12, "days": days}


def _days_in_month(year: int, month: int) -> int:
    next_month = date(year + month // 12, month % 12 + 1, 1)
    return (next_month - date(year, month, 1)).days


def _month_starts(today: date, count: int) -> list[date]:
    """The first day of the last ``count`` months, oldest first, ending with today's month."""
    index = today.year * 12 + today.month - 1
    return [date(i // 12, i % 12 + 1, 1) for i in range(index - count + 1, index + 1)]


def tagged_keeps(person):
    """The person's posts that their feed would show."""
    displayable = KeepMedia.objects.filter(keep=OuterRef("pk")).filter(
        Q(media_type="photo") | Q(media_type="video", thumbnails_generated=True)
    )
    return (
        Keep.objects.filter(circle_id=person.circle_id)
        .filter(Exists(KeepPerson.objects.filter(keep=OuterRef("pk"), person=person)))
        .filter(Q(keep_type=KeepType.NOTE) | Exists(displayable))
    )


def _post_summary(keep) -> dict | None:
    if keep is None:
        return None
    thumbnail = next((media for media in keep.media_files.all() if is_displayable(media)), None)
    thumbnail_url = None
    if thumbnail is not None:
        size = "thumbnail" if thumbnail.thumbnails_generated else "original"
        thumbnail_url = thumbnail.get_url(size, FEED_URL_EXPIRES_IN)
    return {
        "id": str(keep.id),
        "title": keep.title,
        "date_of_memory": keep.date_of_memory,
        "like_count": getattr(keep, "like_count", None),
        "thumbnail_url": thumbnail_url,
    }


def person_stats(person, today: date | None = None) -> dict:
    today = today or timezone.now().astimezone(dt_timezone.utc).date()
    keeps = tagged_keeps(person)
    media_order = Prefetch("media_files", queryset=KeepMedia.objects.order_by("upload_order", "id"))

    post_count = keeps.count()
    media_counts = KeepMedia.objects.filter(keep__in=keeps.values("pk")).aggregate(
        photos=Count("id", filter=Q(media_type="photo")),
        videos=Count("id", filter=Q(media_type="video", thumbnails_generated=True)),
    )

    months = _month_starts(today, POSTS_PER_MONTH_SPAN)
    since = datetime(months[0].year, months[0].month, 1, tzinfo=dt_timezone.utc)
    per_month = {
        row["month"].date(): row["count"]
        for row in keeps.filter(date_of_memory__gte=since)
        .annotate(month=TruncMonth("date_of_memory", tzinfo=dt_timezone.utc))
        .values("month")
        .annotate(count=Count("id"))
        .order_by()
    }

    first_post = keeps.order_by("date_of_memory", "created_at", "id").prefetch_related(media_order).first()
    # Any reaction counts as a like, as in the feed. Ties go to the newer memory.
    most_liked = (
        keeps.annotate(like_count=Count("reactions"))
        .filter(like_count__gt=0)
        .order_by("-like_count", "-date_of_memory", "-id")
        .prefetch_related(media_order)
        .first()
    )

    birthdate = person.child.birthdate if person.child_id else None
    return {
        "birthdate": birthdate,
        "age": age_on(birthdate, today) if birthdate else None,
        "post_count": post_count,
        "photo_count": media_counts["photos"],
        "video_count": media_counts["videos"],
        "posts_per_month": [{"month": month.strftime("%Y-%m"), "count": per_month.get(month, 0)} for month in months],
        "first_post": _post_summary(first_post),
        "most_liked_post": _post_summary(most_liked),
    }
