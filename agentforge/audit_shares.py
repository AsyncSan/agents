"""Token helpers for the auditor read-only share mechanism.

Tokens are generated with ``secrets.token_urlsafe`` (256 bits) and
prefixed with ``ar_`` so they are recognisable as audit-read tokens in
logs. Only the SHA-256 hash of the token is persisted; the raw token is
shown to the owner exactly once on creation.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

TOKEN_PREFIX = "ar_"
DEFAULT_TTL_DAYS = 30
MAX_TTL_DAYS = 180


def generate_token() -> tuple[str, str, str]:
    """Return ``(raw_token, token_hash, token_prefix)``.

    ``raw_token`` is ``ar_<urlsafe-base64>``; ``token_prefix`` is the first
    12 characters of the raw token, stored for owner-side identification.
    """
    raw = TOKEN_PREFIX + secrets.token_urlsafe(32)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return raw, digest, raw[:12]


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def resolve_expiry(ttl_days: int | None) -> datetime:
    if ttl_days is None:
        ttl_days = DEFAULT_TTL_DAYS
    if ttl_days < 1:
        raise ValueError("ttl_days must be at least 1")
    if ttl_days > MAX_TTL_DAYS:
        raise ValueError(f"ttl_days may not exceed {MAX_TTL_DAYS}")
    return datetime.now(timezone.utc) + timedelta(days=ttl_days)


def is_active(
    expires_at: datetime,
    revoked_at: datetime | None,
    now: datetime | None = None,
) -> bool:
    now = now or datetime.now(timezone.utc)
    if revoked_at is not None and revoked_at <= now:
        return False
    return expires_at > now
