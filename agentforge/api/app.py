"""FastAPI application entry point."""

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from agentforge.api.errors import register_error_handlers
from agentforge.api.routes_agents import router as agents_router
from agentforge.api.routes_annex_iv import router as annex_iv_router
from agentforge.api.routes_auth import router as auth_router
from agentforge.api.routes_bundle import router as bundle_router
from agentforge.api.routes_compliance import router as compliance_router
from agentforge.api.routes_data_governance import router as data_governance_router
from agentforge.api.routes_declaration import router as declaration_router
from agentforge.api.routes_eu_db import router as eu_db_router
from agentforge.api.routes_dashboard import router as dashboard_router
from agentforge.api.routes_fria import router as fria_router
from agentforge.api.routes_incidents import router as incidents_router
from agentforge.api.routes_literacy import router as literacy_router
from agentforge.api.routes_me import router as me_router
from agentforge.api.routes_modifications import router as modifications_router
from agentforge.api.routes_oversight import router as oversight_router
from agentforge.api.routes_audit_shares import router as audit_shares_router
from agentforge.api.routes_audit_view import router as audit_view_router
from agentforge.api.routes_payment import (
    connect_router,
    wallet_router,
)
from agentforge.api.routes_payment import (
    router as payment_router,
)
from agentforge.api.routes_pipelines import router as pipelines_router
from agentforge.api.routes_platform import router as platform_router
from agentforge.api.routes_pmm import router as pmm_router
from agentforge.api.routes_qms import router as qms_router
from agentforge.api.routes_providers import router as providers_router
from agentforge.api.routes_ratings import router as ratings_router
from agentforge.api.routes_schedules import router as schedules_router
from agentforge.api.routes_secrets import router as secrets_router
from agentforge.api.routes_stripe import router as stripe_router
from agentforge.api.routes_tasks import router as tasks_router
from agentforge.api.routes_webhooks import router as webhooks_router
from agentforge.config import settings

log = logging.getLogger("agentforge")

# Configure agentforge logger to output to stderr (captured by journald)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logging.getLogger("agentforge").setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Recover stuck tasks from previous run (dispatching → failed)
    from agentforge.db import async_session as recovery_session_factory
    from agentforge.models.task import Task
    from sqlalchemy import update as sql_update
    async with recovery_session_factory() as db:
        result = await db.execute(
            sql_update(Task)
            .where(Task.status == "dispatching")
            .values(status="failed")
            .returning(Task.id)
        )
        stuck = result.scalars().all()
        if stuck:
            await db.commit()
            log.warning(f"Recovered {len(stuck)} stuck dispatching tasks: {stuck}")

    # Start dispatch worker if HCLOUD_TOKEN is configured
    worker_task = None
    if settings.hcloud_token:
        from agentforge.dispatch.worker import dispatch_worker_loop
        worker_task = asyncio.create_task(dispatch_worker_loop())
        log.info("Dispatch worker started")
    else:
        log.warning("HCLOUD_TOKEN not set, dispatch worker disabled")

    # Start schedule worker (always, creates tasks even without compute)
    from agentforge.dispatch.scheduler import scheduler_loop
    scheduler_task = asyncio.create_task(scheduler_loop())
    log.info("Schedule worker started")

    # Start async webhook delivery worker
    from agentforge.db import async_session as webhook_session_factory
    from agentforge.webhook_delivery import webhook_queue
    webhook_task = asyncio.create_task(webhook_queue.run(webhook_session_factory))
    log.info("Webhook delivery worker started")

    # Start cleanup worker (results + event log retention)
    from agentforge.cleanup import cleanup_loop
    cleanup_task = asyncio.create_task(cleanup_loop())
    log.info("Cleanup worker started")

    yield

    # Shutdown
    await webhook_queue.stop()
    scheduler_task.cancel()
    webhook_task.cancel()
    cleanup_task.cancel()
    if worker_task:
        worker_task.cancel()
    for t in [scheduler_task, worker_task, webhook_task, cleanup_task]:
        if t:
            try:
                await t
            except asyncio.CancelledError:
                pass


TAG_METADATA = [
    {"name": "auth", "description": "Registration and authentication"},
    {"name": "agents", "description": "Agent registry: CRUD, discovery, stats, health, versioning"},
    {"name": "tasks", "description": "Task lifecycle: submit, track, cancel, retrieve results"},
    {"name": "pipelines", "description": "Multi-agent pipelines: chain agents with output mapping"},
    {"name": "schedules", "description": "Recurring task execution via cron expressions"},
    {"name": "ratings", "description": "Consumer feedback on completed tasks"},
    {"name": "webhooks", "description": "Event subscriptions with HMAC-signed delivery"},
    {"name": "secrets", "description": "Secret brokerage: isolated credential injection"},
    {
        "name": "payment",
        "description": "Payments: Stripe Checkout, Connect payouts, Solana USDC, PM CRUD",
    },
    {"name": "providers", "description": "Public provider profiles and aggregated stats"},
    {"name": "dashboard", "description": "Usage analytics, cost tracking, compliance export"},
    {"name": "me", "description": "Authenticated user profile and account management"},
    {"name": "platform", "description": "System health, event log, platform metrics"},
    {"name": "stripe", "description": "Stripe webhook handler (internal)"},
]

ERROR_RESPONSES = {
    401: {
        "description": "Invalid or missing API key",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "invalid_api_key",
                        "message": "Invalid API key",
                    }
                }
            }
        },
    },
    403: {
        "description": "Insufficient permissions",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "forbidden",
                        "message": "Not your resource",
                    }
                }
            }
        },
    },
    404: {
        "description": "Resource not found",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "agent_not_found",
                        "message": "Agent not found",
                    }
                }
            }
        },
    },
    429: {
        "description": "Rate limit exceeded",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "rate_limit",
                        "message": "Maximum 20 active schedules",
                    }
                }
            }
        },
    },
}

app = FastAPI(
    title="Managed Agent Runtime API",
    description=(
        "Run AI agents on ephemeral infrastructure. "
        "Registry, compute, payments, trust scoring, and audit logging. "
        "EU-hosted (Hetzner, Germany). GDPR compliant."
    ),
    version="0.2.0",
    lifespan=lifespan,
    openapi_tags=TAG_METADATA,
    responses=ERROR_RESPONSES,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://agents.renemurrell.de",
        "https://renemurrell.de",
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next) -> Response:
    """Attach X-Request-ID to every request/response for tracing."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


app.include_router(auth_router)
app.include_router(agents_router)
app.include_router(providers_router)
app.include_router(tasks_router)
app.include_router(pipelines_router)
app.include_router(secrets_router)
app.include_router(stripe_router)
app.include_router(platform_router)
app.include_router(pmm_router)
app.include_router(qms_router)
app.include_router(webhooks_router)
app.include_router(ratings_router)
app.include_router(payment_router)
app.include_router(connect_router)
app.include_router(wallet_router)
app.include_router(schedules_router)
app.include_router(dashboard_router)
app.include_router(fria_router)
app.include_router(annex_iv_router)
app.include_router(compliance_router)
app.include_router(bundle_router)
app.include_router(data_governance_router)
app.include_router(declaration_router)
app.include_router(eu_db_router)
app.include_router(incidents_router)
app.include_router(literacy_router)
app.include_router(me_router)
app.include_router(modifications_router)
app.include_router(oversight_router)
app.include_router(audit_shares_router)
app.include_router(audit_view_router)


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "version": "0.2.0"}
