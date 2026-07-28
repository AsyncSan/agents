"""Unit tests for the incident module (deadlines + template)."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from agentforge.incidents import (
    SEVERITY_DEADLINE_DAYS,
    build_incident_report_template,
    deadline_for,
    incident_report_to_markdown,
    severity_catalog,
    time_remaining,
)


class TestDeadlines:
    def test_widespread_is_two_days(self):
        awareness = datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc)
        d = deadline_for("widespread_infringement", awareness)
        assert d == awareness + timedelta(days=2)

    def test_critical_infrastructure_is_two_days(self):
        awareness = datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc)
        d = deadline_for("critical_infrastructure", awareness)
        assert d == awareness + timedelta(days=2)

    def test_fundamental_rights_is_ten_days(self):
        awareness = datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc)
        d = deadline_for("fundamental_rights", awareness)
        assert d == awareness + timedelta(days=10)

    def test_property_harm_is_fifteen_days(self):
        awareness = datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc)
        d = deadline_for("serious_property_harm", awareness)
        assert d == awareness + timedelta(days=15)

    def test_unknown_severity_raises(self):
        with pytest.raises(ValueError):
            deadline_for("not_a_category", datetime.now(timezone.utc))

    def test_time_remaining_positive_before_deadline(self):
        awareness = datetime.now(timezone.utc)
        remaining = time_remaining("serious_property_harm", awareness)
        assert remaining.total_seconds() > 0

    def test_time_remaining_negative_when_overdue(self):
        awareness = datetime.now(timezone.utc) - timedelta(days=20)
        remaining = time_remaining("serious_property_harm", awareness)
        assert remaining.total_seconds() < 0

    def test_catalog_includes_all_categories(self):
        catalog = severity_catalog()
        assert len(catalog) == len(SEVERITY_DEADLINE_DAYS)
        for entry in catalog:
            assert entry["deadline_days"] == SEVERITY_DEADLINE_DAYS[entry["key"]]


def _sample_incident(severity: str = "fundamental_rights", overdue: bool = False):
    detected = datetime(2026, 4, 20, 10, 0, tzinfo=timezone.utc)
    awareness = (
        detected - timedelta(days=20) if overdue else detected
    )
    return SimpleNamespace(
        id="inc-abc",
        status="confirmed",
        agent_version=3,
        title="Incorrect credit denial for protected class",
        summary="Investigation showed disparate impact on applicants over 65.",
        severity=severity,
        detected_at=detected,
        awareness_at=awareness,
        affected_persons_estimate=120,
        root_cause=None,
        mitigation_taken="Suspended automated decisioning for this cohort.",
        mitigation_planned=None,
        reported_to_authority_at=None,
        authority_name=None,
        authority_reference=None,
    )


def _sample_agent():
    return SimpleNamespace(
        id="credit-scorer-v1",
        name="Credit Scorer",
        version=3,
        risk_class="high",
    )


class TestReportTemplate:
    def test_contains_schema_metadata(self):
        report = build_incident_report_template(_sample_incident(), _sample_agent())
        assert report["regulation"] == "EU 2024/1689 Art. 73"
        assert report["schema_version"] == "1"

    def test_uses_agent_metadata(self):
        report = build_incident_report_template(_sample_incident(), _sample_agent())
        assert report["system"]["id"] == "credit-scorer-v1"
        assert report["system"]["risk_class"] == "high"

    def test_falls_back_to_placeholders_without_agent(self):
        report = build_incident_report_template(_sample_incident(), None)
        assert "[PROVIDER" in report["system"]["id"]

    def test_deadline_and_overdue_flag(self):
        overdue_report = build_incident_report_template(
            _sample_incident(overdue=True), _sample_agent()
        )
        assert overdue_report["reporting"]["overdue"] is True
        assert overdue_report["reporting"]["time_remaining_seconds"] < 0

    def test_provider_contact_override(self):
        report = build_incident_report_template(
            _sample_incident(),
            _sample_agent(),
            {"organisation": "Acme Bank GmbH", "contact": "compliance@acme.example"},
        )
        assert report["provider"]["organisation"] == "Acme Bank GmbH"

    def test_markdown_renders_key_sections(self):
        report = build_incident_report_template(_sample_incident(), _sample_agent())
        md = incident_report_to_markdown(report)
        assert "# Serious Incident Report" in md
        assert "## Incident" in md
        assert "## Provider" in md
        assert "credit-scorer-v1" in md

    def test_overdue_markdown_contains_warning(self):
        report = build_incident_report_template(
            _sample_incident(overdue=True), _sample_agent()
        )
        md = incident_report_to_markdown(report)
        assert "OVERDUE" in md
