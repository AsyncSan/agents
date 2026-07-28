"""Agent-like object for compliance flows without a registered agent.

A substantial share of evaluators land on the platform with an AI system
that is *not* published here (internal tool, third-party product, a
pre-platform prototype). They still need FRIA, Annex IV, data sheets,
PMM plans, and EU-DB registration drafts.

``ManualAgentInput`` is a Pydantic schema that collects the fields the
compliance generators need. ``build_manual_agent`` returns an object that
quacks like ``agentforge.models.agent.Agent`` well enough for the
downstream template builders without touching the database.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from pydantic import BaseModel, Field

RISK_CLASSES = ("minimal", "limited", "high")


class ManualAgentInput(BaseModel):
    """User-supplied agent description for compliance flows.

    ``id`` is optional; when omitted we synthesise a slug from the name.
    """

    name: str = Field(..., min_length=1, max_length=255)
    version: int = Field(default=1, ge=1)
    risk_class: str = Field(default="minimal")
    description: str | None = None
    domain: str | None = None
    model: str | None = None
    tools: list[str] | None = None
    inputs: list[dict[str, Any]] | None = None
    outputs: list[dict[str, Any]] | None = None
    id: str | None = None


def _slugify(name: str) -> str:
    base = "".join(c.lower() if c.isalnum() else "-" for c in name.strip())
    return "-".join(filter(None, base.split("-"))) or "external-system"


def build_manual_agent(spec: ManualAgentInput) -> Any:
    """Return an Agent-like object suitable for the template generators."""
    if spec.risk_class not in RISK_CLASSES:
        raise ValueError(
            f"risk_class must be one of {list(RISK_CLASSES)}, got {spec.risk_class!r}"
        )

    agent_id = spec.id or f"external/{_slugify(spec.name)}"

    card = {
        "capabilities": {
            "domain": spec.domain,
            "description": spec.description,
            "inputs": spec.inputs or [],
            "outputs": spec.outputs or [],
            "tags": [],
            "constraints": {},
        },
        "runtime": {
            "model": spec.model,
            "tools": spec.tools or [],
        },
    }

    return SimpleNamespace(
        id=agent_id,
        name=spec.name,
        description=spec.description,
        version=spec.version,
        risk_class=spec.risk_class,
        card=card,
        # No runtime metrics for externally-described systems.
        total_executions=0,
        success_count=0,
        trust_score=None,
        avg_duration_seconds=None,
    )
