"""Utilities for safely resolving client IP addresses."""
from __future__ import annotations

import ipaddress
from typing import Iterable, List

from django.conf import settings


def _parse_ip_list(header_value: str | None) -> List[str]:
    if not header_value:
        return []
    return [part.strip() for part in header_value.split(',') if part.strip()]


def _normalize_ip(ip: str | None) -> str | None:
    if not ip:
        return None
    try:
        return str(ipaddress.ip_address(ip))
    except ValueError:
        return ip.strip()


def _is_trusted_proxy(ip: str | None, trusted_proxies: Iterable[str]) -> bool:
    normalized = _normalize_ip(ip)
    return normalized is not None and normalized in trusted_proxies


def get_client_ip(request) -> str | None:
    """Resolve the originating client IP with proxy awareness.

    Uses environment-configured trust settings to avoid spoofing via
    X-Forwarded-For. In local development a permissive fallback keeps the
    previous behaviour to reduce setup friction.
    """
    remote_addr = request.META.get('REMOTE_ADDR')
    forwarded_for = _parse_ip_list(request.META.get('HTTP_X_FORWARDED_FOR'))
    real_ip = request.META.get('HTTP_X_REAL_IP')

    trust_forwarded = getattr(settings, 'TRUST_FORWARDED_FOR', settings.DEBUG)
    trusted_proxies = getattr(settings, 'TRUSTED_PROXY_IPS', []) or []

    # Local/dev environments stay permissive by default.
    if trust_forwarded and (settings.DEBUG or not trusted_proxies):
        if forwarded_for:
            return _normalize_ip(forwarded_for[0]) or remote_addr
        if real_ip:
            return _normalize_ip(real_ip) or remote_addr
        return _normalize_ip(remote_addr)

    if not trust_forwarded:
        # Ignore forwarded headers entirely.
        return _normalize_ip(remote_addr)

    # Production/staging with explicit trusted proxies.
    if not _is_trusted_proxy(remote_addr, trusted_proxies):
        # If the immediate sender isn't trusted, do not honour forwarded data.
        return _normalize_ip(remote_addr)

    # Walk the chain from left to right; first non-trusted IP is the client.
    for candidate in forwarded_for:
        normalized = _normalize_ip(candidate)
        if normalized and not _is_trusted_proxy(normalized, trusted_proxies):
            return normalized

    # Header only contained trusted proxies; fall back to real-ip header or remote.
    if real_ip and not _is_trusted_proxy(real_ip, trusted_proxies):
        return _normalize_ip(real_ip)

    if forwarded_for:
        return _normalize_ip(forwarded_for[0]) or _normalize_ip(remote_addr)

    return _normalize_ip(remote_addr)


__all__ = ['get_client_ip']
