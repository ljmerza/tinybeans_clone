"""Circle activity notifications: new photos, comments, replies, mentions and likes.

Views call the ``notify_*`` helpers after a write. Those queue
``send_activity_notifications``, which works out who should hear about it and
hands each recipient to the sender for the channel they picked. The journal
import writes rows straight to the database and never calls these helpers, so
imported history doesn't notify anyone.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils.text import Truncator

from mysite.circles.models import CircleMembership
from mysite.emails.tasks import send_email_task
from mysite.emails.templates import (
    KEEP_COMMENT_TEMPLATE,
    KEEP_LIKE_TEMPLATE,
    KEEP_MENTION_TEMPLATE,
    KEEP_NEW_MEDIA_TEMPLATE,
    KEEP_REPLY_TEMPLATE,
)
from mysite.users.models import NotificationChannel, User, UserNotificationPreferences

from .models import Keep, KeepComment, KeepCommentMention, KeepReaction

logger = logging.getLogger(__name__)


class ActivityEvent:
    NEW_MEDIA = "new_media"
    COMMENT = "comment"
    REPLY = "reply"
    MENTION = "mention"
    LIKE = "like"


# Preference flag that switches each event on or off.
PREFERENCE_FIELDS = {
    ActivityEvent.NEW_MEDIA: "notify_new_media",
    ActivityEvent.COMMENT: "notify_comments",
    ActivityEvent.REPLY: "notify_replies",
    # Shown as "Replies and mentions" in settings.
    ActivityEvent.MENTION: "notify_replies",
    ActivityEvent.LIKE: "notify_likes",
}

EMAIL_TEMPLATES = {
    ActivityEvent.NEW_MEDIA: KEEP_NEW_MEDIA_TEMPLATE,
    ActivityEvent.COMMENT: KEEP_COMMENT_TEMPLATE,
    ActivityEvent.REPLY: KEEP_REPLY_TEMPLATE,
    ActivityEvent.MENTION: KEEP_MENTION_TEMPLATE,
    ActivityEvent.LIKE: KEEP_LIKE_TEMPLATE,
}

# Unliking and liking again inside this window doesn't notify a second time.
LIKE_REPEAT_WINDOW_SECONDS = 24 * 60 * 60


def _queue(event: str, object_id, countdown: int = 0) -> None:
    from .tasks import send_activity_notifications

    transaction.on_commit(
        lambda: send_activity_notifications.apply_async(args=[event, str(object_id)], countdown=countdown)
    )


def notify_new_post(keep: Keep) -> None:
    """Tell the circle about a new post once its photos have had time to upload."""
    _queue(ActivityEvent.NEW_MEDIA, keep.id, countdown=settings.NOTIFICATIONS_NEW_MEDIA_DELAY_SECONDS)


def notify_new_comment(comment: KeepComment) -> None:
    """Tell the post's author, the person replied to and anyone mentioned about a comment."""
    _queue(ActivityEvent.COMMENT, comment.id)


def notify_new_mentions(mentions) -> None:
    """Tell members an edit newly mentions about the comment."""
    for mention in mentions:
        _queue(ActivityEvent.MENTION, mention.id)


def notify_new_like(reaction: KeepReaction) -> None:
    """Tell the post's author about a like, at most once per liker per day."""
    if cache.add(f"notifications:like:{reaction.keep_id}:{reaction.user_id}", True, LIKE_REPEAT_WINDOW_SECONDS):
        _queue(ActivityEvent.LIKE, reaction.id)


def send_activity(event: str, object_id: str) -> None:
    """Resolve an activity to its recipients and send each one a notification.

    The object may be gone by now (deleted post, removed like); then nothing
    is sent.
    """
    if event == ActivityEvent.NEW_MEDIA:
        keep = Keep.objects.select_related("circle", "created_by").filter(id=object_id).first()
        if keep is None:
            return
        media_types = list(keep.media_files.values_list("media_type", flat=True))
        if not media_types:
            return
        members = User.objects.filter(circle_memberships__circle=keep.circle)
        _deliver(event, keep, keep.created_by, members, {"media_label": media_label(media_types)})

    elif event == ActivityEvent.COMMENT:
        comment = (
            KeepComment.objects.select_related("keep__circle", "keep__created_by", "user", "parent__user")
            .filter(id=object_id)
            .first()
        )
        if comment is None:
            return
        keep = comment.keep
        extra = {"comment_text": Truncator(comment.comment).chars(280)}
        # One notice per person per comment: a reply beats a mention (a reply's
        # @tag of the person replied to is a mention too), and both beat the
        # post author's comment notice.
        replied_to = comment.parent.user if comment.parent_id else None
        notified = set()
        if replied_to is not None:
            _deliver(ActivityEvent.REPLY, keep, comment.user, [replied_to], extra)
            notified.add(replied_to.id)
        mentioned = [
            mention.user for mention in comment.mentions.select_related("user") if mention.user_id not in notified
        ]
        if mentioned:
            _deliver(ActivityEvent.MENTION, keep, comment.user, mentioned, extra)
            notified.update(user.id for user in mentioned)
        if keep.created_by_id not in notified:
            _deliver(ActivityEvent.COMMENT, keep, comment.user, [keep.created_by], extra)

    elif event == ActivityEvent.MENTION:
        # Someone an edit added to a comment's mentions.
        mention = (
            KeepCommentMention.objects.select_related(
                "user", "comment__keep__circle", "comment__keep__created_by", "comment__user", "comment__parent"
            )
            .filter(id=object_id)
            .first()
        )
        if mention is None:
            return
        comment = mention.comment
        # The post's author and the person replied to heard about the comment when it was posted.
        if mention.user_id in (comment.keep.created_by_id, comment.parent.user_id if comment.parent_id else None):
            return
        extra = {"comment_text": Truncator(comment.comment).chars(280)}
        _deliver(event, comment.keep, comment.user, [mention.user], extra)

    elif event == ActivityEvent.LIKE:
        reaction = (
            KeepReaction.objects.select_related("keep__circle", "keep__created_by", "user").filter(id=object_id).first()
        )
        if reaction is None:
            return
        _deliver(event, reaction.keep, reaction.user, [reaction.keep.created_by], {})

    else:
        logger.warning("Unknown activity notification event %s", event)


def media_label(media_types: list[str]) -> str:
    """Describe a post's media for a subject line, e.g. "3 new photos"."""
    count = len(media_types)
    kinds = set(media_types)
    if kinds == {"video"}:
        noun = "video" if count == 1 else "videos"
    elif kinds == {"photo"}:
        noun = "photo" if count == 1 else "photos"
    else:
        noun = "photos and videos"
    return f"a new {noun}" if count == 1 else f"{count} new {noun}"


def _deliver(event: str, keep: Keep, actor, candidates, extra: dict) -> None:
    """Send ``event`` to each candidate who is still in the circle and wants it."""
    candidate_ids = [user.id for user in candidates if user.id != actor.id]
    member_ids = CircleMembership.objects.filter(circle=keep.circle, user_id__in=candidate_ids).values_list(
        "user_id", flat=True
    )
    recipients = list(User.objects.filter(id__in=member_ids, is_active=True))
    if not recipients:
        return

    preferences = UserNotificationPreferences.effective_for_users(recipients, keep.circle)
    base_url = (settings.ACCOUNT_FRONTEND_BASE_URL or "http://localhost:3000").rstrip("/")
    context = {
        "actor_name": actor.display_name,
        "circle_name": keep.circle.name,
        "post_summary": Truncator(keep.title or keep.description).chars(80),
        "keep_url": f"{base_url}/keeps/{keep.id}",
        "settings_url": f"{base_url}/profile/notifications",
        **extra,
    }
    for recipient in recipients:
        prefs = preferences[recipient.id]
        if not getattr(prefs, PREFERENCE_FIELDS[event]):
            continue
        sender = CHANNEL_SENDERS.get(prefs.channel)
        if sender is None:
            logger.warning("No sender for notification channel %s", prefs.channel)
            continue
        sender(recipient, event, context)


def _send_email(recipient, event: str, context: dict) -> None:
    if not (recipient.email and recipient.email_verified):
        return
    send_email_task.delay(
        to_email=recipient.email,
        template_id=EMAIL_TEMPLATES[event],
        context={**context, "recipient_name": recipient.first_name or recipient.display_name},
    )


def _send_sms(recipient, event: str, context: dict) -> None:
    # Phone delivery isn't built yet; the preferences API won't let anyone pick it
    # unless NOTIFICATIONS_SMS_ENABLED is on.
    logger.info("Skipping %s notification for user %s: phone delivery is not available yet", event, recipient.id)


CHANNEL_SENDERS = {
    NotificationChannel.EMAIL: _send_email,
    NotificationChannel.SMS: _send_sms,
}
