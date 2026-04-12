"""Pipeline orchestration: advance steps after task completion."""

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


async def advance_pipeline(task_id: str, db: AsyncSession) -> None:
    """After a pipeline task completes, advance to next step or finalize."""
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

    # Task failed: cancel pipeline
    if task.status == "failed":
        pipeline.status = "failed"
        pipeline.current_step = task.step_index
        await db.commit()
        await _send_pipeline_callback(pipeline, "failed")
        return

    next_step_index = task.step_index + 1

    # Update captured totals
    if task.amount_captured_cents:
        pipeline.total_captured_cents += task.amount_captured_cents

    # Last step completed: finalize pipeline
    if next_step_index >= len(pipeline.steps):
        pipeline.status = "completed"
        pipeline.current_step = task.step_index
        await db.commit()
        await _send_pipeline_callback(pipeline, "completed")
        return

    # Get previous task's results_path
    exec_result = await db.execute(
        select(Execution)
        .where(Execution.task_id == task_id)
        .where(Execution.results_path.isnot(None))
        .order_by(Execution.created_at.desc())
        .limit(1)
    )
    execution = exec_result.scalar_one_or_none()
    results_path = execution.results_path if execution else None

    # Build next step's inputs from output mapping
    step_def = pipeline.steps[next_step_index]

    # Re-validate agent is still active before advancing
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

    next_inputs = resolve_inputs(results_path, step_def)

    # Timeout enforcement for next step
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

    pipeline.current_step = next_step_index
    pipeline.status = "running"
    await db.commit()

    log.info(
        f"Pipeline {pipeline.id} advanced to step {next_step_index}: "
        f"task {next_task.id} ({step_def['agent_id']})"
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
                    "total_steps": len(pipeline.steps),
                    "total_captured_cents": pipeline.total_captured_cents,
                },
            )
        log.info(f"Pipeline callback sent for {pipeline.id}")
    except Exception as e:
        log.warning(f"Pipeline callback failed for {pipeline.id}: {e}")
