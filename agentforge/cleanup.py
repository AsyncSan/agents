"""Background cleanup: prune old results and event logs.

Runs as an asyncio background task alongside the API server.

Retention policy is tied to EU AI Act Art. 19: high-risk AI systems must
keep automatic logs for at least 6 months (180 days). Defaults in
``config.py`` reflect that floor. Operators may extend via environment
variables but must not drop below 180 days for the event log.
"""

import asyncio
import logging
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.config import settings
from agentforge.db import async_session
from agentforge.models.event_log import EventLog
from agentforge.models.execution import Execution

log = logging.getLogger("agentforge.cleanup")

CLEANUP_INTERVAL = 3600  # run every hour
RESULTS_DIR = Path("results")


async def cleanup_old_results() -> int:
    """Delete result directories older than retention period.

    Returns number of directories removed.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.results_retention_days)
    removed = 0

    async with async_session() as db:
        # Find executions older than cutoff with results_path set
        result = await db.execute(
            select(Execution.id, Execution.results_path)
            .where(
                Execution.completed_at < cutoff,
                Execution.results_path.isnot(None),
            )
        )
        old_executions = result.all()

        for exec_id, results_path in old_executions:
            path = Path(results_path)
            if path.exists() and path.is_dir():
                try:
                    shutil.rmtree(path)
                    removed += 1
                    log.debug(f"Removed results: {path}")
                except OSError as e:
                    log.warning(f"Failed to remove {path}: {e}")

            # Clear results_path in DB (results no longer available)
            from sqlalchemy import update

            await db.execute(
                update(Execution)
                .where(Execution.id == exec_id)
                .values(results_path=None)
            )

        if removed > 0:
            await db.commit()
            log.info(
                f"Cleaned up {removed} result directories "
                f"(older than {settings.results_retention_days}d)"
            )

    return removed


AI_ACT_MIN_LOG_RETENTION_DAYS = 180


def enforce_ai_act_retention_floor() -> int:
    """Return the effective event log retention, floor-clamped to Art. 19.

    Art. 19 requires high-risk AI systems to retain automatic logs for at
    least 6 months. If configuration drops below that, we log a warning and
    use the floor.
    """
    configured = settings.event_log_retention_days
    if configured < AI_ACT_MIN_LOG_RETENTION_DAYS:
        log.warning(
            "event_log_retention_days=%d is below EU AI Act Art. 19 floor "
            "of %d days; enforcing the floor",
            configured,
            AI_ACT_MIN_LOG_RETENTION_DAYS,
        )
        return AI_ACT_MIN_LOG_RETENTION_DAYS
    return configured


async def cleanup_old_events(db: AsyncSession | None = None) -> int:
    """Delete event log entries older than retention period.

    Returns number of events deleted.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=enforce_ai_act_retention_floor())

    async def _run(session: AsyncSession) -> int:
        result = await session.execute(
            delete(EventLog)
            .where(EventLog.created_at < cutoff)
            .returning(EventLog.id)
        )
        deleted = len(result.all())
        if deleted > 0:
            await session.commit()
            log.info(
                f"Pruned {deleted} event log entries "
                f"(older than {settings.event_log_retention_days}d)"
            )
        return deleted

    if db:
        return await _run(db)

    async with async_session() as session:
        return await _run(session)


async def cleanup_orphan_result_dirs() -> int:
    """Remove result directories that have no matching execution record.

    Catches directories left behind by crashed workers.
    """
    if not RESULTS_DIR.exists():
        return 0

    removed = 0
    async with async_session() as db:
        # Get all known results_paths
        result = await db.execute(
            select(Execution.results_path).where(Execution.results_path.isnot(None))
        )
        known_paths = {row[0] for row in result.all()}

    for subdir in RESULTS_DIR.iterdir():
        if subdir.is_dir() and str(subdir) not in known_paths:
            # Check age first (only remove if older than 1 day)
            try:
                age = datetime.now() - datetime.fromtimestamp(subdir.stat().st_mtime)
                if age > timedelta(days=1):
                    shutil.rmtree(subdir)
                    removed += 1
                    log.debug(f"Removed orphan results: {subdir}")
            except OSError:
                pass

    if removed > 0:
        log.info(f"Cleaned up {removed} orphan result directories")
    return removed


async def cleanup_loop() -> None:
    """Background cleanup loop. Runs hourly."""
    log.info(
        f"Cleanup worker started "
        f"(results: {settings.results_retention_days}d, "
        f"events: {settings.event_log_retention_days}d)"
    )

    while True:
        try:
            await cleanup_old_results()
            await cleanup_old_events()
            await cleanup_orphan_result_dirs()
        except Exception as e:
            log.error(f"Cleanup loop error: {e}")

        await asyncio.sleep(CLEANUP_INTERVAL)
