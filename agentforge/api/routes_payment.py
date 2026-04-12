"""Payment setup routes: attach payment methods to consumer accounts."""

import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.api.auth import require_role
from agentforge.api.schemas import PaymentSetupRequest, PaymentSetupResponse
from agentforge.billing import is_billing_enabled
from agentforge.config import settings
from agentforge.db import get_db
from agentforge.models.consumer import Consumer

log = logging.getLogger("agentforge.payment")

router = APIRouter(prefix="/v1/me", tags=["payment"])


@router.post("/payment-method", response_model=PaymentSetupResponse)
async def attach_payment_method(
    req: PaymentSetupRequest,
    user: dict = Depends(require_role("consumer")),
    db: AsyncSession = Depends(get_db),
):
    """Attach a Stripe PaymentMethod to the consumer's account.

    The consumer must first create a PaymentMethod client-side using
    Stripe.js or the Stripe mobile SDK, then pass the PM ID here.
    """
    if not is_billing_enabled():
        raise HTTPException(status_code=503, detail="Billing not configured")

    stripe.api_key = settings.stripe_secret_key

    # Load consumer
    result = await db.execute(select(Consumer).where(Consumer.id == user["id"]))
    consumer = result.scalar_one_or_none()
    if not consumer:
        raise HTTPException(status_code=404, detail="Consumer not found")

    # Create Stripe Customer if none exists
    if not consumer.stripe_customer_id:
        try:
            customer = stripe.Customer.create(
                email=consumer.email,
                name=consumer.name,
                metadata={
                    "consumer_id": str(consumer.id),
                    "platform": "agents.renemurrell.de",
                },
            )
            consumer.stripe_customer_id = customer.id
            await db.flush()
            log.info(f"Created Stripe customer {customer.id} for {consumer.id}")
        except stripe.StripeError as e:
            log.error(f"Failed to create Stripe customer: {e}")
            raise HTTPException(status_code=502, detail="Payment provider error")

    # Attach PaymentMethod to customer
    try:
        stripe.PaymentMethod.attach(
            req.payment_method_id,
            customer=consumer.stripe_customer_id,
        )
        # Set as default payment method
        stripe.Customer.modify(
            consumer.stripe_customer_id,
            invoice_settings={"default_payment_method": req.payment_method_id},
        )
        log.info(
            f"Attached PM {req.payment_method_id} to customer "
            f"{consumer.stripe_customer_id}"
        )
    except stripe.StripeError as e:
        log.error(f"Failed to attach payment method: {e}")
        raise HTTPException(status_code=400, detail=f"Payment method error: {e}")

    await db.commit()

    return PaymentSetupResponse(
        stripe_customer_id=consumer.stripe_customer_id,
        payment_method_attached=True,
        default_payment_method=req.payment_method_id,
    )


@router.get("/payment-method", response_model=PaymentSetupResponse)
async def get_payment_status(
    user: dict = Depends(require_role("consumer")),
    db: AsyncSession = Depends(get_db),
):
    """Check consumer's payment setup status."""
    result = await db.execute(select(Consumer).where(Consumer.id == user["id"]))
    consumer = result.scalar_one_or_none()
    if not consumer:
        raise HTTPException(status_code=404, detail="Consumer not found")

    if not consumer.stripe_customer_id:
        return PaymentSetupResponse(
            stripe_customer_id="",
            payment_method_attached=False,
            default_payment_method=None,
        )

    # Check for default payment method
    default_pm = None
    if is_billing_enabled():
        stripe.api_key = settings.stripe_secret_key
        try:
            customer = stripe.Customer.retrieve(consumer.stripe_customer_id)
            default_pm = (
                customer.invoice_settings.default_payment_method
                if customer.invoice_settings
                else None
            )
        except stripe.StripeError:
            pass

    return PaymentSetupResponse(
        stripe_customer_id=consumer.stripe_customer_id,
        payment_method_attached=default_pm is not None,
        default_payment_method=default_pm,
    )
