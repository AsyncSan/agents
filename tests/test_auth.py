"""Tests for authentication utilities."""

from agentforge.api.auth import generate_api_key, hash_api_key


class TestAPIKeyGeneration:
    def test_key_format(self):
        key = generate_api_key()
        assert key.startswith("af_")
        assert len(key) > 10

    def test_keys_are_unique(self):
        keys = {generate_api_key() for _ in range(100)}
        assert len(keys) == 100

    def test_hash_deterministic(self):
        key = "af_test_key_123"
        h1 = hash_api_key(key)
        h2 = hash_api_key(key)
        assert h1 == h2

    def test_hash_different_keys(self):
        h1 = hash_api_key("af_key_one")
        h2 = hash_api_key("af_key_two")
        assert h1 != h2

    def test_hash_is_hex(self):
        h = hash_api_key("af_test_key")
        assert all(c in "0123456789abcdef" for c in h)
        assert len(h) == 64  # SHA256 hex digest


class TestSecretSet:
    def test_consumer_provider_isolation(self):
        """Verify SecretSet supports isolated consumer/provider keys."""
        from agentforge.dispatch.dispatcher import SecretSet  # noqa: F811

        s = SecretSet(
            consumer_keys={"OPENAI_API_KEY": "sk-consumer-123"},
            provider_keys={"ANTHROPIC_API_KEY": "sk-provider-456"},
        )
        assert "OPENAI_API_KEY" in s.consumer_keys
        assert "ANTHROPIC_API_KEY" in s.provider_keys
        # Keys don't leak across tenants
        assert "ANTHROPIC_API_KEY" not in s.consumer_keys
        assert "OPENAI_API_KEY" not in s.provider_keys

    def test_empty_secrets(self):
        from agentforge.dispatch.dispatcher import SecretSet

        s = SecretSet()
        assert s.consumer_keys is None
        assert s.provider_keys is None
        assert s.platform_keys is None
        assert s.gh_token is None
