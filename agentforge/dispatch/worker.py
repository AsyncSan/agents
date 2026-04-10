"""Background dispatch worker: picks up pending tasks and executes them.

Runs as an asyncio task alongside the FastAPI server. Polls the database
for pending tasks and dispatches them via the AgentForgeDispatcher.
"""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select, update

from agentforge.config import settings
from agentforge.db import async_session
from agentforge.dispatch.compute import HetznerProvider
from agentforge.dispatch.dispatcher import AgentForgeDispatcher, SecretSet
from agentforge.models.agent import Agent
from agentforge.models.execution import Execution
from agentforge.models.task import Task

log = logging.getLogger("agentforge.worker")

# Singleton dispatcher (initialized lazily)
_dispatcher: AgentForgeDispatcher | None = None


def get_dispatcher() -> AgentForgeDispatcher:
    global _dispatcher
    if _dispatcher is None:
        provider = HetznerProvider(
            hcloud_token=settings.hcloud_token,
            ssh_key_name=settings.hcloud_ssh_key_name,
            network_name=settings.hcloud_network_name,
            firewall_name=settings.hcloud_firewall_name,
            location=settings.hcloud_location,
            default_server_type=settings.hcloud_default_server_type,
            snapshots={
                "base": settings.snapshot_base,
                "gui": settings.snapshot_gui,
                "gui-x86": settings.snapshot_gui_x86,
            },
        )
        _dispatcher = AgentForgeDispatcher(compute=provider, results_dir="results")
    return _dispatcher


async def process_task(task_id: str) -> None:
    """Process a single pending task: dispatch to ephemeral compute."""
    dispatcher = get_dispatcher()

    async with async_session() as db:
        # Load task + agent
        result = await db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if not task or task.status != "pending":
            return

        result = await db.execute(select(Agent).where(Agent.id == task.agent_id))
        agent = result.scalar_one_or_none()
        if not agent:
            task.status = "failed"
            await db.commit()
            return

        # Mark as dispatching
        task.status = "dispatching"
        await db.commit()

        # Create execution record
        run_id = dispatcher.generate_run_id(agent.id)
        execution = Execution(
            id=run_id,
            task_id=task.id,
            status="provisioning",
            started_at=datetime.now(timezone.utc),
        )
        db.add(execution)
        await db.commit()

    # Run dispatch in thread pool (blocking I/O: SSH, hcloud CLI)
    try:
        # Build secrets from platform config
        # In production, these come from a vault per-consumer and per-provider
        secrets = SecretSet(api_keys={})
        if settings.hcloud_token:
            # For now, use platform-level API keys
            # TODO: Per-consumer and per-provider secret isolation
            pass

        dispatch_result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: dispatcher.dispatch(
                agent_card=agent.card,
                task_inputs=task.inputs or {},
                run_id=run_id,
                secrets=secrets,
            ),
        )

        # Update execution + task in DB
        async with async_session() as db:
            await db.execute(
                update(Execution)
                .where(Execution.id == run_id)
                .values(
                    status="completed" if dispatch_result.success else "failed",
                    completed_at=datetime.now(timezone.utc),
                    elapsed_seconds=dispatch_result.elapsed_seconds,
                    exit_code=dispatch_result.exit_code,
                    server_id=dispatch_result.server.id if dispatch_result.server else None,
                    server_ip=dispatch_result.server.ip if dispatch_result.server else None,
                    metrics=dispatch_result.metrics,
                    results_path=dispatch_result.results_path,
                )
            )
            await db.execute(
                update(Task)
                .where(Task.id == task_id)
                .values(status="completed" if dispatch_result.success else "failed")
            )

            # Update agent trust metrics
            if dispatch_result.success:
                await db.execute(
                    update(Agent)
                    .where(Agent.id == agent.id)
                    .values(
                        total_executions=Agent.total_executions + 1,
                        success_count=Agent.success_count + 1,
                    )
                )
            else:
                await db.execute(
                    update(Agent)
                    .where(Agent.id == agent.id)
                    .values(total_executions=Agent.total_executions + 1)
                )

            await db.commit()
            log.info(f"Task {task_id} completed: success={dispatch_result.success}")

    except Exception as e:
        log.error(f"Task {task_id} dispatch failed: {e}")
        async with async_session() as db:
            await db.execute(
                update(Task).where(Task.id == task_id).values(status="failed")
            )
            await db.execute(
                update(Execution)
                .where(Execution.id == run_id)
                .values(status="failed", completed_at=datetime.now(timezone.utc))
            )
            await db.commit()


async def dispatch_worker_loop(poll_interval: int = 5) -> None:
    """Continuously poll for pending tasks and dispatch them.

    Runs as an asyncio background task. Respects max_concurrent_agents limit.
    """
    max_c = settings.max_concurrent_agents
    log.info(f"Dispatch worker started (poll every {poll_interval}s, max concurrent: {max_c})")
    active_tasks: set[str] = set()

    while True:
        try:
            # Check for pending tasks
            async with async_session() as db:
                result = await db.execute(
                    select(Task)
                    .where(Task.status == "pending")
                    .order_by(Task.created_at.asc())
                    .limit(settings.max_concurrent_agents - len(active_tasks))
                )
                pending = result.scalars().all()

            for task in pending:
                if task.id in active_tasks:
                    continue
                if len(active_tasks) >= settings.max_concurrent_agents:
                    break

                active_tasks.add(task.id)
                log.info(f"Picking up task {task.id} (active: {len(active_tasks)})")

                # Launch dispatch as background coroutine
                asyncio.create_task(_run_and_cleanup(task.id, active_tasks))

        except Exception as e:
            log.error(f"Worker loop error: {e}")

        await asyncio.sleep(poll_interval)


async def _run_and_cleanup(task_id: str, active_tasks: set[str]) -> None:
    """Run task dispatch and remove from active set when done."""
    try:
        await process_task(task_id)
    finally:
        active_tasks.discard(task_id)
