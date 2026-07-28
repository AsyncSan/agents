"""Async webhook delivery with retry queue.

Decouples webhook delivery from the request/event path. Events are
enqueued and delivered in a background loop with exponential backoff.
Payload formatting for generic / Slack / Splunk HEC / Datadog /
Jira / Linear lives in ``agentforge.webhook_formatters``.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx
from sqlalchemy import update

from agentforge.models.webhook import Webhook
from agentforge.webhook_formatters import format_payload

log = logging.getLogger("agentforge.webhook_delivery")

MAX_RETRIES = 3
BASE_DELAY = 2  # seconds
DELIVERY_TIMEOUT = 10


@dataclass
class WebhookJob:
    webhook_id: str
    url: str
    secret: str
    body: dict
    event_type: str
    webhook_type: str = "generic"
    attempt: int = 0
    next_retry_at: float = 0.0


@dataclass
class WebhookQueue:
    """In-process async webhook delivery queue with retries."""

    _queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=10_000))
    _retry_queue: list[WebhookJob] = field(default_factory=list)
    _running: bool = False

    def enqueue(self, job: WebhookJob) -> None:
        """Add a webhook delivery job to the queue. Non-blocking, drops if full."""
        try:
            self._queue.put_nowait(job)
        except asyncio.QueueFull:
            log.warning(f"Webhook queue full, dropping delivery to {job.url}")

    async def run(self, get_session) -> None:
        """Main delivery loop. Call this as a background asyncio task."""
        self._running = True
        log.info("Webhook delivery worker started")

        while self._running:
            try:
                await self._process_retries(get_session)
                await self._process_queue(get_session)
            except Exception as e:
                log.error(f"Webhook delivery loop error: {e}")

            await asyncio.sleep(1)

    async def stop(self) -> None:
        self._running = False

    async def _process_queue(self, get_session) -> None:
        """Drain the main queue and attempt deliveries."""
        batch: list[WebhookJob] = []
        while not self._queue.empty() and len(batch) < 50:
            try:
                job = self._queue.get_nowait()
                batch.append(job)
            except asyncio.QueueEmpty:
                break

        if batch:
            await asyncio.gather(
                *[self._deliver(job, get_session) for job in batch],
                return_exceptions=True,
            )

    async def _process_retries(self, get_session) -> None:
        """Process retry queue, only jobs whose delay has elapsed."""
        now = asyncio.get_event_loop().time()
        ready = [j for j in self._retry_queue if j.next_retry_at <= now]
        self._retry_queue = [j for j in self._retry_queue if j.next_retry_at > now]

        if ready:
            await asyncio.gather(
                *[self._deliver(job, get_session) for job in ready],
                return_exceptions=True,
            )

    async def _deliver(self, job: WebhookJob, get_session) -> None:
        """Attempt to deliver a single webhook. Retries on failure."""
        try:
            body_bytes, headers = format_payload(
                job.webhook_type, job.body, job.event_type, job.secret
            )
        except ValueError as e:
            log.warning(
                f"Webhook {job.webhook_id} ({job.webhook_type}) formatter error: {e}"
            )
            self._schedule_retry(job, f"formatter: {e}")
            return

        try:
            async with httpx.AsyncClient(timeout=DELIVERY_TIMEOUT) as client:
                resp = await client.post(
                    job.url,
                    content=body_bytes,
                    headers=headers,
                )

            if resp.status_code < 400:
                # Success
                async with get_session() as db:
                    await db.execute(
                        update(Webhook)
                        .where(Webhook.id == job.webhook_id)
                        .values(
                            total_deliveries=Webhook.total_deliveries + 1,
                            last_delivery_at=datetime.now(timezone.utc),
                        )
                    )
                    await db.commit()
                log.debug(
                    f"Webhook delivered: {job.event_type} -> {job.url} "
                    f"(attempt {job.attempt + 1})"
                )
            else:
                # HTTP error, retry
                self._schedule_retry(job, f"HTTP {resp.status_code}")

        except Exception as e:
            self._schedule_retry(job, str(e))

    def _schedule_retry(self, job: WebhookJob, reason: str) -> None:
        """Schedule a retry with exponential backoff, or give up."""
        job.attempt += 1
        if job.attempt >= MAX_RETRIES:
            log.warning(
                f"Webhook delivery permanently failed after {MAX_RETRIES} attempts: "
                f"{job.url} ({reason})"
            )
            # Record failure asynchronously (best effort)
            asyncio.get_event_loop().create_task(
                self._record_failure(job)
            )
            return

        delay = BASE_DELAY * (2 ** job.attempt)  # 4s, 8s
        job.next_retry_at = asyncio.get_event_loop().time() + delay
        self._retry_queue.append(job)
        log.debug(
            f"Webhook retry scheduled: {job.url} "
            f"(attempt {job.attempt}/{MAX_RETRIES}, delay {delay}s, reason: {reason})"
        )

    async def _record_failure(self, job: WebhookJob) -> None:
        """Record permanent failure in DB."""
        try:
            from agentforge.db import async_session

            async with async_session() as db:
                await db.execute(
                    update(Webhook)
                    .where(Webhook.id == job.webhook_id)
                    .values(total_failures=Webhook.total_failures + 1)
                )
                await db.commit()
        except Exception:
            pass


# Global queue instance
webhook_queue = WebhookQueue()
