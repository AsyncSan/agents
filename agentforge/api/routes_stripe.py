"""Stripe webhook handler and payment routes."""

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.api.errors import APIError, ErrorCode
from agentforge.billing import is_billing_enabled, verify_webhook_signature
from agentforge.db import get_db
from agentforge.models.consumer import Consumer
from agentforge.models.provider import Provider
from agentforge.models.task import Task

log = logging.getLogger("agentforge.stripe")

router = APIRouter(tags=["stripe"])


@router.post("/v1/stripe/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Stripe webhook events. Signature-verified."""
    if not is_billing_enabled():
        raise APIError(503, ErrorCode.BILLING_NOT_CONFIGURED, "Billing not configured")

    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    event = verify_webhook_signature(payload, sig)
    if event is None:
        raise APIError(400, ErrorCode.INVALID_SIGNATURE, "Invalid webhook signature")

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

    elif event_type == "checkout.session.completed":
        # Consumer completed Stripe Checkout, attach setup intent's PM
        consumer_id = data.get("metadata", {}).get("consumer_id")
        setup_intent = data.get("setup_intent")
        customer_id = data.get("customer")

        if consumer_id and customer_id:
            result = await db.execute(
                select(Consumer).where(Consumer.id == consumer_id)
            )
            consumer = result.scalar_one_or_none()
            if consumer:
                consumer.stripe_customer_id = customer_id
                await db.commit()
                log.info(
                    f"Checkout completed for consumer {consumer_id}, "
                    f"customer={customer_id}, setup_intent={setup_intent}"
                )

    elif event_type == "account.updated":
        # Connect account status change
        account_id = data.get("id")
        payouts_enabled = data.get("payouts_enabled", False)
        details_submitted = data.get("details_submitted", False)

        if account_id:
            if payouts_enabled:
                status = "active"
            elif details_submitted:
                status = "pending"
            else:
                status = "restricted"

            result = await db.execute(
                select(Provider).where(Provider.stripe_connect_id == account_id)
            )
            provider = result.scalar_one_or_none()
            if provider:
                provider.stripe_connect_status = status
                await db.commit()
                log.info(f"Connect account {account_id} status → {status}")

    return {"received": True}
