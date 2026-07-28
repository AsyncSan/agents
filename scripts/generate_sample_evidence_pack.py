"""Generate a static sample evidence pack for the landing page download CTA.

Produces ``frontend/public/sample-evidence-pack.zip`` using mock data that
mirrors a real Security Audit Agent execution.

Run from the repo root:

    python scripts/generate_sample_evidence_pack.py
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from agentforge.evidence_pack import build_evidence_pack

REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET = REPO_ROOT / "frontend" / "public" / "sample-evidence-pack.zip"
SAMPLE_OUTPUT = REPO_ROOT / "examples" / "sample-report-juice-shop.md"


def _build() -> None:
    task = SimpleNamespace(
        id="tc-20260415-sample01",
        agent_id="security-audit-v1",
        status="completed",
        inputs={
            "repo_url": "https://github.com/juice-shop/juice-shop",
            "branch": "master",
        },
        constraints={"timeout_max": 600},
        created_at=datetime(2026, 4, 15, 11, 16, 10, tzinfo=timezone.utc),
        updated_at=datetime(2026, 4, 15, 11, 21, 30, tzinfo=timezone.utc),
    )
    agent = SimpleNamespace(
        id="security-audit-v1",
        name="Codebase Security Audit",
        version=2,
        risk_class="limited",
        card={
            "kind": "AgentCapabilityCard",
            "meta": {
                "id": "security-audit-v1",
                "name": "Codebase Security Audit",
                "provider": "5202ffa9-e103-4bd5-a4db-d89f31d2f998",
            },
            "capabilities": {
                "domain": "security",
                "tags": ["security", "audit", "compliance", "sast", "vulnerability"],
                "description": "Automated security audit: dependency vulnerabilities, secret scanning, SAST analysis, license compliance.",
                "inputs": [
                    {"name": "repo_url", "type": "string", "required": True},
                    {"name": "branch", "type": "string", "required": False, "default": "main"},
                ],
                "outputs": [{"name": "output.md", "type": "markdown", "guaranteed": True}],
            },
            "runtime": {
                "model": "anthropic/claude-sonnet-4-6",
                "server_type": "cax11",
                "snapshot_profile": "base",
                "estimated_duration_seconds": 240,
            },
            "pricing": {"model": "per_execution", "base_price_usd": 2.0},
        },
        signature="3e416f0cb99a99505499cb4d03aa9f996183a778a05353359bcbe46b5398e80037597512a0e5893f3b2988e3516a0c7b1f298603a2f1c299e1af599f22c94204",
    )
    execution = SimpleNamespace(
        id="run-sample-001",
        task_id=task.id,
        server_id="127039826",
        status="completed",
        started_at=datetime(2026, 4, 15, 11, 16, 26, tzinfo=timezone.utc),
        completed_at=datetime(2026, 4, 15, 11, 21, 10, tzinfo=timezone.utc),
        elapsed_seconds=284,
        exit_code=0,
        metrics={
            "model": "anthropic/claude-sonnet-4-6",
            "output_bytes": 5809,
            "output_tokens_est": 1452,
            "gateway_mode": "false",
        },
        results_path=None,
    )
    events = [
        SimpleNamespace(
            id=f"evt-{i:03d}",
            created_at=ts,
            event_type=event_type,
            actor_id=actor_id,
            actor_role=actor_role,
            resource_type="task",
            resource_id=task.id,
            payload=payload,
        )
        for i, (ts, event_type, actor_id, actor_role, payload) in enumerate(
            [
                (
                    datetime(2026, 4, 15, 11, 16, 10, tzinfo=timezone.utc),
                    "task.created",
                    "consumer-demo",
                    "consumer",
                    {"agent_id": agent.id, "inputs": task.inputs},
                ),
                (
                    datetime(2026, 4, 15, 11, 16, 11, tzinfo=timezone.utc),
                    "payment.authorized",
                    "consumer-demo",
                    "system",
                    {"amount_cents": 200, "rail": "stripe"},
                ),
                (
                    datetime(2026, 4, 15, 11, 16, 14, tzinfo=timezone.utc),
                    "server.provisioned",
                    "system",
                    "system",
                    {"server_id": "127039826", "snapshot": "370464673", "region": "nbg1"},
                ),
                (
                    datetime(2026, 4, 15, 11, 16, 26, tzinfo=timezone.utc),
                    "execution.started",
                    "system",
                    "system",
                    {"run_id": execution.id},
                ),
                (
                    datetime(2026, 4, 15, 11, 21, 10, tzinfo=timezone.utc),
                    "execution.completed",
                    "system",
                    "system",
                    {"exit_code": 0, "elapsed_seconds": 284},
                ),
                (
                    datetime(2026, 4, 15, 11, 21, 12, tzinfo=timezone.utc),
                    "server.destroyed",
                    "system",
                    "system",
                    {"server_id": "127039826"},
                ),
                (
                    datetime(2026, 4, 15, 11, 21, 20, tzinfo=timezone.utc),
                    "payment.captured",
                    "system",
                    "system",
                    {"amount_cents": 200, "platform_fee_cents": 40},
                ),
                (
                    datetime(2026, 4, 15, 11, 21, 22, tzinfo=timezone.utc),
                    "task.completed",
                    "system",
                    "system",
                    {"status": "completed"},
                ),
            ],
            start=1,
        )
    ]

    results_dir: Path | None = None
    if SAMPLE_OUTPUT.is_file():
        staging = REPO_ROOT / ".tmp_sample_pack"
        staging.mkdir(exist_ok=True)
        (staging / "output.md").write_text(SAMPLE_OUTPUT.read_text())
        (staging / "usage.json").write_text(
            '{"model": "anthropic/claude-sonnet-4-6", "output_tokens_est": 1452}'
        )
        results_dir = staging

    pack = build_evidence_pack(task, agent, execution, events, results_dir)
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_bytes(pack)
    print(f"Wrote {TARGET} ({len(pack):,} bytes)")

    if results_dir is not None:
        for f in results_dir.iterdir():
            f.unlink()
        results_dir.rmdir()


if __name__ == "__main__":
    _build()
