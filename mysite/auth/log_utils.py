"""Helpers for emitting auth logs without leaking PII (ADR-015).

OAuth and account flows previously logged raw email addresses and Google
subject ids at INFO/WARNING level. These helpers mask those values so logs
stay useful for correlation/debugging without becoming a PII store.
"""
from __future__ import annotations


def mask_email(email: str | None) -> str:
    """Mask an email for logging.

    ``jane.doe@example.com`` -> ``j***@example.com``. The domain is kept (useful
    for debugging) while the local part is reduced to its first character.
    """
    if not email or '@' not in email:
        return '***'
    local, _, domain = email.partition('@')
    visible = local[:1] if local else ''
    return f"{visible}***@{domain}"


def mask_id(value: str | None, keep: int = 6) -> str:
    """Mask an opaque identifier (e.g. a Google ``sub``) for logging."""
    if not value:
        return '***'
    return f"{value[:keep]}..." if len(value) > keep else value
