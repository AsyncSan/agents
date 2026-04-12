"""Tests for Ed25519 agent card signing and verification."""

from agentforge.signing import (
    canonicalize_card,
    generate_keypair,
    sign_card,
    verify_card,
)


def _sample_card():
    return {
        "kind": "AgentCapabilityCard",
        "version": 1,
        "meta": {"id": "test-agent", "name": "Test", "provider": "p1"},
        "capabilities": {
            "domain": "research",
            "tags": ["web"],
            "description": "Test",
            "inputs": [],
            "outputs": [],
            "constraints": {},
        },
        "runtime": {"snapshot_profile": "base"},
        "pricing": {"model": "per_execution", "base_price_usd": 3.00},
        "instructions": "secret prompt here",
    }


class TestKeypairGeneration:
    def test_returns_hex_strings(self):
        pub, priv = generate_keypair()
        assert len(bytes.fromhex(pub)) == 32
        assert len(bytes.fromhex(priv)) == 32

    def test_unique_keys(self):
        pairs = [generate_keypair() for _ in range(10)]
        public_keys = {p[0] for p in pairs}
        assert len(public_keys) == 10

    def test_pub_priv_different(self):
        pub, priv = generate_keypair()
        assert pub != priv


class TestCanonicalize:
    def test_strips_instructions(self):
        card = _sample_card()
        canonical = canonicalize_card(card)
        assert b"instructions" not in canonical
        assert b"secret prompt" not in canonical

    def test_strips_signature_field(self):
        card = _sample_card()
        card["signature"] = "abc123"
        canonical = canonicalize_card(card)
        assert b"signature" not in canonical

    def test_deterministic(self):
        card = _sample_card()
        assert canonicalize_card(card) == canonicalize_card(card)

    def test_sorted_keys(self):
        card = _sample_card()
        canonical = canonicalize_card(card).decode()
        # "capabilities" should come before "kind" alphabetically
        assert canonical.index("capabilities") < canonical.index("kind")

    def test_no_whitespace(self):
        canonical = canonicalize_card(_sample_card()).decode()
        assert "\n" not in canonical
        assert "  " not in canonical


class TestSignAndVerify:
    def test_sign_and_verify_roundtrip(self):
        pub, priv = generate_keypair()
        card = _sample_card()
        sig = sign_card(card, priv)
        assert verify_card(card, sig, pub)

    def test_tampered_card_fails(self):
        pub, priv = generate_keypair()
        card = _sample_card()
        sig = sign_card(card, priv)

        # Tamper with the card
        card["pricing"]["base_price_usd"] = 0.01
        assert not verify_card(card, sig, pub)

    def test_wrong_key_fails(self):
        _, priv = generate_keypair()
        other_pub, _ = generate_keypair()
        card = _sample_card()
        sig = sign_card(card, priv)
        assert not verify_card(card, sig, other_pub)

    def test_invalid_signature_fails(self):
        pub, _ = generate_keypair()
        card = _sample_card()
        assert not verify_card(card, "deadbeef" * 16, pub)

    def test_instructions_change_does_not_invalidate(self):
        pub, priv = generate_keypair()
        card = _sample_card()
        sig = sign_card(card, priv)

        # Changing instructions should NOT invalidate (instructions are stripped)
        card["instructions"] = "completely different prompt"
        assert verify_card(card, sig, pub)

    def test_signature_is_hex(self):
        _, priv = generate_keypair()
        sig = sign_card(_sample_card(), priv)
        bytes.fromhex(sig)  # should not raise
        assert len(sig) == 128  # Ed25519 sig is 64 bytes = 128 hex chars


class TestEdgeCases:
    def test_empty_card(self):
        pub, priv = generate_keypair()
        card = {}
        sig = sign_card(card, priv)
        assert verify_card(card, sig, pub)

    def test_verify_garbage_public_key(self):
        card = _sample_card()
        assert not verify_card(card, "aa" * 64, "not_hex")

    def test_verify_short_public_key(self):
        card = _sample_card()
        assert not verify_card(card, "aa" * 64, "aabb")
