"""Unit tests for the modification tracker (Art. 43)."""

from agentforge.modifications import (
    NON_SUBSTANTIAL_SIGNALS,
    SUBSTANTIAL_SIGNALS,
    classify_auto,
    diff_cards,
    modifications_to_markdown,
    summarise_diff,
)


def _card(**overrides):
    base = {
        "kind": "AgentCapabilityCard",
        "version": 1,
        "meta": {"id": "credit-scorer-v1", "name": "Credit Scorer"},
        "capabilities": {
            "domain": "fintech",
            "tags": ["credit", "ml"],
            "description": "Scores consumer credit applications.",
            "inputs": [{"name": "payload", "type": "string"}],
            "outputs": [{"name": "score", "type": "number"}],
            "constraints": {"max_input_size": 1024},
        },
        "runtime": {
            "model": "anthropic/claude-sonnet-4-6",
            "tools": ["python"],
            "server_type": "cax11",
            "compute_tier": "container",
        },
        "pricing": {"model": "per_run", "base_price_usd": 0.5},
        "risk_class": "high",
    }
    for k, v in overrides.items():
        if "." in k:
            path, leaf = k.rsplit(".", 1)
            parts = path.split(".")
            target = base
            for p in parts:
                target = target[p]
            target[leaf] = v
        else:
            base[k] = v
    return base


class TestDiffCards:
    def test_no_change_returns_empty(self):
        assert diff_cards(_card(), _card()) == {}

    def test_detects_leaf_change(self):
        diff = diff_cards(_card(), _card(**{"runtime.model": "openai/gpt-5-mini"}))
        assert "runtime.model" in diff
        assert diff["runtime.model"]["new"] == "openai/gpt-5-mini"

    def test_detects_new_field(self):
        a = _card()
        b = _card()
        b["runtime"]["gpu"] = "rtx-4090"
        diff = diff_cards(a, b)
        assert "runtime.gpu" in diff
        assert diff["runtime.gpu"]["old"] is None

    def test_detects_missing_field(self):
        a = _card()
        b = _card()
        del b["runtime"]["server_type"]
        diff = diff_cards(a, b)
        assert "runtime.server_type" in diff
        assert diff["runtime.server_type"]["new"] is None


class TestClassifyAuto:
    def test_empty_diff_is_non_substantial(self):
        assert classify_auto({}) == "non_substantial"

    def test_model_change_is_substantial(self):
        assert classify_auto({"runtime.model": {"old": "a", "new": "b"}}) == "substantial"

    def test_risk_class_change_is_substantial(self):
        assert classify_auto({"risk_class": {"old": "high", "new": "limited"}}) == "substantial"

    def test_tags_only_change_is_non_substantial(self):
        assert (
            classify_auto({"capabilities.tags": {"old": ["a"], "new": ["b"]}})
            == "non_substantial"
        )

    def test_pricing_change_is_non_substantial(self):
        assert (
            classify_auto({"pricing.base_price_usd": {"old": 0.5, "new": 0.75}})
            == "non_substantial"
        )

    def test_mixed_substantial_wins(self):
        diff = {
            "capabilities.tags": {"old": [], "new": ["x"]},
            "runtime.model": {"old": "a", "new": "b"},
        }
        assert classify_auto(diff) == "substantial"

    def test_unknown_field_is_unclassified(self):
        assert classify_auto({"weird.new_field": {"old": None, "new": 1}}) == "unclassified"

    def test_nested_substantial_field_detected(self):
        # A field like runtime.tools.0 (specific tool index) should still match
        diff = {"runtime.tools.0": {"old": "python", "new": "bash"}}
        assert classify_auto(diff) == "substantial"

    def test_signal_sets_cover_key_fields(self):
        assert "risk_class" in SUBSTANTIAL_SIGNALS
        assert "runtime.model" in SUBSTANTIAL_SIGNALS
        assert "pricing" in NON_SUBSTANTIAL_SIGNALS


class TestSummariseDiff:
    def test_empty(self):
        assert summarise_diff({}) == "No card fields changed."

    def test_short_list(self):
        s = summarise_diff(
            {"runtime.model": {}, "capabilities.tags": {}}
        )
        assert "runtime.model" in s
        assert "capabilities.tags" in s

    def test_long_list_truncates(self):
        s = summarise_diff({f"k{i}": {} for i in range(10)})
        assert "including:" in s


class TestMarkdownExport:
    def test_empty_records(self):
        md = modifications_to_markdown("a1", "Agent One", [])
        assert "No modifications recorded" in md
        assert "Annex IV addendum" in md
        assert "a1" in md

    def test_renders_records(self):
        md = modifications_to_markdown(
            "a1",
            "Agent One",
            [
                {
                    "created_at": "2026-04-22T10:00:00Z",
                    "modification_type": "version_bump",
                    "classification": "substantial",
                    "version_from": 1,
                    "version_to": 2,
                    "summary": "Changed: runtime.model",
                    "rationale": "Switched to newer foundation model",
                    "triggered_reassessment": True,
                    "reassessment_at": "2026-04-23T09:00:00Z",
                }
            ],
        )
        assert "substantial" in md
        assert "v1 → v2" in md
        assert "conformity assessment repeated" in md
        assert "Switched to newer foundation model" in md

    def test_regulation_reference(self):
        md = modifications_to_markdown("a1", "Agent One", [])
        assert "Art. 43" in md
