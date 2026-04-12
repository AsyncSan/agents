"""Stripe billing service for agent task payments.

Flow:
  1. Consumer submits task → authorize PaymentIntent (manual capture)
  2. Task dispatches to ephemeral compute
  3. On success → capture funds
  4. On failure → cancel authorization

Uses idempotency keys tied to task IDs. Platform fee extracted as percentage.
"""

import logging
import math

import stripe

from agentforge.config import settings

log = logging.getLogger("agentforge.billing")


def _init_stripe() -> bool:
    """Initialize Stripe with secret key. Returns True if configured."""
    if not settings.stripe_secret_key:
        return False
    stripe.api_key = settings.stripe_secret_key
    return True


def is_billing_enabled() -> bool:
    return bool(settings.stripe_secret_key)


def price_to_cents(usd: float) -> int:
    """Convert USD float to cents integer."""
    return max(50, math.ceil(usd * 100))  # Stripe minimum is $0.50


def authorize_task_payment(
    task_id: str,
    amount_usd: float,
    customer_id: str | None = None,
    description: str = "",
) -> dict:
    """Create a PaymentIntent with manual capture (authorize only).

    Returns dict with payment_intent_id and amount_cents, or None fields
    if billing is not configured.
    """
    if not _init_stripe():
        log.info("Billing not configured, skipping authorization")
        return {"payment_intent_id": None, "amount_cents": None}

    amount_cents = price_to_cents(amount_usd)

    params: dict = {
        "amount": amount_cents,
        "currency": "usd",
        "capture_method": "manual",
        "description": description,
        "metadata": {"task_id": task_id, "platform": "agents.renemurrell.de"},
    }
    if customer_id:
        params["customer"] = customer_id

    try:
        intent = stripe.PaymentIntent.create(
            idempotency_key=f"auth-{task_id}",
            **params,
        )
        log.info(f"Authorized ${amount_usd:.2f} for task {task_id}: {intent.id}")
        return {
            "payment_intent_id": intent.id,
            "amount_cents": amount_cents,
            "client_secret": intent.client_secret,
        }
    except stripe.StripeError as e:
        log.error(f"Authorization failed for task {task_id}: {e}")
        raise


def compute_platform_fee(amount_cents: int) -> int:
    """Calculate platform fee in cents based on configured percentage."""
    return round(amount_cents * settings.stripe_platform_fee_percent / 100)


def capture_payment(
    task_id: str, payment_intent_id: str, amount_cents: int = 0
) -> dict:
    """Capture an authorized PaymentIntent after successful task execution.

    Returns dict with captured status, amount, and computed platform fee.
    """
    if not _init_stripe():
        return {"captured": True, "fee_cents": 0}

    fee_cents = compute_platform_fee(amount_cents) if amount_cents else 0

    try:
        intent = stripe.PaymentIntent.capture(
            payment_intent_id,
            idempotency_key=f"capture-{task_id}",
        )
        log.info(
            f"Captured {intent.amount} cents for task {task_id}, "
            f"platform fee {fee_cents} cents"
        )
        return {
            "captured": intent.status == "succeeded",
            "fee_cents": fee_cents,
        }
    except stripe.StripeError as e:
        log.error(f"Capture failed for task {task_id}: {e}")
        return {"captured": False, "fee_cents": 0}


def cancel_payment(task_id: str, payment_intent_id: str) -> bool:
    """Cancel an authorized PaymentIntent after task failure."""
    if not _init_stripe():
        return True

    try:
        intent = stripe.PaymentIntent.cancel(
            payment_intent_id,
            idempotency_key=f"cancel-{task_id}",
        )
        log.info(f"Cancelled authorization for task {task_id}")
        return intent.status == "canceled"
    except stripe.StripeError as e:
        log.error(f"Cancel failed for task {task_id}: {e}")
        return False


def refund_payment(task_id: str, payment_intent_id: str, reason: str = "") -> bool:
    """Refund a captured payment."""
    if not _init_stripe():
        return True

    try:
        refund = stripe.Refund.create(
            payment_intent=payment_intent_id,
            reason="requested_by_customer",
            metadata={"task_id": task_id, "reason": reason},
            idempotency_key=f"refund-{task_id}",
        )
        log.info(f"Refunded task {task_id}: {refund.id}")
        return refund.status in ("succeeded", "pending")
    except stripe.StripeError as e:
        log.error(f"Refund failed for task {task_id}: {e}")
        return False


def verify_webhook_signature(payload: bytes, sig_header: str) -> dict | None:
    """Verify Stripe webhook signature and return event dict."""
    if not settings.stripe_webhook_secret:
        return None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
        return event
    except (stripe.SignatureVerificationError, ValueError) as e:
        log.warning(f"Webhook signature verification failed: {e}")
        return None
