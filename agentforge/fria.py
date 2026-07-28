"""EU AI Act Art. 27 — Fundamental Rights Impact Assessment (FRIA).

Art. 27 requires deployers of certain high-risk AI systems (public bodies,
private actors delivering public services, credit scoring, and life/health
insurance pricing) to perform a Fundamental Rights Impact Assessment before
first use. The assessment must describe the process, duration and frequency
of use, affected categories of people, specific risks of harm, human
oversight measures, and governance measures if a risk materialises.

This module builds a machine-readable FRIA template from an Agent and a
small set of deployer-provided inputs. The result pre-fills the sections
derived from the capability card; sections that require qualitative
judgement by the deployer are left as scaffold prompts.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agentforge.models.agent import Agent

SCHEMA_VERSION = "1"
REGULATION_REF = "EU 2024/1689 Art. 27"

TRIGGER_USE_CASES = {
    "credit_scoring": "Credit scoring of natural persons (Annex III §5(b))",
    "insurance_pricing": "Risk assessment and pricing for life or health insurance (Annex III §5(c))",
    "public_service": "Deployment by a public body or in the delivery of a public service",
    "other_high_risk": "Other Annex III high-risk deployment with deployer obligations",
}


def _process_description(agent: Agent, deployer_process: str) -> dict[str, Any]:
    card = agent.card or {}
    capabilities = card.get("capabilities", {}) if isinstance(card, dict) else {}
    return {
        "agent_id": agent.id,
        "agent_name": agent.name,
        "agent_version": agent.version,
        "agent_domain": capabilities.get("domain"),
        "agent_description": capabilities.get("description") or agent.description,
        "deployer_process_summary": deployer_process
        or "[DEPLOYER: describe the concrete business process where the agent is used, "
        "including which steps are automated and which remain human-driven.]",
    }


def _duration_and_frequency(deployer_inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "intended_duration": deployer_inputs.get("intended_duration")
        or "[DEPLOYER: calendar duration or 'ongoing']",
        "frequency": deployer_inputs.get("frequency")
        or "[DEPLOYER: e.g., 'every incoming credit application', 'daily batch', 'on request']",
        "estimated_volume_per_month": deployer_inputs.get("estimated_volume_per_month")
        or "[DEPLOYER: approximate number of affected persons per month]",
    }


def _affected_persons(deployer_inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "primary_categories": deployer_inputs.get("affected_categories")
        or [
            "[DEPLOYER: e.g., 'credit applicants', 'insurance policyholders', 'citizens applying for X']",
        ],
        "vulnerable_groups_considered": deployer_inputs.get("vulnerable_groups")
        or [
            "[DEPLOYER: minors, elderly, persons with disabilities, linguistic minorities, etc.]",
        ],
        "special_categories_of_data": deployer_inputs.get("special_categories_of_data")
        or "[DEPLOYER: GDPR Art. 9 data processed, if any]",
    }


def _harm_risks(agent: Agent, deployer_inputs: dict[str, Any]) -> dict[str, Any]:
    risk_class = agent.risk_class or "unspecified"
    return {
        "platform_risk_class": risk_class,
        "potential_harms": deployer_inputs.get("potential_harms")
        or [
            "[DEPLOYER: discriminatory outcomes on protected characteristics]",
            "[DEPLOYER: economic harm via erroneous decisions]",
            "[DEPLOYER: procedural unfairness if recourse is limited]",
            "[DEPLOYER: privacy impact beyond what the DPIA covers]",
        ],
        "severity_assessment": deployer_inputs.get("severity_assessment")
        or "[DEPLOYER: qualitative severity scoring per identified harm]",
        "likelihood_assessment": deployer_inputs.get("likelihood_assessment")
        or "[DEPLOYER: qualitative likelihood scoring per identified harm]",
    }


def _human_oversight(agent: Agent, deployer_inputs: dict[str, Any]) -> dict[str, Any]:
    risk_class = agent.risk_class or "minimal"
    platform_measures = [
        "Immutable event log per execution (Art. 12)",
        "Ephemeral compute: fresh VM per task, destroyed on completion (Art. 15)",
        "Signed capability card identifying model, data access, and side effects (Art. 13)",
        "Machine-readable Art. 50 provenance headers on every output",
    ]
    if risk_class == "high":
        platform_measures.insert(
            0,
            "Mandatory approval gate: tasks enter 'awaiting_approval' before execution (Art. 14)",
        )

    return {
        "platform_measures": platform_measures,
        "deployer_measures": deployer_inputs.get("deployer_oversight_measures")
        or [
            "[DEPLOYER: name and role of the natural person responsible for oversight]",
            "[DEPLOYER: training provided to oversight staff]",
            "[DEPLOYER: criteria and procedure for overriding or discarding agent output]",
        ],
        "instructions_for_use_version": deployer_inputs.get("ifu_version")
        or f"capability-card@v{agent.version}",
    }


def _mitigation_and_governance(deployer_inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "internal_governance": deployer_inputs.get("internal_governance")
        or [
            "[DEPLOYER: escalation path when oversight detects an issue]",
            "[DEPLOYER: cadence of post-deployment review]",
            "[DEPLOYER: named role responsible for stopping deployment]",
        ],
        "complaint_mechanism": deployer_inputs.get("complaint_mechanism")
        or "[DEPLOYER: how affected persons contest an outcome; response SLA]",
        "authority_reporting": deployer_inputs.get("authority_reporting")
        or "[DEPLOYER: process for reporting serious incidents to the national MSA (Art. 73)]",
        "dpia_reference": deployer_inputs.get("dpia_reference")
        or "[DEPLOYER: reference to the GDPR DPIA; Art. 27(4) allows DPIA content to cover parts of this FRIA]",
    }


def build_fria_template(
    agent: Agent,
    deployer_inputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compose a pre-filled FRIA document for one agent / use-case pairing."""
    inputs = deployer_inputs or {}

    use_case_key = inputs.get("use_case_key")
    use_case_description = TRIGGER_USE_CASES.get(use_case_key) if use_case_key else None

    return {
        "schema_version": SCHEMA_VERSION,
        "regulation": REGULATION_REF,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "deployer": {
            "organisation": inputs.get("deployer_organisation")
            or "[DEPLOYER: legal name of the deploying organisation]",
            "contact": inputs.get("deployer_contact")
            or "[DEPLOYER: accountable contact person and role]",
            "role": inputs.get("deployer_role") or "deployer",
        },
        "use_case": {
            "trigger_category": use_case_key or "[DEPLOYER: select trigger category]",
            "trigger_reference": use_case_description
            or "[DEPLOYER: explain why Art. 27 applies to this use-case]",
        },
        "section_1_process_description": _process_description(
            agent, inputs.get("deployer_process_summary", "")
        ),
        "section_2_duration_frequency": _duration_and_frequency(inputs),
        "section_3_affected_persons": _affected_persons(inputs),
        "section_4_harm_risks": _harm_risks(agent, inputs),
        "section_5_human_oversight": _human_oversight(agent, inputs),
        "section_6_mitigation_governance": _mitigation_and_governance(inputs),
        "status": "draft",
    }


def fria_to_markdown(fria: dict[str, Any]) -> str:
    """Render a FRIA dict as a human-readable Markdown document."""
    deployer = fria.get("deployer", {})
    use_case = fria.get("use_case", {})

    def _bullets(items: Any) -> str:
        if isinstance(items, list):
            return "\n".join(f"- {item}" for item in items)
        return f"- {items}"

    process = fria.get("section_1_process_description", {})
    duration = fria.get("section_2_duration_frequency", {})
    affected = fria.get("section_3_affected_persons", {})
    harm = fria.get("section_4_harm_risks", {})
    oversight = fria.get("section_5_human_oversight", {})
    mitigation = fria.get("section_6_mitigation_governance", {})

    return f"""# Fundamental Rights Impact Assessment

**Regulation:** {fria.get("regulation")}
**Generated:** {fria.get("generated_at")}
**Status:** {fria.get("status")}

## Deployer

- **Organisation:** {deployer.get("organisation")}
- **Contact:** {deployer.get("contact")}
- **Role:** {deployer.get("role")}

## Trigger

- **Category:** `{use_case.get("trigger_category")}`
- **Reference:** {use_case.get("trigger_reference")}

## 1. Process description (Art. 27(1)(a))

- **Agent:** {process.get("agent_name")} (`{process.get("agent_id")}` v{process.get("agent_version")}, {process.get("agent_domain")})
- **Agent description:** {process.get("agent_description")}
- **Deployer process summary:** {process.get("deployer_process_summary")}

## 2. Duration and frequency (Art. 27(1)(b))

- **Intended duration:** {duration.get("intended_duration")}
- **Frequency:** {duration.get("frequency")}
- **Estimated volume per month:** {duration.get("estimated_volume_per_month")}

## 3. Affected persons (Art. 27(1)(c))

**Primary categories:**
{_bullets(affected.get("primary_categories"))}

**Vulnerable groups considered:**
{_bullets(affected.get("vulnerable_groups_considered"))}

**Special categories of data (GDPR Art. 9):** {affected.get("special_categories_of_data")}

## 4. Specific risks of harm (Art. 27(1)(d))

- **Platform risk class:** `{harm.get("platform_risk_class")}`

**Identified potential harms:**
{_bullets(harm.get("potential_harms"))}

- **Severity assessment:** {harm.get("severity_assessment")}
- **Likelihood assessment:** {harm.get("likelihood_assessment")}

## 5. Human oversight (Art. 27(1)(e))

**Platform-provided measures:**
{_bullets(oversight.get("platform_measures"))}

**Deployer-provided measures:**
{_bullets(oversight.get("deployer_measures"))}

- **Instructions for Use (IFU) version:** `{oversight.get("instructions_for_use_version")}`

## 6. Governance and mitigation (Art. 27(1)(f))

**Internal governance:**
{_bullets(mitigation.get("internal_governance"))}

- **Complaint mechanism:** {mitigation.get("complaint_mechanism")}
- **Authority reporting (Art. 73):** {mitigation.get("authority_reporting")}
- **DPIA reference (Art. 27(4)):** {mitigation.get("dpia_reference")}

---

*Generated by the agents.renemurrell.de FRIA scaffolding engine. Sections marked
`[DEPLOYER: …]` require completion by the deploying organisation. This document
does not replace legal counsel.*
"""
