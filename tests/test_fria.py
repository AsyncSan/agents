"""Unit tests for the FRIA template builder."""

from types import SimpleNamespace

from agentforge.fria import (
    REGULATION_REF,
    SCHEMA_VERSION,
    TRIGGER_USE_CASES,
    build_fria_template,
    fria_to_markdown,
)


def _agent(risk_class: str = "limited") -> SimpleNamespace:
    return SimpleNamespace(
        id="credit-scorer-v1",
        name="Credit Scorer",
        description="Scores consumer credit applications.",
        version=2,
        risk_class=risk_class,
        card={
            "capabilities": {
                "domain": "fintech",
                "description": "Scores consumer credit applications.",
            },
        },
    )


class TestBuildFRIATemplate:
    def test_default_scaffold_has_all_sections(self):
        fria = build_fria_template(_agent())
        for key in [
            "section_1_process_description",
            "section_2_duration_frequency",
            "section_3_affected_persons",
            "section_4_harm_risks",
            "section_5_human_oversight",
            "section_6_mitigation_governance",
        ]:
            assert key in fria

    def test_schema_metadata(self):
        fria = build_fria_template(_agent())
        assert fria["schema_version"] == SCHEMA_VERSION
        assert fria["regulation"] == REGULATION_REF
        assert fria["status"] == "draft"

    def test_deployer_inputs_override_placeholders(self):
        inputs = {
            "deployer_organisation": "Acme Bank GmbH",
            "deployer_process_summary": "Evaluate applications within 10 minutes.",
            "affected_categories": ["Consumer credit applicants in Germany"],
        }
        fria = build_fria_template(_agent(), inputs)
        assert fria["deployer"]["organisation"] == "Acme Bank GmbH"
        summary = fria["section_1_process_description"]["deployer_process_summary"]
        assert summary == "Evaluate applications within 10 minutes."
        assert fria["section_3_affected_persons"]["primary_categories"] == [
            "Consumer credit applicants in Germany"
        ]

    def test_high_risk_adds_approval_gate_measure(self):
        fria = build_fria_template(_agent("high"))
        measures = fria["section_5_human_oversight"]["platform_measures"]
        assert any("approval gate" in m.lower() for m in measures)

    def test_limited_risk_does_not_add_approval_gate(self):
        fria = build_fria_template(_agent("limited"))
        measures = fria["section_5_human_oversight"]["platform_measures"]
        assert not any("approval gate" in m.lower() for m in measures)

    def test_unknown_use_case_key_left_as_placeholder(self):
        fria = build_fria_template(_agent(), {"use_case_key": "not_a_real_key"})
        assert "[DEPLOYER" in fria["use_case"]["trigger_reference"]

    def test_known_use_case_key_fills_trigger(self):
        for key in TRIGGER_USE_CASES:
            fria = build_fria_template(_agent(), {"use_case_key": key})
            assert fria["use_case"]["trigger_category"] == key
            assert fria["use_case"]["trigger_reference"] == TRIGGER_USE_CASES[key]

    def test_agent_metadata_populates_section_1(self):
        fria = build_fria_template(_agent())
        s1 = fria["section_1_process_description"]
        assert s1["agent_id"] == "credit-scorer-v1"
        assert s1["agent_version"] == 2
        assert s1["agent_domain"] == "fintech"

    def test_ifu_version_defaults_to_card_version(self):
        fria = build_fria_template(_agent())
        assert (
            fria["section_5_human_oversight"]["instructions_for_use_version"]
            == "capability-card@v2"
        )


class TestFRIAMarkdown:
    def test_renders_all_headings(self):
        fria = build_fria_template(_agent())
        md = fria_to_markdown(fria)
        for heading in [
            "# Fundamental Rights Impact Assessment",
            "## 1. Process description",
            "## 2. Duration and frequency",
            "## 3. Affected persons",
            "## 4. Specific risks of harm",
            "## 5. Human oversight",
            "## 6. Governance and mitigation",
        ]:
            assert heading in md

    def test_includes_regulation_reference(self):
        md = fria_to_markdown(build_fria_template(_agent()))
        assert REGULATION_REF in md

    def test_lists_platform_measures_as_bullets(self):
        md = fria_to_markdown(build_fria_template(_agent("high")))
        assert "- Mandatory approval gate" in md
        assert "- Immutable event log" in md

    def test_handles_deployer_filled_lists(self):
        fria = build_fria_template(
            _agent(),
            {"affected_categories": ["Policyholders", "Beneficiaries"]},
        )
        md = fria_to_markdown(fria)
        assert "- Policyholders" in md
        assert "- Beneficiaries" in md
