"""Token format: ``circ_`` plus 43 url-safe characters (256 random bits), stored as unkeyed SHA-256.

SHA-256 without a key is enough for 256-bit random input, costs nothing per
request and, unlike an HMAC on ``SECRET_KEY``, survives key rotation.
"""

from __future__ import annotations

import hashlib
import re
import secrets

TOKEN_PREFIX = "circ_"
TOKEN_LENGTH = 48
DISPLAY_PREFIX_LENGTH = 12
TOKEN_RE = re.compile(r"^circ_[A-Za-z0-9_-]{43}$")


def generate_token() -> str:
    return TOKEN_PREFIX + secrets.token_urlsafe(32)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def display_prefix(raw: str) -> str:
    return raw[:DISPLAY_PREFIX_LENGTH]


def is_well_formed(raw: str) -> bool:
    return len(raw) == TOKEN_LENGTH and bool(TOKEN_RE.match(raw))
