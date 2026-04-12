"""Stripe webhook handler and payment routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.billing import is_billing_enabled, verify_webhook_signature
from agentforge.db import get_db
from agentforge.models.task import Task

log = logging.getLogger("agentforge.stripe")

router = APIRouter(tags=["stripe"])


@router.post("/v1/stripe/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Stripe webhook events. Signature-verified."""
    if not is_billing_enabled():
        raise HTTPException(status_code=503, detail="Billing not configured")

    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    event = verify_webhook_signature(payload, sig)
    if event is None:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})
    task_id = data.get("metadata", {}).get("task_id")

    log.info(f"Stripe webhook: {event_type}, task={task_id}")

    if event_type == "payment_intent.succeeded":
        if task_id:
            await db.execute(
                update(Task)
                .where(Task.id == task_id)
                .values(payment_status="captured")
            )
            await db.commit()

    elif event_type == "payment_intent.canceled":
        if task_id:
            await db.execute(
                update(Task)
                .where(Task.id == task_id)
                .values(payment_status="cancelled")
            )
            await db.commit()

    elif event_type == "charge.dispute.created":
        pi_id = data.get("payment_intent")
        if pi_id:
            result = await db.execute(
                select(Task).where(Task.payment_intent_id == pi_id)
            )
            task = result.scalar_one_or_none()
            if task:
                log.warning(f"Dispute on task {task.id}, PI {pi_id}")
                task.payment_status = "disputed"
                await db.commit()

    elif event_type == "charge.refunded":
        pi_id = data.get("payment_intent")
        if pi_id:
            await db.execute(
                update(Task)
                .where(Task.payment_intent_id == pi_id)
                .values(payment_status="refunded")
            )
            await db.commit()

    return {"received": True}
