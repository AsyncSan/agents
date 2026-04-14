"""Pipeline orchestration: advance steps after task completion.

Supports both linear and parallel pipelines. Steps sharing the same
step_index run concurrently (fan-out). The pipeline advances when ALL
tasks at the current step_index have completed (fan-in).
"""

import json
import logging
import secrets
from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.models.agent import Agent
from agentforge.models.execution import Execution
from agentforge.models.pipeline import Pipeline
from agentforge.models.task import Task

log = logging.getLogger("agentforge.pipeline")

_MAX_OUTPUT_SIZE = 100 * 1024  # 100KB truncation limit


def _generate_task_id() -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%d")
    suffix = secrets.token_hex(4)
    return f"tc-{now}-{suffix}"


def evaluate_condition(condition: dict, context: dict) -> bool:
    """Evaluate a step condition against pipeline context.

    Returns True if the condition is met (step should run).
    """
    field = condition.get("field", "")
    op = condition.get("op", "eq")
    expected = condition.get("value")

    # Navigate dotpath: "results.severity" -> context["results"]["severity"]
    value = context
    for part in field.split("."):
        if isinstance(value, dict):
            value = value.get(part)
        else:
            value = None
            break

    if op == "exists":
        return value is not None
    if op == "eq":
        return value == expected
    if op == "ne":
        return value != expected
    if op == "gt":
        return value is not None and value > expected
    if op == "lt":
        return value is not None and value < expected
    if op == "gte":
        return value is not None and value >= expected
    if op == "lte":
        return value is not None and value <= expected
    if op == "in":
        return value in (expected or [])
    if op == "contains":
        return expected in (value or [])

    return False


def resolve_inputs(results_path: str, step_def: dict) -> dict:
    """Map previous task's output files to next task's input dict.

    Reads files from the filesystem at results_path and injects them
    into the input dict based on the step's output_map.
    """
    inputs = dict(step_def.get("inputs", {}))
    output_map = step_def.get("output_map", {})

    if not output_map or not results_path:
        return inputs

    results_dir = Path(results_path)

    for source, target_key in output_map.items():
        try:
            if source.startswith("output.json."):
                # Dotpath: "output.json.summary" -> data["summary"]
                field = source.split(".", 2)[2]
                data = json.loads(
                    (results_dir / "output.json").read_text(encoding="utf-8")
                )
                inputs[target_key] = data.get(field)
            elif source == "output.json":
                data = json.loads(
                    (results_dir / "output.json").read_text(encoding="utf-8")
                )
                inputs[target_key] = data
            elif source in ("output.md", "stdout.log", "stderr.log"):
                content = (results_dir / source).read_text(
                    encoding="utf-8", errors="replace"
                )
                if len(content) > _MAX_OUTPUT_SIZE:
                    log.warning(
                        f"Truncating {source} from {len(content)} to {_MAX_OUTPUT_SIZE} bytes"
                    )
                    content = content[:_MAX_OUTPUT_SIZE]
                inputs[target_key] = content
            else:
                log.warning(f"Unknown output_map source: {source}")
        except FileNotFoundError:
            log.warning(f"Output file not found: {results_dir / source}")
        except (json.JSONDecodeError, KeyError) as e:
            log.warning(f"Failed to parse {source}: {e}")

    return inputs


def resolve_parallel_inputs(
    parallel_results: dict[str, str | None],
    step_def: dict,
) -> dict:
    """Resolve inputs for a fan-in step from multiple parallel predecessors.

    parallel_results maps agent_id -> results_path for each parallel task.
    Output map keys can use "agent_id:output.md" syntax to pick a specific
    parallel task's output, or plain "output.md" to get the first available.
    """
    inputs = dict(step_def.get("inputs", {}))
    output_map = step_def.get("output_map", {})

    if not output_map:
        return inputs

    for source, target_key in output_map.items():
        if ":" in source:
            # Specific agent: "research-agent:output.md"
            agent_ref, file_source = source.split(":", 1)
            results_path = parallel_results.get(agent_ref)
            if results_path:
                partial = resolve_inputs(
                    results_path, {"output_map": {file_source: target_key}}
                )
                if target_key in partial:
                    inputs[target_key] = partial[target_key]
        else:
            # Take from first available parallel result
            for agent_id, results_path in parallel_results.items():
                if not results_path:
                    continue
                partial = resolve_inputs(
                    results_path, {"output_map": {source: target_key}}
                )
                if target_key in partial:
                    inputs[target_key] = partial[target_key]
                    break

    # Also inject parallel_outputs summary for agents that want all results
    inputs["_parallel_sources"] = list(parallel_results.keys())

    return inputs


async def advance_pipeline(task_id: str, db: AsyncSession) -> None:
    """After a pipeline task completes, advance to next step or finalize.

    For parallel pipelines: waits until ALL tasks at the current step_index
    have completed before advancing (fan-in).
    """
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task or not task.pipeline_id:
        return

    result = await db.execute(
        select(Pipeline).where(Pipeline.id == task.pipeline_id)
    )
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        return

    current_step_index = task.step_index

    # Task failed: cancel pipeline
    if task.status == "failed":
        pipeline.status = "failed"
        pipeline.current_step = current_step_index
        await db.commit()
        await _send_pipeline_callback(pipeline, "failed")
        return

    # Update captured totals
    if task.amount_captured_cents:
        pipeline.total_captured_cents += task.amount_captured_cents

    # Check if ALL tasks at this step_index are completed (fan-in)
    sibling_result = await db.execute(
        select(Task).where(
            Task.pipeline_id == pipeline.id,
            Task.step_index == current_step_index,
        )
    )
    sibling_tasks = sibling_result.scalars().all()

    pending_siblings = [
        t for t in sibling_tasks
        if t.status not in ("completed", "failed")
    ]
    if pending_siblings:
        # Other parallel tasks still running, wait for them
        await db.commit()
        log.debug(
            f"Pipeline {pipeline.id} step {current_step_index}: "
            f"{len(pending_siblings)} sibling tasks still running"
        )
        return

    # Check for any failed siblings
    failed_siblings = [t for t in sibling_tasks if t.status == "failed"]
    if failed_siblings:
        pipeline.status = "failed"
        pipeline.current_step = current_step_index
        await db.commit()
        await _send_pipeline_callback(pipeline, "failed")
        return

    # All tasks at this step completed. Find the next step_index.
    # Backward compat: old pipelines may not have step_index in JSONB
    for i, s in enumerate(pipeline.steps):
        if "step_index" not in s:
            s["step_index"] = i
    step_indices = sorted({s["step_index"] for s in pipeline.steps})
    current_pos = step_indices.index(current_step_index)

    # Last step completed: finalize pipeline
    if current_pos >= len(step_indices) - 1:
        pipeline.status = "completed"
        pipeline.current_step = current_step_index
        await db.commit()
        await _send_pipeline_callback(pipeline, "completed")
        return

    next_step_index = step_indices[current_pos + 1]

    # Gather results from all completed sibling tasks for fan-in
    is_parallel = len(sibling_tasks) > 1
    if is_parallel:
        parallel_results: dict[str, str | None] = {}
        for sib in sibling_tasks:
            exec_result = await db.execute(
                select(Execution)
                .where(Execution.task_id == sib.id)
                .where(Execution.results_path.isnot(None))
                .order_by(Execution.created_at.desc())
                .limit(1)
            )
            execution = exec_result.scalar_one_or_none()
            parallel_results[sib.agent_id] = (
                execution.results_path if execution else None
            )
    else:
        # Single predecessor
        exec_result = await db.execute(
            select(Execution)
            .where(Execution.task_id == task_id)
            .where(Execution.results_path.isnot(None))
            .order_by(Execution.created_at.desc())
            .limit(1)
        )
        execution = exec_result.scalar_one_or_none()
        single_results_path = execution.results_path if execution else None

    # Get all steps at the next step_index (could be multiple for fan-out)
    next_step_defs = [
        s for s in pipeline.steps if s["step_index"] == next_step_index
    ]

    # Evaluate conditions: filter out steps whose condition is not met
    ctx = dict(pipeline.context or {})
    eligible_steps = []
    for step_def in next_step_defs:
        cond = step_def.get("condition")
        if cond and not evaluate_condition(cond, ctx):
            log.info(
                f"Pipeline {pipeline.id} step {next_step_index}: "
                f"skipping {step_def['agent_id']} (condition not met: "
                f"{cond['field']} {cond['op']} {cond.get('value')})"
            )
            continue
        eligible_steps.append(step_def)

    # If all steps at this index are skipped, try to advance further
    if not eligible_steps:
        log.info(
            f"Pipeline {pipeline.id}: all steps at index {next_step_index} "
            f"skipped by conditions, advancing further"
        )
        # Check if there are more steps after this
        next_next_pos = step_indices.index(next_step_index) + 1
        if next_next_pos >= len(step_indices):
            # No more steps, pipeline is done
            pipeline.status = "completed"
            pipeline.current_step = next_step_index
            await db.commit()
            await _send_pipeline_callback(pipeline, "completed")
            return

        # Create a synthetic completed task to trigger next advancement
        pipeline.current_step = next_step_index
        await db.commit()
        # Recursively try the step after the skipped one
        # We simulate by creating a "skipped" marker task
        skip_task = Task(
            id=_generate_task_id(),
            consumer_id=pipeline.consumer_id,
            agent_id=next_step_defs[0]["agent_id"],
            inputs={"_skipped": True, "_reason": "condition not met"},
            pipeline_id=pipeline.id,
            step_index=next_step_index,
            status="completed",
        )
        db.add(skip_task)
        await db.commit()
        # Advance from the skipped step
        await advance_pipeline(skip_task.id, db)
        return

    created_count = 0
    for step_def in eligible_steps:
        # Re-validate agent is still active
        agent_result = await db.execute(
            select(Agent).where(Agent.id == step_def["agent_id"])
        )
        next_agent = agent_result.scalar_one_or_none()
        if not next_agent or next_agent.status != "active":
            pipeline.status = "failed"
            pipeline.current_step = next_step_index
            await db.commit()
            log.warning(
                f"Pipeline {pipeline.id} failed: agent {step_def['agent_id']} "
                f"no longer active at step {next_step_index}"
            )
            await _send_pipeline_callback(pipeline, "failed")
            return

        # Resolve inputs based on predecessor type
        if is_parallel:
            next_inputs = resolve_parallel_inputs(parallel_results, step_def)
        else:
            next_inputs = resolve_inputs(single_results_path, step_def)

        # Inject shared pipeline context
        if pipeline.context:
            next_inputs["_pipeline_context"] = dict(pipeline.context)

        task_timeout = step_def.get("constraints", {}).get("timeout")

        next_task = Task(
            id=_generate_task_id(),
            consumer_id=pipeline.consumer_id,
            agent_id=step_def["agent_id"],
            inputs=next_inputs,
            constraints={"timeout": task_timeout} if task_timeout else {},
            pipeline_id=pipeline.id,
            step_index=next_step_index,
            status="pending",
        )
        db.add(next_task)
        created_count += 1

    pipeline.current_step = next_step_index
    pipeline.status = "running"
    await db.commit()

    log.info(
        f"Pipeline {pipeline.id} advanced to step {next_step_index}: "
        f"{created_count} task(s) created"
    )


async def _send_pipeline_callback(pipeline: Pipeline, status: str) -> None:
    """Fire callback when pipeline completes or fails."""
    if not pipeline.callback_url:
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                pipeline.callback_url,
                json={
                    "pipeline_id": pipeline.id,
                    "status": status,
                    "current_step": pipeline.current_step,
                    "total_steps": pipeline.total_steps or len(pipeline.steps),
                    "total_captured_cents": pipeline.total_captured_cents,
                },
            )
        log.info(f"Pipeline callback sent for {pipeline.id}")
    except Exception as e:
        log.warning(f"Pipeline callback failed for {pipeline.id}: {e}")
