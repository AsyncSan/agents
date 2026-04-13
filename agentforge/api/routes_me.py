"""Me routes: authenticated user's own profile and usage summary."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.api.auth import get_current_user
from agentforge.db import get_db
from agentforge.models.agent import Agent
from agentforge.models.consumer import Consumer
from agentforge.models.provider import Provider
from agentforge.models.schedule import Schedule
from agentforge.models.task import Task
from agentforge.models.webhook import Webhook

router = APIRouter(prefix="/v1/me", tags=["me"])


class MeResponse(BaseModel):
    id: str
    name: str
    role: str
    email: str
    secrets_count: int
    webhooks_count: int
    schedules_count: int | None  # only for consumers
    tasks_count: int
    agents_count: int | None  # only for providers
    stripe_configured: bool
    created_at: str


@router.get("", response_model=MeResponse)
async def get_me(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get authenticated user's profile and usage summary."""
    if user["role"] == "consumer":
        result = await db.execute(select(Consumer).where(Consumer.id == user["id"]))
        entity = result.scalar_one()

        secrets_count = len(entity.secrets or {})
        stripe_ok = bool(entity.stripe_customer_id)

        wh_count = (await db.execute(
            select(func.count()).select_from(Webhook).where(
                Webhook.owner_id == user["id"], Webhook.active.is_(True)
            )
        )).scalar() or 0

        sched_count = (await db.execute(
            select(func.count()).select_from(Schedule).where(
                Schedule.consumer_id == user["id"], Schedule.active.is_(True)
            )
        )).scalar() or 0

        task_count = (await db.execute(
            select(func.count()).select_from(Task).where(Task.consumer_id == user["id"])
        )).scalar() or 0

        return MeResponse(
            id=str(entity.id),
            name=entity.name,
            role="consumer",
            email=entity.email,
            secrets_count=secrets_count,
            webhooks_count=wh_count,
            schedules_count=sched_count,
            tasks_count=task_count,
            agents_count=None,
            stripe_configured=stripe_ok,
            created_at=entity.created_at.isoformat(),
        )

    else:
        result = await db.execute(select(Provider).where(Provider.id == user["id"]))
        entity = result.scalar_one()

        secrets_count = len(entity.secrets or {})

        wh_count = (await db.execute(
            select(func.count()).select_from(Webhook).where(
                Webhook.owner_id == user["id"], Webhook.active.is_(True)
            )
        )).scalar() or 0

        agent_count = (await db.execute(
            select(func.count()).select_from(Agent).where(
                Agent.provider_id == user["id"], Agent.status == "active"
            )
        )).scalar() or 0

        task_count = (await db.execute(
            select(func.count()).select_from(Task).where(
                Task.agent_id.in_(
                    select(Agent.id).where(Agent.provider_id == user["id"])
                )
            )
        )).scalar() or 0

        return MeResponse(
            id=str(entity.id),
            name=entity.name,
            role="provider",
            email=entity.email,
            secrets_count=secrets_count,
            webhooks_count=wh_count,
            schedules_count=None,
            tasks_count=task_count,
            agents_count=agent_count,
            stripe_configured=False,
            created_at=entity.created_at.isoformat(),
        )
