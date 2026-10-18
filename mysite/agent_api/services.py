"""Creating and revoking API tokens.

Revocation is a conditional ``UPDATE ... WHERE revoked_at IS NULL``, so a
token is revoked once and its reason is never overwritten. Nothing here logs
or returns a plaintext token except ``create_token``'s return value.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from mysite.audit import AuditEvent, log_audit_event, log_security_event
from mysite.circles.models import Circle
from mysite.users.models import UserRole

from . import tokens
from .models import CircleApiToken, RevokeReason


class TokenLimitReached(Exception):
    """The circle already has ``AGENT_API_MAX_TOKENS_PER_CIRCLE`` active tokens."""


def active_tokens(circle_id):
    """The circle's tokens that are neither revoked nor expired."""
    now = timezone.now()
    return CircleApiToken.objects.filter(circle_id=circle_id, revoked_at__isnull=True).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now)
    )


def at_token_limit(circle_id) -> bool:
    return active_tokens(circle_id).count() >= settings.AGENT_API_MAX_TOKENS_PER_CIRCLE


def create_token(*, circle_id, user, name: str, can_suggest: bool, expires_at) -> tuple[CircleApiToken, str]:
    """Make a token and return it with its plaintext, which is never stored or shown again.

    Raises ``TokenLimitReached`` at the cap. Every admin of the circle is
    emailed a notice once the transaction commits.
    """
    raw = tokens.generate_token()
    with transaction.atomic():
        # Holding the circle row makes the cap exact when two admins create at once.
        circle = Circle.objects.select_for_update().get(pk=circle_id)
        if at_token_limit(circle.pk):
            raise TokenLimitReached
        token = CircleApiToken.objects.create(
            circle=circle,
            created_by=user,
            name=name,
            token_hash=tokens.hash_token(raw),
            display_prefix=tokens.display_prefix(raw),
            can_suggest=can_suggest,
            expires_at=expires_at,
        )
        transaction.on_commit(lambda: _send_created_notice(token))

    log_audit_event(
        AuditEvent(
            action="api_token.create",
            actor_type="user",
            actor_id=str(user.pk),
            target_type="api_token",
            target_id=str(token.id),
            metadata={
                "circle_id": token.circle_id,
                "prefix": token.display_prefix,
                "can_suggest": token.can_suggest,
                "expires_at": token.expires_at.isoformat() if token.expires_at else None,
            },
        )
    )
    return token, raw


def circle_admins(circle_id):
    return (
        get_user_model()
        .objects.filter(
            circle_memberships__circle_id=circle_id,
            circle_memberships__role=UserRole.CIRCLE_ADMIN,
            is_active=True,
        )
        .order_by("id")
    )


def _send_created_notice(token: CircleApiToken) -> None:
    from mysite.emails.mailers import TokenMailer

    TokenMailer.send_api_token_created(token, list(circle_admins(token.circle_id)))


def revoke_token(token: CircleApiToken, *, by_user) -> bool:
    """Revoke one token by hand. Returns False if it was already revoked."""
    revoked = (
        CircleApiToken.objects.filter(pk=token.pk, revoked_at__isnull=True).update(
            revoked_at=timezone.now(), revoked_by=by_user, revoked_reason=RevokeReason.MANUAL
        )
        > 0
    )
    if revoked:
        log_audit_event(
            AuditEvent(
                action="api_token.revoke",
                actor_type="user",
                actor_id=str(by_user.pk),
                target_type="api_token",
                target_id=str(token.pk),
                metadata={"circle_id": token.circle_id, "prefix": token.display_prefix},
            )
        )
    token.refresh_from_db()
    return revoked


def _auto_revoke(queryset, reason: str) -> int:
    """Revoke every still-active token in ``queryset`` for ``reason``, logging each one."""
    targets = list(queryset.filter(revoked_at__isnull=True).values_list("id", "circle_id", "display_prefix"))
    revoked = 0
    for token_id, circle_id, prefix in targets:
        if not CircleApiToken.objects.filter(pk=token_id, revoked_at__isnull=True).update(
            revoked_at=timezone.now(), revoked_reason=reason
        ):
            continue  # someone else revoked it first
        revoked += 1
        log_security_event(
            "api_token.auto_revoke",
            target_id=str(token_id),
            status="success",
            severity="warning",
            metadata={"reason": reason, "circle_id": circle_id, "prefix": prefix},
        )
    return revoked


def auto_revoke(token: CircleApiToken, reason: str) -> bool:
    """Revoke a token whose creator lost the right to it (see ``authentication``)."""
    return _auto_revoke(CircleApiToken.objects.filter(pk=token.pk), reason) > 0


def revoke_tokens_for_user(user, *, reason: str, circle_id=None) -> int:
    """Revoke the active tokens ``user`` created, in one circle or all of them."""
    user_id = getattr(user, "pk", user)
    queryset = CircleApiToken.objects.filter(created_by_id=user_id)
    if circle_id is not None:
        queryset = queryset.filter(circle_id=circle_id)
    return _auto_revoke(queryset, reason)
