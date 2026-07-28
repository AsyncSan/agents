"""EU AI Act Annex IV technical documentation generator.

Annex IV lists the technical documentation a provider of a high-risk AI
system must maintain before placing the system on the market. This module
assembles a pre-filled draft from the agent capability card, runtime
metrics already tracked by the platform, and provider-supplied inputs.

The output covers all nine Annex IV sections. Sections derivable from the
card or runtime data are filled directly; the rest are emitted as scaffold
placeholders for the provider to complete.

Art. 11 allows SMEs to supply the documentation in a simplified form. The
template therefore ships two variants: ``full`` and ``simplified``. The
simplified variant collapses sections 2, 4, and 6 into shorter summaries
and omits sub-items that only apply to larger deployments.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agentforge.models.agent import Agent

SCHEMA_VERSION = "1"
REGULATION_REF = "EU 2024/1689 Annex IV (Art. 11)"
VARIANTS = ("full", "simplified")


def _runtime_from_card(card: dict[str, Any]) -> dict[str, Any]:
    runtime = card.get("runtime", {}) if isinstance(card, dict) else {}
    return {
        "model": runtime.get("model"),
        "server_type": runtime.get("server_type"),
        "snapshot_profile": runtime.get("snapshot_profile"),
        "compute_tier": runtime.get("compute_tier", "vm"),
        "tools": runtime.get("tools", []),
        "estimated_duration_seconds": runtime.get("estimated_duration_seconds"),
        "estimated_cost_usd": runtime.get("estimated_cost_usd"),
    }


def _capabilities_from_card(card: dict[str, Any]) -> dict[str, Any]:
    caps = card.get("capabilities", {}) if isinstance(card, dict) else {}
    return {
        "domain": caps.get("domain"),
        "tags": caps.get("tags", []),
        "description": caps.get("description"),
        "inputs": caps.get("inputs", []),
        "outputs": caps.get("outputs", []),
        "constraints": caps.get("constraints", {}),
    }


def _observed_metrics(agent: Agent) -> dict[str, Any]:
    total = agent.total_executions or 0
    success = agent.success_count or 0
    success_rate = (success / total) if total > 0 else None
    return {
        "total_executions": total,
        "success_count": success,
        "observed_success_rate": round(success_rate, 4) if success_rate is not None else None,
        "trust_score": float(agent.trust_score) if agent.trust_score is not None else None,
        "avg_duration_seconds": (
            float(agent.avg_duration_seconds)
            if agent.avg_duration_seconds is not None
            else None
        ),
    }


def _section_1_general(agent: Agent, inputs: dict[str, Any]) -> dict[str, Any]:
    caps = _capabilities_from_card(agent.card or {})
    runtime = _runtime_from_card(agent.card or {})
    return {
        "intended_purpose": caps.get("description") or agent.description
        or "[PROVIDER: describe the intended purpose]",
        "provider_name": inputs.get("provider_name")
        or "[PROVIDER: legal name and address]",
        "provider_contact": inputs.get("provider_contact")
        or "[PROVIDER: accountable contact, email, phone]",
        "system_identifier": agent.id,
        "system_name": agent.name,
        "system_version": f"v{agent.version}",
        "form": "Managed runtime (API). Executed as an ephemeral server task on agents.renemurrell.de.",
        "underlying_model": runtime.get("model"),
        "required_tools": runtime.get("tools"),
        "compute_profile": {
            "server_type": runtime.get("server_type"),
            "snapshot_profile": runtime.get("snapshot_profile"),
            "compute_tier": runtime.get("compute_tier"),
        },
        "user_interface_summary": (
            "Operated via REST API (POST /v1/tasks) or CLI (agents-cli run). "
            "A browser dashboard surfaces status, results, and evidence packs."
        ),
        "instructions_for_use_reference": f"capability-card@v{agent.version}",
        "third_country_variants": inputs.get("third_country_variants")
        or "[PROVIDER: list Member-State-specific variants, if any; otherwise 'none']",
    }


def _section_2_detailed(agent: Agent, inputs: dict[str, Any], variant: str) -> dict[str, Any]:
    caps = _capabilities_from_card(agent.card or {})
    runtime = _runtime_from_card(agent.card or {})
    base = {
        "development_methodology": inputs.get("development_methodology")
        or "[PROVIDER: development process, design decisions, validation method]",
        "third_party_components": inputs.get("third_party_components")
        or [f"Foundation model: {runtime.get('model')}"]
        + [f"Tool: {t}" for t in runtime.get("tools", [])]
        + ["Runtime: agents.renemurrell.de managed runtime"],
        "system_architecture": (
            "Each task runs on an isolated ephemeral server provisioned from a "
            "pre-baked snapshot, executed by the agent runtime, then destroyed. "
            "State is persisted to the platform event log, not to the compute node."
        ),
        "data_requirements": {
            "input_schema": caps.get("inputs"),
            "output_schema": caps.get("outputs"),
            "constraints": caps.get("constraints"),
            "training_data_summary": inputs.get("training_data_summary")
            or "[PROVIDER: source, licensing, curation, bias analysis; 'not applicable' if the agent does not fine-tune]",
        },
        "validation_and_testing": inputs.get("validation_and_testing")
        or "[PROVIDER: test corpora, acceptance criteria, drift monitoring]",
        "pre_determined_changes": inputs.get("pre_determined_changes")
        or "[PROVIDER: changes that do not trigger re-assessment, per Art. 43]",
        "continuous_learning_behaviour": inputs.get("continuous_learning_behaviour")
        or "No online learning. The agent is stateless between executions; "
        "model weights are fixed per capability-card version.",
    }
    if variant == "simplified":
        return {
            "development_methodology": base["development_methodology"],
            "third_party_components": base["third_party_components"],
            "system_architecture": base["system_architecture"],
            "data_requirements": {
                "input_schema": base["data_requirements"]["input_schema"],
                "output_schema": base["data_requirements"]["output_schema"],
            },
            "validation_and_testing_summary": base["validation_and_testing"],
        }
    return base


def _section_3_monitoring(agent: Agent, inputs: dict[str, Any]) -> dict[str, Any]:
    metrics = _observed_metrics(agent)
    caps = _capabilities_from_card(agent.card or {})
    return {
        "capabilities": caps.get("description"),
        "known_limitations": inputs.get("known_limitations")
        or [
            "Outputs depend on the underlying LLM; factual claims require verification.",
            "Performance degrades on inputs outside the documented schema or constraints.",
        ],
        "accuracy_metrics_observed": metrics,
        "foreseeable_unintended_outcomes": inputs.get("foreseeable_unintended_outcomes")
        or [
            "[PROVIDER: incorrect outputs due to ambiguous inputs]",
            "[PROVIDER: privacy leakage if sensitive data is included in the prompt]",
            "[PROVIDER: bias reinforcement if the underlying model is biased]",
        ],
        "human_oversight_measures": [
            "Approval gates for high-risk agents (Art. 14)",
            "Immutable event log per execution (Art. 12)",
            "Signed capability cards with declared capabilities (Art. 13)",
            "Art. 50 provenance header on every output",
        ],
        "input_data_specifications": caps.get("inputs"),
    }


def _section_4_performance_metrics(agent: Agent, inputs: dict[str, Any], variant: str) -> dict[str, Any]:
    common = {
        "platform_provided_metrics": [
            "5-factor trust score (success rate, duration accuracy, volume, recency, ratings)",
            "Observed success rate and failure-class breakdown from the event log",
            "Execution latency (avg and p95) per agent version",
        ],
        "metric_rationale": inputs.get("metric_rationale")
        or "[PROVIDER: why the chosen metrics are appropriate for the intended purpose]",
    }
    if variant == "simplified":
        return common
    return {
        **common,
        "robustness_testing": inputs.get("robustness_testing")
        or "[PROVIDER: adversarial inputs, edge cases, redundancy behaviour]",
        "cybersecurity_testing": inputs.get("cybersecurity_testing")
        or [
            "3-path secret isolation (consumer / provider / platform)",
            "Ephemeral compute: no persistent tenant state",
            "Firewalled VPC, no SMTP egress",
        ],
    }


def _section_5_risk_management(agent: Agent, inputs: dict[str, Any]) -> dict[str, Any]:
    risk_class = agent.risk_class or "minimal"
    return {
        "platform_risk_class": risk_class,
        "rms_owner": inputs.get("rms_owner")
        or "[PROVIDER: role accountable for the Art. 9 risk management system]",
        "identified_risks": inputs.get("identified_risks")
        or [
            "[PROVIDER: inaccurate outputs leading to harm]",
            "[PROVIDER: discriminatory outcomes]",
            "[PROVIDER: data leakage via output content]",
        ],
        "mitigation_measures": inputs.get("mitigation_measures")
        or [
            "[PROVIDER: mitigation measure with owner and review cadence]",
        ],
        "review_cadence": inputs.get("review_cadence") or "quarterly",
    }


def _section_6_changes(agent: Agent, inputs: dict[str, Any], variant: str) -> dict[str, Any]:
    full = {
        "version_history_policy": (
            "Each published change increments the agent capability card version. "
            "The platform stores prior versions and keeps their event logs for the "
            "Art. 19 retention window."
        ),
        "substantial_modification_definition": inputs.get("substantial_modification_definition")
        or "[PROVIDER: define what constitutes a substantial modification per Art. 43]",
        "current_version": f"v{agent.version}",
    }
    if variant == "simplified":
        return {
            "current_version": full["current_version"],
            "version_history_policy": full["version_history_policy"],
        }
    return full


def _section_7_standards(inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "harmonised_standards_applied": inputs.get("harmonised_standards_applied")
        or [
            "[PROVIDER: list applied harmonised standards once published; CEN-CENELEC JTC 21 target Q4 2026]",
        ],
        "common_specifications_applied": inputs.get("common_specifications_applied") or [],
        "other_adopted_solutions": inputs.get("other_adopted_solutions")
        or [
            "ISO/IEC 42001 (AI management system) as baseline reference where applicable",
        ],
    }


def _section_8_declaration(agent: Agent, inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "declaration_of_conformity_reference": inputs.get("declaration_of_conformity_reference")
        or f"[PROVIDER: attach EU Declaration of Conformity for {agent.id} v{agent.version} per Annex V]",
        "ce_marking_affixed": inputs.get("ce_marking_affixed", False),
        "eu_database_registration": inputs.get("eu_database_registration")
        or "[PROVIDER: EU database registration identifier, per Art. 49]",
    }


def _section_9_post_market(agent: Agent, inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "monitoring_plan_summary": inputs.get("monitoring_plan_summary")
        or "[PROVIDER: post-market monitoring plan per Art. 72: data collection, analysis, re-assessment triggers]",
        "incident_reporting_process": inputs.get("incident_reporting_process")
        or "Serious incidents reported to the MSA within Art. 73 deadlines "
        "(15 days standard, 10 days critical infrastructure, 2 days widespread).",
        "feedback_channels": inputs.get("feedback_channels")
        or [
            "Consumer ratings and complaint forms on the platform",
            "Trust-score drift monitoring",
            "[PROVIDER: additional channels: customer support, user surveys, etc.]",
        ],
    }


def build_annex_iv_template(
    agent: Agent,
    provider_inputs: dict[str, Any] | None = None,
    variant: str = "full",
) -> dict[str, Any]:
    """Compose the Annex IV technical documentation draft."""
    if variant not in VARIANTS:
        raise ValueError(f"variant must be one of {VARIANTS}, got {variant!r}")
    inputs = provider_inputs or {}

    return {
        "schema_version": SCHEMA_VERSION,
        "regulation": REGULATION_REF,
        "variant": variant,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agent": {
            "id": agent.id,
            "name": agent.name,
            "version": agent.version,
            "risk_class": agent.risk_class,
        },
        "section_1_general_description": _section_1_general(agent, inputs),
        "section_2_detailed_description": _section_2_detailed(agent, inputs, variant),
        "section_3_monitoring_information": _section_3_monitoring(agent, inputs),
        "section_4_performance_metrics": _section_4_performance_metrics(agent, inputs, variant),
        "section_5_risk_management_system": _section_5_risk_management(agent, inputs),
        "section_6_changes": _section_6_changes(agent, inputs, variant),
        "section_7_applied_standards": _section_7_standards(inputs),
        "section_8_declaration_of_conformity": _section_8_declaration(agent, inputs),
        "section_9_post_market_monitoring": _section_9_post_market(agent, inputs),
        "status": "draft",
    }


def annex_iv_to_markdown(doc: dict[str, Any]) -> str:
    """Render an Annex IV draft as a human-readable Markdown document."""

    def _bullets(items: Any) -> str:
        if items is None:
            return "- [PROVIDER: complete]"
        if isinstance(items, list):
            if not items:
                return "- (none)"
            return "\n".join(f"- {item}" for item in items)
        return f"- {items}"

    def _kv(obj: Any) -> str:
        if not isinstance(obj, dict):
            return str(obj)
        return "\n".join(f"- **{k}:** {v}" for k, v in obj.items())

    a = doc["agent"]
    s1 = doc["section_1_general_description"]
    s2 = doc["section_2_detailed_description"]
    s3 = doc["section_3_monitoring_information"]
    s4 = doc["section_4_performance_metrics"]
    s5 = doc["section_5_risk_management_system"]
    s6 = doc["section_6_changes"]
    s7 = doc["section_7_applied_standards"]
    s8 = doc["section_8_declaration_of_conformity"]
    s9 = doc["section_9_post_market_monitoring"]

    simplified_note = ""
    if doc["variant"] == "simplified":
        simplified_note = (
            "\n> **SME simplified form (Art. 11(1) subpara. 3).** Sections 2, 4, and 6 "
            "are condensed. Full-form sub-items remain available on request.\n"
        )

    return f"""# Annex IV Technical Documentation

**Regulation:** {doc["regulation"]}
**Variant:** {doc["variant"]}
**Generated:** {doc["generated_at"]}
**Status:** {doc["status"]}

**System:** `{a["id"]}` · {a["name"]} · v{a["version"]} · risk class `{a["risk_class"]}`
{simplified_note}
---

## 1. General description

- **Intended purpose:** {s1["intended_purpose"]}
- **Provider:** {s1["provider_name"]}
- **Contact:** {s1["provider_contact"]}
- **System identifier:** `{s1["system_identifier"]}`
- **Version:** {s1["system_version"]}
- **Form:** {s1["form"]}
- **Underlying model:** `{s1["underlying_model"]}`
- **Required tools:** {', '.join(s1["required_tools"] or []) or '-'}
- **User interface summary:** {s1["user_interface_summary"]}
- **IFU reference:** `{s1["instructions_for_use_reference"]}`
- **Third-country variants:** {s1["third_country_variants"]}

## 2. Detailed description

- **Development methodology:** {s2.get("development_methodology", "-")}

**Third-party components:**
{_bullets(s2.get("third_party_components"))}

- **System architecture:** {s2.get("system_architecture", "-")}

**Data requirements:**
{_kv(s2.get("data_requirements", {}))}

- **Validation and testing:** {s2.get("validation_and_testing") or s2.get("validation_and_testing_summary", "-")}
- **Pre-determined changes:** {s2.get("pre_determined_changes", "-")}
- **Continuous-learning behaviour:** {s2.get("continuous_learning_behaviour", "-")}

## 3. Monitoring information

- **Capabilities:** {s3["capabilities"]}

**Known limitations:**
{_bullets(s3["known_limitations"])}

**Observed accuracy metrics:**
{_kv(s3["accuracy_metrics_observed"])}

**Foreseeable unintended outcomes:**
{_bullets(s3["foreseeable_unintended_outcomes"])}

**Human oversight measures:**
{_bullets(s3["human_oversight_measures"])}

## 4. Appropriateness of performance metrics

**Platform-provided metrics:**
{_bullets(s4["platform_provided_metrics"])}

- **Metric rationale:** {s4["metric_rationale"]}
{('''

- **Robustness testing:** ''' + s4.get("robustness_testing", "-") + '''

**Cybersecurity testing:**
''' + _bullets(s4.get("cybersecurity_testing"))) if "robustness_testing" in s4 else ""}

## 5. Risk management system

- **Platform risk class:** `{s5["platform_risk_class"]}`
- **RMS owner:** {s5["rms_owner"]}

**Identified risks:**
{_bullets(s5["identified_risks"])}

**Mitigation measures:**
{_bullets(s5["mitigation_measures"])}

- **Review cadence:** {s5["review_cadence"]}

## 6. Changes

- **Current version:** {s6["current_version"]}
- **Version history policy:** {s6["version_history_policy"]}
{('- **Substantial modification definition:** ' + s6["substantial_modification_definition"]) if "substantial_modification_definition" in s6 else ""}

## 7. Applied standards

**Harmonised standards applied:**
{_bullets(s7["harmonised_standards_applied"])}

**Common specifications applied:**
{_bullets(s7["common_specifications_applied"])}

**Other adopted solutions:**
{_bullets(s7["other_adopted_solutions"])}

## 8. Declaration of conformity

- **DoC reference:** {s8["declaration_of_conformity_reference"]}
- **CE marking affixed:** {s8["ce_marking_affixed"]}
- **EU database registration (Art. 49):** {s8["eu_database_registration"]}

## 9. Post-market monitoring

- **Plan summary:** {s9["monitoring_plan_summary"]}
- **Incident reporting process (Art. 73):** {s9["incident_reporting_process"]}

**Feedback channels:**
{_bullets(s9["feedback_channels"])}

---

*Generated by the agents.renemurrell.de Annex IV scaffolding engine. Sections
marked `[PROVIDER: …]` require completion by the placing-on-market organisation.
Retain this document for 10 years per Art. 18.*
"""
