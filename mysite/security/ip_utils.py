"""Utilities for safely resolving client IP addresses.

Behind reverse proxies ``REMOTE_ADDR`` is the nearest proxy, not the visitor.
Each proxy appends the address it received the request from to
``X-Forwarded-For``, so the only entries that can be believed are the ones
added by proxies we trust. Everything to their left was written by whoever
connected to the first trusted proxy, which may be the client itself.

``get_client_ip`` therefore walks the header from the right, skipping trusted
proxies (``TRUSTED_PROXY_IPS``, addresses or CIDR ranges), and returns the
first address that is not one. The left-most entry is never taken on trust
outside DEBUG.
"""

from __future__ import annotations

import ipaddress
from functools import lru_cache
from typing import Iterable, List, Tuple, Union

from django.conf import settings

IPAddress = Union[ipaddress.IPv4Address, ipaddress.IPv6Address]
IPNetwork = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]


def _parse_ip_list(header_value: str | None) -> List[str]:
    if not header_value:
        return []
    return [part.strip() for part in header_value.split(",") if part.strip()]


def _normalize_ip(ip: str | None) -> str | None:
    if not ip:
        return None
    try:
        return str(ipaddress.ip_address(ip))
    except ValueError:
        return ip.strip()


def _parse_ip(value: str | None) -> IPAddress | None:
    """Parse one address, or return None when it is missing or malformed."""
    if not value:
        return None
    try:
        ip = ipaddress.ip_address(value.strip())
    except ValueError:
        return None
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        return ip.ipv4_mapped
    return ip


def parse_trusted_proxies(entries: Iterable[str]) -> Tuple[IPNetwork, ...]:
    """Parse proxy addresses and CIDR ranges.

    Raises ValueError on an entry that is neither.
    """
    return _parse_trusted_proxies(tuple(entry.strip() for entry in entries if entry and entry.strip()))


@lru_cache(maxsize=16)
def _parse_trusted_proxies(entries: Tuple[str, ...]) -> Tuple[IPNetwork, ...]:
    return tuple(ipaddress.ip_network(entry, strict=False) for entry in entries)


def _is_trusted(ip: IPAddress, networks: Iterable[IPNetwork]) -> bool:
    return any(ip in network for network in networks)


def _debug_client_ip(remote_addr: str | None, forwarded_for: List[str], real_ip: str | None) -> str | None:
    """Permissive DEBUG-only resolution: the left-most forwarded address.

    A client can spoof this. It is kept so local development behaves as it
    always has; rate limits and throttles are off there anyway.
    """
    if forwarded_for:
        return _normalize_ip(forwarded_for[0]) or remote_addr
    if real_ip:
        return _normalize_ip(real_ip) or remote_addr
    return _normalize_ip(remote_addr)


def get_client_ip(request) -> str | None:
    """Resolve the originating client IP with proxy awareness.

    - ``TRUST_FORWARDED_FOR`` off: ``REMOTE_ADDR``; forwarded headers are ignored.
    - DEBUG: the left-most ``X-Forwarded-For`` entry (spoofable, dev only).
    - Otherwise forwarded headers count only when ``REMOTE_ADDR`` is a trusted
      proxy. ``X-Forwarded-For`` is walked right to left past trusted proxies;
      the first untrusted address is the client. A malformed entry stops the
      walk at the last trusted hop, since nothing to its left can be vouched for.
    """
    raw_remote_addr = request.META.get("REMOTE_ADDR")
    forwarded_for = _parse_ip_list(request.META.get("HTTP_X_FORWARDED_FOR"))
    real_ip = request.META.get("HTTP_X_REAL_IP")

    trust_forwarded = getattr(settings, "TRUST_FORWARDED_FOR", settings.DEBUG)
    if not trust_forwarded:
        return _normalize_ip(raw_remote_addr)

    if settings.DEBUG:
        return _debug_client_ip(raw_remote_addr, forwarded_for, real_ip)

    remote_ip = _parse_ip(raw_remote_addr)
    trusted = parse_trusted_proxies(getattr(settings, "TRUSTED_PROXY_IPS", []) or [])
    if remote_ip is None or not trusted or not _is_trusted(remote_ip, trusted):
        # Without a trusted immediate peer, forwarded data is attacker-controlled.
        return _normalize_ip(raw_remote_addr)

    if forwarded_for:
        nearest_trusted = remote_ip
        for candidate in reversed(forwarded_for):
            ip = _parse_ip(candidate)
            if ip is None:
                return str(nearest_trusted)
            if not _is_trusted(ip, trusted):
                return str(ip)
            nearest_trusted = ip
        # Every hop is a trusted proxy; the left-most one originated the request.
        return str(nearest_trusted)

    parsed_real_ip = _parse_ip(real_ip)
    if parsed_real_ip is not None:
        return str(parsed_real_ip)

    return str(remote_ip)


def ratelimit_client_ip(request) -> str:
    """django-ratelimit ``RATELIMIT_IP_META_KEY`` hook (``key="ip"``).

    Also the identity DRF throttles use, so every IP-keyed limit shares one
    resolver. Always returns a parseable address, which django-ratelimit needs.
    """
    ip = _parse_ip(get_client_ip(request)) or _parse_ip(request.META.get("REMOTE_ADDR"))
    return str(ip) if ip is not None else "0.0.0.0"


__all__ = ["get_client_ip", "parse_trusted_proxies", "ratelimit_client_ip"]
