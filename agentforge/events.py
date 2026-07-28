"""Event emission: log events and deliver to webhook subscribers.

Events are persisted to the event_log table and delivered asynchronously
via the webhook delivery queue (non-blocking, with retries).
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.models.event_log import EventLog
from agentforge.models.webhook import Webhook
from agentforge.webhook_delivery import WebhookJob, webhook_queue

log = logging.getLogger("agentforge.events")

# All valid event types
EVENT_TYPES = [
    "agent.created",
    "agent.updated",
    "agent.deleted",
    "task.created",
    "task.awaiting_approval",
    "task.approved",
    "task.dispatching",
    "task.completed",
    "task.failed",
    "execution.started",
    "execution.completed",
    "execution.failed",
    "pipeline.created",
    "pipeline.completed",
    "pipeline.failed",
    "payment.authorized",
    "payment.captured",
    "payment.cancelled",
    "rating.created",
    "schedule.created",
    "schedule.deleted",
    "schedule.fired",
    "webhook.created",
    "webhook.deleted",
    "webhook.test",
]


async def emit_event(
    db: AsyncSession,
    event_type: str,
    actor_id: str | None = None,
    actor_role: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    payload: dict | None = None,
    deliver: bool = True,
) -> EventLog:
    """Log an event and enqueue webhook deliveries (non-blocking)."""
    event = EventLog(
        id=uuid.uuid4(),
        event_type=event_type,
        actor_id=str(actor_id) if actor_id else None,
        actor_role=actor_role,
        resource_type=resource_type,
        resource_id=resource_id,
        payload=payload,
        created_at=datetime.now(timezone.utc),
    )
    db.add(event)
    await db.flush()

    if deliver:
        await _enqueue_deliveries(db, event)

    return event


async def _enqueue_deliveries(db: AsyncSession, event: EventLog) -> None:
    """Find matching webhooks and enqueue delivery jobs (non-blocking)."""
    result = await db.execute(
        select(Webhook).where(Webhook.active.is_(True))
    )
    webhooks = result.scalars().all()

    body = {
        "event_id": str(event.id),
        "event_type": event.event_type,
        "resource_type": event.resource_type,
        "resource_id": event.resource_id,
        "payload": event.payload,
        "timestamp": event.created_at.isoformat(),
    }

    for wh in webhooks:
        if not _event_matches(event.event_type, wh.event_types):
            continue

        webhook_queue.enqueue(
            WebhookJob(
                webhook_id=str(wh.id),
                url=wh.url,
                secret=wh.secret,
                body=body,
                event_type=event.event_type,
                webhook_type=getattr(wh, "webhook_type", "generic") or "generic",
            )
        )


def _event_matches(event_type: str, subscribed: list[str]) -> bool:
    """Check if event_type matches any subscription pattern."""
    for pattern in subscribed:
        if pattern == "*":
            return True
        if pattern == event_type:
            return True
        # Wildcard prefix: "task.*" matches "task.completed"
        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            if event_type.startswith(prefix + "."):
                return True
    return False
