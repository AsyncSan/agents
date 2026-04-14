"""Payment routes: Stripe Checkout, payment method CRUD, Solana wallet, Connect."""

import logging
import re

import stripe
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.api.auth import require_role
from agentforge.api.errors import APIError, ErrorCode
from agentforge.api.schemas import (
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    ConnectOnboardResponse,
    ConnectStatusResponse,
    PaymentMethodItem,
    PaymentMethodListResponse,
    PaymentSetupRequest,
    PaymentSetupResponse,
    SetDefaultPaymentMethodRequest,
    SolanaPaymentVerifyRequest,
    SolanaPaymentVerifyResponse,
    WalletRegisterRequest,
    WalletRegisterResponse,
)
from agentforge.billing import (
    create_checkout_session,
    create_connect_account,
    create_connect_login_link,
    delete_payment_method,
    get_connect_account_status,
    is_billing_enabled,
    list_payment_methods,
)
from agentforge.billing_solana import (
    is_solana_enabled,
    verify_usdc_transfer,
    verify_wallet_signature,
)
from agentforge.config import settings
from agentforge.db import get_db
from agentforge.models.consumer import Consumer
from agentforge.models.provider import Provider

log = logging.getLogger("agentforge.payment")

router = APIRouter(prefix="/v1/me", tags=["payment"])

# ---- Stripe Checkout Session (Consumer 1-Click) ----


@router.post("/checkout-session", response_model=CheckoutSessionResponse)
async def create_consumer_checkout_session(
    req: CheckoutSessionRequest,
    user: dict = Depends(require_role("consumer")),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe Checkout Session for payment method setup.

    Consumer gets redirected to Stripe-hosted page. No client-side Stripe.js needed.
    """
    if not is_billing_enabled():
        raise APIError(503, ErrorCode.BILLING_NOT_CONFIGURED, "Billing not configured")

    result = await db.execute(select(Consumer).where(Consumer.id == user["id"]))
    consumer = result.scalar_one_or_none()
    if not consumer:
        raise APIError(404, ErrorCode.CONSUMER_NOT_FOUND, "Consumer not found")

    # Create Stripe Customer if none exists
    if not consumer.stripe_customer_id:
        stripe.api_key = settings.stripe_secret_key
        try:
            customer = stripe.Customer.create(
                email=consumer.email,
                name=consumer.name,
                metadata={"consumer_id": str(consumer.id)},
            )
            consumer.stripe_customer_id = customer.id
            await db.flush()
        except stripe.StripeError:
            raise APIError(502, ErrorCode.PAYMENT_PROVIDER_ERROR, "Payment provider error")

    session = create_checkout_session(
        customer_id=consumer.stripe_customer_id,
        consumer_id=str(consumer.id),
        success_url=req.success_url,
        cancel_url=req.cancel_url,
    )
    if not session:
        raise APIError(502, ErrorCode.PAYMENT_PROVIDER_ERROR, "Failed to create checkout session")

    await db.commit()
    return CheckoutSessionResponse(**session)


# ---- Legacy: Direct PM Attachment ----


@router.post("/payment-method", response_model=PaymentSetupResponse)
async def attach_payment_method(
    req: PaymentSetupRequest,
    user: dict = Depends(require_role("consumer")),
    db: AsyncSession = Depends(get_db),
):
    """Attach a Stripe PaymentMethod to the consumer's account.

    The consumer must first create a PaymentMethod client-side using
    Stripe.js or the Stripe mobile SDK, then pass the PM ID here.
    For easier setup, use POST /checkout-session instead.
    """
    if not is_billing_enabled():
        raise APIError(503, ErrorCode.BILLING_NOT_CONFIGURED, "Billing not configured")

    stripe.api_key = settings.stripe_secret_key

    result = await db.execute(select(Consumer).where(Consumer.id == user["id"]))
    consumer = result.scalar_one_or_none()
    if not consumer:
        raise APIError(404, ErrorCode.CONSUMER_NOT_FOUND, "Consumer not found")

    if not consumer.stripe_customer_id:
        try:
            customer = stripe.Customer.create(
                email=consumer.email,
                name=consumer.name,
                metadata={"consumer_id": str(consumer.id)},
            )
            consumer.stripe_customer_id = customer.id
            await db.flush()
        except stripe.StripeError:
            raise APIError(502, ErrorCode.PAYMENT_PROVIDER_ERROR, "Payment provider error")

    try:
        stripe.PaymentMethod.attach(
            req.payment_method_id,
            customer=consumer.stripe_customer_id,
        )
        stripe.Customer.modify(
            consumer.stripe_customer_id,
            invoice_settings={"default_payment_method": req.payment_method_id},
        )
    except stripe.StripeError:
        raise APIError(400, ErrorCode.PAYMENT_ERROR, "Failed to attach payment method")

    await db.commit()

    return PaymentSetupResponse(
        stripe_customer_id=consumer.stripe_customer_id,
        payment_method_attached=True,
        default_payment_method=req.payment_method_id,
    )


# ---- Payment Method CRUD ----


@router.get("/payment-methods", response_model=PaymentMethodListResponse)
async def list_consumer_payment_methods(
    user: dict = Depends(require_role("consumer")),
    db: AsyncSession = Depends(get_db),
):
    """List all payment methods attached to the consumer."""
    result = await db.execute(select(Consumer).where(Consumer.id == user["id"]))
    consumer = result.scalar_one_or_none()
    if not consumer or not consumer.stripe_customer_id:
        return PaymentMethodListResponse(payment_methods=[])

    methods = list_payment_methods(consumer.stripe_customer_id)

    # Mark default
    default_pm = None
    if is_billing_enabled():
        stripe.api_key = settings.stripe_secret_key
        try:
            cust = stripe.Customer.retrieve(consumer.stripe_customer_id)
            default_pm = (
                cust.invoice_settings.default_payment_method
                if cust.invoice_settings
                else None
            )
        except stripe.StripeError:
            pass

    for m in methods:
        m["is_default"] = m["id"] == default_pm

    return PaymentMethodListResponse(
        payment_methods=[PaymentMethodItem(**m) for m in methods]
    )


@router.delete("/payment-methods/{payment_method_id}")
async def remove_payment_method(
    payment_method_id: str,
    user: dict = Depends(require_role("consumer")),
    db: AsyncSession = Depends(get_db),
):
    """Detach a payment method from the consumer's account."""
    if not is_billing_enabled():
        raise APIError(503, ErrorCode.BILLING_NOT_CONFIGURED, "Billing not configured")

    result = await db.execute(select(Consumer).where(Consumer.id == user["id"]))
    consumer = result.scalar_one_or_none()
    if not consumer or not consumer.stripe_customer_id:
        raise APIError(400, ErrorCode.PAYMENT_ERROR, "No payment methods configured")

    # Verify the PM belongs to this customer
    stripe.api_key = settings.stripe_secret_key
    try:
        pm = stripe.PaymentMethod.retrieve(payment_method_id)
        if pm.customer != consumer.stripe_customer_id:
            raise APIError(403, ErrorCode.FORBIDDEN, "Not your payment method")
    except stripe.StripeError:
        raise APIError(404, ErrorCode.PAYMENT_ERROR, "Payment method not found")

    if not delete_payment_method(payment_method_id):
        raise APIError(500, ErrorCode.PAYMENT_PROVIDER_ERROR, "Failed to remove payment method")

    return {"removed": True, "payment_method_id": payment_method_id}


@router.post("/payment-methods/default")
async def set_default_payment_method(
    req: SetDefaultPaymentMethodRequest,
    user: dict = Depends(require_role("consumer")),
    db: AsyncSession = Depends(get_db),
):
    """Set the default payment method for the consumer."""
    if not is_billing_enabled():
        raise APIError(503, ErrorCode.BILLING_NOT_CONFIGURED, "Billing not configured")

    result = await db.execute(select(Consumer).where(Consumer.id == user["id"]))
    consumer = result.scalar_one_or_none()
    if not consumer or not consumer.stripe_customer_id:
        raise APIError(400, ErrorCode.PAYMENT_ERROR, "No Stripe customer configured")

    stripe.api_key = settings.stripe_secret_key
    try:
        pm = stripe.PaymentMethod.retrieve(req.payment_method_id)
        if pm.customer != consumer.stripe_customer_id:
            raise APIError(403, ErrorCode.FORBIDDEN, "Not your payment method")
        stripe.Customer.modify(
            consumer.stripe_customer_id,
            invoice_settings={"default_payment_method": req.payment_method_id},
        )
    except stripe.StripeError:
        raise APIError(400, ErrorCode.PAYMENT_ERROR, "Failed to set default payment method")

    return {"default_payment_method": req.payment_method_id}


# ---- Legacy single-PM status ----


@router.get("/payment-method", response_model=PaymentSetupResponse)
async def get_payment_status(
    user: dict = Depends(require_role("consumer")),
    db: AsyncSession = Depends(get_db),
):
    """Check consumer's payment setup status."""
    result = await db.execute(select(Consumer).where(Consumer.id == user["id"]))
    consumer = result.scalar_one_or_none()
    if not consumer:
        raise APIError(404, ErrorCode.CONSUMER_NOT_FOUND, "Consumer not found")

    if not consumer.stripe_customer_id:
        return PaymentSetupResponse(
            stripe_customer_id="",
            payment_method_attached=False,
            default_payment_method=None,
        )

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


# ---- Stripe Connect (Provider Payouts) ----

connect_router = APIRouter(prefix="/v1/me/connect", tags=["payment"])


@connect_router.post("/onboard", response_model=ConnectOnboardResponse)
async def connect_onboard(
    user: dict = Depends(require_role("provider")),
    db: AsyncSession = Depends(get_db),
):
    """Start Stripe Connect Express onboarding for provider payouts.

    Returns a URL where the provider completes identity verification and
    bank account setup on Stripe's hosted page. One click.
    """
    if not is_billing_enabled():
        raise APIError(503, ErrorCode.BILLING_NOT_CONFIGURED, "Billing not configured")

    result = await db.execute(select(Provider).where(Provider.id == user["id"]))
    provider = result.scalar_one_or_none()
    if not provider:
        raise APIError(404, ErrorCode.PROVIDER_NOT_FOUND, "Provider not found")

    if provider.stripe_connect_id:
        # Already has account, create new onboarding link (for incomplete accounts)
        stripe.api_key = settings.stripe_secret_key
        try:
            link = stripe.AccountLink.create(
                account=provider.stripe_connect_id,
                refresh_url=settings.stripe_connect_refresh_url,
                return_url=settings.stripe_connect_return_url,
                type="account_onboarding",
            )
            return ConnectOnboardResponse(
                account_id=provider.stripe_connect_id,
                onboarding_url=link.url,
            )
        except stripe.StripeError:
            raise APIError(
                502, ErrorCode.PAYMENT_PROVIDER_ERROR,
                "Failed to create onboarding link",
            )

    connect = create_connect_account(
        provider_id=str(provider.id),
        email=provider.email,
        name=provider.name,
    )
    if not connect:
        raise APIError(502, ErrorCode.PAYMENT_PROVIDER_ERROR, "Failed to create Connect account")

    provider.stripe_connect_id = connect["account_id"]
    provider.stripe_connect_status = "pending"
    await db.commit()

    return ConnectOnboardResponse(**connect)


@connect_router.get("/status", response_model=ConnectStatusResponse)
async def connect_status(
    user: dict = Depends(require_role("provider")),
    db: AsyncSession = Depends(get_db),
):
    """Check Stripe Connect account status and get dashboard link."""
    result = await db.execute(select(Provider).where(Provider.id == user["id"]))
    provider = result.scalar_one_or_none()
    if not provider:
        raise APIError(404, ErrorCode.PROVIDER_NOT_FOUND, "Provider not found")

    if not provider.stripe_connect_id:
        raise APIError(
            400, ErrorCode.CONNECT_NOT_READY,
            "No Connect account. Run POST /connect/onboard first",
        )

    status = get_connect_account_status(provider.stripe_connect_id)
    if not status:
        raise APIError(502, ErrorCode.PAYMENT_PROVIDER_ERROR, "Failed to get account status")

    # Update local status
    if status["payouts_enabled"]:
        provider.stripe_connect_status = "active"
    elif status["details_submitted"]:
        provider.stripe_connect_status = "pending"
    else:
        provider.stripe_connect_status = "restricted"
    await db.commit()

    # Dashboard link for active accounts
    dashboard_url = None
    if status["details_submitted"]:
        try:
            dashboard_url = create_connect_login_link(provider.stripe_connect_id)
        except Exception:
            pass

    return ConnectStatusResponse(
        **status,
        dashboard_url=dashboard_url,
    )


# ---- Solana Wallet ----

wallet_router = APIRouter(prefix="/v1/me/wallet", tags=["payment"])

_SOLANA_ADDR_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,64}$")


@wallet_router.post("/solana", response_model=WalletRegisterResponse)
async def register_solana_wallet(
    req: WalletRegisterRequest,
    user: dict = Depends(require_role()),
    db: AsyncSession = Depends(get_db),
):
    """Register and verify a Solana wallet address.

    Works for both consumers (to pay with USDC) and providers (to receive payouts).
    Wallet ownership is verified via Ed25519 signature.
    """
    if not _SOLANA_ADDR_RE.match(req.wallet_address):
        raise APIError(400, ErrorCode.INVALID_WALLET, "Invalid Solana wallet address")

    # Verify signature
    if not verify_wallet_signature(req.wallet_address, req.message, req.signature):
        raise APIError(
            400, ErrorCode.SOLANA_VERIFICATION_FAILED,
            "Wallet signature verification failed",
        )

    if user["role"] == "consumer":
        result = await db.execute(select(Consumer).where(Consumer.id == user["id"]))
        entity = result.scalar_one_or_none()
        if not entity:
            raise APIError(404, ErrorCode.CONSUMER_NOT_FOUND, "Consumer not found")
        entity.solana_wallet = req.wallet_address
    else:
        result = await db.execute(select(Provider).where(Provider.id == user["id"]))
        entity = result.scalar_one_or_none()
        if not entity:
            raise APIError(404, ErrorCode.PROVIDER_NOT_FOUND, "Provider not found")
        entity.solana_wallet = req.wallet_address

    await db.commit()

    return WalletRegisterResponse(
        wallet_address=req.wallet_address,
        verified=True,
    )


@wallet_router.get("/solana")
async def get_solana_wallet(
    user: dict = Depends(require_role()),
    db: AsyncSession = Depends(get_db),
):
    """Get the registered Solana wallet address."""
    if user["role"] == "consumer":
        result = await db.execute(select(Consumer).where(Consumer.id == user["id"]))
        entity = result.scalar_one_or_none()
    else:
        result = await db.execute(select(Provider).where(Provider.id == user["id"]))
        entity = result.scalar_one_or_none()

    if not entity:
        raise APIError(404, ErrorCode.USER_NOT_FOUND, "User not found")

    wallet = getattr(entity, "solana_wallet", None)
    return {
        "wallet_address": wallet,
        "configured": wallet is not None,
        "rail": "solana",
    }


@wallet_router.delete("/solana")
async def remove_solana_wallet(
    user: dict = Depends(require_role()),
    db: AsyncSession = Depends(get_db),
):
    """Remove the registered Solana wallet."""
    if user["role"] == "consumer":
        result = await db.execute(select(Consumer).where(Consumer.id == user["id"]))
        entity = result.scalar_one_or_none()
    else:
        result = await db.execute(select(Provider).where(Provider.id == user["id"]))
        entity = result.scalar_one_or_none()

    if not entity:
        raise APIError(404, ErrorCode.USER_NOT_FOUND, "User not found")

    entity.solana_wallet = None
    await db.commit()
    return {"removed": True}


# ---- Solana Payment Verification ----


@wallet_router.post("/verify-payment", response_model=SolanaPaymentVerifyResponse)
async def verify_solana_payment(
    req: SolanaPaymentVerifyRequest,
    user: dict = Depends(require_role("consumer")),
):
    """Verify a USDC payment on Solana.

    Consumer sends USDC to the platform wallet, then calls this endpoint
    with the transaction signature to verify the transfer on-chain.
    """
    if not is_solana_enabled():
        raise APIError(503, ErrorCode.WALLET_NOT_CONFIGURED, "Solana payments not configured")

    result = await verify_usdc_transfer(
        tx_signature=req.tx_signature,
        expected_amount_lamports=0,  # any amount, will be matched to task
    )

    if result["verified"]:
        amount_usdc = result["amount_lamports"] / 10**6
        return SolanaPaymentVerifyResponse(
            verified=True,
            amount_usdc=amount_usdc,
            tx_signature=req.tx_signature,
        )
    else:
        return SolanaPaymentVerifyResponse(
            verified=False,
            error=result.get("error", "Verification failed"),
        )
