"""Unit tests for data governance generator."""

from types import SimpleNamespace

from agentforge.data_governance import (
    REGULATION_REF,
    SCHEMA_VERSION,
    agent_data_sheet_to_markdown,
    build_agent_data_sheet,
    build_org_data_inventory,
)


def _agent(
    *,
    agent_id: str = "credit-scorer-v1",
    domain: str = "fintech",
    risk_class: str = "limited",
    total: int = 100,
    success: int = 90,
    inputs: list[dict] | None = None,
    outputs: list[dict] | None = None,
    tools: list[str] | None = None,
    model: str = "anthropic/claude-sonnet-4-6",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=agent_id,
        name="Test Agent",
        description="Does testing",
        version=1,
        risk_class=risk_class,
        total_executions=total,
        success_count=success,
        trust_score=0.85,
        avg_duration_seconds=120.0,
        card={
            "capabilities": {
                "domain": domain,
                "tags": ["credit", "scoring"],
                "description": "Does testing",
                "inputs": inputs or [{"name": "payload", "type": "object", "required": True}],
                "outputs": outputs or [{"name": "result.json", "type": "json", "guaranteed": True}],
                "constraints": {"timeout_max": 60},
            },
            "runtime": {
                "model": model,
                "tools": tools or ["shell"],
            },
        },
    )


class TestAgentDataSheet:
    def test_schema_metadata(self):
        sheet = build_agent_data_sheet(_agent())
        assert sheet["schema_version"] == SCHEMA_VERSION
        assert sheet["regulation"] == REGULATION_REF
        assert sheet["status"] == "draft"

    def test_includes_required_sections(self):
        sheet = build_agent_data_sheet(_agent())
        for key in [
            "purpose_and_scope",
            "input_data",
            "output_data",
            "tool_access",
            "model_and_training_data",
            "quality_and_bias",
            "platform_controls",
            "observed_runtime_metrics",
        ]:
            assert key in sheet

    def test_observed_metrics_match_agent(self):
        sheet = build_agent_data_sheet(_agent(total=200, success=160))
        m = sheet["observed_runtime_metrics"]
        assert m["total_executions"] == 200
        assert m["success_count"] == 160
        assert m["observed_success_rate"] == 0.8

    def test_provider_overrides_used(self):
        sheet = build_agent_data_sheet(
            _agent(),
            {
                "representativeness": "Training set sampled across 27 EU countries",
                "known_gaps": ["< 1% representation of Baltic states"],
            },
        )
        quality = sheet["quality_and_bias"]
        assert "27 EU" in quality["relevance_and_representativeness"]
        assert quality["known_gaps"] == ["< 1% representation of Baltic states"]

    def test_placeholders_for_untouched_fields(self):
        sheet = build_agent_data_sheet(_agent())
        assert "[PROVIDER" in sheet["input_data"]["deployer_source_description"]
        assert "[PROVIDER" in sheet["quality_and_bias"]["bias_assessment_method"]

    def test_platform_controls_always_injected(self):
        sheet = build_agent_data_sheet(_agent())
        controls = sheet["platform_controls"]
        assert any("secret isolation" in c.lower() for c in controls)
        assert any("ephemeral" in c.lower() for c in controls)


class TestOrgInventory:
    def test_empty_org_returns_zero_counts(self):
        inv = build_org_data_inventory([])
        assert inv["agent_count"] == 0
        assert inv["total_executions_observed"] == 0

    def test_aggregates_domains_and_risk_classes(self):
        agents = [
            _agent(agent_id="a1", domain="fintech", risk_class="high"),
            _agent(agent_id="a2", domain="fintech", risk_class="limited"),
            _agent(agent_id="a3", domain="hr-tech", risk_class="limited"),
        ]
        inv = build_org_data_inventory(agents)
        assert inv["agent_count"] == 3
        assert inv["by_domain"]["fintech"] == 2
        assert inv["by_domain"]["hr-tech"] == 1
        assert inv["by_risk_class"]["limited"] == 2

    def test_aggregates_input_output_types(self):
        agents = [
            _agent(
                agent_id="a1",
                inputs=[{"name": "x", "type": "string"}, {"name": "y", "type": "number"}],
                outputs=[{"name": "z", "type": "json"}],
            ),
            _agent(
                agent_id="a2",
                inputs=[{"name": "x", "type": "string"}],
                outputs=[{"name": "z", "type": "markdown"}],
            ),
        ]
        inv = build_org_data_inventory(agents)
        assert inv["input_type_distribution"]["string"] == 2
        assert inv["input_type_distribution"]["number"] == 1
        assert inv["output_type_distribution"]["markdown"] == 1

    def test_aggregates_models_and_tools(self):
        agents = [
            _agent(agent_id="a1", model="anthropic/claude-sonnet-4-6", tools=["shell"]),
            _agent(agent_id="a2", model="anthropic/claude-sonnet-4-6", tools=["shell", "browser"]),
        ]
        inv = build_org_data_inventory(agents)
        assert inv["model_distribution"]["anthropic/claude-sonnet-4-6"] == 2
        assert inv["tool_distribution"]["shell"] == 2
        assert inv["tool_distribution"]["browser"] == 1

    def test_total_executions_summed(self):
        agents = [_agent(total=100), _agent(agent_id="a2", total=250)]
        inv = build_org_data_inventory(agents)
        assert inv["total_executions_observed"] == 350


class TestMarkdown:
    def test_renders_sections(self):
        md = agent_data_sheet_to_markdown(build_agent_data_sheet(_agent()))
        for heading in [
            "# Agent Data Sheet",
            "## Purpose and scope",
            "## Input data",
            "## Output data",
            "## Tool access",
            "## Model and training data",
            "## Quality, representativeness, bias (Art. 10)",
            "## Platform-level data controls",
            "## Observed runtime metrics",
        ]:
            assert heading in md

    def test_regulation_referenced(self):
        md = agent_data_sheet_to_markdown(build_agent_data_sheet(_agent()))
        assert REGULATION_REF in md
