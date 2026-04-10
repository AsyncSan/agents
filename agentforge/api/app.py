"""FastAPI application entry point."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agentforge.api.routes_agents import router as agents_router
from agentforge.api.routes_auth import router as auth_router
from agentforge.api.routes_tasks import router as tasks_router
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
    title="AgentForge",
    description="Agent Commerce Infrastructure: Registry, Compute, Payments, Trust",
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
app.include_router(tasks_router)


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "version": "0.1.0"}
