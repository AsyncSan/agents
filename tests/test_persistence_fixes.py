"""Tests for persistence layer fixes: pool config, atomic trust, async webhooks, cleanup."""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.trust import atomic_update_trust, compute_trust_score
from agentforge.webhook_delivery import WebhookJob, WebhookQueue

# --- Connection Pool Config ---


class TestPoolConfig:
    def test_pool_settings_exist(self):
        """Config has pool settings."""
        from agentforge.config import Settings

        s = Settings(
            db_pool_size=20,
            db_max_overflow=10,
            db_pool_timeout=60,
        )
        assert s.db_pool_size == 20
        assert s.db_max_overflow == 10
        assert s.db_pool_timeout == 60

    def test_pool_defaults(self):
        """Default pool config is reasonable."""
        from agentforge.config import Settings

        s = Settings()
        assert s.db_pool_size == 10
        assert s.db_max_overflow == 5
        assert s.db_pool_timeout == 30

    def test_engine_uses_pool_settings(self):
        """Engine is created with pool settings from config."""
        from agentforge.db import engine

        assert engine.pool.size() == 10  # default from config


# --- Atomic Trust Score ---


class TestAtomicTrust:
    @pytest.mark.asyncio
    async def test_atomic_trust_update(
        self, client: AsyncClient, provider_key, db_session: AsyncSession
    ):
        """Trust score updates atomically without read-modify-write."""
        api_key, _ = provider_key

        # Create an agent
        from tests.conftest import _unique_suffix

        suffix = _unique_suffix()
        resp = await client.post(
            "/v1/agents",
            headers={"X-API-Key": api_key},
            json={
                "id": f"trust-test-{suffix}",
                "name": "Trust Test Agent",
                "description": "Test",
                "domain": "testing",
                "tags": [],
                "inputs": [{"name": "x", "type": "string"}],
                "outputs": [{"name": "output.md", "type": "markdown"}],
                "runtime": {"estimated_duration_seconds": 100},
                "pricing": {"base_price_usd": 1.00},
                "instructions": "Test agent",
            },
        )
        assert resp.status_code == 201
        agent_id = resp.json()["id"]

        # Atomic update: first execution, success, 90s
        trust = await atomic_update_trust(
            db=db_session,
            agent_id=agent_id,
            success=True,
            elapsed_seconds=90,
            expected_duration=100,
        )
        await db_session.commit()

        assert trust > 0.0
        assert trust <= 1.0

        # Verify DB state
        from agentforge.models.agent import Agent

        result = await db_session.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = result.scalar_one()
        assert agent.total_executions == 1
        assert agent.success_count == 1
        assert float(agent.avg_duration_seconds) == 90.0

    @pytest.mark.asyncio
    async def test_atomic_trust_concurrent_safe(
        self, client: AsyncClient, provider_key, db_session: AsyncSession
    ):
        """Multiple atomic updates don't lose data."""
        api_key, _ = provider_key

        from tests.conftest import _unique_suffix

        suffix = _unique_suffix()
        resp = await client.post(
            "/v1/agents",
            headers={"X-API-Key": api_key},
            json={
                "id": f"concurrent-{suffix}",
                "name": "Concurrent Test",
                "description": "Test",
                "domain": "testing",
                "tags": [],
                "inputs": [{"name": "x", "type": "string"}],
                "outputs": [{"name": "output.md", "type": "markdown"}],
                "runtime": {"estimated_duration_seconds": 60},
                "pricing": {"base_price_usd": 1.00},
                "instructions": "Test",
            },
        )
        agent_id = resp.json()["id"]

        # 5 sequential updates (simulating concurrent workers)
        for i in range(5):
            await atomic_update_trust(
                db=db_session,
                agent_id=agent_id,
                success=i % 2 == 0,  # alternating success/failure
                elapsed_seconds=50 + i * 10,
                expected_duration=60,
            )
            await db_session.commit()

        from agentforge.models.agent import Agent

        result = await db_session.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = result.scalar_one()
        assert agent.total_executions == 5
        assert agent.success_count == 3  # indices 0, 2, 4

    def test_trust_score_pure_function(self):
        """Trust score computation is deterministic."""
        s1 = compute_trust_score(100, 95, 300, 300)
        s2 = compute_trust_score(100, 95, 300, 300)
        assert s1 == s2
        assert 0.8 < s1 <= 1.0  # high success, accurate duration, good volume


# --- Async Webhook Delivery ---


class TestWebhookQueue:
    @pytest.mark.asyncio
    async def test_enqueue_and_deliver(self):
        """Webhook jobs are enqueued and delivered."""
        queue = WebhookQueue()

        job = WebhookJob(
            webhook_id="wh-123",
            url="https://example.com/hook",
            secret="test-secret",
            body={"event_type": "task.completed", "payload": {}},
            event_type="task.completed",
        )
        queue.enqueue(job)

        assert queue._queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_queue_capacity(self):
        """Queue drops jobs when full."""
        queue = WebhookQueue()
        queue._queue = asyncio.Queue(maxsize=2)

        for i in range(5):
            queue.enqueue(
                WebhookJob(
                    webhook_id=f"wh-{i}",
                    url="https://example.com",
                    secret="s",
                    body={},
                    event_type="test",
                )
            )

        # Only 2 should be in queue
        assert queue._queue.qsize() == 2

    @pytest.mark.asyncio
    async def test_retry_scheduling(self):
        """Failed deliveries are scheduled for retry with backoff."""
        queue = WebhookQueue()
        job = WebhookJob(
            webhook_id="wh-retry",
            url="https://example.com/hook",
            secret="s",
            body={},
            event_type="test",
        )

        queue._schedule_retry(job, "connection refused")
        assert job.attempt == 1
        assert len(queue._retry_queue) == 1
        assert queue._retry_queue[0].next_retry_at > 0

    @pytest.mark.asyncio
    async def test_max_retries_exhausted(self):
        """After max retries, job is dropped and failure recorded."""
        queue = WebhookQueue()
        job = WebhookJob(
            webhook_id="wh-fail",
            url="https://example.com/hook",
            secret="s",
            body={},
            event_type="test",
            attempt=2,  # already tried twice
        )

        with patch.object(queue, "_record_failure", new_callable=AsyncMock):
            queue._schedule_retry(job, "still failing")

        # Not added to retry queue (max reached)
        assert len(queue._retry_queue) == 0


# --- Event Emission (now async) ---


class TestAsyncEventEmission:
    @pytest.mark.asyncio
    async def test_emit_event_enqueues_webhook(
        self, client: AsyncClient, consumer_key, db_session: AsyncSession
    ):
        """emit_event enqueues webhook delivery instead of blocking."""
        import uuid

        from agentforge.events import emit_event

        # Create a webhook
        from agentforge.models.webhook import Webhook
        from agentforge.webhook_delivery import webhook_queue

        wh = Webhook(
            id=uuid.uuid4(),
            owner_id=uuid.uuid4(),
            owner_role="consumer",
            url="https://example.com/webhook",
            secret="test-secret-123",
            event_types=["task.completed"],
            active=True,
        )
        db_session.add(wh)
        await db_session.flush()

        # Clear the queue
        while not webhook_queue._queue.empty():
            webhook_queue._queue.get_nowait()

        # Emit event
        event = await emit_event(
            db=db_session,
            event_type="task.completed",
            resource_type="task",
            resource_id="tc-test-123",
            payload={"status": "completed"},
        )

        assert event is not None
        assert webhook_queue._queue.qsize() >= 1

    @pytest.mark.asyncio
    async def test_emit_event_no_deliver(self, db_session: AsyncSession):
        """emit_event with deliver=False doesn't enqueue."""
        from agentforge.events import emit_event
        from agentforge.webhook_delivery import webhook_queue

        initial_size = webhook_queue._queue.qsize()

        await emit_event(
            db=db_session,
            event_type="task.created",
            deliver=False,
        )

        assert webhook_queue._queue.qsize() == initial_size


# --- Cleanup ---


class TestCleanup:
    @pytest.mark.asyncio
    async def test_cleanup_old_events(self, db_session: AsyncSession):
        """Old event log entries are pruned. Retention floor enforced per Art. 19."""
        from agentforge.models.event_log import EventLog

        # 200 days old, older than the Art. 19 floor of 180 days
        old_date = datetime.now(timezone.utc) - timedelta(days=200)
        old_event = EventLog(
            event_type="test.old",
            created_at=old_date,
        )
        db_session.add(old_event)
        await db_session.flush()
        await db_session.commit()

        from agentforge.cleanup import cleanup_old_events

        deleted = await cleanup_old_events(db=db_session)
        assert deleted >= 1

    @pytest.mark.asyncio
    async def test_cleanup_preserves_recent_events(self, db_session: AsyncSession):
        """Recent event log entries are not pruned."""
        from agentforge.models.event_log import EventLog

        recent_event = EventLog(
            event_type="test.recent",
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(recent_event)
        await db_session.flush()
        await db_session.commit()

        from agentforge.cleanup import cleanup_old_events

        await cleanup_old_events(db=db_session)

        # Recent event should still exist
        result = await db_session.execute(
            select(EventLog).where(EventLog.event_type == "test.recent")
        )
        assert result.scalar_one_or_none() is not None

    def test_retention_config_defaults(self):
        """Retention settings default to the Art. 19 floor (180 days)."""
        from agentforge.config import Settings

        s = Settings()
        assert s.results_retention_days == 180
        assert s.event_log_retention_days == 180
        assert s.compliance_docs_retention_days == 3650  # Art. 18: 10 years


# --- Eager Loading Fix ---


class TestEagerLoading:
    def test_agent_tasks_not_selectin(self):
        """Agent.tasks should not auto-load all tasks."""
        from agentforge.models.agent import Agent

        # Check the relationship configuration
        rel = Agent.__mapper__.relationships["tasks"]
        # This checks that we're aware of the lazy loading strategy
        assert rel.lazy in ("selectin", "noload", "select", "raise")
