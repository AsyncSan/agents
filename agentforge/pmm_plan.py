"""EU AI Act Art. 72 — Post-Market Monitoring Plan.

Art. 72 requires providers of high-risk AI systems to establish a
post-market monitoring (PMM) system that actively and systematically
collects, documents and analyses relevant data about the system's
performance after it is placed on the market. The plan is part of the
technical documentation (Annex IV §9) but stands on its own as the
operational playbook for the monitoring loop.

This module builds a PMM plan from the agent capability card, observed
runtime metrics, and provider-supplied policy inputs. The result pre-fills
the data-source and metric sections from platform-native telemetry and
leaves cadence/ownership/escalation as scaffold prompts.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agentforge.models.agent import Agent

SCHEMA_VERSION = "1"
REGULATION_REF = "EU 2024/1689 Art. 72"

REVIEW_CADENCES = ("weekly", "monthly", "quarterly", "annual")


def _platform_data_sources() -> list[dict[str, str]]:
    return [
        {
            "name": "Immutable event log",
            "source": "Platform (Art. 12)",
            "collected": "Per execution: inputs, outputs, duration, cost, actor, agent version",
        },
        {
            "name": "Trust score",
            "source": "Platform (5-factor, updated per execution)",
            "collected": "Success rate, duration accuracy, volume, recency, ratings",
        },
        {
            "name": "User ratings and complaints",
            "source": "Consumer portal",
            "collected": "Post-task rating 1-5, optional feedback text",
        },
        {
            "name": "Serious incident register",
            "source": "Platform (Art. 73)",
            "collected": "Logged incidents with severity, deadlines, mitigation",
        },
    ]


def _observed_metrics(agent: Agent) -> dict[str, Any]:
    total = agent.total_executions or 0
    success = agent.success_count or 0
    success_rate = (success / total) if total > 0 else None
    return {
        "total_executions_observed": total,
        "success_count_observed": success,
        "observed_success_rate": round(success_rate, 4) if success_rate is not None else None,
        "trust_score": float(agent.trust_score) if agent.trust_score is not None else None,
        "avg_duration_seconds": (
            float(agent.avg_duration_seconds)
            if agent.avg_duration_seconds is not None
            else None
        ),
    }


def _default_metrics(agent: Agent) -> list[dict[str, Any]]:
    metrics = _observed_metrics(agent)
    baseline = metrics["observed_success_rate"] or 0.95
    return [
        {
            "name": "Success rate (rolling 7d)",
            "baseline": f"{baseline:.2%}" if metrics["observed_success_rate"] else "[baseline TBD]",
            "alert_threshold": "-10 percentage points vs. baseline over any 24h window",
            "data_source": "event log",
        },
        {
            "name": "Average duration (rolling 7d)",
            "baseline": (
                f"{metrics['avg_duration_seconds']:.0f}s"
                if metrics["avg_duration_seconds"]
                else "[baseline TBD]"
            ),
            "alert_threshold": "+50% vs. rolling 30d baseline",
            "data_source": "event log",
        },
        {
            "name": "Trust score",
            "baseline": (
                f"{metrics['trust_score']:.2f}"
                if metrics["trust_score"] is not None
                else "[baseline TBD]"
            ),
            "alert_threshold": "-0.20 drop over any 14d window",
            "data_source": "platform trust system",
        },
        {
            "name": "User complaint volume",
            "baseline": "[PROVIDER: complaints per 1000 runs]",
            "alert_threshold": "[PROVIDER: threshold, e.g., >3 per 1000]",
            "data_source": "consumer portal",
        },
        {
            "name": "Serious incidents (Art. 73)",
            "baseline": "0 per month",
            "alert_threshold": ">=1 confirmed incident triggers immediate review",
            "data_source": "incident register",
        },
    ]


def _default_triggers() -> list[str]:
    return [
        "Metric alert threshold breached (see Metrics section)",
        "Serious incident reported under Art. 73",
        "Substantial modification of the system (Art. 43)",
        "Regulatory update that affects the intended purpose",
        "Complaint volume exceeds baseline",
        "Detected systematic bias against a protected group",
    ]


def _default_corrective_actions() -> list[str]:
    return [
        "Classify the finding (incident / near-miss / observed drift)",
        "Decide on execution pause scope (agent-wide or consumer-specific)",
        "Notify affected deployers and consumers via webhook + email",
        "Open a serious incident record if Art. 73 applies",
        "Assign root-cause investigation owner with a deadline",
        "Update the risk management system (Art. 9) log",
    ]


def build_pmm_plan_template(
    agent: Agent,
    provider_inputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compose a Post-Market Monitoring plan for one agent."""
    inputs = provider_inputs or {}
    cadence = inputs.get("review_cadence", "monthly")
    if cadence not in REVIEW_CADENCES:
        cadence = "monthly"

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
        "ownership": {
            "pmm_owner": inputs.get("pmm_owner")
            or "[PROVIDER: role accountable for the post-market monitoring system]",
            "escalation_chain": inputs.get("escalation_chain")
            or [
                "[PROVIDER: first-line on-call engineer]",
                "[PROVIDER: head of AI engineering]",
                "[PROVIDER: compliance officer]",
            ],
        },
        "data_sources": _platform_data_sources()
        + (inputs.get("additional_data_sources") or []),
        "metrics": inputs.get("metrics") or _default_metrics(agent),
        "analysis_methodology": inputs.get("analysis_methodology")
        or (
            "Scheduled aggregation of platform metrics into a weekly dashboard. "
            "Month-to-month comparison plus anomaly detection on the event log. "
            "Manual spot-check of 2-5% of runs for qualitative review."
        ),
        "review_cadence": cadence,
        "re_assessment_triggers": inputs.get("re_assessment_triggers") or _default_triggers(),
        "corrective_action_procedure": inputs.get("corrective_action_procedure")
        or _default_corrective_actions(),
        "reporting_flow": {
            "internal_report": (
                f"{cadence.capitalize()} PMM report to the pmm_owner, summarising metric"
                " deltas, open incidents, user complaints, and corrective actions."
            ),
            "regulatory_report": (
                "Serious incidents reported via Art. 73 pipeline within the applicable"
                " 2/10/15-day deadline. PMM evidence accompanies any market-surveillance request."
            ),
            "integration_with_fria": (
                "PMM findings that change the risk picture for a deployed use-case feed"
                " back into the deployer's FRIA (Art. 27) for re-approval."
            ),
        },
        "retention": "10 years from placing on market under Art. 18. PMM dashboard data kept at least 6 months under Art. 19.",
        "observed_baseline_metrics": _observed_metrics(agent),
        "status": "draft",
    }


def pmm_plan_to_markdown(plan: dict[str, Any]) -> str:
    a = plan["agent"]
    owner = plan["ownership"]
    baseline = plan["observed_baseline_metrics"]
    reporting = plan["reporting_flow"]

    def _bullets(items: Any) -> str:
        if isinstance(items, list):
            return "\n".join(f"- {item}" for item in items)
        return f"- {items}"

    metrics_rows = "\n".join(
        f"| {m.get('name', '-')} | {m.get('baseline', '-')} | {m.get('alert_threshold', '-')} | {m.get('data_source', '-')} |"
        for m in plan.get("metrics", [])
    )

    source_rows = "\n".join(
        f"| {s.get('name', '-')} | {s.get('source', '-')} | {s.get('collected', '-')} |"
        for s in plan.get("data_sources", [])
    )

    return f"""# Post-Market Monitoring Plan

**Regulation:** {plan["regulation"]}
**Generated:** {plan["generated_at"]}
**Status:** {plan["status"]}

**System:** `{a["id"]}` · {a["name"]} · v{a["version"]} · risk class `{a["risk_class"]}`

---

## Ownership

- **PMM owner:** {owner["pmm_owner"]}

**Escalation chain:**
{_bullets(owner["escalation_chain"])}

## Data sources

| Source | Origin | Collected |
|---|---|---|
{source_rows}

## Observed baseline at plan generation

- **Total executions observed:** {baseline["total_executions_observed"]}
- **Success count:** {baseline["success_count_observed"]}
- **Observed success rate:** {baseline["observed_success_rate"]}
- **Trust score:** {baseline["trust_score"]}
- **Average duration (seconds):** {baseline["avg_duration_seconds"]}

## Metrics and alert thresholds

| Metric | Baseline | Alert threshold | Source |
|---|---|---|---|
{metrics_rows}

## Analysis methodology

{plan["analysis_methodology"]}

## Review cadence

`{plan["review_cadence"]}`

## Re-assessment triggers

{_bullets(plan["re_assessment_triggers"])}

## Corrective-action procedure

{_bullets(plan["corrective_action_procedure"])}

## Reporting flow

- **Internal:** {reporting["internal_report"]}
- **Regulatory:** {reporting["regulatory_report"]}
- **FRIA integration:** {reporting["integration_with_fria"]}

## Retention

{plan["retention"]}

---

*Generated by the agents.renemurrell.de PMM scaffolding engine. Sections marked
`[PROVIDER: …]` require completion by the placing-on-market organisation.*
"""
