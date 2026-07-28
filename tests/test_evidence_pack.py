"""Unit tests for the evidence pack builder."""

import io
import json
import zipfile
from datetime import datetime, timezone
from types import SimpleNamespace

from agentforge.evidence_pack import build_evidence_pack


def _sample():
    task = SimpleNamespace(
        id="tc-20260421-abc",
        agent_id="code-review-v1",
        status="completed",
        inputs={"repo_url": "https://example.com/repo"},
        constraints=None,
        created_at=datetime(2026, 4, 21, 10, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 4, 21, 10, 5, tzinfo=timezone.utc),
    )
    agent = SimpleNamespace(
        id="code-review-v1",
        name="Code Review",
        version=3,
        risk_class="limited",
        card={"kind": "AgentCapabilityCard", "meta": {"id": "code-review-v1"}},
        signature="abc123",
    )
    execution = SimpleNamespace(
        id="run-xyz",
        task_id="tc-20260421-abc",
        server_id="srv-1",
        status="completed",
        started_at=datetime(2026, 4, 21, 10, 1, tzinfo=timezone.utc),
        completed_at=datetime(2026, 4, 21, 10, 4, tzinfo=timezone.utc),
        elapsed_seconds=180,
        exit_code=0,
        metrics={"tokens": 500},
        results_path=None,
    )
    events = [
        SimpleNamespace(
            id="e1",
            created_at=datetime(2026, 4, 21, 10, 0, 1, tzinfo=timezone.utc),
            event_type="task.created",
            actor_id="consumer-1",
            actor_role="consumer",
            resource_type="task",
            resource_id="tc-20260421-abc",
            payload={"inputs": {"repo_url": "https://example.com/repo"}},
        ),
        SimpleNamespace(
            id="e2",
            created_at=datetime(2026, 4, 21, 10, 4, 30, tzinfo=timezone.utc),
            event_type="task.completed",
            actor_id="system",
            actor_role="system",
            resource_type="task",
            resource_id="tc-20260421-abc",
            payload={"exit_code": 0},
        ),
    ]
    return task, agent, execution, events


def _open_pack(pack_bytes: bytes) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(pack_bytes))


class TestBuildEvidencePack:
    def test_produces_valid_zip(self):
        task, agent, execution, events = _sample()
        pack = build_evidence_pack(task, agent, execution, events, None)
        assert zipfile.is_zipfile(io.BytesIO(pack))

    def test_contains_required_files(self):
        task, agent, execution, events = _sample()
        pack = build_evidence_pack(task, agent, execution, events, None)
        with _open_pack(pack) as zf:
            names = set(zf.namelist())
        required = {
            "README.md",
            "manifest.json",
            "task.json",
            "capability_card.json",
            "provenance.json",
            "event_log.json",
            "execution.json",
        }
        assert required.issubset(names)

    def test_manifest_lists_included_files(self):
        task, agent, execution, events = _sample()
        pack = build_evidence_pack(task, agent, execution, events, None)
        with _open_pack(pack) as zf:
            manifest = json.loads(zf.read("manifest.json"))
        assert manifest["task_id"] == task.id
        assert manifest["regulation"] == "EU 2024/1689"
        assert "event_log.json" in manifest["files"]

    def test_event_log_roundtrip(self):
        task, agent, execution, events = _sample()
        pack = build_evidence_pack(task, agent, execution, events, None)
        with _open_pack(pack) as zf:
            log = json.loads(zf.read("event_log.json"))
        assert len(log) == 2
        assert log[0]["event_type"] == "task.created"

    def test_provenance_matches_schema(self):
        task, agent, execution, events = _sample()
        pack = build_evidence_pack(task, agent, execution, events, None)
        with _open_pack(pack) as zf:
            prov = json.loads(zf.read("provenance.json"))
        assert prov["ai_generated"] is True
        assert prov["agent"]["risk_class"] == "limited"

    def test_includes_result_files_when_present(self, tmp_path):
        task, agent, execution, events = _sample()
        (tmp_path / "output.md").write_text("# Report\n\nFindings.")
        (tmp_path / "usage.json").write_text('{"tokens": 500}')

        pack = build_evidence_pack(task, agent, execution, events, tmp_path)
        with _open_pack(pack) as zf:
            names = set(zf.namelist())
        assert "output/output.md" in names
        assert "output/usage.json" in names

    def test_skips_missing_results_dir(self):
        task, agent, execution, events = _sample()
        pack = build_evidence_pack(task, agent, execution, events, None)
        with _open_pack(pack) as zf:
            names = set(zf.namelist())
        assert not any(n.startswith("output/") for n in names)

    def test_works_without_execution(self):
        task, agent, _, events = _sample()
        pack = build_evidence_pack(task, agent, None, events, None)
        with _open_pack(pack) as zf:
            names = set(zf.namelist())
        assert "execution.json" not in names
        assert "manifest.json" in names
