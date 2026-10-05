"""Circle activity notifications: new photos, comments, replies, mentions and likes.

Views call the ``notify_*`` helpers after a write. Those queue
``send_activity_notifications``, which works out who should hear about it and
hands each recipient to the sender of every channel they turned on. The journal
import writes rows straight to the database and never calls these helpers, so
imported history doesn't notify anyone.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from django.utils.text import Truncator

from mysite.circles.models import CircleMembership
from mysite.emails.services import email_dispatch_service
from mysite.emails.tasks import send_email_task
from mysite.emails.templates import (
    KEEP_COMMENT_TEMPLATE,
    KEEP_LIKE_TEMPLATE,
    KEEP_MENTION_TEMPLATE,
    KEEP_NEW_MEDIA_TEMPLATE,
    KEEP_REPLY_TEMPLATE,
)
from mysite.messaging.tasks import send_push_async, send_sms_async
from mysite.users.models import (
    NotificationChannel,
    NotificationPhone,
    PushSubscription,
    User,
    UserNotificationPreferences,
)

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
# The daily text counter outlives its day by a little, then expires.
SMS_ALLOWANCE_WINDOW_SECONDS = 25 * 60 * 60


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
        for channel in prefs.enabled_channels():
            CHANNEL_SENDERS[channel](recipient, event, context)


def _send_email(recipient, event: str, context: dict) -> None:
    if not (recipient.email and recipient.email_verified):
        return
    send_email_task.delay(
        to_email=recipient.email,
        template_id=EMAIL_TEMPLATES[event],
        context={**context, "recipient_name": recipient.first_name or recipient.display_name},
    )


def _summary(event: str, context: dict) -> str:
    """One line describing the activity: the email's subject, e.g. "Pat liked your post in Smith Family"."""
    return email_dispatch_service.get_template(EMAIL_TEMPLATES[event]).render(context).subject


def _send_sms(recipient, event: str, context: dict) -> None:
    # Texts cost money: only when switched on server-side, only to a number the
    # user proved is theirs, and only up to a daily cap.
    if not settings.NOTIFICATIONS_SMS_ENABLED:
        return
    phone = NotificationPhone.objects.filter(user=recipient, verified_at__isnull=False).first()
    if phone is None:
        return
    if not _take_sms_allowance(recipient):
        logger.warning("Daily text limit reached; not texting %s notification to user %s", event, recipient.id)
        return
    # The summary and a link only: comment text stays out of texts.
    send_sms_async.delay(phone.phone_number, f"Circles: {_summary(event, context)} {context['keep_url']}")


def _take_sms_allowance(recipient) -> bool:
    """Count one text against the recipient's daily limit; False once it's used up."""
    key = f"notifications:sms:{recipient.id}:{timezone.localdate().isoformat()}"
    cache.add(key, 0, SMS_ALLOWANCE_WINDOW_SECONDS)
    try:
        sent = cache.incr(key)
    except ValueError:
        # The key expired between add and incr.
        cache.set(key, 1, SMS_ALLOWANCE_WINDOW_SECONDS)
        sent = 1
    return sent <= settings.NOTIFICATIONS_SMS_DAILY_LIMIT


def _send_push(recipient, event: str, context: dict) -> None:
    if not settings.NOTIFICATIONS_PUSH_ENABLED:
        return
    if not PushSubscription.objects.filter(user=recipient).exists():
        return
    send_push_async.delay(
        recipient.id,
        {
            "title": _summary(event, context),
            "body": context.get("comment_text") or context["post_summary"],
            "url": context["keep_url"],
            # Later notices about the same post replace earlier ones on the device.
            "tag": context["keep_url"],
        },
    )


CHANNEL_SENDERS = {
    NotificationChannel.EMAIL: _send_email,
    NotificationChannel.SMS: _send_sms,
    NotificationChannel.PUSH: _send_push,
}
