"""Bearer authentication for API tokens. Used only by the agent API views.

It is never in ``DEFAULT_AUTHENTICATION_CLASSES``. Sent anywhere else, a
``circ_`` token reaches SimpleJWT, which rejects it (401). Sent here, a JWT is
ignored, so a stolen browser session can't reach the agent API either.
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from mysite.audit import log_security_event
from mysite.circles.models import CircleMembership
from mysite.security.ip_utils import get_client_ip_address
from mysite.users.models import UserRole

from . import services, tokens
from .models import CircleApiToken, RevokeReason
from .principal import ApiTokenPrincipal

# One message for every failure, so a caller can't tell an unknown token from a revoked one.
INVALID_TOKEN_MESSAGE = "Invalid, expired or revoked API token."
# last_used_at is written at most this often per token.
LAST_USED_INTERVAL = timedelta(seconds=60)


class CircleApiTokenAuthentication(BaseAuthentication):
    """``Authorization: Bearer circ_...``. Query-string tokens are ignored.

    The creator is checked on every request: they must still be active,
    verified (when that is enforced) and an admin of the token's circle.
    There is no superuser bypass. A failed creator check revokes the token
    for good.
    """

    def authenticate(self, request):
        parts = get_authorization_header(request).split()
        if len(parts) != 2 or parts[0].lower() != b"bearer":
            return None
        try:
            raw = parts[1].decode("ascii")
        except UnicodeDecodeError:
            return None
        if not raw.startswith(tokens.TOKEN_PREFIX):
            return None  # e.g. a JWT: not ours, and no other authenticator runs here
        if not tokens.is_well_formed(raw):
            self._fail(request, "malformed", raw)

        creator_is_admin = CircleMembership.objects.filter(
            circle=OuterRef("circle"), user=OuterRef("created_by"), role=UserRole.CIRCLE_ADMIN
        )
        token = (
            CircleApiToken.objects.select_related("circle", "created_by")
            .annotate(creator_is_admin=Exists(creator_is_admin))
            .filter(token_hash=tokens.hash_token(raw))
            .first()
        )
        if token is None:
            self._fail(request, "unknown", raw)
        if token.revoked_at is not None:
            self._fail(request, "revoked", raw)
        now = timezone.now()
        if token.expires_at is not None and token.expires_at <= now:
            self._fail(request, "expired", raw)

        reason = self._creator_problem(token)
        if reason:
            services.auto_revoke(token, reason)
            self._fail(request, reason, raw)

        if token.last_used_at is None or token.last_used_at < now - LAST_USED_INTERVAL:
            # Conditional, so concurrent requests still write once.
            CircleApiToken.objects.filter(pk=token.pk).filter(
                Q(last_used_at__isnull=True) | Q(last_used_at__lt=now - LAST_USED_INTERVAL)
            ).update(last_used_at=now, last_used_ip=get_client_ip_address(request))
        return ApiTokenPrincipal(token), token

    def authenticate_header(self, request):
        # Makes failures 401s rather than DRF's 403 fallback.
        return 'Bearer realm="circles-agent"'

    @staticmethod
    def _creator_problem(token) -> str | None:
        creator = token.created_by
        if not creator.is_active:
            return RevokeReason.CREATOR_INACTIVE
        # Same rule as ``mysite.auth.permissions.IsEmailVerified``.
        if getattr(settings, "EMAIL_VERIFICATION_ENFORCED", True) and not creator.email_verified:
            return RevokeReason.CREATOR_UNVERIFIED
        if not token.creator_is_admin:
            return RevokeReason.CREATOR_NOT_ADMIN
        return None

    @staticmethod
    def _fail(request, reason: str, raw: str):
        log_security_event(
            "api_token.auth_failed",
            status="denied",
            severity="warning",
            # Only the display-length prefix; never the token itself.
            metadata={
                "reason": str(reason),
                "prefix": tokens.display_prefix(raw),
                "ip": get_client_ip_address(request),
                "path": request.path,
            },
        )
        raise AuthenticationFailed(INVALID_TOKEN_MESSAGE)
