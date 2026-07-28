"""Unit tests for EU Declaration of Conformity generator."""

from types import SimpleNamespace

from agentforge.declaration import (
    DEFAULT_HARMONISED_STANDARDS,
    REGULATION_REF,
    SCHEMA_VERSION,
    build_declaration,
    declaration_to_markdown,
)


def _agent(risk_class: str = "high", domain: str = "fintech") -> SimpleNamespace:
    return SimpleNamespace(
        id="credit-scorer-v1",
        name="Credit Scorer",
        description="Scores consumer credit applications",
        version=3,
        risk_class=risk_class,
        card={
            "capabilities": {
                "domain": domain,
                "description": "Scores consumer credit applications",
            },
            "runtime": {"model": "anthropic/claude-sonnet-4-6"},
        },
    )


class TestBuildDeclaration:
    def test_schema_metadata(self):
        r = build_declaration(_agent())
        assert r["schema_version"] == SCHEMA_VERSION
        assert r["regulation"] == REGULATION_REF
        assert r["status"] == "draft"

    def test_all_nine_annex_v_sections_present(self):
        r = build_declaration(_agent())
        for i in range(1, 10):
            matches = [k for k in r if k.startswith(f"annex_v_{i}_")]
            assert matches, f"missing Annex V section {i}"

    def test_ce_marking_block_present(self):
        r = build_declaration(_agent())
        assert "ce_marking" in r
        assert "affixed" in r["ce_marking"]
        assert r["ce_marking"]["affixed_electronically"] is True

    def test_agent_identification(self):
        r = build_declaration(_agent())
        ident = r["annex_v_1_system_identification"]
        assert ident["unique_reference"] == "credit-scorer-v1"
        assert ident["traceability_id"] == "capability-card@v3"
        assert ident["version"] == "v3"

    def test_provider_inputs_override_placeholders(self):
        r = build_declaration(
            _agent(),
            {
                "provider_name": "Acme Bank GmbH",
                "provider_address": "Friedrichstr. 1, 10117 Berlin",
                "signatory_name": "Maria Schmidt",
            },
        )
        assert r["annex_v_2_provider"]["name"] == "Acme Bank GmbH"
        assert r["annex_v_8_signature"]["signatory_name"] == "Maria Schmidt"

    def test_fintech_agent_triggers_pii_statement(self):
        r = build_declaration(_agent(domain="fintech"))
        assert r["annex_v_5_data_protection_statement"]["applicable"] is True
        assert "GDPR" in r["annex_v_4_conformity_statement"]

    def test_non_pii_domain_has_simple_statement(self):
        r = build_declaration(_agent(domain="security"))
        assert r["annex_v_5_data_protection_statement"]["applicable"] is False
        assert "does not process personal data" in r["annex_v_5_data_protection_statement"]["text"]

    def test_explicit_pii_flag_overrides_domain_heuristic(self):
        r = build_declaration(
            _agent(domain="security"),
            {"processes_personal_data": True},
        )
        assert r["annex_v_5_data_protection_statement"]["applicable"] is True

    def test_notified_body_default_not_applicable(self):
        r = build_declaration(_agent("high"))
        assert r["annex_v_7_notified_body"]["applicable"] is False
        assert "Annex VI" in r["annex_v_7_notified_body"]["rationale"]

    def test_notified_body_only_for_high_risk_when_required(self):
        low = build_declaration(_agent("limited"), {"notified_body_required": True})
        assert low["annex_v_7_notified_body"]["applicable"] is False

        high = build_declaration(
            _agent("high"),
            {
                "notified_body_required": True,
                "notified_body_name": "TÜV Nord",
                "notified_body_id": "0044",
            },
        )
        assert high["annex_v_7_notified_body"]["applicable"] is True
        assert high["annex_v_7_notified_body"]["name"] == "TÜV Nord"
        assert high["annex_v_7_notified_body"]["identification_number"] == "0044"

    def test_default_harmonised_standards_applied(self):
        r = build_declaration(_agent())
        applied = r["annex_v_6_harmonised_standards"]["standards_applied"]
        assert applied == DEFAULT_HARMONISED_STANDARDS

    def test_custom_harmonised_standards_override(self):
        r = build_declaration(
            _agent(),
            {"harmonised_standards": ["ISO/IEC 27001:2022"]},
        )
        assert r["annex_v_6_harmonised_standards"]["standards_applied"] == [
            "ISO/IEC 27001:2022"
        ]

    def test_retention_notice_mentions_ten_years(self):
        r = build_declaration(_agent())
        assert "10 years" in r["retention_notice"]

    def test_signature_defaults_to_today(self):
        r = build_declaration(_agent())
        sig = r["annex_v_8_signature"]
        assert len(sig["date"]) == 10  # YYYY-MM-DD

    def test_ce_marking_nb_flag_mirrors_notified_body(self):
        r = build_declaration(
            _agent("high"),
            {"notified_body_required": True},
        )
        assert r["ce_marking"]["notified_body_number_alongside"] is True


class TestMarkdown:
    def test_all_section_headings(self):
        md = declaration_to_markdown(build_declaration(_agent()))
        for heading in [
            "## 1. System identification",
            "## 2. Provider",
            "## 3. Sole responsibility",
            "## 4. Conformity statement",
            "## 5. Data protection statement",
            "## 6. Harmonised standards and common specifications",
            "## 7. Notified body",
            "## 8. Signature",
            "## 9. Language",
            "## CE marking (Art. 48)",
        ]:
            assert heading in md

    def test_regulation_referenced(self):
        md = declaration_to_markdown(build_declaration(_agent()))
        assert REGULATION_REF in md

    def test_pii_block_present_for_fintech(self):
        md = declaration_to_markdown(build_declaration(_agent(domain="fintech")))
        assert "processes personal data" in md
        assert "GDPR" in md

    def test_non_pii_block_when_not_applicable(self):
        md = declaration_to_markdown(build_declaration(_agent(domain="security")))
        assert "does not process personal data" in md

    def test_notified_body_renders_rationale_when_not_applicable(self):
        md = declaration_to_markdown(build_declaration(_agent("high")))
        assert "Annex VI" in md

    def test_notified_body_renders_details_when_applicable(self):
        md = declaration_to_markdown(
            build_declaration(
                _agent("high"),
                {"notified_body_required": True, "notified_body_id": "0044"},
            )
        )
        assert "0044" in md
