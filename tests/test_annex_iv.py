"""Unit tests for the Annex IV technical documentation generator."""

from types import SimpleNamespace

import pytest

from agentforge.annex_iv import (
    REGULATION_REF,
    SCHEMA_VERSION,
    VARIANTS,
    annex_iv_to_markdown,
    build_annex_iv_template,
)


def _agent(
    *,
    risk_class: str = "limited",
    total_executions: int = 100,
    success_count: int = 95,
    trust_score: float = 0.8,
    avg_duration_seconds: float | None = 180.0,
) -> SimpleNamespace:
    return SimpleNamespace(
        id="credit-scorer-v1",
        name="Credit Scorer",
        description="Scores consumer credit applications.",
        version=3,
        risk_class=risk_class,
        total_executions=total_executions,
        success_count=success_count,
        trust_score=trust_score,
        avg_duration_seconds=avg_duration_seconds,
        card={
            "capabilities": {
                "domain": "fintech",
                "tags": ["credit", "scoring"],
                "description": "Scores consumer credit applications.",
                "inputs": [{"name": "application_json", "type": "object", "required": True}],
                "outputs": [{"name": "score.json", "type": "json", "guaranteed": True}],
                "constraints": {"timeout_max": 60},
            },
            "runtime": {
                "model": "anthropic/claude-sonnet-4-6",
                "server_type": "cax11",
                "snapshot_profile": "base",
                "tools": ["shell"],
                "estimated_duration_seconds": 60,
            },
        },
    )


class TestBuildAnnexIVTemplate:
    def test_has_all_nine_sections(self):
        doc = build_annex_iv_template(_agent())
        for i in range(1, 10):
            key = {
                1: "section_1_general_description",
                2: "section_2_detailed_description",
                3: "section_3_monitoring_information",
                4: "section_4_performance_metrics",
                5: "section_5_risk_management_system",
                6: "section_6_changes",
                7: "section_7_applied_standards",
                8: "section_8_declaration_of_conformity",
                9: "section_9_post_market_monitoring",
            }[i]
            assert key in doc, f"missing section {i}"

    def test_schema_metadata(self):
        doc = build_annex_iv_template(_agent())
        assert doc["schema_version"] == SCHEMA_VERSION
        assert doc["regulation"] == REGULATION_REF
        assert doc["status"] == "draft"
        assert doc["variant"] == "full"

    def test_agent_metadata_echoed(self):
        doc = build_annex_iv_template(_agent())
        assert doc["agent"]["id"] == "credit-scorer-v1"
        assert doc["agent"]["version"] == 3
        assert doc["agent"]["risk_class"] == "limited"

    def test_card_populates_section_1(self):
        doc = build_annex_iv_template(_agent())
        s1 = doc["section_1_general_description"]
        assert s1["system_identifier"] == "credit-scorer-v1"
        assert s1["underlying_model"] == "anthropic/claude-sonnet-4-6"
        assert s1["instructions_for_use_reference"] == "capability-card@v3"

    def test_observed_success_rate_from_metrics(self):
        doc = build_annex_iv_template(_agent(total_executions=200, success_count=180))
        metrics = doc["section_3_monitoring_information"]["accuracy_metrics_observed"]
        assert metrics["total_executions"] == 200
        assert metrics["success_count"] == 180
        assert metrics["observed_success_rate"] == 0.9

    def test_zero_executions_leaves_success_rate_none(self):
        doc = build_annex_iv_template(_agent(total_executions=0, success_count=0))
        metrics = doc["section_3_monitoring_information"]["accuracy_metrics_observed"]
        assert metrics["observed_success_rate"] is None

    def test_provider_inputs_override_placeholders(self):
        inputs = {
            "provider_name": "Acme Bank GmbH",
            "provider_contact": "legal@acme.example",
            "rms_owner": "Head of AI Governance",
            "identified_risks": ["Disparate impact on protected classes"],
        }
        doc = build_annex_iv_template(_agent(), inputs)
        assert doc["section_1_general_description"]["provider_name"] == "Acme Bank GmbH"
        assert doc["section_5_risk_management_system"]["rms_owner"] == "Head of AI Governance"
        assert doc["section_5_risk_management_system"]["identified_risks"] == [
            "Disparate impact on protected classes"
        ]

    def test_simplified_variant_collapses_sections(self):
        full = build_annex_iv_template(_agent(), variant="full")
        simplified = build_annex_iv_template(_agent(), variant="simplified")
        assert "robustness_testing" in full["section_4_performance_metrics"]
        assert "robustness_testing" not in simplified["section_4_performance_metrics"]
        assert "substantial_modification_definition" not in simplified["section_6_changes"]

    def test_invalid_variant_rejected(self):
        with pytest.raises(ValueError):
            build_annex_iv_template(_agent(), variant="nonsense")

    def test_known_variants_listed(self):
        assert "full" in VARIANTS
        assert "simplified" in VARIANTS

    def test_platform_oversight_measures_include_art_50(self):
        doc = build_annex_iv_template(_agent(risk_class="limited"))
        measures = doc["section_3_monitoring_information"]["human_oversight_measures"]
        assert any("Art. 50" in m for m in measures)


class TestMarkdown:
    def test_renders_all_section_headings(self):
        md = annex_iv_to_markdown(build_annex_iv_template(_agent()))
        for heading in [
            "## 1. General description",
            "## 2. Detailed description",
            "## 3. Monitoring information",
            "## 4. Appropriateness of performance metrics",
            "## 5. Risk management system",
            "## 6. Changes",
            "## 7. Applied standards",
            "## 8. Declaration of conformity",
            "## 9. Post-market monitoring",
        ]:
            assert heading in md

    def test_includes_regulation_reference(self):
        md = annex_iv_to_markdown(build_annex_iv_template(_agent()))
        assert REGULATION_REF in md

    def test_simplified_note_only_on_simplified(self):
        md_full = annex_iv_to_markdown(build_annex_iv_template(_agent(), variant="full"))
        md_simplified = annex_iv_to_markdown(
            build_annex_iv_template(_agent(), variant="simplified")
        )
        assert "SME simplified form" not in md_full
        assert "SME simplified form" in md_simplified

    def test_handles_provider_supplied_lists(self):
        doc = build_annex_iv_template(
            _agent(),
            {"harmonised_standards_applied": ["EN ISO/IEC 42001"]},
        )
        md = annex_iv_to_markdown(doc)
        assert "- EN ISO/IEC 42001" in md
