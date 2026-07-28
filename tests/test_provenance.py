"""Unit tests for Art. 50 provenance / watermarking."""

import json
from datetime import datetime, timezone
from types import SimpleNamespace

from agentforge.provenance import (
    DISCLOSURE_TEXT,
    PLATFORM_ID,
    PROVENANCE_VERSION,
    REGULATION_REF,
    build_provenance,
    provenance_headers,
    wrap_json,
    wrap_markdown,
)


def _sample_objects():
    task = SimpleNamespace(id="tc-20260421-aabbccdd")
    agent = SimpleNamespace(
        id="code-review-v1",
        name="Code Review Agent",
        version=3,
        risk_class="limited",
    )
    execution = SimpleNamespace(
        id="run-xyz-001",
        completed_at=datetime(2026, 4, 21, 12, 0, 0, tzinfo=timezone.utc),
    )
    return task, agent, execution


class TestBuildProvenance:
    def test_contains_ai_generated_flag(self):
        task, agent, execution = _sample_objects()
        p = build_provenance(task, agent, execution)
        assert p["ai_generated"] is True

    def test_identifies_platform_and_regulation(self):
        task, agent, execution = _sample_objects()
        p = build_provenance(task, agent, execution)
        assert p["platform"] == PLATFORM_ID
        assert p["regulation"] == REGULATION_REF
        assert p["schema_version"] == PROVENANCE_VERSION

    def test_embeds_agent_metadata(self):
        task, agent, execution = _sample_objects()
        p = build_provenance(task, agent, execution)
        assert p["agent"]["id"] == "code-review-v1"
        assert p["agent"]["name"] == "Code Review Agent"
        assert p["agent"]["version"] == 3
        assert p["agent"]["risk_class"] == "limited"

    def test_uses_execution_completion_time(self):
        task, agent, execution = _sample_objects()
        p = build_provenance(task, agent, execution)
        assert p["generated_at"].startswith("2026-04-21T12:00:00")

    def test_falls_back_when_execution_missing(self):
        task, agent, _ = _sample_objects()
        p = build_provenance(task, agent, None)
        assert p["execution_id"] is None
        assert p["generated_at"]


class TestProvenanceHeaders:
    def test_x_ai_generated_always_true(self):
        task, agent, execution = _sample_objects()
        h = provenance_headers(build_provenance(task, agent, execution))
        assert h["X-AI-Generated"] == "true"
        assert h["X-AI-Provenance-Version"] == PROVENANCE_VERSION

    def test_provenance_header_is_compact_json(self):
        task, agent, execution = _sample_objects()
        provenance = build_provenance(task, agent, execution)
        h = provenance_headers(provenance)
        parsed = json.loads(h["X-AI-Provenance"])
        assert parsed["task_id"] == "tc-20260421-aabbccdd"
        pretty = json.dumps(provenance, indent=2, sort_keys=True)
        assert len(h["X-AI-Provenance"]) < len(pretty)


class TestWrapMarkdown:
    def test_appends_disclosure_block(self):
        task, agent, execution = _sample_objects()
        p = build_provenance(task, agent, execution)
        wrapped = wrap_markdown("# Result\n\nBody.", p)
        assert "# Result\n\nBody." in wrapped
        assert "AI Content Disclosure" in wrapped
        assert DISCLOSURE_TEXT in wrapped

    def test_contains_machine_readable_block(self):
        task, agent, execution = _sample_objects()
        p = build_provenance(task, agent, execution)
        wrapped = wrap_markdown("# Result", p)
        start = wrapped.index("```json") + len("```json\n")
        end = wrapped.index("```\n", start)
        parsed = json.loads(wrapped[start:end])
        assert parsed["ai_generated"] is True


class TestWrapJson:
    def test_embeds_provenance_in_dict(self):
        task, agent, execution = _sample_objects()
        p = build_provenance(task, agent, execution)
        wrapped = wrap_json('{"answer": 42}', p)
        parsed = json.loads(wrapped)
        assert parsed["answer"] == 42
        assert parsed["_ai_provenance"]["ai_generated"] is True

    def test_leaves_invalid_json_untouched(self):
        task, agent, execution = _sample_objects()
        p = build_provenance(task, agent, execution)
        assert wrap_json("not json", p) == "not json"

    def test_leaves_array_payload_untouched(self):
        task, agent, execution = _sample_objects()
        p = build_provenance(task, agent, execution)
        assert wrap_json("[1,2,3]", p) == "[1,2,3]"
