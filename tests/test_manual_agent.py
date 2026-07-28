"""Unit tests for the manual-agent helper."""

import pytest

from agentforge.annex_iv import build_annex_iv_template
from agentforge.data_governance import build_agent_data_sheet
from agentforge.eu_db import build_eu_db_registration
from agentforge.fria import build_fria_template
from agentforge.manual_agent import ManualAgentInput, build_manual_agent
from agentforge.pmm_plan import build_pmm_plan_template


class TestBuildManualAgent:
    def test_minimal_input(self):
        agent = build_manual_agent(ManualAgentInput(name="Internal Scorer"))
        assert agent.name == "Internal Scorer"
        assert agent.id.startswith("external/")
        assert agent.risk_class == "minimal"
        assert agent.version == 1

    def test_full_input(self):
        agent = build_manual_agent(
            ManualAgentInput(
                name="Credit Scorer",
                version=3,
                risk_class="high",
                description="Scores applications.",
                domain="fintech",
                model="gpt-4o",
                tools=["sql"],
            )
        )
        assert agent.version == 3
        assert agent.risk_class == "high"
        assert agent.card["capabilities"]["domain"] == "fintech"
        assert agent.card["runtime"]["model"] == "gpt-4o"
        assert agent.card["runtime"]["tools"] == ["sql"]

    def test_invalid_risk_class_raises(self):
        with pytest.raises(ValueError):
            build_manual_agent(
                ManualAgentInput(name="Test", risk_class="nonsense")
            )

    def test_slug_synthesis(self):
        agent = build_manual_agent(ManualAgentInput(name="Acme Credit Bot!"))
        assert "acme-credit-bot" in agent.id

    def test_explicit_id_retained(self):
        agent = build_manual_agent(
            ManualAgentInput(name="X", id="my-explicit-id")
        )
        assert agent.id == "my-explicit-id"


class TestManualAgentWorksWithGenerators:
    def _agent(self) -> object:
        return build_manual_agent(
            ManualAgentInput(
                name="Internal HR Assistant",
                version=2,
                risk_class="limited",
                description="Ranks CVs against a job spec.",
                domain="hr",
                model="gpt-4o",
            )
        )

    def test_fria_accepts_manual_agent(self):
        doc = build_fria_template(self._agent())
        assert doc["schema_version"]
        assert "Internal HR Assistant" in doc["section_1_process_description"]["agent_name"]

    def test_annex_iv_accepts_manual_agent(self):
        doc = build_annex_iv_template(self._agent())
        assert doc["agent"]["name"] == "Internal HR Assistant"
        assert doc["section_3_monitoring_information"]["accuracy_metrics_observed"][
            "total_executions"
        ] == 0

    def test_pmm_accepts_manual_agent(self):
        doc = build_pmm_plan_template(self._agent())
        assert doc["agent"]["version"] == 2

    def test_eu_db_accepts_manual_agent(self):
        doc = build_eu_db_registration(self._agent())
        assert doc["agent"]["name"] == "Internal HR Assistant"
        assert doc["section_b_4_system_identification"]["unique_reference"].startswith(
            "external/"
        )

    def test_data_sheet_accepts_manual_agent(self):
        doc = build_agent_data_sheet(self._agent())
        assert doc["agent"]["name"] == "Internal HR Assistant"
        assert doc["observed_runtime_metrics"]["total_executions"] == 0
