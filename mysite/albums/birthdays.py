"""Birthdays album: one album per circle with the posts about its children's birthdays.

Off by default; a circle admin turns it on (``Circle.birthday_album_enabled``).
Each night beat runs ``tasks.sync_birthday_albums``, and turning the setting on
or setting a child's birthdate runs it for that circle straight away.

- It works from each child's ``ChildProfile.birthdate``; children without one
  are skipped. Only real birthdays count (1st, 2nd, ...), not the birth itself.
- A post is a birthday post when its ``date_of_memory`` (as a date in
  ``TIME_ZONE``) is from ``DAYS_BEFORE`` days before to ``DAYS_AFTER`` days
  after any child's birthday, and its title or caption mentions a birthday
  (``is_birthday_caption``). Parties are often held on the weekend before or
  after, so the window is wider after the day than before it.
- Posts about an age in weeks or months ("4 month birthday", "half birthday")
  don't count, except whole years ("12 month birthday"): they are monthly
  milestones, and in a circle with two children one child's monthly post can
  fall in the other's birthday window.
- The album ("Birthdays") is made the first time a birthday post is found. It
  is then an ordinary album: admins can rename it, pick a cover, add posts
  or take them out.
- Every post the sync adds is recorded (``BirthdayAlbumMatch``) and never
  added again, so a post an admin took out stays out. The sync only adds.
- Deleting the album turns the setting off (see ``signals``). Turning it back
  on makes a new album from scratch. Turning it off just stops the sync; the
  album stays.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from mysite.circles.models import Circle
from mysite.keeps.models import Keep

from .models import ALBUM_KEEP_ORDERING, Album, AlbumKeep, BirthdayAlbum, BirthdayAlbumMatch

logger = logging.getLogger(__name__)

ALBUM_NAME = "Birthdays"
DAYS_BEFORE = 7
DAYS_AFTER = 14

_NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}
_NUMBER = r"(?:\d{1,2}|" + "|".join(_NUMBER_WORDS) + r")"
_BIRTHDAY_WORD = r"(?:birthday|b[-'’]?day)"
_PART_UNIT = r"(?:months?|mos?|weeks?|wks?)"

BIRTHDAY_RE = re.compile(
    rf"birthday|\bb[-'’]?days?\b|cumpleaños|\bcumple\b|compleanno"
    rf"|\bturn(?:s|ed|ing)\s+{_NUMBER}\b(?![\s-]*(?:{_PART_UNIT}|days?)\b)",
    re.IGNORECASE,
)
# "4 month birthday", "6-months bday", "3 weeks old birthday", "half birthday".
PART_AGE_RE = re.compile(
    rf"\b(?P<count>{_NUMBER})[\s-]*(?P<unit>{_PART_UNIT})(?:[\s-]+old)?['’]?s?[\s-]+{_BIRTHDAY_WORD}"
    rf"|\bhalf[\s-]+{_BIRTHDAY_WORD}",
    re.IGNORECASE,
)


def _count(text: str) -> int:
    return int(text) if text.isdigit() else _NUMBER_WORDS[text.lower()]


def _strip_part_age(match: re.Match) -> str:
    """Blank out an age-in-weeks/months birthday, unless it is a whole number of years."""
    unit = match.group("unit")
    if unit and unit.lower().startswith("mo") and _count(match.group("count")) % 12 == 0:
        return match.group(0)
    return " "


def is_birthday_caption(text: str) -> bool:
    """Whether ``text`` talks about a birthday, ignoring monthly/weekly "birthdays"."""
    return bool(BIRTHDAY_RE.search(PART_AGE_RE.sub(_strip_part_age, text or "")))


def anniversary(birthdate: date, year: int) -> date:
    """The birthday in ``year``; Feb 29 birthdays fall on Feb 28 in other years."""
    try:
        return birthdate.replace(year=year)
    except ValueError:
        return date(year, 2, 28)


def birthdays(birthdate: date, through: date) -> list[date]:
    """Every birthday (1st onwards) whose window can hold a post dated up to ``through``."""
    return [
        anniversary(birthdate, year)
        for year in range(birthdate.year + 1, through.year + 2)
        if anniversary(birthdate, year) - timedelta(days=DAYS_BEFORE) <= through
    ]


def _local_midnight(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=timezone.get_default_timezone())


def birthday_window_filter(circle: Circle, today: date) -> Q | None:
    """A ``Keep`` filter for posts dated near any of the circle's children's birthdays; None if there are none."""
    windows = Q()
    found = False
    for birthdate in circle.children.exclude(birthdate=None).values_list("birthdate", flat=True):
        for day in birthdays(birthdate, today):
            start = _local_midnight(day - timedelta(days=DAYS_BEFORE))
            end = _local_midnight(day + timedelta(days=DAYS_AFTER + 1))
            windows |= Q(date_of_memory__gte=start, date_of_memory__lt=end)
            found = True
    return windows if found else None


def birthday_keeps(circle: Circle, today: date, *, exclude_ids=()) -> list[Keep]:
    """The circle's birthday posts (see the module docstring), oldest memory first."""
    windows = birthday_window_filter(circle, today)
    if windows is None:
        return []
    candidates = (
        Keep.objects.filter(circle=circle)
        .filter(windows)
        .exclude(id__in=list(exclude_ids))
        .only("id", "title", "description", "date_of_memory", "created_at")
        .order_by(*ALBUM_KEEP_ORDERING)
    )
    return [keep for keep in candidates if is_birthday_caption(f"{keep.title}\n{keep.description}")]


def sync_birthday_album(circle_id: int, today: date | None = None) -> int:
    """Add the circle's new birthday posts to its Birthdays album, making it if needed.

    Does nothing unless the circle has the setting on. Returns how many posts
    were added.
    """
    today = today or timezone.localdate()
    with transaction.atomic():
        # One sync per circle at a time, so two runs can't both make the album.
        circle = Circle.objects.select_for_update().filter(pk=circle_id, birthday_album_enabled=True).first()
        if circle is None:
            return 0
        link = BirthdayAlbum.objects.filter(circle=circle).select_related("album").first()
        seen = set(link.matches.values_list("keep_id", flat=True)) if link else set()
        keeps = birthday_keeps(circle, today, exclude_ids=seen)
        if not keeps:
            return 0
        if link is None:
            album = Album.objects.create(circle=circle, name=ALBUM_NAME)
            link = BirthdayAlbum.objects.create(circle=circle, album=album)
        album = link.album
        for keep in keeps:
            # An admin may have added it by hand already.
            AlbumKeep.objects.get_or_create(album=album, keep=keep)
            BirthdayAlbumMatch.objects.create(birthday_album=link, keep=keep)
        album.touch()
    logger.info("Added %s posts to the birthdays album of circle %s", len(keeps), circle_id)
    return len(keeps)


def sync_enabled_circles(circle_id: int | None = None, today: date | None = None) -> tuple[int, list[int]]:
    """Sync every circle with the setting on (or just ``circle_id``).

    One circle failing doesn't stop the rest. Returns how many posts were
    added and the ids of the circles that failed.
    """
    circles = Circle.objects.filter(birthday_album_enabled=True)
    if circle_id is not None:
        circles = circles.filter(pk=circle_id)
    added, failed = 0, []
    for pk in circles.order_by("id").values_list("id", flat=True):
        try:
            added += sync_birthday_album(pk, today)
        except Exception:
            logger.exception("Birthdays album sync failed for circle %s", pk)
            failed.append(pk)
    return added, failed


def queue_sync(circle_id: int) -> None:
    """Sync one circle's Birthdays album in the background once the current transaction commits.

    ``robust``: if the broker is down, the change is still saved and the
    nightly run picks it up.
    """
    from .tasks import sync_birthday_albums

    transaction.on_commit(lambda: sync_birthday_albums.delay(circle_id=circle_id), robust=True)
