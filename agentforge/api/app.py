"""FastAPI application entry point."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agentforge.api.routes_agents import router as agents_router
from agentforge.api.routes_auth import router as auth_router
from agentforge.api.routes_payment import router as payment_router
from agentforge.api.routes_pipelines import router as pipelines_router
from agentforge.api.routes_platform import router as platform_router
from agentforge.api.routes_providers import router as providers_router
from agentforge.api.routes_ratings import router as ratings_router
from agentforge.api.routes_secrets import router as secrets_router
from agentforge.api.routes_stripe import router as stripe_router
from agentforge.api.routes_tasks import router as tasks_router
from agentforge.api.routes_webhooks import router as webhooks_router
from agentforge.config import settings

log = logging.getLogger("agentforge")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start dispatch worker if HCLOUD_TOKEN is configured
    worker_task = None
    if settings.hcloud_token:
        from agentforge.dispatch.worker import dispatch_worker_loop
        worker_task = asyncio.create_task(dispatch_worker_loop())
        log.info("Dispatch worker started")
    else:
        log.warning("HCLOUD_TOKEN not set, dispatch worker disabled")

    yield

    # Shutdown
    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="renemurrell.de Agents",
    description="Agent Commerce Infrastructure: Registry, Ephemeral Compute, Payments, Trust",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(agents_router)
app.include_router(providers_router)
app.include_router(tasks_router)
app.include_router(pipelines_router)
app.include_router(secrets_router)
app.include_router(stripe_router)
app.include_router(platform_router)
app.include_router(webhooks_router)
app.include_router(ratings_router)
app.include_router(payment_router)


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "version": "0.1.0"}
