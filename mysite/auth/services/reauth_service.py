"""Re-authentication by emailed one-time code.

Sensitive actions (creating an API token) ask a signed-in user to prove they
still control the account's email. The code lives only in the cache, hashed,
and is checked inside the protected request itself; no grant is stored.

Not reusing ``TwoFactorService.send_otp``/``verify_otp`` on purpose: that path
stores the full code as ``code_preview``, never counts wrong guesses and shares
the login 2FA send budget. TOTP, SMS and recovery codes are never accepted here,
because a stolen session can re-enrol those factors.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

from django.conf import settings
from django.core.cache import cache

from mysite.audit import log_security_event

MAX_ATTEMPTS_PER_CODE = 5
MAX_FAILURES_PER_WINDOW = 10
FAILURE_WINDOW_SECONDS = 24 * 60 * 60
LOCK_SECONDS = 24 * 60 * 60


def _code_key(user_id) -> str:
    return f"reauth:code:{user_id}"


def _attempts_key(user_id) -> str:
    return f"reauth:attempts:{user_id}"


def _fails_key(user_id) -> str:
    return f"reauth:fails:{user_id}"


def _locked_key(user_id) -> str:
    return f"reauth:locked:{user_id}"


def _code_ttl_seconds() -> int:
    # Same lifetime the code email promises ("expires in N minutes").
    return int(getattr(settings, "TWOFA_CODE_EXPIRY_MINUTES", 10)) * 60


def _hash_code(code: str) -> str:
    key = getattr(settings, "TWOFA_CODE_SIGNING_KEY", None) or settings.SECRET_KEY
    return hmac.new(key.encode("utf-8"), code.encode("utf-8"), hashlib.sha256).hexdigest()


def _incr(key: str, timeout: int) -> int:
    """Atomically bump a counter, starting its expiry window on first use."""
    cache.add(key, 0, timeout=timeout)
    try:
        return cache.incr(key)
    except ValueError:  # expired between add and incr
        cache.set(key, 1, timeout=timeout)
        return 1


def is_reauth_locked(user) -> bool:
    return bool(cache.get(_locked_key(user.pk)))


def send_reauth_code(user) -> bool:
    """Email a fresh 6-digit code to ``user.email``, replacing any earlier one.

    Returns False without sending while the user is locked out, since a code
    could not be used anyway.
    """
    if is_reauth_locked(user):
        log_security_event(
            "reauth.code_sent",
            actor_id=str(user.pk),
            status="denied",
            severity="warning",
            metadata={"reason": "locked"},
        )
        return False

    code = f"{secrets.randbelow(10**6):06d}"
    ttl = _code_ttl_seconds()
    cache.set(_code_key(user.pk), _hash_code(code), timeout=ttl)
    cache.delete(_attempts_key(user.pk))

    from mysite.emails.mailers import TwoFactorMailer

    TwoFactorMailer.send_2fa_code(user, code)
    log_security_event("reauth.code_sent", actor_id=str(user.pk), status="success", severity="info")
    return True


def verify_reauth(user, code) -> bool:
    """Check ``code`` against the user's emailed code. A match consumes it.

    Each code allows ``MAX_ATTEMPTS_PER_CODE`` wrong guesses before it is
    deleted. ``MAX_FAILURES_PER_WINDOW`` failures in 24h lock re-auth for 24h
    and email the user.
    """
    if is_reauth_locked(user):
        return False

    submitted = code.strip() if isinstance(code, str) else ""
    stored_hash = cache.get(_code_key(user.pk))
    if stored_hash and submitted and hmac.compare_digest(stored_hash, _hash_code(submitted)):
        # The delete is what consumes the code: of two concurrent requests that
        # both read the hash, only the one whose delete removed the key wins.
        if not cache.delete(_code_key(user.pk)):
            return False
        cache.delete(_attempts_key(user.pk))
        return True

    if stored_hash:
        attempts = _incr(_attempts_key(user.pk), _code_ttl_seconds())
        if attempts >= MAX_ATTEMPTS_PER_CODE:
            cache.delete_many([_code_key(user.pk), _attempts_key(user.pk)])

    failures = _incr(_fails_key(user.pk), FAILURE_WINDOW_SECONDS)
    log_security_event(
        "reauth.failed",
        actor_id=str(user.pk),
        status="denied",
        severity="warning",
        metadata={"failures": failures, "code_pending": bool(stored_hash)},
    )
    if failures >= MAX_FAILURES_PER_WINDOW:
        _lock(user)
    return False


def _lock(user) -> None:
    # add() so concurrent failures past the threshold send one email, not several.
    if not cache.add(_locked_key(user.pk), True, timeout=LOCK_SECONDS):
        return
    cache.delete_many([_code_key(user.pk), _attempts_key(user.pk), _fails_key(user.pk)])

    from mysite.emails.mailers import TwoFactorMailer

    TwoFactorMailer.send_reauth_locked_alert(user, lock_hours=LOCK_SECONDS // 3600)
    log_security_event(
        "reauth.locked",
        actor_id=str(user.pk),
        status="denied",
        severity="warning",
        metadata={"lock_hours": LOCK_SECONDS // 3600},
    )


__all__ = ["is_reauth_locked", "send_reauth_code", "verify_reauth"]
