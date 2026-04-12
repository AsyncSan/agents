"""Webhook management: CRUD for event subscriptions."""

import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.api.auth import get_current_user
from agentforge.api.schemas import (
    WebhookCreateRequest,
    WebhookListResponse,
    WebhookResponse,
)
from agentforge.db import get_db
from agentforge.events import EVENT_TYPES, emit_event
from agentforge.models.webhook import Webhook

router = APIRouter(prefix="/v1/me/webhooks", tags=["webhooks"])

# Valid event type patterns (exact or wildcard like "task.*")
_VALID_PREFIXES = {t.split(".")[0] for t in EVENT_TYPES}


def _validate_event_types(types: list[str]) -> None:
    for t in types:
        if t == "*":
            continue
        if t in EVENT_TYPES:
            continue
        if t.endswith(".*") and t[:-2] in _VALID_PREFIXES:
            continue
        raise HTTPException(
            status_code=422,
            detail=f"Invalid event type: {t}. Valid types: {EVENT_TYPES}",
        )


@router.post("", response_model=WebhookResponse, status_code=201)
async def create_webhook(
    req: WebhookCreateRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register a webhook endpoint for event delivery."""
    _validate_event_types(req.event_types)

    # Limit to 10 webhooks per user
    count_result = await db.execute(
        select(Webhook).where(
            Webhook.owner_id == user["id"], Webhook.active.is_(True)
        )
    )
    existing = count_result.scalars().all()
    if len(existing) >= 10:
        raise HTTPException(status_code=429, detail="Maximum 10 active webhooks")

    webhook_secret = f"whsec_{secrets.token_urlsafe(32)}"

    webhook = Webhook(
        owner_id=user["id"],
        owner_role=user["role"],
        url=req.url,
        secret=webhook_secret,
        event_types=req.event_types,
    )
    db.add(webhook)
    await db.commit()
    await db.refresh(webhook)

    await emit_event(
        db,
        "webhook.created",
        actor_id=str(user["id"]),
        actor_role=user["role"],
        resource_type="webhook",
        resource_id=str(webhook.id),
        deliver=False,
    )
    await db.commit()

    return WebhookResponse(
        id=webhook.id,
        url=webhook.url,
        secret=webhook_secret,
        event_types=webhook.event_types,
        active=webhook.active,
        total_deliveries=webhook.total_deliveries,
        total_failures=webhook.total_failures,
        created_at=webhook.created_at,
    )


@router.get("", response_model=WebhookListResponse)
async def list_webhooks(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all webhooks for the authenticated user."""
    result = await db.execute(
        select(Webhook)
        .where(Webhook.owner_id == user["id"])
        .order_by(Webhook.created_at.desc())
    )
    webhooks = result.scalars().all()

    return WebhookListResponse(
        webhooks=[
            WebhookResponse(
                id=wh.id,
                url=wh.url,
                secret="whsec_****",  # masked after creation
                event_types=wh.event_types,
                active=wh.active,
                total_deliveries=wh.total_deliveries,
                total_failures=wh.total_failures,
                created_at=wh.created_at,
            )
            for wh in webhooks
        ]
    )


@router.delete("/{webhook_id}", status_code=204)
async def delete_webhook(
    webhook_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a webhook."""
    result = await db.execute(
        select(Webhook).where(Webhook.id == webhook_id)
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    if webhook.owner_id != user["id"]:
        raise HTTPException(status_code=403, detail="Not your webhook")

    webhook.active = False
    await emit_event(
        db,
        "webhook.deleted",
        actor_id=str(user["id"]),
        actor_role=user["role"],
        resource_type="webhook",
        resource_id=str(webhook.id),
        deliver=False,
    )
    await db.commit()
