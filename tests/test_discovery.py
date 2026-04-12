"""Tests for agent discovery and registry API."""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

from agentforge.api.schemas import CategoryItem, CategoryListResponse

_NOW = datetime.now(timezone.utc)


def _make_mock_agent(**overrides):
    """Build a MagicMock Agent with valid defaults."""
    agent = MagicMock()
    agent.id = overrides.get("id", "test-agent")
    agent.name = overrides.get("name", "Test Agent")
    agent.description = overrides.get("description", "A test agent")
    agent.provider_id = overrides.get("provider_id", uuid.uuid4())
    agent.status = overrides.get("status", "active")
    agent.card = overrides.get("card", _make_agent_card())
    agent.trust_score = overrides.get("trust_score", 0.85)
    agent.total_executions = overrides.get("total_executions", 10)
    agent.success_count = overrides.get("success_count", 9)
    agent.created_at = overrides.get("created_at", _NOW)
    agent.updated_at = overrides.get("updated_at", _NOW)
    agent.signature = overrides.get("signature", None)
    agent.provider = overrides.get("provider", None)
    return agent


def _make_agent_card(
    domain="research",
    tags=None,
    base_price_usd=3.00,
):
    """Build a minimal agent card dict for testing."""
    return {
        "kind": "AgentCapabilityCard",
        "version": 1,
        "meta": {"id": "test", "name": "Test Agent", "provider": "p1"},
        "capabilities": {
            "domain": domain,
            "tags": tags or ["research", "web"],
            "description": "Test agent",
            "inputs": [],
            "outputs": [],
            "constraints": {},
        },
        "runtime": {"snapshot_profile": "base", "server_type": "cax11"},
        "pricing": {"model": "per_execution", "base_price_usd": base_price_usd},
        "instructions": "SECRET: do the thing",
    }


class TestInstructionStripping:
    def test_public_response_strips_instructions(self):
        from agentforge.api.routes_agents import _agent_to_response

        agent = _make_mock_agent()
        resp = _agent_to_response(agent, provider_name="TestProvider")
        assert "instructions" not in resp.card

    def test_provider_response_includes_instructions(self):
        from agentforge.api.routes_agents import _agent_to_response

        agent = _make_mock_agent()
        resp = _agent_to_response(
            agent, provider_name="TestProvider", include_instructions=True
        )
        assert "instructions" in resp.card
        assert resp.card["instructions"] == "SECRET: do the thing"

    def test_original_card_not_mutated(self):
        from agentforge.api.routes_agents import _agent_to_response

        card = _make_agent_card()
        agent = _make_mock_agent(card=card, trust_score=None)
        _agent_to_response(agent, provider_name="P")
        assert "instructions" in card


class TestSortOptions:
    def test_all_sort_keys_defined(self):
        from agentforge.api.routes_agents import _SORT_OPTIONS

        assert "trust" in _SORT_OPTIONS
        assert "price" in _SORT_OPTIONS
        assert "executions" in _SORT_OPTIONS
        assert "newest" in _SORT_OPTIONS


class TestCategorySchemas:
    def test_category_item(self):
        item = CategoryItem(name="research", count=5)
        assert item.name == "research"
        assert item.count == 5

    def test_category_list_response(self):
        resp = CategoryListResponse(
            domains=[CategoryItem(name="research", count=3)],
            tags=[
                CategoryItem(name="web", count=5),
                CategoryItem(name="analysis", count=2),
            ],
        )
        assert len(resp.domains) == 1
        assert len(resp.tags) == 2
        assert resp.tags[0].name == "web"


class TestDiscoveryQueryParams:
    """Test that the list_agents endpoint signature accepts all discovery params."""

    def test_endpoint_has_search_param(self):
        import inspect

        from agentforge.api.routes_agents import list_agents

        sig = inspect.signature(list_agents)
        params = list(sig.parameters.keys())
        assert "q" in params
        assert "min_trust" in params
        assert "max_price_usd" in params
        assert "sort_by" in params
        assert "domain" in params
        assert "tag" in params

    def test_categories_endpoint_exists(self):
        from agentforge.api.routes_agents import list_categories

        assert callable(list_categories)


class TestAgentCardStructure:
    def test_card_has_required_sections(self):
        card = _make_agent_card()
        assert card["kind"] == "AgentCapabilityCard"
        assert "capabilities" in card
        assert "runtime" in card
        assert "pricing" in card
        assert "domain" in card["capabilities"]
        assert "tags" in card["capabilities"]

    def test_pricing_accessible(self):
        card = _make_agent_card(base_price_usd=5.50)
        assert card["pricing"]["base_price_usd"] == 5.50

    def test_tags_are_list(self):
        card = _make_agent_card(tags=["code", "python", "review"])
        assert isinstance(card["capabilities"]["tags"], list)
        assert "python" in card["capabilities"]["tags"]
