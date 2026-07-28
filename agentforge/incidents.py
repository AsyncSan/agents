"""EU AI Act Art. 73 — Serious Incident Reporting.

Art. 73 requires providers of high-risk AI systems to report serious
incidents to the national market surveillance authority (MSA). This
module classifies incidents by category, computes reporting deadlines
from the time the provider became aware, and generates the document the
deployer hands to the authority.

Deadlines per Art. 73(2):
  * Critical infrastructure disruption: 2 days
  * Widespread infringement: 2 days (Art. 73(3))
  * Fundamental rights or health/life incidents: 10 days
  * All other serious incidents: 15 days

The "shortest possible" rule (Art. 73(2) para 2) requires an initial
incomplete report within the deadline if a full assessment is not yet
available.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from agentforge.models.agent import Agent
from agentforge.models.incident import SEVERITIES, IncidentReport

SCHEMA_VERSION = "1"
REGULATION_REF = "EU 2024/1689 Art. 73"

# Deadline in days from awareness_at
SEVERITY_DEADLINE_DAYS: dict[str, int] = {
    "death_or_serious_health": 10,
    "critical_infrastructure": 2,
    "fundamental_rights": 10,
    "widespread_infringement": 2,
    "serious_property_harm": 15,
    "environmental_harm": 15,
}

SEVERITY_DESCRIPTION: dict[str, str] = {
    "death_or_serious_health": "Death of a person or serious harm to a person's health",
    "critical_infrastructure": "Serious and irreversible disruption of critical infrastructure",
    "fundamental_rights": "Infringement of fundamental rights protected by Union law",
    "widespread_infringement": "Widespread infringement affecting multiple persons across at least three Member States",
    "serious_property_harm": "Serious harm to property",
    "environmental_harm": "Serious harm to the environment",
}


def deadline_for(severity: str, awareness_at: datetime) -> datetime:
    """Compute the reporting deadline for a given severity and awareness timestamp."""
    days = SEVERITY_DEADLINE_DAYS.get(severity)
    if days is None:
        raise ValueError(f"Unknown severity: {severity!r}")
    return awareness_at + timedelta(days=days)


def time_remaining(severity: str, awareness_at: datetime, now: datetime | None = None) -> timedelta:
    """Signed time remaining to the reporting deadline. Negative when overdue."""
    current = now or datetime.now(timezone.utc)
    return deadline_for(severity, awareness_at) - current


def severity_catalog() -> list[dict[str, Any]]:
    """Public catalog of severities with deadlines and descriptions."""
    return [
        {
            "key": key,
            "deadline_days": SEVERITY_DEADLINE_DAYS[key],
            "description": SEVERITY_DESCRIPTION[key],
        }
        for key in SEVERITIES
    ]


def build_incident_report_template(
    incident: IncidentReport,
    agent: Agent | None,
    provider_contact: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Compose the machine-readable Art. 73 report for an incident.

    The deployer hands this (JSON, Markdown, or PDF) to the MSA within the
    deadline. Unknown fields are surfaced as ``[PROVIDER: ...]`` placeholders
    so the document stays valid even when the investigation is ongoing.
    """
    contact = provider_contact or {}
    awareness = incident.awareness_at
    deadline = deadline_for(incident.severity, awareness)
    remaining = time_remaining(incident.severity, awareness)

    agent_block: dict[str, Any] = {}
    if agent is not None:
        agent_block = {
            "id": agent.id,
            "name": agent.name,
            "version": incident.agent_version or agent.version,
            "risk_class": agent.risk_class,
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "regulation": REGULATION_REF,
        "incident_id": str(incident.id),
        "status": incident.status,
        "provider": {
            "organisation": contact.get("organisation")
            or "[PROVIDER: legal name and address]",
            "contact": contact.get("contact") or "[PROVIDER: accountable contact]",
        },
        "system": agent_block
        or {
            "id": "[PROVIDER: system identifier]",
            "name": "[PROVIDER: system name]",
        },
        "incident": {
            "title": incident.title,
            "summary": incident.summary,
            "severity_category": incident.severity,
            "severity_description": SEVERITY_DESCRIPTION.get(incident.severity),
            "detected_at": incident.detected_at.isoformat() if incident.detected_at else None,
            "awareness_at": awareness.isoformat() if awareness else None,
            "affected_persons_estimate": incident.affected_persons_estimate,
        },
        "analysis": {
            "root_cause": incident.root_cause
            or "[PROVIDER: root cause analysis, if known at reporting time]",
            "mitigation_taken": incident.mitigation_taken
            or "[PROVIDER: immediate actions already executed]",
            "mitigation_planned": incident.mitigation_planned
            or "[PROVIDER: planned follow-up actions and timeline]",
        },
        "reporting": {
            "deadline_at": deadline.isoformat(),
            "deadline_days": SEVERITY_DEADLINE_DAYS[incident.severity],
            "time_remaining_seconds": int(remaining.total_seconds()),
            "overdue": remaining.total_seconds() < 0,
            "reported_at": incident.reported_to_authority_at.isoformat()
            if incident.reported_to_authority_at
            else None,
            "authority_name": incident.authority_name,
            "authority_reference": incident.authority_reference,
        },
        "notes": (
            "Initial filing may be incomplete under Art. 73(5); provide the "
            "information available at reporting time and supplement later. "
            "Retain this document for 10 years with the technical documentation."
        ),
    }


def incident_report_to_markdown(report: dict[str, Any]) -> str:
    """Render an Art. 73 report as a MSA-ready Markdown document."""
    inc = report["incident"]
    prov = report["provider"]
    sys = report["system"]
    ana = report["analysis"]
    rep = report["reporting"]

    overdue_line = ""
    if rep["overdue"]:
        overdue_line = "\n\n> **OVERDUE.** The reporting deadline has passed. File immediately.\n"

    return f"""# Serious Incident Report

**Regulation:** {report["regulation"]}
**Incident ID:** `{report["incident_id"]}`
**Status:** {report["status"]}
**Reporting deadline:** {rep["deadline_at"]} ({rep["deadline_days"]} days from awareness)
{overdue_line}
---

## Provider

- **Organisation:** {prov["organisation"]}
- **Contact:** {prov["contact"]}

## System

- **Identifier:** `{sys.get("id")}`
- **Name:** {sys.get("name")}
- **Version:** {sys.get("version", "-")}
- **Risk class:** {sys.get("risk_class", "-")}

## Incident

- **Title:** {inc["title"]}
- **Severity:** `{inc["severity_category"]}`
- **Category description:** {inc["severity_description"]}
- **Detected at:** {inc["detected_at"]}
- **Provider became aware at:** {inc["awareness_at"]}
- **Affected persons (estimate):** {inc.get("affected_persons_estimate") or "-"}

### Summary

{inc["summary"]}

## Analysis

- **Root cause:** {ana["root_cause"]}
- **Mitigation taken:** {ana["mitigation_taken"]}
- **Mitigation planned:** {ana["mitigation_planned"]}

## Authority filing

- **Reported at:** {rep["reported_at"] or "[not yet reported]"}
- **Authority:** {rep["authority_name"] or "[MSA name]"}
- **Authority reference:** {rep["authority_reference"] or "-"}

---

*{report["notes"]}*
"""
