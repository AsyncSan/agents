"""Unit tests for EU database registration generator."""

from types import SimpleNamespace

from agentforge.eu_db import (
    REGULATION_REF,
    SCHEMA_VERSION,
    STATUSES,
    build_eu_db_registration,
    eu_db_to_markdown,
)


def _agent(risk_class: str = "high") -> SimpleNamespace:
    return SimpleNamespace(
        id="credit-scorer-v1",
        name="Credit Scorer",
        description="Scores consumer credit applications",
        version=3,
        risk_class=risk_class,
        total_executions=100,
        success_count=95,
        trust_score=0.85,
        avg_duration_seconds=120.0,
        card={
            "capabilities": {
                "domain": "fintech",
                "description": "Scores consumer credit applications",
            },
            "runtime": {"model": "anthropic/claude-sonnet-4-6"},
        },
    )


class TestBuildRegistration:
    def test_schema_metadata(self):
        r = build_eu_db_registration(_agent())
        assert r["schema_version"] == SCHEMA_VERSION
        assert r["regulation"] == REGULATION_REF
        assert r["status"] == "draft"

    def test_all_eleven_sections_present(self):
        r = build_eu_db_registration(_agent())
        for i in range(1, 12):
            matches = [k for k in r if k.startswith(f"section_b_{i}_")]
            assert matches, f"missing section B.{i}"

    def test_default_status_is_on_market(self):
        r = build_eu_db_registration(_agent())
        assert r["section_b_6_status"]["current_status"] == "on_market"

    def test_invalid_status_falls_back(self):
        r = build_eu_db_registration(_agent(), {"status": "not_a_real_status"})
        assert r["section_b_6_status"]["current_status"] == "on_market"

    def test_agent_metadata_in_identification(self):
        r = build_eu_db_registration(_agent())
        ident = r["section_b_4_system_identification"]
        assert ident["unique_reference"] == "credit-scorer-v1"
        assert "capability-card@v3" in ident["traceability_id"]

    def test_provider_inputs_override_placeholders(self):
        r = build_eu_db_registration(
            _agent(),
            {
                "provider_name": "Acme Bank GmbH",
                "provider_address": "Friedrichstr. 1, 10117 Berlin",
                "member_states": ["Germany", "Austria"],
            },
        )
        assert r["section_b_1_provider"]["name"] == "Acme Bank GmbH"
        assert r["section_b_8_member_states"] == ["Germany", "Austria"]

    def test_auth_rep_block_follows_flag(self):
        off = build_eu_db_registration(_agent(), {"auth_rep_required": False})
        on = build_eu_db_registration(
            _agent(),
            {"auth_rep_required": True, "auth_rep_name": "EU Rep Ltd., Dublin"},
        )
        assert off["section_b_3_authorised_representative"]["required"] is False
        assert on["section_b_3_authorised_representative"]["required"] is True
        assert on["section_b_3_authorised_representative"]["name"] == "EU Rep Ltd., Dublin"

    def test_non_high_risk_declaration_only_for_lower_risk_classes(self):
        high = build_eu_db_registration(
            _agent("high"),
            {"non_high_risk_justification": "Irrelevant for high risk"},
        )
        assert high["non_high_risk_declaration"] is None

        limited = build_eu_db_registration(
            _agent("limited"),
            {"non_high_risk_justification": "Advisory only; human makes final decision."},
        )
        assert limited["non_high_risk_declaration"] is not None
        assert limited["non_high_risk_declaration"]["applicable"] is True

    def test_non_high_risk_requires_justification(self):
        r = build_eu_db_registration(_agent("limited"))
        assert r["non_high_risk_declaration"] is None

    def test_statuses_constant_complete(self):
        assert "on_market" in STATUSES
        assert "recalled" in STATUSES


class TestMarkdown:
    def test_all_section_headings(self):
        md = eu_db_to_markdown(build_eu_db_registration(_agent()))
        for heading in [
            "## 1. Provider",
            "## 2. Submitter",
            "## 3. Authorised representative",
            "## 4. System identification",
            "## 5. Description",
            "## 6. Status",
            "## 7. Software",
            "## 8. Member States on market",
            "## 9. Declaration of conformity",
            "## 10. Instructions for use",
            "## 11. Additional info URL",
        ]:
            assert heading in md

    def test_regulation_referenced(self):
        md = eu_db_to_markdown(build_eu_db_registration(_agent()))
        assert REGULATION_REF in md

    def test_non_hr_section_appears_when_applicable(self):
        md = eu_db_to_markdown(
            build_eu_db_registration(
                _agent("limited"),
                {"non_high_risk_justification": "Advisory only."},
            )
        )
        assert "Non-high-risk declaration" in md

    def test_non_hr_section_absent_for_high_risk(self):
        md = eu_db_to_markdown(build_eu_db_registration(_agent("high")))
        assert "Non-high-risk declaration" not in md
