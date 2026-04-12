"""Background dispatch worker: picks up pending tasks and executes them.

Runs as an asyncio task alongside the FastAPI server. Polls the database
for pending tasks and dispatches them via the AgentForgeDispatcher.
"""

import asyncio
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import select, update

from agentforge.billing import (
    authorize_task_payment,
    cancel_payment,
    capture_payment,
    is_billing_enabled,
)
from agentforge.config import settings
from agentforge.db import async_session
from agentforge.dispatch.compute import HetznerProvider
from agentforge.dispatch.dispatcher import AgentForgeDispatcher, SecretSet
from agentforge.dispatch.pipeline import advance_pipeline
from agentforge.models.agent import Agent
from agentforge.models.consumer import Consumer
from agentforge.models.execution import Execution
from agentforge.models.provider import Provider
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
            ssh_key_path=settings.hcloud_ssh_key_path or None,
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


async def _send_callback(
    task: Task,
    execution_id: str,
    status: str,
    elapsed: int | None = None,
) -> None:
    """Fire-and-forget POST to task.callback_url after completion."""
    if not task.callback_url:
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                task.callback_url,
                json={
                    "task_id": task.id,
                    "agent_id": task.agent_id,
                    "status": status,
                    "execution_id": execution_id,
                    "elapsed_seconds": elapsed,
                },
            )
        log.info(f"Callback sent for {task.id} to {task.callback_url}")
    except Exception as e:
        log.warning(f"Callback failed for {task.id}: {e}")


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

        # Authorize payment if billing is configured
        payment_intent_id = None
        if is_billing_enabled():
            agent_price = agent.card.get("pricing", {}).get("base_price_usd", 0)
            if agent_price > 0:
                try:
                    stripe_customer = None
                    cr = await db.execute(
                        select(Consumer).where(Consumer.id == task.consumer_id)
                    )
                    c = cr.scalar_one_or_none()
                    if c:
                        stripe_customer = c.stripe_customer_id

                    payment = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: authorize_task_payment(
                            task_id=task.id,
                            amount_usd=agent_price,
                            customer_id=stripe_customer,
                            description=f"Agent task: {agent.name}",
                        ),
                    )
                    payment_intent_id = payment.get("payment_intent_id")
                    task.payment_intent_id = payment_intent_id
                    task.payment_status = "authorized"
                    task.amount_authorized_cents = payment.get("amount_cents")
                except Exception as e:
                    log.error(f"Payment authorization failed for {task.id}: {e}")
                    task.status = "failed"
                    task.payment_status = "auth_failed"
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

    # Load consumer and provider secrets from DB
    consumer_keys: dict[str, str] = {}
    provider_keys: dict[str, str] = {}
    async with async_session() as db:
        consumer_result = await db.execute(
            select(Consumer).where(Consumer.id == task.consumer_id)
        )
        consumer = consumer_result.scalar_one_or_none()
        if consumer and consumer.secrets:
            consumer_keys = consumer.secrets

        provider_result = await db.execute(
            select(Provider).where(Provider.id == agent.provider_id)
        )
        provider = provider_result.scalar_one_or_none()
        if provider and provider.secrets:
            provider_keys = provider.secrets

    # Run dispatch in thread pool (blocking I/O: SSH, hcloud CLI)
    try:
        secrets = SecretSet(
            consumer_keys=consumer_keys or None,
            provider_keys=provider_keys or None,
        )

        # Extract task-level timeout from constraints
        task_constraints = task.constraints or {}
        task_timeout = task_constraints.get("timeout")

        dispatch_result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: dispatcher.dispatch(
                agent_card=agent.card,
                task_inputs=task.inputs or {},
                run_id=run_id,
                secrets=secrets,
                task_timeout=task_timeout,
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

            # Update agent trust metrics and recompute trust score
            from agentforge.trust import compute_trust_score

            agent_result = await db.execute(select(Agent).where(Agent.id == agent.id))
            agent_fresh = agent_result.scalar_one()

            new_total = agent_fresh.total_executions + 1
            new_success = agent_fresh.success_count + (1 if dispatch_result.success else 0)

            # Rolling average duration
            old_avg = float(agent_fresh.avg_duration_seconds or 0)
            elapsed = dispatch_result.elapsed_seconds or 0
            if old_avg == 0:
                new_avg = float(elapsed)
            else:
                new_avg = old_avg + (elapsed - old_avg) / new_total

            # Expected duration from agent card
            expected_duration = agent_fresh.card.get("runtime", {}).get(
                "estimated_duration_seconds", 300
            )

            trust = compute_trust_score(
                total_executions=new_total,
                success_count=new_success,
                avg_duration=new_avg,
                expected_duration=expected_duration,
            )

            await db.execute(
                update(Agent)
                .where(Agent.id == agent.id)
                .values(
                    total_executions=new_total,
                    success_count=new_success,
                    avg_duration_seconds=new_avg,
                    trust_score=trust,
                )
            )

            # Capture or cancel payment
            if payment_intent_id:
                if dispatch_result.success:
                    auth_cents = task.amount_authorized_cents or 0
                    cap_result = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: capture_payment(
                            task_id, payment_intent_id, auth_cents
                        ),
                    )
                    if cap_result["captured"]:
                        await db.execute(
                            update(Task)
                            .where(Task.id == task_id)
                            .values(
                                payment_status="captured",
                                amount_captured_cents=auth_cents,
                                platform_fee_cents=cap_result["fee_cents"],
                            )
                        )
                else:
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: cancel_payment(task_id, payment_intent_id),
                    )
                    await db.execute(
                        update(Task)
                        .where(Task.id == task_id)
                        .values(payment_status="cancelled")
                    )

            await db.commit()

            log.info(
                f"Task {task_id} completed: success={dispatch_result.success}, "
                f"trust={trust:.2f}"
            )

        # Pipeline advancement or standalone callback
        if task.pipeline_id:
            async with async_session() as db:
                await advance_pipeline(task_id, db)
        else:
            final_status = "completed" if dispatch_result.success else "failed"
            await _send_callback(
                task, run_id, final_status, dispatch_result.elapsed_seconds
            )

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
            # Cancel payment on dispatch failure
            if payment_intent_id:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: cancel_payment(task_id, payment_intent_id),
                )
                await db.execute(
                    update(Task)
                    .where(Task.id == task_id)
                    .values(payment_status="cancelled")
                )
            await db.commit()

        # Pipeline advancement or standalone callback on failure
        if task.pipeline_id:
            async with async_session() as db:
                await advance_pipeline(task_id, db)
        else:
            await _send_callback(task, run_id, "failed")


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
