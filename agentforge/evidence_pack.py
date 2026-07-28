"""Evidence Pack: downloadable bundle of per-task compliance artefacts.

Assembles a single ZIP containing everything an auditor needs to verify one
AI agent execution: the output, the immutable event log, the signed
capability card, the Art. 50 provenance record, and a README mapping each
file to the relevant EU AI Act article.
"""

from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentforge.models.agent import Agent
from agentforge.models.event_log import EventLog
from agentforge.models.execution import Execution
from agentforge.models.task import Task
from agentforge.provenance import build_provenance

_RESULT_FILENAMES = ("output.md", "stdout.log", "stderr.log", "usage.json")


def _serialize_event(event: EventLog) -> dict[str, Any]:
    return {
        "id": str(event.id),
        "timestamp": event.created_at.isoformat() if event.created_at else None,
        "event_type": event.event_type,
        "actor_id": event.actor_id,
        "actor_role": event.actor_role,
        "resource_type": event.resource_type,
        "resource_id": event.resource_id,
        "payload": event.payload,
    }


def _build_readme(task: Task, agent: Agent, provenance: dict[str, Any]) -> str:
    generated_at = datetime.now(timezone.utc).isoformat()
    return f"""# Evidence Pack

Task: `{task.id}`
Agent: `{agent.id}` (version {agent.version}, risk class `{agent.risk_class}`)
Generated at: {generated_at}

This bundle contains the per-execution compliance artefacts required by the
EU AI Act (Regulation 2024/1689). It is intended for handover to auditors,
market surveillance authorities, or internal compliance reviews.

## Contents

| File | Purpose | Article |
|---|---|---|
| `manifest.json` | Machine-readable index of the pack | - |
| `README.md` | This document | - |
| `output/` | Raw agent outputs, including Art. 50 disclosure block | Art. 13 |
| `event_log.json` | Immutable event log for this task | Art. 12 / 19 |
| `capability_card.json` | Agent capability card with Ed25519 signature | Art. 13 |
| `provenance.json` | Machine-readable AI-generated content marker | Art. 50 |
| `execution.json` | Execution lifecycle (start, end, server, metrics) | Art. 12 |
| `task.json` | Task contract (inputs, constraints, status) | Art. 12 |

## Verification

1. Check the capability card signature against the provider's public key.
2. Cross-reference `provenance.json` with the `X-AI-Provenance` header
   returned by the `/v1/tasks/{task.id}/result` endpoint.
3. Confirm the event log covers the full lifecycle from creation to completion.

This pack is one of several compliance artefacts. Technical documentation
(Annex IV), the Quality Management System (Art. 17), and the risk management
system (Art. 9) are maintained separately and retained for 10 years under
Art. 18.
"""


def _manifest(
    task: Task,
    agent: Agent,
    execution: Execution | None,
    provenance: dict[str, Any],
    files: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "regulation": "EU 2024/1689",
        "task_id": task.id,
        "agent_id": agent.id,
        "agent_version": agent.version,
        "risk_class": agent.risk_class,
        "execution_id": execution.id if execution else None,
        "provenance": provenance,
        "files": files,
    }


def _serialize_task(task: Task) -> dict[str, Any]:
    return {
        "id": task.id,
        "agent_id": task.agent_id,
        "status": task.status,
        "inputs": task.inputs,
        "constraints": task.constraints,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }


def _serialize_execution(execution: Execution) -> dict[str, Any]:
    return {
        "id": execution.id,
        "task_id": execution.task_id,
        "server_id": execution.server_id,
        "status": execution.status,
        "started_at": execution.started_at.isoformat() if execution.started_at else None,
        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
        "elapsed_seconds": execution.elapsed_seconds,
        "exit_code": execution.exit_code,
        "metrics": execution.metrics,
    }


def _serialize_agent_card(agent: Agent) -> dict[str, Any]:
    return {
        "id": agent.id,
        "name": agent.name,
        "version": agent.version,
        "risk_class": agent.risk_class,
        "card": agent.card,
        "signature": agent.signature,
    }


def build_evidence_pack(
    task: Task,
    agent: Agent,
    execution: Execution | None,
    events: list[EventLog],
    results_dir: Path | None,
) -> bytes:
    """Assemble the evidence pack ZIP and return its bytes."""
    provenance = build_provenance(task, agent, execution)
    included_files: list[str] = [
        "README.md",
        "manifest.json",
        "task.json",
        "capability_card.json",
        "provenance.json",
        "event_log.json",
    ]

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("task.json", json.dumps(_serialize_task(task), indent=2, sort_keys=True))
        zf.writestr(
            "capability_card.json",
            json.dumps(_serialize_agent_card(agent), indent=2, sort_keys=True),
        )
        zf.writestr("provenance.json", json.dumps(provenance, indent=2, sort_keys=True))
        zf.writestr(
            "event_log.json",
            json.dumps(
                [_serialize_event(e) for e in events],
                indent=2,
                sort_keys=True,
            ),
        )

        if execution is not None:
            zf.writestr(
                "execution.json",
                json.dumps(_serialize_execution(execution), indent=2, sort_keys=True),
            )
            included_files.append("execution.json")

        if results_dir is not None and results_dir.is_dir():
            for name in _RESULT_FILENAMES:
                path = results_dir / name
                if path.is_file():
                    zf.writestr(f"output/{name}", path.read_bytes())
                    included_files.append(f"output/{name}")

        zf.writestr(
            "manifest.json",
            json.dumps(
                _manifest(task, agent, execution, provenance, included_files),
                indent=2,
                sort_keys=True,
            ),
        )
        zf.writestr("README.md", _build_readme(task, agent, provenance))

    return buf.getvalue()
