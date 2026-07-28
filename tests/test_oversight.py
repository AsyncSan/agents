"""Unit tests for the oversight roster builder (Art. 14, 26(2))."""

import pytest

from agentforge.oversight import (
    AUTHORITY_LEVELS,
    OVERSIGHT_ROLES,
    build_agent_oversight_roster,
    coverage_gap,
    roster_to_markdown,
    validate_authority,
    validate_role,
)


def _assignment(**overrides):
    base = {
        "staff_name": "Elena Schmidt",
        "staff_email": "elena@example.com",
        "staff_role_title": "Senior Risk Analyst",
        "oversight_role": "approver",
        "authority_level": "approve",
        "assigned_agent_ids": None,
        "training_certificates": [
            {"certificate_id": "abcd1234", "module_title": "AI Act Essentials"}
        ],
        "competence_notes": "5 years credit underwriting",
        "authority_source": "Delegation memo 2026-03-01",
        "assigned_by": "00000000-0000-0000-0000-000000000001",
        "active": True,
    }
    base.update(overrides)
    return base


class TestValidators:
    def test_role_accepts_known(self):
        for r in OVERSIGHT_ROLES:
            validate_role(r)

    def test_role_rejects_unknown(self):
        with pytest.raises(ValueError):
            validate_role("god_mode")

    def test_authority_accepts_known(self):
        for a in AUTHORITY_LEVELS:
            validate_authority(a)

    def test_authority_rejects_unknown(self):
        with pytest.raises(ValueError):
            validate_authority("root")


class TestCoverageGap:
    def test_low_risk_requires_only_approver(self):
        gaps = coverage_gap([_assignment()], "agent-1", high_risk=False)
        assert gaps == []

    def test_high_risk_requires_overseer_and_incident_owner(self):
        gaps = coverage_gap([_assignment()], "agent-1", high_risk=True)
        assert set(gaps) == {"overseer", "incident_owner"}

    def test_high_risk_all_roles_covered(self):
        assignments = [
            _assignment(oversight_role="approver"),
            _assignment(oversight_role="overseer", staff_email="o@example.com"),
            _assignment(oversight_role="incident_owner", staff_email="i@example.com"),
        ]
        gaps = coverage_gap(assignments, "agent-1", high_risk=True)
        assert gaps == []

    def test_assignment_scoped_to_other_agent_does_not_cover(self):
        assignments = [_assignment(assigned_agent_ids=["other-agent"])]
        gaps = coverage_gap(assignments, "agent-1", high_risk=False)
        assert "approver" in gaps

    def test_inactive_assignment_does_not_cover(self):
        gaps = coverage_gap([_assignment(active=False)], "agent-1", high_risk=False)
        assert "approver" in gaps

    def test_explicit_scope_covers(self):
        assignments = [_assignment(assigned_agent_ids=["agent-1", "agent-2"])]
        gaps = coverage_gap(assignments, "agent-1", high_risk=False)
        assert gaps == []


class TestRoster:
    def test_roster_metadata(self):
        r = build_agent_oversight_roster("a1", "Agent One", "limited", [_assignment()])
        assert r["agent"]["id"] == "a1"
        assert r["agent"]["risk_class"] == "limited"
        assert "Art. 14" in r["regulation"]

    def test_compliant_flag_for_low_risk_with_approver(self):
        r = build_agent_oversight_roster("a1", "Agent One", "limited", [_assignment()])
        assert r["compliant"] is True
        assert r["coverage_gaps"] == []

    def test_high_risk_without_full_coverage_is_non_compliant(self):
        r = build_agent_oversight_roster("a1", "Agent One", "high", [_assignment()])
        assert r["compliant"] is False
        assert set(r["coverage_gaps"]) == {"overseer", "incident_owner"}

    def test_distinct_person_count(self):
        assignments = [
            _assignment(oversight_role="approver", staff_email="a@example.com"),
            _assignment(oversight_role="reviewer", staff_email="a@example.com"),
            _assignment(oversight_role="reviewer", staff_email="b@example.com"),
        ]
        r = build_agent_oversight_roster("a1", "Agent One", "limited", assignments)
        assert r["total_assigned_persons"] == 2

    def test_roster_groups_by_role(self):
        assignments = [
            _assignment(oversight_role="approver"),
            _assignment(oversight_role="reviewer", staff_email="r@example.com"),
        ]
        r = build_agent_oversight_roster("a1", "Agent One", "limited", assignments)
        roles_present = {block["role"] for block in r["roster"]}
        assert roles_present == {"approver", "reviewer"}

    def test_org_wide_assignment_included_in_per_agent_roster(self):
        assignments = [_assignment(assigned_agent_ids=None)]
        r = build_agent_oversight_roster("a1", "Agent One", "limited", assignments)
        assert len(r["roster"]) == 1

    def test_scoped_assignment_excluded_when_not_matching(self):
        assignments = [_assignment(assigned_agent_ids=["other"])]
        r = build_agent_oversight_roster("a1", "Agent One", "limited", assignments)
        assert r["roster"] == []


class TestMarkdown:
    def test_empty_roster_says_none(self):
        r = build_agent_oversight_roster("a1", "Agent One", "limited", [])
        md = roster_to_markdown(r)
        assert "No oversight assignments recorded" in md

    def test_renders_staff_details(self):
        r = build_agent_oversight_roster(
            "a1", "Agent One", "limited", [_assignment()]
        )
        md = roster_to_markdown(r)
        assert "Elena Schmidt" in md
        assert "elena@example.com" in md
        assert "approver" in md
        assert "approve" in md
        assert "AI Act Essentials" in md

    def test_renders_gap_status_when_high_risk(self):
        r = build_agent_oversight_roster(
            "a1", "Agent One", "high", [_assignment()]
        )
        md = roster_to_markdown(r)
        assert "Missing roles" in md

    def test_renders_compliant_status(self):
        r = build_agent_oversight_roster(
            "a1",
            "Agent One",
            "limited",
            [_assignment()],
        )
        md = roster_to_markdown(r)
        assert "Fully covered" in md
