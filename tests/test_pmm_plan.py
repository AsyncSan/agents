"""Unit tests for the PMM plan generator."""

from types import SimpleNamespace

from agentforge.pmm_plan import (
    REGULATION_REF,
    REVIEW_CADENCES,
    SCHEMA_VERSION,
    build_pmm_plan_template,
    pmm_plan_to_markdown,
)


def _agent(
    *,
    risk_class: str = "high",
    total: int = 1000,
    success: int = 950,
    trust: float = 0.85,
    avg_duration: float = 180.0,
) -> SimpleNamespace:
    return SimpleNamespace(
        id="credit-scorer-v1",
        name="Credit Scorer",
        version=3,
        risk_class=risk_class,
        total_executions=total,
        success_count=success,
        trust_score=trust,
        avg_duration_seconds=avg_duration,
    )


class TestBuildPMM:
    def test_schema_and_regulation(self):
        plan = build_pmm_plan_template(_agent())
        assert plan["schema_version"] == SCHEMA_VERSION
        assert plan["regulation"] == REGULATION_REF
        assert plan["status"] == "draft"

    def test_default_cadence_is_monthly(self):
        plan = build_pmm_plan_template(_agent())
        assert plan["review_cadence"] == "monthly"

    def test_invalid_cadence_falls_back_to_monthly(self):
        plan = build_pmm_plan_template(_agent(), {"review_cadence": "random"})
        assert plan["review_cadence"] == "monthly"

    def test_valid_cadence_retained(self):
        plan = build_pmm_plan_template(_agent(), {"review_cadence": "quarterly"})
        assert plan["review_cadence"] == "quarterly"

    def test_observed_baseline_computed(self):
        plan = build_pmm_plan_template(_agent(total=200, success=180))
        b = plan["observed_baseline_metrics"]
        assert b["total_executions_observed"] == 200
        assert b["observed_success_rate"] == 0.9

    def test_platform_data_sources_always_present(self):
        plan = build_pmm_plan_template(_agent())
        names = [s["name"] for s in plan["data_sources"]]
        assert "Immutable event log" in names
        assert "Serious incident register" in names

    def test_additional_data_sources_merge(self):
        extra = [{"name": "Customer NPS", "source": "CRM", "collected": "Monthly NPS score"}]
        plan = build_pmm_plan_template(_agent(), {"additional_data_sources": extra})
        names = [s["name"] for s in plan["data_sources"]]
        assert "Customer NPS" in names
        assert "Immutable event log" in names  # platform sources still there

    def test_default_metrics_include_trust_and_success(self):
        plan = build_pmm_plan_template(_agent())
        metric_names = [m["name"] for m in plan["metrics"]]
        assert any("Success rate" in n for n in metric_names)
        assert any("Trust score" in n for n in metric_names)

    def test_provider_metrics_replace_defaults(self):
        custom = [{"name": "Custom metric", "baseline": "x", "alert_threshold": "y", "data_source": "z"}]
        plan = build_pmm_plan_template(_agent(), {"metrics": custom})
        assert plan["metrics"] == custom

    def test_provider_owner_and_escalation_override(self):
        plan = build_pmm_plan_template(
            _agent(),
            {
                "pmm_owner": "Head of AI Governance",
                "escalation_chain": ["L1: on-call", "L2: VP Eng"],
            },
        )
        assert plan["ownership"]["pmm_owner"] == "Head of AI Governance"
        assert plan["ownership"]["escalation_chain"] == ["L1: on-call", "L2: VP Eng"]

    def test_cadence_list_matches_valid_set(self):
        assert set(REVIEW_CADENCES) == {"weekly", "monthly", "quarterly", "annual"}


class TestMarkdown:
    def test_renders_expected_sections(self):
        md = pmm_plan_to_markdown(build_pmm_plan_template(_agent()))
        for heading in [
            "# Post-Market Monitoring Plan",
            "## Ownership",
            "## Data sources",
            "## Metrics and alert thresholds",
            "## Review cadence",
            "## Re-assessment triggers",
            "## Corrective-action procedure",
            "## Reporting flow",
            "## Retention",
        ]:
            assert heading in md

    def test_metric_table_has_observed_values(self):
        md = pmm_plan_to_markdown(build_pmm_plan_template(_agent(success=950, total=1000)))
        assert "95.00%" in md  # 0.95 rendered

    def test_regulation_referenced(self):
        md = pmm_plan_to_markdown(build_pmm_plan_template(_agent()))
        assert REGULATION_REF in md
