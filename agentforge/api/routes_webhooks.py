"""Webhook management: CRUD for event subscriptions."""

import hashlib
import hmac
import json
import logging
import secrets
from datetime import datetime, timezone
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.api.auth import get_current_user
from agentforge.api.errors import APIError, ErrorCode
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
        raise APIError(
            422, ErrorCode.INVALID_EVENT_TYPE,
            f"Invalid event type: {t}",
            {"valid_types": EVENT_TYPES},
        )


_WEBHOOK_LIMIT = 10


@router.post("", response_model=WebhookResponse, status_code=201)
async def create_webhook(
    req: WebhookCreateRequest,
    response: Response,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register a webhook endpoint for event delivery."""
    _validate_event_types(req.event_types)

    # Limit active webhooks per user
    count_result = await db.execute(
        select(Webhook).where(
            Webhook.owner_id == user["id"], Webhook.active.is_(True)
        )
    )
    existing = count_result.scalars().all()
    current_count = len(existing)
    if current_count >= _WEBHOOK_LIMIT:
        raise APIError(
            429, ErrorCode.RATE_LIMIT,
            f"Maximum {_WEBHOOK_LIMIT} active webhooks",
            {"limit": _WEBHOOK_LIMIT, "current": current_count},
        )
    response.headers["X-RateLimit-Limit"] = str(_WEBHOOK_LIMIT)
    response.headers["X-RateLimit-Remaining"] = str(_WEBHOOK_LIMIT - current_count - 1)

    # For third-party integrations, the ``secret`` field holds the service
    # credential rather than our HMAC signing secret. Fall back to a generated
    # HMAC secret if the caller didn't supply one.
    if req.secret_override and req.webhook_type in {
        "splunk_hec",
        "datadog_logs",
        "jira",
        "linear",
    }:
        webhook_secret = req.secret_override
    else:
        webhook_secret = f"whsec_{secrets.token_urlsafe(32)}"

    webhook = Webhook(
        owner_id=user["id"],
        owner_role=user["role"],
        url=req.url,
        webhook_type=req.webhook_type,
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
    active_only: bool = True,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all webhooks for the authenticated user."""
    query = select(Webhook).where(Webhook.owner_id == user["id"])
    if active_only:
        query = query.where(Webhook.active.is_(True))
    result = await db.execute(
        query.order_by(Webhook.created_at.desc())
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
        raise APIError(404, ErrorCode.WEBHOOK_NOT_FOUND, "Webhook not found")
    if webhook.owner_id != user["id"]:
        raise APIError(403, ErrorCode.FORBIDDEN, "Not your webhook")

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


log = logging.getLogger("agentforge.webhooks")


class WebhookTestResponse(BaseModel):
    success: bool
    status_code: int | None = None
    response_body: str | None = None
    error: str | None = None


@router.post("/{webhook_id}/test", response_model=WebhookTestResponse)
async def test_webhook(
    webhook_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a test event to a webhook and return the response.

    Useful for verifying webhook setup before going live.
    """
    result = await db.execute(
        select(Webhook).where(Webhook.id == webhook_id)
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise APIError(404, ErrorCode.WEBHOOK_NOT_FOUND, "Webhook not found")
    if webhook.owner_id != user["id"]:
        raise APIError(403, ErrorCode.FORBIDDEN, "Not your webhook")

    body = {
        "event_id": str(uuid4()),
        "event_type": "webhook.test",
        "resource_type": "webhook",
        "resource_id": str(webhook.id),
        "payload": {"test": True, "message": "This is a test event"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    body_bytes = json.dumps(body, default=str).encode()

    signature = hmac.new(
        webhook.secret.encode(), body_bytes, hashlib.sha256
    ).hexdigest()

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                webhook.url,
                content=body_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Signature": f"sha256={signature}",
                    "X-Webhook-Event": "webhook.test",
                },
            )
        return WebhookTestResponse(
            success=resp.status_code < 400,
            status_code=resp.status_code,
            response_body=resp.text[:500],
        )
    except httpx.TimeoutException:
        return WebhookTestResponse(
            success=False, error="Connection timed out (10s)"
        )
    except httpx.ConnectError as e:
        return WebhookTestResponse(
            success=False, error=f"Connection failed: {e}"
        )
