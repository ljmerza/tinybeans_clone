"""Milestones album and the milestone suggestion queue shared by the in-app AI and API tokens.

Each circle has at most one Milestones album (``MilestoneAlbum``). The in-app
AI and API tokens / MCP clients pick posts that look like milestones and hand
them to ``propose``; each post gets one ``MilestoneSuggestion`` row, ever.

- With ``Circle.review_ai_milestones`` off (the default), a pick goes into the
  album straight away (status ``auto_added``). Admins see an "Added by AI"
  tag on it; members don't.
- With it on, a pick waits (``pending``) until a circle admin approves it
  (``approve``, which adds it to the album) or dismisses it (``dismiss``).
- A row is never reopened, so a post an admin dismissed, or took out of the
  album, is never picked again. The one exception: an API token may overrule
  the in-app AI's "not a milestone".
- Birthday posts are kept out of Milestones, "1 month birthday" included; the
  Birthdays album covers them. Plain "6 months old" posts are fine.
- Switching review on or off only affects new picks.

The legacy ``keeps.Milestone`` model, ``KeepType.MILESTONE`` and the
Milestone inline in Django admin belong to a different, removed feature and
are not used here.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from django.conf import settings
from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from mysite.audit import AuditEvent, log_audit_event
from mysite.circles.models import Circle
from mysite.keeps.models import Keep, KeepMedia, KeepType

from .birthdays import BIRTHDAY_RE
from .models import Album, AlbumKeep, MilestoneAlbum, MilestoneSuggestion

logger = logging.getLogger(__name__)

ALBUM_NAME = "Milestones"

Status = MilestoneSuggestion.Status

# ``propose`` outcomes that write nothing.
BIRTHDAY = "birthday"
IN_ALBUM = "in_album"
PENDING_CAP = "pending_cap"


def mentions_birthday(text: str) -> bool:
    """Whether ``text`` mentions any birthday, monthly "birthdays" included.

    Unlike ``birthdays.is_birthday_caption`` this does not ignore "1 month
    birthday" or "half birthday" posts: none of them belong in Milestones.
    "Turned 6 months" is not a birthday (``BIRTHDAY_RE`` leaves it out).
    """
    return bool(BIRTHDAY_RE.search(text or ""))


def in_album_q(circle_id: int) -> Q:
    """A ``MilestoneSuggestion`` filter for rows whose post is in the circle's Milestones album."""
    return Q(keep__album_memberships__album__milestone_album__circle_id=circle_id)


def keep_in_album(circle_id: int, keep) -> bool:
    return AlbumKeep.objects.filter(keep=keep, album__milestone_album__circle_id=circle_id).exists()


def pending_suggestions(circle_id: int):
    """The circle's pending rows, minus any whose post is already in the album (e.g. added by hand)."""
    return MilestoneSuggestion.objects.filter(circle_id=circle_id, status=Status.PENDING).exclude(in_album_q(circle_id))


def scan_candidates(circle_id: int, *, include_album: bool = False, include_not_milestone: bool = False):
    """The circle's posts the in-app AI hasn't looked at yet, newest first.

    Leaves out posts with a suggestion row (any status: scanned, picked or
    turned down), posts already in the Milestones album, and posts the feed
    wouldn't show (media still processing). Birthday and empty captions are
    left to the caller, which skips them without a row.

    ``include_album`` and ``include_not_milestone`` are for the
    ``scan_milestones`` command: a recall check against the album, and a rescan.
    """
    displayable = KeepMedia.objects.filter(keep=OuterRef("pk")).filter(
        Q(media_type="photo") | Q(media_type="video", thumbnails_generated=True)
    )
    unscanned = Q(milestone_suggestion__isnull=True)
    if include_not_milestone:
        unscanned |= Q(milestone_suggestion__status=Status.NOT_MILESTONE)
    keeps = Keep.objects.filter(unscanned, circle_id=circle_id).filter(Q(keep_type=KeepType.NOTE) | Exists(displayable))
    if not include_album:
        keeps = keeps.exclude(album_memberships__album__milestone_album__isnull=False)
    return keeps.order_by("-date_of_memory", "-created_at")


@dataclass(frozen=True)
class ProposeResult:
    """What ``propose`` did.

    Attributes:
        outcome: ``BIRTHDAY``, ``IN_ALBUM`` or ``PENDING_CAP`` when nothing was
            written; otherwise the row's status
        suggestion: The post's row, if it has one
        created: Whether this call wrote the row (new, or a ``not_milestone``
            row an API token overruled)
    """

    outcome: str
    suggestion: MilestoneSuggestion | None = None
    created: bool = False


def _truncate(field: str, value: str) -> str:
    # SQLite in tests doesn't enforce varchar lengths; Postgres would refuse the row.
    return (value or "")[: MilestoneSuggestion._meta.get_field(field).max_length]


def _milestone_album(circle: Circle, created_by=None) -> Album:
    """The circle's Milestones album, linking or making one if there is none.

    With no link, a single existing album named "Milestones" (any case) is
    linked, as migration 0005 does; with none or several, a new one is made.
    Callers hold the circle row lock, so two calls can't both make one.
    """
    link = MilestoneAlbum.objects.filter(circle=circle).select_related("album").first()
    if link is not None:
        return link.album
    matches = list(Album.objects.filter(circle=circle, name__iexact=ALBUM_NAME)[:2])
    if len(matches) == 1:
        album = matches[0]
    else:
        album = Album.objects.create(circle=circle, name=ALBUM_NAME, created_by=created_by)
    MilestoneAlbum.objects.create(circle=circle, album=album)
    return album


def _add_to_album(circle: Circle, keep, user=None) -> Album:
    album = _milestone_album(circle, created_by=user)
    _, created = AlbumKeep.objects.get_or_create(album=album, keep=keep, defaults={"added_by": user})
    if created:
        album.touch()
    return album


def _audit(action: str, suggestion: MilestoneSuggestion, *, actor_type: str, actor_id: str | None, **metadata):
    log_audit_event(
        AuditEvent(
            action=action,
            actor_type=actor_type,
            actor_id=actor_id,
            target_type="milestone_suggestion",
            target_id=str(suggestion.pk),
            metadata={
                "circle_id": suggestion.circle_id,
                "keep_id": str(suggestion.keep_id),
                "status": suggestion.status,
                "source": suggestion.source,
                **metadata,
            },
        )
    )


def propose(
    *,
    circle_id: int,
    keep,
    source: str,
    label: str,
    reason: str,
    model_name: str = "",
    token_prefix: str = "",
) -> ProposeResult:
    """Suggest ``keep`` as a milestone of its circle (see the module docstring).

    In order:

    1. A post from another circle raises ``NotFound``.
    2. A post whose title or caption mentions a birthday is refused (``BIRTHDAY``).
    3. A post already in the Milestones album is refused (``IN_ALBUM``).
    4. A post that already has a row keeps it unchanged, except that an API
       token may turn the in-app AI's ``not_milestone`` into a pick.
    5. With review on, a new pick is refused while the circle has
       ``MILESTONE_MAX_PENDING`` pending rows (``PENDING_CAP``).
    6. Otherwise the pick is written: ``pending`` with review on, or
       ``auto_added`` and put into the album with review off.
    """
    if keep.circle_id != circle_id:
        raise NotFound
    if mentions_birthday(f"{keep.title}\n{keep.description}"):
        return ProposeResult(BIRTHDAY)

    fields = {
        "source": source,
        "label": _truncate("label", label),
        "reason": _truncate("reason", reason),
        "model_name": _truncate("model_name", model_name),
        "source_token_prefix": _truncate("source_token_prefix", token_prefix),
    }
    with transaction.atomic():
        # One pick per circle at a time, so the pending cap holds and two picks can't both make the album.
        circle = Circle.objects.select_for_update().get(pk=circle_id)
        if keep_in_album(circle_id, keep):
            return ProposeResult(IN_ALBUM)

        existing = MilestoneSuggestion.objects.filter(keep=keep).first()
        overrule = (
            existing is not None
            and existing.status == Status.NOT_MILESTONE
            and source == MilestoneSuggestion.Source.AGENT
        )
        if existing is not None and not overrule:
            return ProposeResult(existing.status, existing)

        status = Status.PENDING if circle.review_ai_milestones else Status.AUTO_ADDED
        if status == Status.PENDING and pending_suggestions(circle_id).count() >= settings.MILESTONE_MAX_PENDING:
            return ProposeResult(PENDING_CAP, existing)

        if existing is None:
            # get_or_create runs its insert in its own savepoint, so losing a race is safe on Postgres.
            suggestion, created = MilestoneSuggestion.objects.get_or_create(
                keep=keep, defaults={"circle": circle, "status": status, **fields}
            )
            if not created:
                return ProposeResult(suggestion.status, suggestion)
        else:
            updated = MilestoneSuggestion.objects.filter(pk=existing.pk, status=Status.NOT_MILESTONE).update(
                status=status, created_at=timezone.now(), **fields
            )
            existing.refresh_from_db()
            if not updated:
                return ProposeResult(existing.status, existing)
            suggestion = existing

        if status == Status.AUTO_ADDED:
            _add_to_album(circle, keep)

    _audit(
        "milestone_suggestion.propose",
        suggestion,
        actor_type=source,
        actor_id=suggestion.source_token_prefix or None,
        model_name=suggestion.model_name,
    )
    return ProposeResult(suggestion.status, suggestion, created=True)


def approve(suggestion: MilestoneSuggestion, user) -> tuple[MilestoneSuggestion, Album]:
    """Add the suggested post to the circle's Milestones album, making the album if needed.

    Allowed from ``pending``, from ``dismissed`` (undoing a dismiss) and again
    from ``approved`` (a no-op). Returns the row and the album.
    """
    with transaction.atomic():
        # Same lock order as ``propose``: the circle, then the row.
        circle = Circle.objects.select_for_update().get(pk=suggestion.circle_id)
        suggestion = MilestoneSuggestion.objects.select_for_update().select_related("keep").get(pk=suggestion.pk)
        if suggestion.status not in (Status.PENDING, Status.DISMISSED, Status.APPROVED):
            raise ValidationError({"status": "Only pending or dismissed suggestions can be approved."})
        album = _add_to_album(circle, suggestion.keep, user)
        changed = suggestion.status != Status.APPROVED
        if changed:
            suggestion.status = Status.APPROVED
            suggestion.decided_by = user
            suggestion.decided_at = timezone.now()
            suggestion.save(update_fields=["status", "decided_by", "decided_at"])
    if changed:
        _audit(
            "milestone_suggestion.approve", suggestion, actor_type="user", actor_id=str(user.pk), album_id=str(album.pk)
        )
    return suggestion, album


def dismiss(suggestion: MilestoneSuggestion, user) -> MilestoneSuggestion:
    """Turn a pending suggestion down; the post is never suggested again. Dismissing twice is a no-op."""
    with transaction.atomic():
        suggestion = MilestoneSuggestion.objects.select_for_update().select_related("keep").get(pk=suggestion.pk)
        if suggestion.status not in (Status.PENDING, Status.DISMISSED):
            raise ValidationError({"status": "Only pending suggestions can be dismissed."})
        changed = suggestion.status == Status.PENDING
        if changed:
            suggestion.status = Status.DISMISSED
            suggestion.reason = ""
            suggestion.decided_by = user
            suggestion.decided_at = timezone.now()
            suggestion.save(update_fields=["status", "reason", "decided_by", "decided_at"])
    if changed:
        _audit("milestone_suggestion.dismiss", suggestion, actor_type="user", actor_id=str(user.pk))
    return suggestion
