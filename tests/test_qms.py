"""Unit tests for the QMS manual generator."""

from types import SimpleNamespace

import pytest

from agentforge.qms import (
    DEFAULT_STANDARDS,
    REGULATION_REF,
    SCHEMA_VERSION,
    VARIANTS,
    build_qms_template,
    qms_to_markdown,
)


class TestBuildQMS:
    def test_schema_metadata(self):
        doc = build_qms_template()
        assert doc["schema_version"] == SCHEMA_VERSION
        assert doc["regulation"] == REGULATION_REF
        assert doc["status"] == "draft"

    def test_contains_all_thirteen_sections(self):
        doc = build_qms_template()
        keys = [
            "section_a_regulatory_strategy",
            "section_b_design_control",
            "section_c_development",
            "section_d_validation",
            "section_e_standards",
            "section_f_data_management",
            "section_g_risk_management",
            "section_h_post_market_monitoring",
            "section_i_incident_reporting",
            "section_j_authority_communication",
            "section_k_record_keeping",
            "section_l_resources",
            "section_m_accountability",
        ]
        for k in keys:
            assert k in doc, f"missing {k}"

    def test_simplified_variant_omits_board_artefacts(self):
        full = build_qms_template({}, variant="full")
        simplified = build_qms_template({}, variant="simplified")
        assert "internal_audit_schedule" in full["section_m_accountability"]
        assert "internal_audit_schedule" not in simplified["section_m_accountability"]
        assert "board_reporting" not in simplified["section_m_accountability"]
        assert "budget_and_staffing" in full["section_l_resources"]
        assert "budget_and_staffing" not in simplified["section_l_resources"]

    def test_invalid_variant_rejected(self):
        with pytest.raises(ValueError):
            build_qms_template({}, variant="nonsense")

    def test_provider_inputs_override_placeholders(self):
        doc = build_qms_template(
            {
                "organisation_name": "Acme Bank GmbH",
                "risk_owner": "Head of AI Governance",
                "accountability_owner": "CEO",
            },
        )
        assert doc["organisation"]["name"] == "Acme Bank GmbH"
        assert doc["section_g_risk_management"]["owner"] == "Head of AI Governance"
        assert doc["section_m_accountability"]["accountability_owner"] == "CEO"

    def test_platform_controls_always_injected(self):
        doc = build_qms_template()
        assert any(
            "event log" in c.lower()
            for c in doc["section_f_data_management"]["platform_controls"]
        )
        assert any(
            "PMM" in c or "post-market" in c.lower() or "plan" in c.lower()
            for c in doc["section_h_post_market_monitoring"]["platform_controls"]
        )

    def test_default_standards_referenced(self):
        doc = build_qms_template()
        assert doc["section_e_standards"]["baseline_standards"] == DEFAULT_STANDARDS

    def test_agent_addendum_appended_when_provided(self):
        agent = SimpleNamespace(
            id="credit-scorer-v1",
            name="Credit Scorer",
            version=3,
            risk_class="high",
        )
        doc = build_qms_template(agent=agent)
        assert "system_specific_addendum" in doc
        assert doc["system_specific_addendum"]["agent_id"] == "credit-scorer-v1"

    def test_no_addendum_without_agent(self):
        doc = build_qms_template()
        assert "system_specific_addendum" not in doc

    def test_variants_constant(self):
        assert set(VARIANTS) == {"full", "simplified"}


class TestMarkdown:
    def test_renders_all_thirteen_section_headings(self):
        md = qms_to_markdown(build_qms_template())
        for letter in "ABCDEFGHIJKLM":
            assert f"## {letter}." in md

    def test_simplified_banner(self):
        full_md = qms_to_markdown(build_qms_template({}, variant="full"))
        simp_md = qms_to_markdown(build_qms_template({}, variant="simplified"))
        assert "Art. 63 simplified form" not in full_md
        assert "Art. 63 simplified form" in simp_md

    def test_regulation_referenced(self):
        md = qms_to_markdown(build_qms_template())
        assert REGULATION_REF in md

    def test_addendum_rendered_when_agent_supplied(self):
        agent = SimpleNamespace(
            id="credit-scorer-v1", name="Credit Scorer", version=3, risk_class="high"
        )
        md = qms_to_markdown(build_qms_template(agent=agent))
        assert "System-specific addendum" in md
        assert "credit-scorer-v1" in md
