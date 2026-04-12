"""Event emission: log events and deliver to webhook subscribers.

Events are persisted to the event_log table and delivered asynchronously
to matching webhook subscribers via HMAC-signed HTTP POST.
"""

import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.models.event_log import EventLog
from agentforge.models.webhook import Webhook

log = logging.getLogger("agentforge.events")

# All valid event types
EVENT_TYPES = [
    "agent.created",
    "agent.updated",
    "agent.deleted",
    "task.created",
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
    """Log an event and optionally deliver to webhook subscribers."""
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
        await _deliver_to_subscribers(db, event)

    return event


async def _deliver_to_subscribers(db: AsyncSession, event: EventLog) -> None:
    """Find matching webhooks and deliver the event payload."""
    result = await db.execute(
        select(Webhook).where(
            Webhook.active.is_(True),
        )
    )
    webhooks = result.scalars().all()

    for wh in webhooks:
        if not _event_matches(event.event_type, wh.event_types):
            continue

        # Build payload
        body = {
            "event_id": str(event.id),
            "event_type": event.event_type,
            "resource_type": event.resource_type,
            "resource_id": event.resource_id,
            "payload": event.payload,
            "timestamp": event.created_at.isoformat(),
        }
        body_bytes = json.dumps(body, default=str).encode()

        # HMAC signature
        signature = hmac.new(
            wh.secret.encode(), body_bytes, hashlib.sha256
        ).hexdigest()

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    wh.url,
                    content=body_bytes,
                    headers={
                        "Content-Type": "application/json",
                        "X-AgentForge-Signature": f"sha256={signature}",
                        "X-AgentForge-Event": event.event_type,
                    },
                )
            await db.execute(
                update(Webhook)
                .where(Webhook.id == wh.id)
                .values(
                    total_deliveries=Webhook.total_deliveries + 1,
                    last_delivery_at=datetime.now(timezone.utc),
                )
            )
            log.debug(f"Webhook delivered: {event.event_type} -> {wh.url}")
        except Exception as e:
            await db.execute(
                update(Webhook)
                .where(Webhook.id == wh.id)
                .values(total_failures=Webhook.total_failures + 1)
            )
            log.warning(f"Webhook delivery failed: {wh.url}: {e}")


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
