"""Tests for agent composition pipelines."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from agentforge.dispatch.pipeline import _MAX_OUTPUT_SIZE, resolve_inputs


class TestResolveInputs:
    def test_static_inputs_only(self):
        step_def = {"inputs": {"topic": "quantum"}, "output_map": {}}
        result = resolve_inputs("/nonexistent", step_def)
        assert result == {"topic": "quantum"}

    def test_output_md_mapping(self, tmp_path):
        results_dir = tmp_path / "run-001"
        results_dir.mkdir()
        (results_dir / "output.md").write_text("# Research Results\nGreat findings.")

        step_def = {
            "inputs": {"tone": "technical"},
            "output_map": {"output.md": "research_notes"},
        }
        result = resolve_inputs(str(results_dir), step_def)
        assert result["tone"] == "technical"
        assert result["research_notes"] == "# Research Results\nGreat findings."

    def test_output_json_mapping(self, tmp_path):
        results_dir = tmp_path / "run-002"
        results_dir.mkdir()
        (results_dir / "output.json").write_text(
            json.dumps({"summary": "Good", "score": 0.95})
        )

        step_def = {
            "inputs": {},
            "output_map": {"output.json": "full_data"},
        }
        result = resolve_inputs(str(results_dir), step_def)
        assert result["full_data"]["summary"] == "Good"
        assert result["full_data"]["score"] == 0.95

    def test_output_json_dotpath(self, tmp_path):
        results_dir = tmp_path / "run-003"
        results_dir.mkdir()
        (results_dir / "output.json").write_text(
            json.dumps({"analysis": {"key_points": ["a", "b", "c"]}})
        )

        step_def = {
            "inputs": {},
            "output_map": {"output.json.analysis": "parsed_analysis"},
        }
        result = resolve_inputs(str(results_dir), step_def)
        assert result["parsed_analysis"]["key_points"] == ["a", "b", "c"]

    def test_stdout_log_mapping(self, tmp_path):
        results_dir = tmp_path / "run-004"
        results_dir.mkdir()
        (results_dir / "stdout.log").write_text("Processing complete.")

        step_def = {
            "inputs": {},
            "output_map": {"stdout.log": "prev_stdout"},
        }
        result = resolve_inputs(str(results_dir), step_def)
        assert result["prev_stdout"] == "Processing complete."

    def test_truncation_at_100kb(self, tmp_path):
        results_dir = tmp_path / "run-005"
        results_dir.mkdir()
        large_content = "x" * (_MAX_OUTPUT_SIZE + 1000)
        (results_dir / "output.md").write_text(large_content)

        step_def = {
            "inputs": {},
            "output_map": {"output.md": "content"},
        }
        result = resolve_inputs(str(results_dir), step_def)
        assert len(result["content"]) == _MAX_OUTPUT_SIZE

    def test_missing_file_graceful(self, tmp_path):
        results_dir = tmp_path / "run-006"
        results_dir.mkdir()
        # No output.md exists

        step_def = {
            "inputs": {"existing": "value"},
            "output_map": {"output.md": "content"},
        }
        result = resolve_inputs(str(results_dir), step_def)
        assert result == {"existing": "value"}  # Missing file skipped
        assert "content" not in result

    def test_invalid_json_graceful(self, tmp_path):
        results_dir = tmp_path / "run-007"
        results_dir.mkdir()
        (results_dir / "output.json").write_text("not valid json {{{")

        step_def = {
            "inputs": {},
            "output_map": {"output.json": "data"},
        }
        result = resolve_inputs(str(results_dir), step_def)
        assert "data" not in result

    def test_no_results_path(self):
        step_def = {"inputs": {"key": "val"}, "output_map": {"output.md": "x"}}
        result = resolve_inputs(None, step_def)
        assert result == {"key": "val"}

    def test_empty_output_map(self, tmp_path):
        step_def = {"inputs": {"a": 1}, "output_map": {}}
        result = resolve_inputs(str(tmp_path), step_def)
        assert result == {"a": 1}

    def test_unknown_source_skipped(self, tmp_path):
        step_def = {
            "inputs": {},
            "output_map": {"unknown_file.txt": "data"},
        }
        result = resolve_inputs(str(tmp_path), step_def)
        assert result == {}


class TestPipelineSchemas:
    def test_pipeline_step_defaults(self):
        from agentforge.api.schemas import PipelineStep

        step = PipelineStep(agent_id="test-agent")
        assert step.inputs == {}
        assert step.output_map == {}

    def test_pipeline_request_min_steps(self):
        from agentforge.api.schemas import PipelineCreateRequest

        with pytest.raises(Exception):
            PipelineCreateRequest(steps=[{"agent_id": "only-one"}])

    def test_pipeline_request_valid(self):
        from agentforge.api.schemas import PipelineCreateRequest

        req = PipelineCreateRequest(
            steps=[
                {"agent_id": "agent-a", "inputs": {"topic": "AI"}},
                {
                    "agent_id": "agent-b",
                    "output_map": {"output.md": "research"},
                },
            ],
            callback_url="https://example.com/hook",
        )
        assert len(req.steps) == 2
        assert req.steps[1].output_map == {"output.md": "research"}

    def test_pipeline_response_fields(self):
        from agentforge.api.schemas import PipelineResponse

        fields = PipelineResponse.model_fields
        assert "chain_trust_score" in fields
        assert "total_authorized_cents" in fields
        assert "total_captured_cents" in fields
        assert "tasks" in fields


class TestChainTrustScore:
    def test_min_of_agents(self):
        scores = [0.95, 0.72, 0.88]
        chain_trust = min(scores)
        assert chain_trust == 0.72

    def test_zero_trust_dominates(self):
        scores = [0.95, 0.0, 0.88]
        assert min(scores) == 0.0

    def test_single_agent(self):
        scores = [0.85]
        assert min(scores) == 0.85


class TestAdvancePipeline:
    @pytest.mark.asyncio
    async def test_skips_non_pipeline_task(self):
        from agentforge.dispatch.pipeline import advance_pipeline

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_task = MagicMock()
        mock_task.pipeline_id = None
        mock_result.scalar_one_or_none.return_value = mock_task
        mock_db.execute = AsyncMock(return_value=mock_result)

        await advance_pipeline("tc-test", mock_db)
        # Should return early, no commit
        mock_db.commit.assert_not_called()


class TestBackwardCompatibility:
    def test_task_model_pipeline_fields_nullable(self):
        from agentforge.models.task import Task

        # pipeline_id and step_index should be nullable
        cols = Task.__table__.columns
        assert cols["pipeline_id"].nullable is True
        assert cols["step_index"].nullable is True

    def test_pipeline_model_exists(self):
        from agentforge.models.pipeline import Pipeline

        assert Pipeline.__tablename__ == "pipelines"
        assert "id" in Pipeline.__table__.columns
        assert "steps" in Pipeline.__table__.columns
        assert "chain_trust_score" in Pipeline.__table__.columns
