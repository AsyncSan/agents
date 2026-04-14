"""Tests for parallel pipeline steps (fan-out/fan-in) and conditional branching."""

import secrets as stdlib_secrets

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.dispatch.pipeline import evaluate_condition, resolve_parallel_inputs


def _uid():
    return stdlib_secrets.token_hex(6)


class TestParallelPipelineCreation:
    @pytest.mark.asyncio
    async def test_create_parallel_pipeline(
        self, client: AsyncClient, consumer_key, seed_agent
    ):
        """Steps with same step_index create parallel tasks."""
        api_key, _ = consumer_key
        agent_id = seed_agent["id"]

        resp = await client.post(
            "/v1/pipelines",
            headers={"X-API-Key": api_key},
            json={
                "steps": [
                    {"agent_id": agent_id, "inputs": {"topic": "research"}, "step_index": 0},
                    {"agent_id": agent_id, "inputs": {"topic": "analyze-A"}, "step_index": 1},
                    {"agent_id": agent_id, "inputs": {"topic": "analyze-B"}, "step_index": 1},
                    {"agent_id": agent_id, "inputs": {"topic": "summarize"}, "step_index": 2},
                ],
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["total_steps"] == 3  # 3 distinct step groups

        # Only step 0 tasks created initially
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["inputs"]["topic"] == "research"

    @pytest.mark.asyncio
    async def test_backward_compat_sequential(
        self, client: AsyncClient, consumer_key, seed_agent
    ):
        """Pipelines without step_index remain sequential."""
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/pipelines",
            headers={"X-API-Key": api_key},
            json={
                "steps": [
                    {"agent_id": seed_agent["id"], "inputs": {"x": "1"}},
                    {"agent_id": seed_agent["id"], "inputs": {"x": "2"}},
                ],
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["total_steps"] == 2
        # Steps should have sequential indices in JSONB
        assert data["steps"][0]["step_index"] == 0
        assert data["steps"][1]["step_index"] == 1

    @pytest.mark.asyncio
    async def test_parallel_creates_multiple_initial_tasks(
        self, client: AsyncClient, consumer_key, seed_agent
    ):
        """Parallel step at index 0 creates multiple initial tasks."""
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/pipelines",
            headers={"X-API-Key": api_key},
            json={
                "steps": [
                    {"agent_id": seed_agent["id"], "inputs": {"x": "A"}, "step_index": 0},
                    {"agent_id": seed_agent["id"], "inputs": {"x": "B"}, "step_index": 0},
                    {"agent_id": seed_agent["id"], "inputs": {"x": "merge"}, "step_index": 1},
                ],
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        # Two tasks created for step 0
        assert len(data["tasks"]) == 2
        task_inputs = sorted([t["inputs"]["x"] for t in data["tasks"]])
        assert task_inputs == ["A", "B"]

    @pytest.mark.asyncio
    async def test_parallel_budget_counts_all_steps(
        self, client: AsyncClient, consumer_key, seed_agent
    ):
        """Budget enforcement counts all parallel steps."""
        api_key, _ = consumer_key
        # 4 steps * $1 = $4, cap at $3
        resp = await client.post(
            "/v1/pipelines",
            headers={"X-API-Key": api_key},
            json={
                "steps": [
                    {"agent_id": seed_agent["id"], "step_index": 0},
                    {"agent_id": seed_agent["id"], "step_index": 1},
                    {"agent_id": seed_agent["id"], "step_index": 1},
                    {"agent_id": seed_agent["id"], "step_index": 2},
                ],
                "constraints": {"max_cost_usd": 3.00},
            },
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "budget_exceeded"


class TestParallelInputResolution:
    def test_resolve_parallel_inputs_specific_agent(self, tmp_path):
        """Fan-in can reference specific agent's output."""
        # Create mock results for two agents
        agent_a_dir = tmp_path / "agent-a"
        agent_a_dir.mkdir()
        (agent_a_dir / "output.md").write_text("Analysis A results")

        agent_b_dir = tmp_path / "agent-b"
        agent_b_dir.mkdir()
        (agent_b_dir / "output.md").write_text("Analysis B results")

        parallel_results = {
            "agent-a": str(agent_a_dir),
            "agent-b": str(agent_b_dir),
        }

        step_def = {
            "inputs": {"base": "context"},
            "output_map": {
                "agent-a:output.md": "analysis_a",
                "agent-b:output.md": "analysis_b",
            },
        }

        result = resolve_parallel_inputs(parallel_results, step_def)
        assert result["base"] == "context"
        assert result["analysis_a"] == "Analysis A results"
        assert result["analysis_b"] == "Analysis B results"
        assert "_parallel_sources" in result

    def test_resolve_parallel_inputs_first_available(self, tmp_path):
        """Fan-in without agent prefix takes first available."""
        agent_dir = tmp_path / "agent-x"
        agent_dir.mkdir()
        (agent_dir / "output.md").write_text("First result")

        parallel_results = {
            "agent-x": str(agent_dir),
            "agent-y": None,  # no results
        }

        step_def = {"output_map": {"output.md": "text"}}

        result = resolve_parallel_inputs(parallel_results, step_def)
        assert result["text"] == "First result"

    def test_resolve_parallel_inputs_json_dotpath(self, tmp_path):
        """Fan-in with agent-specific JSON dotpath."""
        agent_dir = tmp_path / "analyzer"
        agent_dir.mkdir()
        (agent_dir / "output.json").write_text('{"score": 0.95, "label": "safe"}')

        parallel_results = {"analyzer": str(agent_dir)}
        step_def = {
            "output_map": {"analyzer:output.json.score": "confidence"},
        }

        result = resolve_parallel_inputs(parallel_results, step_def)
        assert result["confidence"] == 0.95


class TestFanInAdvancement:
    @pytest.mark.asyncio
    async def test_fan_in_waits_for_all_siblings(
        self, client: AsyncClient, consumer_key, seed_agent, db_session: AsyncSession
    ):
        """Pipeline doesn't advance until all parallel tasks complete."""
        api_key, _ = consumer_key

        # Create parallel pipeline
        resp = await client.post(
            "/v1/pipelines",
            headers={"X-API-Key": api_key},
            json={
                "steps": [
                    {"agent_id": seed_agent["id"], "inputs": {"x": "A"}, "step_index": 0},
                    {"agent_id": seed_agent["id"], "inputs": {"x": "B"}, "step_index": 0},
                    {"agent_id": seed_agent["id"], "inputs": {"x": "merge"}, "step_index": 1},
                ],
            },
        )
        pipeline_id = resp.json()["id"]
        tasks = resp.json()["tasks"]
        assert len(tasks) == 2

        # Complete only one of the parallel tasks
        from agentforge.models.task import Task

        task_a = await db_session.get(Task, tasks[0]["id"])
        task_a.status = "completed"
        await db_session.commit()

        # Try to advance: should NOT create step 1 tasks yet
        from agentforge.dispatch.pipeline import advance_pipeline

        await advance_pipeline(tasks[0]["id"], db_session)

        # Check pipeline still at step 0
        from agentforge.models.pipeline import Pipeline

        pipeline = await db_session.get(Pipeline, pipeline_id)
        assert pipeline.current_step == 0

        # Now complete the second task
        task_b = await db_session.get(Task, tasks[1]["id"])
        task_b.status = "completed"
        await db_session.commit()

        await advance_pipeline(tasks[1]["id"], db_session)

        # Pipeline should have advanced to step 1
        await db_session.refresh(pipeline)
        assert pipeline.current_step == 1
        assert pipeline.status == "running"

        # Step 1 task should exist
        result = await db_session.execute(
            select(Task).where(
                Task.pipeline_id == pipeline_id,
                Task.step_index == 1,
            )
        )
        step1_tasks = result.scalars().all()
        assert len(step1_tasks) == 1
        assert step1_tasks[0].inputs["x"] == "merge"


class TestPipelineContext:
    @pytest.mark.asyncio
    async def test_read_empty_context(
        self, client: AsyncClient, consumer_key, seed_agent
    ):
        """New pipeline has empty context."""
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/pipelines",
            headers={"X-API-Key": api_key},
            json={
                "steps": [
                    {"agent_id": seed_agent["id"], "inputs": {"x": "1"}},
                    {"agent_id": seed_agent["id"]},
                ],
            },
        )
        pipeline_id = resp.json()["id"]

        ctx_resp = await client.get(
            f"/v1/pipelines/{pipeline_id}/context",
            headers={"X-API-Key": api_key},
        )
        assert ctx_resp.status_code == 200
        assert ctx_resp.json() == {}

    @pytest.mark.asyncio
    async def test_write_and_read_context(
        self, client: AsyncClient, consumer_key, seed_agent
    ):
        """Context can be written and read back."""
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/pipelines",
            headers={"X-API-Key": api_key},
            json={
                "steps": [
                    {"agent_id": seed_agent["id"], "inputs": {"x": "1"}},
                    {"agent_id": seed_agent["id"]},
                ],
            },
        )
        pipeline_id = resp.json()["id"]

        # Write context
        put_resp = await client.put(
            f"/v1/pipelines/{pipeline_id}/context",
            headers={"X-API-Key": api_key},
            json={"findings": ["vuln-1", "vuln-2"], "severity": "high"},
        )
        assert put_resp.status_code == 200
        assert put_resp.json()["severity"] == "high"

        # Read back
        ctx_resp = await client.get(
            f"/v1/pipelines/{pipeline_id}/context",
            headers={"X-API-Key": api_key},
        )
        assert ctx_resp.json()["findings"] == ["vuln-1", "vuln-2"]

    @pytest.mark.asyncio
    async def test_context_merge_not_replace(
        self, client: AsyncClient, consumer_key, seed_agent
    ):
        """PUT merges keys, doesn't replace entire context."""
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/pipelines",
            headers={"X-API-Key": api_key},
            json={
                "steps": [
                    {"agent_id": seed_agent["id"], "inputs": {"x": "1"}},
                    {"agent_id": seed_agent["id"]},
                ],
            },
        )
        pipeline_id = resp.json()["id"]

        # First write
        await client.put(
            f"/v1/pipelines/{pipeline_id}/context",
            headers={"X-API-Key": api_key},
            json={"step1_result": "done"},
        )

        # Second write (should merge, not replace)
        await client.put(
            f"/v1/pipelines/{pipeline_id}/context",
            headers={"X-API-Key": api_key},
            json={"step2_result": "also done"},
        )

        ctx_resp = await client.get(
            f"/v1/pipelines/{pipeline_id}/context",
            headers={"X-API-Key": api_key},
        )
        ctx = ctx_resp.json()
        assert ctx["step1_result"] == "done"
        assert ctx["step2_result"] == "also done"

    @pytest.mark.asyncio
    async def test_context_delete_key(
        self, client: AsyncClient, consumer_key, seed_agent
    ):
        """Setting a key to null removes it from context."""
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/pipelines",
            headers={"X-API-Key": api_key},
            json={
                "steps": [
                    {"agent_id": seed_agent["id"], "inputs": {"x": "1"}},
                    {"agent_id": seed_agent["id"]},
                ],
            },
        )
        pipeline_id = resp.json()["id"]

        await client.put(
            f"/v1/pipelines/{pipeline_id}/context",
            headers={"X-API-Key": api_key},
            json={"temp": "value", "keep": "this"},
        )

        await client.put(
            f"/v1/pipelines/{pipeline_id}/context",
            headers={"X-API-Key": api_key},
            json={"temp": None},
        )

        ctx_resp = await client.get(
            f"/v1/pipelines/{pipeline_id}/context",
            headers={"X-API-Key": api_key},
        )
        ctx = ctx_resp.json()
        assert "temp" not in ctx
        assert ctx["keep"] == "this"

    @pytest.mark.asyncio
    async def test_context_in_pipeline_response(
        self, client: AsyncClient, consumer_key, seed_agent
    ):
        """Pipeline response includes context."""
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/pipelines",
            headers={"X-API-Key": api_key},
            json={
                "steps": [
                    {"agent_id": seed_agent["id"], "inputs": {"x": "1"}},
                    {"agent_id": seed_agent["id"]},
                ],
            },
        )
        pipeline_id = resp.json()["id"]

        await client.put(
            f"/v1/pipelines/{pipeline_id}/context",
            headers={"X-API-Key": api_key},
            json={"shared_data": 42},
        )

        get_resp = await client.get(
            f"/v1/pipelines/{pipeline_id}",
            headers={"X-API-Key": api_key},
        )
        assert get_resp.json()["context"]["shared_data"] == 42


class TestConditionEvaluation:
    def test_eq(self):
        cond = {"field": "status", "op": "eq", "value": "critical"}
        assert evaluate_condition(cond, {"status": "critical"})
        assert not evaluate_condition(cond, {"status": "low"})

    def test_ne(self):
        assert evaluate_condition({"field": "x", "op": "ne", "value": 0}, {"x": 5})
        assert not evaluate_condition({"field": "x", "op": "ne", "value": 5}, {"x": 5})

    def test_gt_lt(self):
        assert evaluate_condition({"field": "score", "op": "gt", "value": 0.5}, {"score": 0.8})
        assert not evaluate_condition({"field": "score", "op": "gt", "value": 0.5}, {"score": 0.3})
        assert evaluate_condition({"field": "count", "op": "lt", "value": 10}, {"count": 5})

    def test_gte_lte(self):
        assert evaluate_condition({"field": "v", "op": "gte", "value": 5}, {"v": 5})
        assert evaluate_condition({"field": "v", "op": "lte", "value": 5}, {"v": 5})

    def test_in(self):
        assert evaluate_condition(
            {"field": "severity", "op": "in", "value": ["critical", "high"]},
            {"severity": "critical"},
        )
        assert not evaluate_condition(
            {"field": "severity", "op": "in", "value": ["critical", "high"]},
            {"severity": "low"},
        )

    def test_contains(self):
        assert evaluate_condition(
            {"field": "tags", "op": "contains", "value": "security"},
            {"tags": ["security", "audit"]},
        )

    def test_exists(self):
        assert evaluate_condition({"field": "findings", "op": "exists"}, {"findings": [1, 2]})
        assert not evaluate_condition({"field": "findings", "op": "exists"}, {})

    def test_dotpath(self):
        """Condition can reference nested context fields."""
        ctx = {"results": {"severity": "critical", "count": 5}}
        cond_sev = {"field": "results.severity", "op": "eq", "value": "critical"}
        assert evaluate_condition(cond_sev, ctx)
        cond_cnt = {"field": "results.count", "op": "gt", "value": 3}
        assert evaluate_condition(cond_cnt, ctx)

    def test_missing_field_returns_false(self):
        assert not evaluate_condition({"field": "missing", "op": "eq", "value": "x"}, {})
        assert not evaluate_condition({"field": "missing", "op": "gt", "value": 0}, {})


class TestConditionalBranching:
    @pytest.mark.asyncio
    async def test_create_pipeline_with_conditions(
        self, client: AsyncClient, consumer_key, seed_agent
    ):
        """Pipeline accepts steps with conditions."""
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/pipelines",
            headers={"X-API-Key": api_key},
            json={
                "steps": [
                    {"agent_id": seed_agent["id"], "inputs": {"x": "scan"}, "step_index": 0},
                    {
                        "agent_id": seed_agent["id"],
                        "inputs": {"x": "deep-scan"},
                        "step_index": 1,
                        "condition": {"field": "severity", "op": "eq", "value": "critical"},
                    },
                    {
                        "agent_id": seed_agent["id"],
                        "inputs": {"x": "report"},
                        "step_index": 2,
                    },
                ],
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["total_steps"] == 3
        # Condition should be serialized in steps JSONB
        assert data["steps"][1].get("condition") is not None
        assert data["steps"][1]["condition"]["op"] == "eq"

    @pytest.mark.asyncio
    async def test_condition_skips_step(
        self, client: AsyncClient, consumer_key, seed_agent, db_session: AsyncSession
    ):
        """Step with unmet condition is skipped, pipeline advances past it."""
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/pipelines",
            headers={"X-API-Key": api_key},
            json={
                "steps": [
                    {"agent_id": seed_agent["id"], "inputs": {"x": "scan"}, "step_index": 0},
                    {
                        "agent_id": seed_agent["id"],
                        "inputs": {"x": "deep-scan"},
                        "step_index": 1,
                        "condition": {"field": "severity", "op": "eq", "value": "critical"},
                    },
                    {"agent_id": seed_agent["id"], "inputs": {"x": "report"}, "step_index": 2},
                ],
            },
        )
        pipeline_id = resp.json()["id"]
        task0_id = resp.json()["tasks"][0]["id"]

        # Set context: severity is LOW (not critical)
        await client.put(
            f"/v1/pipelines/{pipeline_id}/context",
            headers={"X-API-Key": api_key},
            json={"severity": "low"},
        )

        # Complete step 0
        from agentforge.models.task import Task

        task0 = await db_session.get(Task, task0_id)
        task0.status = "completed"
        await db_session.commit()

        from agentforge.dispatch.pipeline import advance_pipeline

        await advance_pipeline(task0_id, db_session)

        # Step 1 should be skipped (condition not met), pipeline should jump to step 2
        from agentforge.models.pipeline import Pipeline

        pipeline = await db_session.get(Pipeline, pipeline_id)
        assert pipeline.current_step == 2
        assert pipeline.status == "running"

        # Step 2 task should exist
        result = await db_session.execute(
            select(Task).where(
                Task.pipeline_id == pipeline_id,
                Task.step_index == 2,
            )
        )
        step2_tasks = result.scalars().all()
        assert len(step2_tasks) == 1
        assert step2_tasks[0].inputs["x"] == "report"

    @pytest.mark.asyncio
    async def test_condition_met_runs_step(
        self, client: AsyncClient, consumer_key, seed_agent, db_session: AsyncSession
    ):
        """Step with met condition runs normally."""
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/pipelines",
            headers={"X-API-Key": api_key},
            json={
                "steps": [
                    {"agent_id": seed_agent["id"], "inputs": {"x": "scan"}, "step_index": 0},
                    {
                        "agent_id": seed_agent["id"],
                        "inputs": {"x": "deep-scan"},
                        "step_index": 1,
                        "condition": {"field": "severity", "op": "eq", "value": "critical"},
                    },
                    {"agent_id": seed_agent["id"], "inputs": {"x": "report"}, "step_index": 2},
                ],
            },
        )
        pipeline_id = resp.json()["id"]
        task0_id = resp.json()["tasks"][0]["id"]

        # Set context: severity IS critical
        await client.put(
            f"/v1/pipelines/{pipeline_id}/context",
            headers={"X-API-Key": api_key},
            json={"severity": "critical"},
        )

        # Complete step 0
        from agentforge.models.task import Task

        task0 = await db_session.get(Task, task0_id)
        task0.status = "completed"
        await db_session.commit()

        from agentforge.dispatch.pipeline import advance_pipeline

        await advance_pipeline(task0_id, db_session)

        # Step 1 should run (condition met)
        from agentforge.models.pipeline import Pipeline

        pipeline = await db_session.get(Pipeline, pipeline_id)
        assert pipeline.current_step == 1
        assert pipeline.status == "running"

        result = await db_session.execute(
            select(Task).where(
                Task.pipeline_id == pipeline_id,
                Task.step_index == 1,
            )
        )
        step1_tasks = result.scalars().all()
        assert len(step1_tasks) == 1
        assert step1_tasks[0].inputs["x"] == "deep-scan"
