"""EU AI Act Art. 17 — Quality Management System manual.

Art. 17 requires providers of high-risk AI systems to document a QMS that
covers the thirteen elements listed in Art. 17(1)(a)-(m). ISO/IEC 42001
(AI Management System) is the practical baseline; ISO 9001 is acceptable
where it already anchors the provider's engineering practices.

Art. 63 allows microenterprises (under 10 employees, under €2M turnover)
to satisfy Art. 17 in simplified form. The simplified variant in this
module groups related elements and omits board-level artefacts that only
make sense at larger scale.

Scope of the generated document is the provider organisation. An optional
agent reference produces a small system-specific addendum.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agentforge.models.agent import Agent

SCHEMA_VERSION = "1"
REGULATION_REF = "EU 2024/1689 Art. 17"
VARIANTS = ("full", "simplified")

# Baseline standards the platform already aligns with.
DEFAULT_STANDARDS = [
    "ISO/IEC 42001 (AI management system) — 2023",
    "ISO/IEC 23894 (AI risk management) — 2023",
    "ISO/IEC 5259 (Data quality for analytics and ML)",
    "ISO/IEC 24029 (Robustness of neural networks)",
    "EN ISO 9001 (Quality management) — where applicable",
]


def _platform_provided_controls() -> dict[str, list[str]]:
    """Controls the platform enforces on behalf of every provider."""
    return {
        "data_governance": [
            "Per-execution event log with input/output capture (Art. 12)",
            "Three-path secret isolation (consumer / provider / platform)",
            "Ephemeral compute: no persistent tenant state between tasks",
        ],
        "risk_management": [
            "Risk-class tagging (minimal / limited / high) on every agent",
            "Approval gate for high-risk tasks (Art. 14)",
            "Trust score monitoring with quarterly review",
        ],
        "post_market_monitoring": [
            "PMM plan template per agent (Art. 72)",
            "Serious incident pipeline with deadline tracking (Art. 73)",
            "Stale-detection on compliance documents at agent-version bumps",
        ],
        "record_keeping": [
            "Event log retention: minimum 180 days, enforced in code",
            "Evidence pack ZIP per task, retained 10 years (Art. 18)",
            "Technical documentation, DoC, QMS records retained 10 years",
        ],
        "communication": [
            "Webhook delivery for task lifecycle, incidents, approvals",
            "Compliance export (CSV/JSON) for authority requests",
            "Ed25519-signed capability cards for downstream verification",
        ],
    }


def _section_a_regulatory_strategy(inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "policy": inputs.get("regulatory_policy")
        or (
            "Each AI system is classified per the Act. High-risk systems undergo "
            "conformity assessment before placing on the market. Substantial "
            "modifications trigger a fresh assessment per Art. 43."
        ),
        "conformity_assessment_route": inputs.get("conformity_assessment_route")
        or "Annex VI internal control (self-assessment), moving to Annex VII when a notified body is required.",
        "substantial_modification_definition": inputs.get("substantial_modification_definition")
        or "[PROVIDER: define what constitutes a substantial modification per Art. 43]",
    }


def _section_b_design_control(inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "design_review_procedure": inputs.get("design_review_procedure")
        or "[PROVIDER: design review cadence, approvers, artefacts]",
        "change_control": inputs.get("change_control")
        or (
            "Agent card version increments on material change. Old versions retained "
            "for the Art. 19 retention window. Deployers are notified via webhook."
        ),
    }


def _section_c_development(inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "development_methodology": inputs.get("development_methodology")
        or "[PROVIDER: SDLC description, review gates, coverage goals]",
        "quality_control": inputs.get("quality_control")
        or "[PROVIDER: code review, automated tests, human evaluation cadence]",
    }


def _section_d_validation(inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "validation_approach": inputs.get("validation_approach")
        or "Per-agent acceptance criteria with pre-release smoke tests plus observed-runtime trust score.",
        "testing_environment": inputs.get("testing_environment")
        or "Ephemeral isolated compute provisioned per task, matching the production environment.",
    }


def _section_e_standards(inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "baseline_standards": inputs.get("baseline_standards") or DEFAULT_STANDARDS,
        "harmonised_standards_applied": inputs.get("harmonised_standards_applied")
        or [
            "[PROVIDER: list harmonised standards once CEN-CENELEC JTC 21 publishes]"
        ],
    }


def _section_f_data_management(platform_controls: dict[str, list[str]], inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "platform_controls": platform_controls["data_governance"],
        "deployer_data_policy": inputs.get("deployer_data_policy")
        or "[PROVIDER: data classification, minimisation, retention across the lifecycle]",
        "gdpr_bridge": inputs.get("gdpr_bridge")
        or "Art. 10 records complement the GDPR processing register; DPIA references listed in the technical documentation.",
    }


def _section_g_risk_management(platform_controls: dict[str, list[str]], inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "framework_reference": inputs.get("risk_framework") or "ISO/IEC 23894",
        "platform_controls": platform_controls["risk_management"],
        "review_cadence": inputs.get("risk_review_cadence") or "quarterly",
        "owner": inputs.get("risk_owner")
        or "[PROVIDER: role accountable for the Art. 9 risk management system]",
    }


def _section_h_pmm(platform_controls: dict[str, list[str]]) -> dict[str, Any]:
    return {
        "plan_reference": "See the PMM plan template generated at /pmm (Art. 72).",
        "platform_controls": platform_controls["post_market_monitoring"],
    }


def _section_i_incidents(inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "classification_procedure": (
            "Incidents classified against Art. 3(49) categories with deadlines 2/10/15 days"
            " from provider awareness. Recorded at /incidents."
        ),
        "authority_routing": inputs.get("authority_routing")
        or "Primary MSA: BNetzA (Germany). Cross-border cases coordinated per Art. 77.",
    }


def _section_j_communication(platform_controls: dict[str, list[str]], inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "authority_contact": inputs.get("authority_contact")
        or "[PROVIDER: named liaison for MSA communication]",
        "customer_feedback": inputs.get("customer_feedback")
        or "Consumer portal for ratings and complaints; complaint volume tracked in PMM.",
        "platform_controls": platform_controls["communication"],
    }


def _section_k_records(platform_controls: dict[str, list[str]]) -> dict[str, Any]:
    return {
        "platform_controls": platform_controls["record_keeping"],
        "dms_integration": "[PROVIDER: document management system where finalised QMS records live]",
    }


def _section_l_resources(inputs: dict[str, Any], variant: str) -> dict[str, Any]:
    base = {
        "infrastructure_security_of_supply": inputs.get("infrastructure_security_of_supply")
        or "Hetzner Nuremberg primary; Falkenstein as failover compute region. Backup LLM providers configured.",
        "training_and_competence": inputs.get("training_and_competence")
        or "Art. 4 AI literacy module completion tracked per employee. See /literacy.",
    }
    if variant == "simplified":
        return base
    return {
        **base,
        "budget_and_staffing": inputs.get("budget_and_staffing")
        or "[PROVIDER: annual budget line for AI governance and compliance]",
    }


def _section_m_accountability(inputs: dict[str, Any], variant: str) -> dict[str, Any]:
    base = {
        "accountability_owner": inputs.get("accountability_owner")
        or "[PROVIDER: named person or role accountable for the QMS]",
        "management_review": inputs.get("management_review")
        or ("Annual management review for simplified QMS." if variant == "simplified"
            else "Quarterly management review by named accountable officer."),
    }
    if variant == "simplified":
        return base
    return {
        **base,
        "internal_audit_schedule": inputs.get("internal_audit_schedule")
        or "Annual internal audit against ISO/IEC 42001 control set.",
        "board_reporting": inputs.get("board_reporting")
        or "[PROVIDER: cadence of board-level AI governance reporting]",
    }


def build_qms_template(
    provider_inputs: dict[str, Any] | None = None,
    variant: str = "full",
    agent: Agent | None = None,
) -> dict[str, Any]:
    """Compose the QMS manual skeleton for a provider organisation."""
    if variant not in VARIANTS:
        raise ValueError(f"variant must be one of {VARIANTS}, got {variant!r}")
    inputs = provider_inputs or {}
    platform_controls = _platform_provided_controls()

    doc: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "regulation": REGULATION_REF,
        "variant": variant,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "organisation": {
            "name": inputs.get("organisation_name")
            or "[PROVIDER: legal name of the provider organisation]",
            "contact": inputs.get("organisation_contact")
            or "[PROVIDER: accountable contact]",
            "sme_category": inputs.get("sme_category") or "[PROVIDER: microenterprise / SME / large]",
        },
        "section_a_regulatory_strategy": _section_a_regulatory_strategy(inputs),
        "section_b_design_control": _section_b_design_control(inputs),
        "section_c_development": _section_c_development(inputs),
        "section_d_validation": _section_d_validation(inputs),
        "section_e_standards": _section_e_standards(inputs),
        "section_f_data_management": _section_f_data_management(platform_controls, inputs),
        "section_g_risk_management": _section_g_risk_management(platform_controls, inputs),
        "section_h_post_market_monitoring": _section_h_pmm(platform_controls),
        "section_i_incident_reporting": _section_i_incidents(inputs),
        "section_j_authority_communication": _section_j_communication(platform_controls, inputs),
        "section_k_record_keeping": _section_k_records(platform_controls),
        "section_l_resources": _section_l_resources(inputs, variant),
        "section_m_accountability": _section_m_accountability(inputs, variant),
        "status": "draft",
    }

    if agent is not None:
        doc["system_specific_addendum"] = {
            "agent_id": agent.id,
            "agent_name": agent.name,
            "agent_version": agent.version,
            "risk_class": agent.risk_class,
            "applicable_scope": (
                "This QMS manual applies to the named agent. The same QMS covers all"
                " other agents under the same provider unless noted."
            ),
        }

    return doc


def qms_to_markdown(doc: dict[str, Any]) -> str:
    """Render a QMS draft as a printable Markdown document."""
    org = doc["organisation"]
    simplified_note = ""
    if doc["variant"] == "simplified":
        simplified_note = (
            "\n> **Art. 63 simplified form.** Microenterprises may satisfy Art. 17 in this"
            " condensed format. Section L omits budget allocation; Section M omits"
            " internal-audit schedule and board reporting.\n"
        )

    def _bullets(items: Any) -> str:
        if isinstance(items, list):
            return "\n".join(f"- {item}" for item in items)
        return f"- {items}"

    def _kv(obj: Any) -> str:
        if not isinstance(obj, dict):
            return str(obj)
        lines = []
        for k, v in obj.items():
            if isinstance(v, list):
                lines.append(f"**{k}:**\n{_bullets(v)}")
            elif isinstance(v, dict):
                inner = "\n".join(f"  - {kk}: {vv}" for kk, vv in v.items())
                lines.append(f"**{k}:**\n{inner}")
            else:
                lines.append(f"- **{k}:** {v}")
        return "\n".join(lines)

    addendum_block = ""
    if "system_specific_addendum" in doc:
        add = doc["system_specific_addendum"]
        addendum_block = f"""

## System-specific addendum

- **Agent:** `{add["agent_id"]}` · {add["agent_name"]} · v{add["agent_version"]}
- **Risk class:** {add["risk_class"]}
- **Applicable scope:** {add["applicable_scope"]}
"""

    return f"""# Quality Management System Manual

**Regulation:** {doc["regulation"]}
**Variant:** {doc["variant"]}
**Generated:** {doc["generated_at"]}
**Status:** {doc["status"]}

**Provider:** {org["name"]}
**Contact:** {org["contact"]}
**Size category:** {org["sme_category"]}
{simplified_note}
---

## A. Regulatory compliance strategy (Art. 17(1)(a))

{_kv(doc["section_a_regulatory_strategy"])}

## B. Design and design-control (Art. 17(1)(b))

{_kv(doc["section_b_design_control"])}

## C. Development and quality control (Art. 17(1)(c))

{_kv(doc["section_c_development"])}

## D. Examination, testing, validation (Art. 17(1)(d))

{_kv(doc["section_d_validation"])}

## E. Technical specifications and standards (Art. 17(1)(e))

{_kv(doc["section_e_standards"])}

## F. Data management (Art. 17(1)(f))

{_kv(doc["section_f_data_management"])}

## G. Risk management system (Art. 17(1)(g))

{_kv(doc["section_g_risk_management"])}

## H. Post-market monitoring (Art. 17(1)(h))

{_kv(doc["section_h_post_market_monitoring"])}

## I. Serious incident reporting (Art. 17(1)(i))

{_kv(doc["section_i_incident_reporting"])}

## J. Communication with authorities and customers (Art. 17(1)(j))

{_kv(doc["section_j_authority_communication"])}

## K. Record-keeping (Art. 17(1)(k))

{_kv(doc["section_k_record_keeping"])}

## L. Resource management (Art. 17(1)(l))

{_kv(doc["section_l_resources"])}

## M. Accountability framework (Art. 17(1)(m))

{_kv(doc["section_m_accountability"])}
{addendum_block}
---

*Generated by the agents.renemurrell.de QMS scaffolding engine. Sections marked
`[PROVIDER: …]` require completion by the placing-on-market organisation.
Retain for 10 years per Art. 18.*
"""
