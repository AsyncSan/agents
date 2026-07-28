"""EU AI Act Art. 50 provenance / watermarking.

Marks every agent output as AI-generated in a machine-readable form so that
downstream systems, end users, and auditors can detect synthetic content
without out-of-band knowledge.

The provenance record is a JSON document built from the Task, Agent, and
Execution at response time. No schema change is required; it aggregates
fields the platform already persists.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from agentforge.models.agent import Agent
from agentforge.models.execution import Execution
from agentforge.models.task import Task

PLATFORM_ID = "agents.renemurrell.de"
REGULATION_REF = "EU 2024/1689 Art. 50"
PROVENANCE_VERSION = "1"

DISCLOSURE_TEXT = (
    "This content was produced by an AI system. Identifier, agent, and "
    "execution metadata are available via the platform provenance endpoint."
)


def build_provenance(
    task: Task,
    agent: Agent,
    execution: Execution | None,
) -> dict[str, Any]:
    """Compose the machine-readable provenance record for a task result."""
    completed_at = execution.completed_at if execution else None
    return {
        "ai_generated": True,
        "schema_version": PROVENANCE_VERSION,
        "platform": PLATFORM_ID,
        "regulation": REGULATION_REF,
        "agent": {
            "id": agent.id,
            "name": agent.name,
            "version": agent.version,
            "risk_class": agent.risk_class,
        },
        "task_id": task.id,
        "execution_id": execution.id if execution else None,
        "generated_at": (completed_at or datetime.now(timezone.utc)).isoformat(),
        "disclosure": DISCLOSURE_TEXT,
    }


def provenance_headers(provenance: dict[str, Any]) -> dict[str, str]:
    """HTTP headers that surface the provenance record alongside any response."""
    compact = json.dumps(provenance, separators=(",", ":"), sort_keys=True)
    return {
        "X-AI-Generated": "true",
        "X-AI-Provenance-Version": PROVENANCE_VERSION,
        "X-AI-Provenance": compact,
    }


def wrap_markdown(content: str, provenance: dict[str, Any]) -> str:
    """Append a machine-readable provenance block to a Markdown output."""
    block = json.dumps(provenance, indent=2, sort_keys=True)
    footer = (
        "\n\n---\n\n"
        "## AI Content Disclosure (EU AI Act Art. 50)\n\n"
        f"{DISCLOSURE_TEXT}\n\n"
        "```json\n"
        f"{block}\n"
        "```\n"
    )
    return content + footer


def wrap_json(content: str, provenance: dict[str, Any]) -> str:
    """Embed provenance into a JSON payload without breaking its structure."""
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return content
    if isinstance(parsed, dict) and "_ai_provenance" not in parsed:
        parsed["_ai_provenance"] = provenance
        return json.dumps(parsed, indent=2, sort_keys=True)
    return content
