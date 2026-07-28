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

# Plan limits matching CatalogPage pricing tiers
PLAN_LIMITS: dict[str, dict[str, int | float]] = {
    "starter": {
        "tasks_per_month": 4,
        "scheduled_agents": 1,
        "max_concurrent": 1,
    },
    "pro": {
        "tasks_per_month": 20,
        "scheduled_agents": 5,
        "max_concurrent": 5,
    },
    "team": {
        "tasks_per_month": 60,
        "scheduled_agents": 20,
        "max_concurrent": 20,
    },
    "enterprise": {
        "tasks_per_month": float("inf"),
        "scheduled_agents": float("inf"),
        "max_concurrent": float("inf"),
    },
}


def get_plan_limits(plan: str) -> dict[str, int | float]:
    """Get limits for a subscription plan."""
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["starter"])


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


def create_checkout_session(
    customer_id: str | None,
    consumer_id: str,
    success_url: str | None = None,
    cancel_url: str | None = None,
) -> dict | None:
    """Create a Stripe Checkout Session for payment method setup.

    Returns dict with session_id and url, or None if billing disabled.
    """
    if not _init_stripe():
        return None

    params: dict = {
        "mode": "setup",
        "payment_method_types": ["card"],
        "success_url": success_url or settings.stripe_checkout_success_url,
        "cancel_url": cancel_url or settings.stripe_checkout_cancel_url,
        "metadata": {"consumer_id": consumer_id},
    }
    if customer_id:
        params["customer"] = customer_id

    try:
        session = stripe.checkout.Session.create(**params)
        log.info(f"Created checkout session {session.id} for consumer {consumer_id}")
        return {
            "session_id": session.id,
            "url": session.url,
        }
    except stripe.StripeError as e:
        log.error(f"Failed to create checkout session: {e}")
        raise


def create_connect_account(
    provider_id: str,
    email: str,
    name: str,
) -> dict | None:
    """Create a Stripe Connect Express account for a provider.

    Returns dict with account_id and onboarding_url.
    """
    if not _init_stripe():
        return None

    try:
        account = stripe.Account.create(
            type="express",
            email=email,
            metadata={
                "provider_id": provider_id,
                "platform": "agents.renemurrell.de",
            },
            capabilities={
                "transfers": {"requested": True},
            },
        )

        link = stripe.AccountLink.create(
            account=account.id,
            refresh_url=settings.stripe_connect_refresh_url,
            return_url=settings.stripe_connect_return_url,
            type="account_onboarding",
        )

        log.info(f"Created Connect account {account.id} for provider {provider_id}")
        return {
            "account_id": account.id,
            "onboarding_url": link.url,
        }
    except stripe.StripeError as e:
        log.error(f"Failed to create Connect account: {e}")
        raise


def create_connect_login_link(connect_account_id: str) -> str | None:
    """Create a Stripe Connect Express dashboard login link."""
    if not _init_stripe():
        return None

    try:
        link = stripe.Account.create_login_link(connect_account_id)
        return link.url
    except stripe.StripeError as e:
        log.error(f"Failed to create login link: {e}")
        raise


def get_connect_account_status(connect_account_id: str) -> dict | None:
    """Get the status of a Stripe Connect account."""
    if not _init_stripe():
        return None

    try:
        account = stripe.Account.retrieve(connect_account_id)
        return {
            "account_id": account.id,
            "charges_enabled": account.charges_enabled,
            "payouts_enabled": account.payouts_enabled,
            "details_submitted": account.details_submitted,
            "requirements": {
                "currently_due": list(account.requirements.currently_due or []),
                "eventually_due": list(account.requirements.eventually_due or []),
                "disabled_reason": account.requirements.disabled_reason,
            },
        }
    except stripe.StripeError as e:
        log.error(f"Failed to get Connect account status: {e}")
        raise


def transfer_to_provider(
    task_id: str,
    connect_account_id: str,
    amount_cents: int,
) -> dict:
    """Transfer provider's share to their Connect account after capture."""
    if not _init_stripe():
        return {"transferred": False, "reason": "billing_disabled"}

    try:
        transfer = stripe.Transfer.create(
            amount=amount_cents,
            currency="usd",
            destination=connect_account_id,
            metadata={"task_id": task_id, "platform": "agents.renemurrell.de"},
            idempotency_key=f"transfer-{task_id}",
        )
        log.info(
            f"Transferred {amount_cents} cents to {connect_account_id} "
            f"for task {task_id}: {transfer.id}"
        )
        return {"transferred": True, "transfer_id": transfer.id}
    except stripe.StripeError as e:
        log.error(f"Transfer failed for task {task_id}: {e}")
        return {"transferred": False, "reason": str(e)}


def list_payment_methods(customer_id: str) -> list[dict]:
    """List all payment methods for a Stripe customer."""
    if not _init_stripe():
        return []

    try:
        methods = stripe.PaymentMethod.list(customer=customer_id, type="card")
        return [
            {
                "id": pm.id,
                "brand": pm.card.brand,
                "last4": pm.card.last4,
                "exp_month": pm.card.exp_month,
                "exp_year": pm.card.exp_year,
                "is_default": False,  # caller sets this
            }
            for pm in methods.data
        ]
    except stripe.StripeError as e:
        log.error(f"Failed to list payment methods: {e}")
        return []


def delete_payment_method(payment_method_id: str) -> bool:
    """Detach a payment method from a customer."""
    if not _init_stripe():
        return False

    try:
        stripe.PaymentMethod.detach(payment_method_id)
        return True
    except stripe.StripeError as e:
        log.error(f"Failed to delete payment method: {e}")
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
