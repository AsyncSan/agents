"""EU AI Act Art. 14 + 26(2) — human oversight role registry.

Produces per-agent and per-organisation rollups of who has been assigned
which oversight role, with what authority, and what training backs their
competence. Feeds the Annex IV technical documentation (Section 5:
Human oversight measures) and the deployer-side FRIA (Section 5).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agentforge.models.oversight import (
    AUTHORITY_LEVELS,
    OVERSIGHT_ROLES,
)

REGULATION_REF = "EU 2024/1689 Art. 14, 26(2), 4"


def validate_role(role: str) -> None:
    if role not in OVERSIGHT_ROLES:
        raise ValueError(
            f"oversight_role must be one of {list(OVERSIGHT_ROLES)}, got '{role}'"
        )


def validate_authority(level: str) -> None:
    if level not in AUTHORITY_LEVELS:
        raise ValueError(
            f"authority_level must be one of {list(AUTHORITY_LEVELS)}, got '{level}'"
        )


def coverage_gap(
    assignments: list[dict[str, Any]],
    agent_id: str,
    high_risk: bool = False,
) -> list[str]:
    """Return missing roles for the given agent.

    For any agent, ``approver`` is a minimum. High-risk agents additionally
    require ``overseer`` (formal Art. 14) and ``incident_owner`` (Art. 73).
    Assignments with empty ``assigned_agent_ids`` count as org-wide and cover
    every agent.
    """
    covered = set()
    for a in assignments:
        if not a.get("active", True):
            continue
        scope = a.get("assigned_agent_ids")
        if not scope or agent_id in scope:
            covered.add(a.get("oversight_role"))

    required = {"approver"}
    if high_risk:
        required |= {"overseer", "incident_owner"}

    return sorted(required - covered)


def build_agent_oversight_roster(
    agent_id: str,
    agent_name: str,
    risk_class: str,
    assignments: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compose the per-agent roster document."""
    high_risk = risk_class == "high"
    applicable = [
        a
        for a in assignments
        if a.get("active", True)
        and (
            not a.get("assigned_agent_ids")
            or agent_id in (a.get("assigned_agent_ids") or [])
        )
    ]
    gaps = coverage_gap(assignments, agent_id, high_risk=high_risk)

    by_role: dict[str, list[dict[str, Any]]] = {r: [] for r in OVERSIGHT_ROLES}
    for a in applicable:
        by_role.setdefault(a["oversight_role"], []).append(a)

    return {
        "regulation": REGULATION_REF,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agent": {"id": agent_id, "name": agent_name, "risk_class": risk_class},
        "total_assigned_persons": len({a["staff_email"] for a in applicable}),
        "required_roles": ["approver"]
        + (["overseer", "incident_owner"] if high_risk else []),
        "coverage_gaps": gaps,
        "compliant": len(gaps) == 0,
        "roster": [
            {
                "role": role,
                "members": [
                    {
                        "name": a["staff_name"],
                        "email": a["staff_email"],
                        "role_title": a.get("staff_role_title"),
                        "authority_level": a["authority_level"],
                        "training_certificates": a.get("training_certificates") or [],
                        "competence_notes": a.get("competence_notes"),
                        "authority_source": a.get("authority_source"),
                        "assigned_by": a.get("assigned_by"),
                    }
                    for a in by_role.get(role, [])
                ],
            }
            for role in OVERSIGHT_ROLES
            if by_role.get(role)
        ],
    }


def roster_to_markdown(roster: dict[str, Any]) -> str:
    a = roster["agent"]
    gap_line = (
        "**Status:** Fully covered."
        if roster["compliant"]
        else f"**Status:** Missing roles: {', '.join(roster['coverage_gaps'])}."
    )
    blocks = []
    for role_block in roster["roster"]:
        members = "\n".join(
            [
                (
                    f"- **{m['name']}** <{m['email']}>"
                    + (f" ({m['role_title']})" if m.get("role_title") else "")
                    + f"\n  - Authority: `{m['authority_level']}`"
                    + (
                        f"\n  - Training: {len(m['training_certificates'])}"
                        f" certificate(s): "
                        + ", ".join(
                            [
                                (
                                    c.get("module_title")
                                    or c.get("certificate_id")
                                    or "unspecified"
                                )
                                for c in m["training_certificates"]
                            ]
                        )
                        if m["training_certificates"]
                        else "\n  - Training: (no certificates recorded)"
                    )
                    + (
                        f"\n  - Competence: {m['competence_notes']}"
                        if m.get("competence_notes")
                        else ""
                    )
                    + (
                        f"\n  - Authority source: {m['authority_source']}"
                        if m.get("authority_source")
                        else ""
                    )
                )
                for m in role_block["members"]
            ]
        )
        blocks.append(f"### {role_block['role']}\n\n{members}\n")
    body = "\n".join(blocks) if blocks else "*No oversight assignments recorded.*"

    return f"""# Human oversight roster

**Regulation:** {roster["regulation"]}
**System:** `{a["id"]}` · {a["name"]} · risk class `{a["risk_class"]}`
**Generated:** {roster["generated_at"]}

{gap_line}

**Required roles:** {", ".join(roster["required_roles"])}
**Assigned persons (distinct):** {roster["total_assigned_persons"]}

---

{body}

---

*Generated by the agents.renemurrell.de oversight registry. Competence
evidence (training certificates) should be archived alongside this
roster under Art. 18 record-keeping.*
"""
