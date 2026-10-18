"""Querysets and response shapes for the agent API.

Everything is scoped to one circle id, taken from the token. Responses carry
no URLs, media ids, storage keys, filenames, emails, user ids, author names
or birthdates; family-written text sits under ``untrusted``.
"""

from __future__ import annotations

from datetime import timezone as dt_timezone

from django.contrib.auth import get_user_model
from django.db.models import Count, Exists, IntegerField, OuterRef, Prefetch, Q, Subquery
from django.db.models.functions import Coalesce, Lower

from mysite.albums.milestones import mentions_birthday
from mysite.albums.models import AlbumKeep, MilestoneSuggestion
from mysite.keeps.models import Keep, KeepComment, KeepMedia, KeepPerson, KeepType, Person
from mysite.keeps.person_stats import age_on

from . import hygiene

COMMENT_LIMIT = 10


def displayable_media():
    """Same rule as the feed: photos always, videos once a poster frame exists."""
    return KeepMedia.objects.filter(Q(media_type="photo") | Q(media_type="video", thumbnails_generated=True))


def agent_posts(circle_id):
    """The circle's posts the feed would show, annotated and prefetched for ``compact_post``."""
    comment_count = (
        KeepComment.objects.filter(keep=OuterRef("pk")).values("keep").annotate(total=Count("id")).values("total")
    )
    return (
        Keep.objects.filter(circle_id=circle_id)
        .filter(Q(keep_type=KeepType.NOTE) | Exists(displayable_media().filter(keep=OuterRef("pk"))))
        .annotate(
            in_milestones_album=Exists(
                AlbumKeep.objects.filter(keep=OuterRef("pk"), album__milestone_album__circle_id=circle_id)
            ),
            suggestion_status=Subquery(MilestoneSuggestion.objects.filter(keep=OuterRef("pk")).values("status")[:1]),
            comment_count=Coalesce(Subquery(comment_count, output_field=IntegerField()), 0),
        )
        .prefetch_related(
            Prefetch("people", queryset=Person.objects.select_related("child").order_by(Lower("name"), "id")),
            Prefetch("media_files", queryset=displayable_media().order_by("upload_order", "id"), to_attr="shown_media"),
        )
    )


def search_q(terms: list[str]) -> Q:
    """Posts matching any term in the title, caption, tags or a media caption (case-insensitive)."""
    query = Q()
    for term in terms:
        query |= (
            Q(title__icontains=term)
            | Q(description__icontains=term)
            | Q(tags__icontains=term)
            | Exists(KeepMedia.objects.filter(keep=OuterRef("pk"), caption__icontains=term))
        )
    return query


def child_q(child_id) -> Q:
    """Posts the child is tagged on; ``Exists`` rather than a join, so no post is listed twice."""
    return Q(Exists(KeepPerson.objects.filter(keep=OuterRef("pk"), person__child_id=child_id)))


def unreviewed_q() -> Q:
    """Not in the album, and either never suggested or only judged "not a milestone" by the in-app AI."""
    decided = MilestoneSuggestion.objects.filter(keep=OuterRef("pk")).exclude(
        status=MilestoneSuggestion.Status.NOT_MILESTONE
    )
    return Q(in_milestones_album=False) & ~Exists(decided)


def _memory_day(keep):
    return keep.date_of_memory.astimezone(dt_timezone.utc).date()


def _person(person, day) -> dict:
    child = person.child if person.child_id else None
    birthdate = child.birthdate if child is not None else None
    return {
        "name": hygiene.strip_hidden(person.name)[: hygiene.NAME_MAX],
        "kind": str(person.kind),
        "age_at_post": age_on(birthdate, day) if birthdate else None,
    }


def compact_post(keep, cleaner: hygiene.TextCleaner | None = None) -> dict:
    cleaner = cleaner or hygiene.TextCleaner()
    day = _memory_day(keep)
    media = keep.shown_media
    item = {
        "id": str(keep.id),
        "date": day.isoformat(),
        "people": [_person(person, day) for person in keep.people.all()],
        "media": {
            "photos": sum(1 for file in media if file.media_type == "photo"),
            "videos": sum(1 for file in media if file.media_type == "video"),
        },
        "comment_count": keep.comment_count,
        "mentions_birthday": mentions_birthday(f"{keep.title}\n{keep.description}"),
        "in_milestones_album": keep.in_milestones_album,
        "suggestion_status": keep.suggestion_status,
        "untrusted": {
            "title": cleaner.clean(keep.title, hygiene.TITLE_MAX),
            "caption": cleaner.clean(keep.description, hygiene.CAPTION_MAX),
            "tags": [cleaner.clean(tag, hygiene.TAG_MAX) for tag in keep.tag_list],
            "media_captions": [
                cleaner.clean(file.caption, hygiene.MEDIA_CAPTION_MAX) for file in media if file.caption.strip()
            ],
        },
    }
    item["truncated"] = cleaner.truncated
    return item


def member_names(circle_id) -> list[str]:
    """Display names and emails of the circle's members, in one query, for ``hygiene.mask_mentions``."""
    users = (
        get_user_model()
        .objects.filter(circle_memberships__circle_id=circle_id)
        .only("first_name", "last_name", "email")
    )
    return [name for user in users for name in (user.display_name, user.email)]


def post_detail(keep, circle_id) -> dict:
    """``compact_post`` plus the latest comments, oldest first, with no authors and members' @names masked."""
    cleaner = hygiene.TextCleaner()
    item = compact_post(keep, cleaner)
    latest = list(KeepComment.objects.filter(keep=keep).order_by("-created_at", "-id")[:COMMENT_LIMIT])
    names = member_names(circle_id) if latest else []
    item["untrusted"]["comments"] = [
        {
            "date": comment.created_at.astimezone(dt_timezone.utc).date().isoformat(),
            "text": cleaner.clean(hygiene.mask_mentions(comment.comment, names), hygiene.COMMENT_MAX),
        }
        for comment in reversed(latest)
    ]
    item["truncated"] = cleaner.truncated
    return item
