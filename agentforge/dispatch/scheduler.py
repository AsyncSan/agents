"""Schedule worker: polls for due schedules and creates tasks.

Runs as a background asyncio task alongside the dispatch worker.
Checks every 60 seconds for schedules whose next_run_at has passed.
"""

import logging
import secrets
from datetime import datetime, timezone

from croniter import croniter
from sqlalchemy import select

from agentforge.db import async_session
from agentforge.models.agent import Agent
from agentforge.models.schedule import Schedule
from agentforge.models.task import Task

log = logging.getLogger("agentforge.scheduler")


def _generate_task_id() -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%d")
    suffix = secrets.token_hex(4)
    return f"tc-{now}-{suffix}"


async def process_due_schedules() -> int:
    """Check for schedules whose next_run_at has passed and create tasks.

    Returns the number of tasks created.
    """
    now = datetime.now(timezone.utc)
    created = 0

    async with async_session() as db:
        result = await db.execute(
            select(Schedule).where(
                Schedule.active.is_(True),
                Schedule.next_run_at.isnot(None),
                Schedule.next_run_at <= now.isoformat(),
            )
        )
        due_schedules = result.scalars().all()

        for schedule in due_schedules:
            # Verify agent still active
            agent_result = await db.execute(
                select(Agent).where(Agent.id == schedule.agent_id)
            )
            agent = agent_result.scalar_one_or_none()
            if not agent or agent.status != "active":
                log.warning(
                    f"Schedule {schedule.id}: agent {schedule.agent_id} inactive, pausing"
                )
                schedule.active = False
                continue

            # Create task from schedule template
            task = Task(
                id=_generate_task_id(),
                consumer_id=schedule.consumer_id,
                agent_id=schedule.agent_id,
                inputs=schedule.inputs,
                constraints=schedule.constraints,
                callback_url=schedule.callback_url,
                status="pending",
            )
            db.add(task)

            # Update schedule metadata
            cron = croniter(schedule.cron_expression, now)
            schedule.next_run_at = cron.get_next(datetime).isoformat()
            schedule.last_run_at = now.isoformat()
            schedule.total_runs = (schedule.total_runs or 0) + 1

            log.info(
                f"Schedule {schedule.id} fired: created task {task.id} "
                f"for agent {schedule.agent_id}, next run {schedule.next_run_at}"
            )
            created += 1

        if created > 0:
            await db.commit()

    return created


async def scheduler_loop(poll_interval: int = 60) -> None:
    """Continuously poll for due schedules.

    Runs as an asyncio background task. Default: every 60 seconds.
    """
    import asyncio

    log.info(f"Schedule worker started (poll every {poll_interval}s)")

    while True:
        try:
            created = await process_due_schedules()
            if created > 0:
                log.info(f"Scheduler created {created} tasks")
        except Exception as e:
            log.error(f"Scheduler error: {e}")

        await asyncio.sleep(poll_interval)
