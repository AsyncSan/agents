"""Unit tests for the auditor share token module."""

from datetime import datetime, timedelta, timezone

import pytest

from agentforge.audit_shares import (
    DEFAULT_TTL_DAYS,
    MAX_TTL_DAYS,
    TOKEN_PREFIX,
    generate_token,
    hash_token,
    is_active,
    resolve_expiry,
)


class TestTokenGeneration:
    def test_prefix_and_uniqueness(self):
        seen = set()
        for _ in range(50):
            raw, digest, prefix = generate_token()
            assert raw.startswith(TOKEN_PREFIX)
            assert prefix == raw[:12]
            assert digest == hash_token(raw)
            assert len(digest) == 64
            seen.add(raw)
        assert len(seen) == 50

    def test_hash_deterministic(self):
        raw, digest, _ = generate_token()
        assert hash_token(raw) == digest

    def test_hash_of_different_tokens_differs(self):
        a, _, _ = generate_token()
        b, _, _ = generate_token()
        assert hash_token(a) != hash_token(b)


class TestExpiry:
    def test_default_ttl_when_none(self):
        expires = resolve_expiry(None)
        delta = expires - datetime.now(timezone.utc)
        assert timedelta(days=DEFAULT_TTL_DAYS - 1) < delta < timedelta(
            days=DEFAULT_TTL_DAYS + 1
        )

    def test_explicit_ttl_respected(self):
        expires = resolve_expiry(7)
        delta = expires - datetime.now(timezone.utc)
        assert timedelta(days=6) < delta < timedelta(days=8)

    def test_rejects_zero(self):
        with pytest.raises(ValueError):
            resolve_expiry(0)

    def test_rejects_over_cap(self):
        with pytest.raises(ValueError):
            resolve_expiry(MAX_TTL_DAYS + 1)

    def test_accepts_max(self):
        resolve_expiry(MAX_TTL_DAYS)


class TestIsActive:
    def test_active_when_future(self):
        future = datetime.now(timezone.utc) + timedelta(days=1)
        assert is_active(future, None) is True

    def test_inactive_when_expired(self):
        past = datetime.now(timezone.utc) - timedelta(minutes=1)
        assert is_active(past, None) is False

    def test_inactive_when_revoked(self):
        future = datetime.now(timezone.utc) + timedelta(days=1)
        revoked = datetime.now(timezone.utc) - timedelta(minutes=1)
        assert is_active(future, revoked) is False

    def test_active_when_revoked_in_future_edge(self):
        # A revoked_at in the future should not yet count as revoked.
        future_exp = datetime.now(timezone.utc) + timedelta(days=7)
        future_rev = datetime.now(timezone.utc) + timedelta(days=1)
        assert is_active(future_exp, future_rev) is True
