"""EU AI Act Art. 10 — Data governance artefacts.

Art. 10 requires that training, validation, and testing datasets for
high-risk systems meet quality criteria: relevance, representativeness,
freedom from errors, and documented statistical properties. It also
demands a documented examination for possible bias, data gaps, and
shortcomings. Deployers that supply inputs for use-case processing must
exercise reasonable control over the input data under Art. 26(4).

The platform does not train foundation models. Its Art. 10 surface is
therefore:
  * per-agent data sheet covering inputs, outputs, tool access, data
    sources, and fairness/bias considerations;
  * organisation-wide data inventory aggregated across all owned agents,
    supporting the deployer's Art. 26(4) obligation.

The generated documents pre-fill everything derivable from the capability
card and runtime telemetry. Fields that require the provider's judgement
(training-data lineage, curation, bias analysis) surface as
``[PROVIDER: …]`` placeholders.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agentforge.models.agent import Agent

SCHEMA_VERSION = "1"
REGULATION_REF = "EU 2024/1689 Art. 10"


def _platform_controls() -> list[str]:
    return [
        "3-path secret isolation: consumer, provider, and platform keys never mix",
        "Ephemeral per-task compute: no persistent tenant state between runs",
        "Input and output captured in the immutable event log (Art. 12)",
        "Egress firewall restricts outbound connections from execution VMs",
        "No SMTP egress, reducing accidental data exfiltration surfaces",
        "Agent cards signed with Ed25519, verifiable by downstream consumers",
    ]


def _agent_runtime_snapshot(agent: Agent) -> dict[str, Any]:
    card = agent.card or {}
    capabilities = card.get("capabilities", {}) if isinstance(card, dict) else {}
    runtime = card.get("runtime", {}) if isinstance(card, dict) else {}
    total = agent.total_executions or 0
    success = agent.success_count or 0
    return {
        "domain": capabilities.get("domain"),
        "tags": capabilities.get("tags", []),
        "description": capabilities.get("description") or agent.description,
        "inputs": capabilities.get("inputs", []),
        "outputs": capabilities.get("outputs", []),
        "constraints": capabilities.get("constraints", {}),
        "underlying_model": runtime.get("model"),
        "tools": runtime.get("tools", []),
        "total_executions_observed": total,
        "success_count_observed": success,
        "observed_success_rate": (
            round(success / total, 4) if total > 0 else None
        ),
    }


def build_agent_data_sheet(
    agent: Agent,
    provider_inputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compose an Art. 10 data sheet for a single agent."""
    inputs = provider_inputs or {}
    snapshot = _agent_runtime_snapshot(agent)

    return {
        "schema_version": SCHEMA_VERSION,
        "regulation": REGULATION_REF,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agent": {
            "id": agent.id,
            "name": agent.name,
            "version": agent.version,
            "risk_class": agent.risk_class,
        },
        "purpose_and_scope": {
            "domain": snapshot["domain"],
            "intended_purpose": snapshot["description"],
            "tags": snapshot["tags"],
        },
        "input_data": {
            "schema": snapshot["inputs"],
            "constraints": snapshot["constraints"],
            "deployer_source_description": inputs.get("deployer_source_description")
            or "[PROVIDER: describe who supplies inputs and how they are collected]",
            "special_categories_flag": inputs.get("special_categories_flag")
            or "[PROVIDER: GDPR Art. 9 special categories, if any]",
        },
        "output_data": {
            "schema": snapshot["outputs"],
            "retention": "Results retained 180 days under Art. 19 default; 10 years in evidence packs under Art. 18.",
        },
        "tool_access": {
            "tools": snapshot["tools"],
            "notes": (
                "Tools execute on the ephemeral VM. Outbound connections gated by the"
                " egress firewall. Each invocation is recorded in the event log."
            ),
        },
        "model_and_training_data": {
            "underlying_model": snapshot["underlying_model"],
            "training_data_statement": inputs.get("training_data_statement")
            or (
                "[PROVIDER: statement covering training data provenance. If the agent"
                " uses a foundation model without fine-tuning, say so and reference"
                " the model provider's Annex XI / XII documentation.]"
            ),
            "fine_tuning_datasets": inputs.get("fine_tuning_datasets")
            or "[PROVIDER: list fine-tuning corpora with licensing and curation notes, or 'not applicable']",
        },
        "quality_and_bias": {
            "relevance_and_representativeness": inputs.get("representativeness")
            or "[PROVIDER: statement on dataset relevance to the intended purpose]",
            "known_gaps": inputs.get("known_gaps")
            or [
                "[PROVIDER: under-represented groups, geographies, languages]",
            ],
            "bias_assessment_method": inputs.get("bias_assessment_method")
            or "[PROVIDER: how bias is measured and monitored; link to Art. 15 accuracy metrics]",
            "mitigation_measures": inputs.get("mitigation_measures")
            or [
                "[PROVIDER: mitigations in place for identified bias]",
            ],
        },
        "platform_controls": _platform_controls(),
        "observed_runtime_metrics": {
            "total_executions": snapshot["total_executions_observed"],
            "success_count": snapshot["success_count_observed"],
            "observed_success_rate": snapshot["observed_success_rate"],
        },
        "status": "draft",
    }


def build_org_data_inventory(agents: list[Agent]) -> dict[str, Any]:
    """Aggregate Art. 10 data surface across the organisation's owned agents."""
    domains: dict[str, int] = {}
    risk_classes: dict[str, int] = {}
    input_types: dict[str, int] = {}
    output_types: dict[str, int] = {}
    tools: dict[str, int] = {}
    models: dict[str, int] = {}
    total_executions = 0

    for agent in agents:
        snap = _agent_runtime_snapshot(agent)
        domain = snap["domain"] or "unspecified"
        domains[domain] = domains.get(domain, 0) + 1
        risk = agent.risk_class or "minimal"
        risk_classes[risk] = risk_classes.get(risk, 0) + 1
        for i in snap["inputs"]:
            t = i.get("type", "unknown")
            input_types[t] = input_types.get(t, 0) + 1
        for o in snap["outputs"]:
            t = o.get("type", "unknown")
            output_types[t] = output_types.get(t, 0) + 1
        for tool in snap["tools"]:
            tools[tool] = tools.get(tool, 0) + 1
        if snap["underlying_model"]:
            m = snap["underlying_model"]
            models[m] = models.get(m, 0) + 1
        total_executions += snap["total_executions_observed"]

    return {
        "schema_version": SCHEMA_VERSION,
        "regulation": REGULATION_REF,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agent_count": len(agents),
        "total_executions_observed": total_executions,
        "by_domain": domains,
        "by_risk_class": risk_classes,
        "input_type_distribution": input_types,
        "output_type_distribution": output_types,
        "tool_distribution": tools,
        "model_distribution": models,
        "platform_controls": _platform_controls(),
    }


def agent_data_sheet_to_markdown(sheet: dict[str, Any]) -> str:
    a = sheet["agent"]
    purpose = sheet["purpose_and_scope"]
    inp = sheet["input_data"]
    out = sheet["output_data"]
    tools = sheet["tool_access"]
    model = sheet["model_and_training_data"]
    quality = sheet["quality_and_bias"]
    metrics = sheet["observed_runtime_metrics"]

    def _bullets(items: Any) -> str:
        if isinstance(items, list):
            return "\n".join(f"- {item}" for item in items)
        return f"- {items}"

    def _schema_rows(schema: list[dict[str, Any]] | None) -> str:
        if not schema:
            return "- (none documented)"
        return "\n".join(
            f"- `{s.get('name', '?')}` ({s.get('type', '?')})"
            + (f" · required" if s.get("required") else "")
            + (f" · default: {s.get('default')}" if s.get("default") is not None else "")
            for s in schema
        )

    return f"""# Agent Data Sheet

**Regulation:** {sheet["regulation"]}
**Generated:** {sheet["generated_at"]}
**Status:** {sheet["status"]}

**Agent:** `{a["id"]}` · {a["name"]} · v{a["version"]} · risk class `{a["risk_class"]}`

---

## Purpose and scope

- **Domain:** {purpose["domain"]}
- **Intended purpose:** {purpose["intended_purpose"]}
- **Tags:** {", ".join(purpose["tags"] or []) or "-"}

## Input data

**Schema:**
{_schema_rows(inp["schema"])}

- **Constraints:** {inp["constraints"]}
- **Deployer source description:** {inp["deployer_source_description"]}
- **Special categories flag:** {inp["special_categories_flag"]}

## Output data

**Schema:**
{_schema_rows(out["schema"])}

- **Retention:** {out["retention"]}

## Tool access

**Tools:** {", ".join(tools["tools"] or []) or "-"}

{tools["notes"]}

## Model and training data

- **Underlying model:** `{model["underlying_model"]}`
- **Training-data statement:** {model["training_data_statement"]}
- **Fine-tuning datasets:** {model["fine_tuning_datasets"]}

## Quality, representativeness, bias (Art. 10)

- **Relevance and representativeness:** {quality["relevance_and_representativeness"]}

**Known gaps:**
{_bullets(quality["known_gaps"])}

- **Bias assessment method:** {quality["bias_assessment_method"]}

**Mitigation measures:**
{_bullets(quality["mitigation_measures"])}

## Platform-level data controls

{_bullets(sheet["platform_controls"])}

## Observed runtime metrics

- **Total executions:** {metrics["total_executions"]}
- **Success count:** {metrics["success_count"]}
- **Observed success rate:** {metrics["observed_success_rate"]}

---

*Generated by the agents.renemurrell.de data-governance engine. Sections
marked `[PROVIDER: …]` require completion by the placing-on-market
organisation. Retain with the technical documentation for 10 years (Art. 18).*
"""
