"""Daily email listing the new posts in a user's circles.

Opt-in from the global notification preferences (``email_digest``); a circle
override row never turns it on or off. Each morning beat runs
``send_new_post_digests``, which queues ``send_new_post_digest`` for every
opted-in user.

A digest picks up where the user's previous one stopped
(``digest_covered_until``), so a late or missed run neither drops nor repeats
posts. "Arrived" means ``created_at``: imported posts carry old memory dates.
The window ends a few minutes before the run, so a post whose photos are still
processing (and so isn't in the feed yet) lands in the next digest instead of
falling between two. Visibility follows the home feed.

Posts are listed as links, without thumbnails: media URLs are presigned and
expire (seven days at most), and mail providers that fetch images through
their own proxies (Gmail) can't reach a LAN-only image host anyway.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone
from django.utils.text import Truncator

from mysite.emails.tasks import send_email_task
from mysite.emails.templates import KEEP_DIGEST_TEMPLATE
from mysite.users.models import UserNotificationPreferences

from .models import KeepMedia
from .notifications import media_label

logger = logging.getLogger(__name__)

# Posts listed in one email; the rest are counted and linked through the feed.
DIGEST_MAX_POSTS = 10
# A first digest looks back a day; one after a long gap looks back at most a week.
DIGEST_FIRST_WINDOW = timedelta(days=1)
DIGEST_MAX_WINDOW = timedelta(days=7)


def digest_recipient_ids() -> list[int]:
    """Users who opted in to the digest and can receive email."""
    return list(
        UserNotificationPreferences.objects.filter(
            circle__isnull=True,
            email_digest=True,
            user__is_active=True,
            user__email_verified=True,
        )
        .exclude(user__email="")
        .values_list("user_id", flat=True)
    )


def send_digest(user_id: int) -> bool:
    """Email ``user_id`` the posts that are new since their last digest.

    Returns whether an email was queued. The window still moves forward when
    nothing is new, so a quiet week doesn't pile up into the next digest.
    """
    # The views package imports the tasks module, which imports this one.
    from .views.feed import feed_queryset

    window_end = timezone.now() - timedelta(seconds=settings.NOTIFICATIONS_NEW_MEDIA_DELAY_SECONDS)
    with transaction.atomic():
        # The row lock keeps two runs for the same user from sending the same posts.
        prefs = (
            UserNotificationPreferences.objects.select_for_update(of=("self",))
            .select_related("user")
            .filter(user_id=user_id, circle__isnull=True, email_digest=True)
            .first()
        )
        if prefs is None:
            return False
        user = prefs.user
        if not (user.is_active and user.email and user.email_verified):
            return False

        window_start = max(
            prefs.digest_covered_until or window_end - DIGEST_FIRST_WINDOW,
            window_end - DIGEST_MAX_WINDOW,
        )
        posts = (
            feed_queryset(user)
            .exclude(created_by=user)
            .filter(created_at__gt=window_start, created_at__lte=window_end)
            # Only the media is needed; drop the feed's comment and reaction prefetches.
            .prefetch_related(None)
            .prefetch_related(Prefetch("media_files", queryset=KeepMedia.objects.order_by("upload_order", "id")))
            .order_by("-created_at", "-id")
        )
        post_count = posts.count()
        shown = list(posts[:DIGEST_MAX_POSTS]) if post_count else []

        prefs.digest_covered_until = window_end
        prefs.save(update_fields=["digest_covered_until"])
        if not shown:
            return False

        base_url = (settings.ACCOUNT_FRONTEND_BASE_URL or "http://localhost:3000").rstrip("/")
        context = {
            "recipient_name": user.first_name or user.display_name,
            "post_count": post_count,
            "posts": [_post_context(keep, base_url) for keep in shown],
            "more_count": post_count - len(shown),
            "feed_url": f"{base_url}/",
            "settings_url": f"{base_url}/profile/notifications",
        }
        transaction.on_commit(
            lambda: send_email_task.delay(to_email=user.email, template_id=KEEP_DIGEST_TEMPLATE, context=context)
        )
    logger.info("Queued new-post digest for user %s with %s posts", user_id, post_count)
    return True


def _post_context(keep, base_url: str) -> dict:
    media_types = [media.media_type for media in keep.media_files.all()]
    return {
        "actor_name": keep.created_by.display_name,
        "circle_name": keep.circle.name,
        "post_summary": Truncator(keep.title or keep.description).chars(80),
        # Empty for a text post, which the email words as "posted in".
        "media_label": media_label(media_types) if media_types else "",
        "keep_url": f"{base_url}/keeps/{keep.id}",
    }
