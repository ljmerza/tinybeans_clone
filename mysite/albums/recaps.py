"""Monthly recap albums: last month's most-loved photos, one album per circle.

Off by default; a circle admin turns it on (``Circle.monthly_recap_enabled``).
On the 1st, beat runs ``tasks.create_monthly_recaps``, which makes an album
named like "September 2026" in every enabled circle. It holds the month's top
``RECAP_SIZE`` photo posts by likes + comments, with the top one as its cover.
After that it is an ordinary album that admins can edit or delete.

- A post counts when it has at least one photo (video-only posts don't) and
  its ``date_of_memory`` falls in the month. That is the date the calendar and
  feed use; ``created_at`` would put years of imported history in one month.
- Score: reactions of any type (the feed counts every reaction as a like) plus
  comments, replies included. Posts scoring 0 are left out. Ties go to the
  earlier memory. If nothing scores, no album is made.
- Month boundaries are in ``TIME_ZONE``, which also sets the calendar's months.
- Each made recap leaves a ``MonthlyRecap`` row, unique per circle and month.
  A rerun or retry finds it and does nothing, and since the row outlives its
  album, a recap an admin deleted is not made again. A month where nothing
  scored leaves no row, so a later manual run can still make it.
- Names are English: the album is shared by the whole circle and the backend
  has no per-circle language to pick from.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Exists, F, IntegerField, OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.utils import timezone

from mysite.circles.models import Circle
from mysite.keeps.models import Keep, KeepComment, KeepMedia, KeepReaction

from .models import ALBUM_KEEP_ORDERING, Album, AlbumKeep, MonthlyRecap

logger = logging.getLogger(__name__)

# Posts in one recap album.
RECAP_SIZE = 12


def previous_month(today: date) -> date:
    """First day of the month before ``today``'s."""
    if today.month == 1:
        return date(today.year - 1, 12, 1)
    return date(today.year, today.month - 1, 1)


def beat_today() -> date:
    """Today in ``CELERY_TIMEZONE``, the zone the beat schedule fires in.

    Picking "last month" from the schedule's own date means a run at 8 AM on
    the 1st always means the month that just ended, even when ``TIME_ZONE``
    is a few hours behind or ahead.
    """
    return timezone.localdate(timezone=ZoneInfo(settings.CELERY_TIMEZONE))


def month_bounds(month: date) -> tuple[datetime, datetime]:
    """[start, end) of ``month`` in ``TIME_ZONE``."""
    zone = timezone.get_default_timezone()
    start = datetime(month.year, month.month, 1, tzinfo=zone)
    following = date(month.year + 1, 1, 1) if month.month == 12 else date(month.year, month.month + 1, 1)
    return start, datetime(following.year, following.month, 1, tzinfo=zone)


def recap_name(month: date) -> str:
    return f"{month:%B %Y}"


def _count(model):
    counts = model.objects.filter(keep=OuterRef("pk")).values("keep").annotate(total=Count("id")).values("total")
    return Coalesce(Subquery(counts, output_field=IntegerField()), 0)


def top_keeps(circle: Circle, month: date) -> list[Keep]:
    """The month's highest-scoring photo posts in ``circle``, best first, annotated with ``score``."""
    start, end = month_bounds(month)
    has_photo = KeepMedia.objects.filter(keep=OuterRef("pk"), media_type="photo")
    return list(
        Keep.objects.filter(circle=circle, date_of_memory__gte=start, date_of_memory__lt=end)
        .filter(Exists(has_photo))
        .annotate(like_count=_count(KeepReaction), comment_count=_count(KeepComment))
        .annotate(score=F("like_count") + F("comment_count"))
        .filter(score__gt=0)
        .order_by("-score", *ALBUM_KEEP_ORDERING)[:RECAP_SIZE]
    )


def create_monthly_recap(circle: Circle, month: date) -> Album | None:
    """Make ``circle``'s recap album for ``month`` (any day in it); None if made before or nothing scored.

    Ignores ``monthly_recap_enabled``; ``create_recaps_for_enabled_circles`` is what
    limits the scheduled run to enabled circles.
    """
    month = month.replace(day=1)
    if MonthlyRecap.objects.filter(circle=circle, month=month).exists():
        return None
    keeps = top_keeps(circle, month)
    if not keeps:
        return None
    with transaction.atomic():
        # The unique constraint settles a race between two runs: the loser
        # gets the winner's row back and stops.
        recap, created = MonthlyRecap.objects.get_or_create(circle=circle, month=month)
        if not created:
            return None
        album = Album.objects.create(circle=circle, name=recap_name(month), cover_keep=keeps[0])
        for keep in sorted(keeps, key=lambda keep: (keep.date_of_memory, keep.created_at, keep.id)):
            AlbumKeep.objects.create(album=album, keep=keep)
        recap.album = album
        recap.save(update_fields=["album"])
    logger.info("Created %s recap for circle %s with %s posts", recap_name(month), circle.id, len(keeps))
    return album


def create_recaps_for_enabled_circles(month: date) -> tuple[int, list[int]]:
    """Make ``month``'s recap in every enabled circle.

    One circle failing doesn't stop the rest. Returns how many albums were
    made and the ids of the circles that failed.
    """
    made, failed = 0, []
    for circle in Circle.objects.filter(monthly_recap_enabled=True).order_by("id"):
        try:
            if create_monthly_recap(circle, month) is not None:
                made += 1
        except Exception:
            logger.exception("Monthly recap failed for circle %s", circle.id)
            failed.append(circle.id)
    return made, failed
