"""Web push delivery to a user's subscribed browsers and installed apps."""

from __future__ import annotations

import json
import logging

from django.conf import settings
from django.utils import timezone

from mysite.users.models import PushSubscription

logger = logging.getLogger(__name__)

# Push services drop a message they can't deliver within this many seconds.
PUSH_TTL_SECONDS = 12 * 60 * 60
PUSH_TIMEOUT_SECONDS = 10
# The push service says the subscription is gone for good.
GONE_STATUSES = {404, 410}


def send_web_push(user_id: int, payload: dict) -> int:
    """Push ``payload`` to every device ``user_id`` subscribed; return how many accepted it.

    Subscriptions the push service reports as gone are deleted. pywebpush is
    imported here so an image built without it only skips push.
    """
    if not settings.NOTIFICATIONS_PUSH_ENABLED:
        return 0
    subscriptions = list(PushSubscription.objects.filter(user_id=user_id))
    if not subscriptions:
        return 0
    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        logger.error(
            "pywebpush is not installed; skipping push notification",
            extra={"event": "messaging.push.unavailable", "extra": {"user_id": user_id}},
        )
        return 0

    data = json.dumps(payload)
    delivered = 0
    for subscription in subscriptions:
        try:
            webpush(
                subscription_info=subscription.subscription_info(),
                data=data,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                # pywebpush fills in aud/exp on this dict, so each send gets its own.
                vapid_claims={"sub": settings.VAPID_SUBJECT},
                ttl=PUSH_TTL_SECONDS,
                timeout=PUSH_TIMEOUT_SECONDS,
            )
        except WebPushException as exc:
            status = getattr(exc.response, "status_code", None)
            if status in GONE_STATUSES:
                subscription.delete()
                logger.info(
                    "Removed expired push subscription",
                    extra={
                        "event": "messaging.push.subscription_expired",
                        "extra": {"user_id": user_id, "status": status},
                    },
                )
            else:
                logger.warning(
                    "Push notification failed",
                    extra={"event": "messaging.push.failed", "extra": {"user_id": user_id, "status": status}},
                )
            continue
        except Exception:
            logger.exception(
                "Push notification failed",
                extra={"event": "messaging.push.failed", "extra": {"user_id": user_id}},
            )
            continue
        delivered += 1
        PushSubscription.objects.filter(pk=subscription.pk).update(last_used_at=timezone.now())
    return delivered
