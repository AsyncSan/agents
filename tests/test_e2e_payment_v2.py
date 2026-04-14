"""Tests for Payment v2: Checkout Sessions, Connect, PM CRUD, Solana Wallet, Dual-Rail."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

# --- Stripe Checkout Session ---


class TestCheckoutSession:
    @pytest.mark.asyncio
    async def test_create_checkout_session(self, client: AsyncClient, consumer_key):
        """Consumer can create a Stripe Checkout Session for 1-click payment setup."""
        api_key, _ = consumer_key

        mock_customer = MagicMock()
        mock_customer.id = "cus_test123"

        with (
            patch("agentforge.api.routes_payment.is_billing_enabled", return_value=True),
            patch("agentforge.api.routes_payment.settings") as mock_settings,
            patch("stripe.Customer.create", return_value=mock_customer),
            patch(
                "agentforge.api.routes_payment.create_checkout_session",
                return_value={
                    "session_id": "cs_test_session123",
                    "url": "https://checkout.stripe.com/session/cs_test_session123",
                },
            ),
        ):
            mock_settings.stripe_secret_key = "sk_test_123"

            resp = await client.post(
                "/v1/me/checkout-session",
                headers={"X-API-Key": api_key},
                json={},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert "url" in data
        assert data["url"].startswith("https://")

    @pytest.mark.asyncio
    async def test_checkout_session_billing_disabled(self, client: AsyncClient, consumer_key):
        """Returns 503 when billing is not configured."""
        api_key, _ = consumer_key
        with patch("agentforge.api.routes_payment.is_billing_enabled", return_value=False):
            resp = await client.post(
                "/v1/me/checkout-session",
                headers={"X-API-Key": api_key},
                json={},
            )
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "billing_not_configured"


# --- Payment Method CRUD ---


class TestPaymentMethodCRUD:
    @pytest.mark.asyncio
    async def test_list_payment_methods_empty(self, client: AsyncClient, consumer_key):
        """Consumer with no Stripe customer gets empty list."""
        api_key, _ = consumer_key
        resp = await client.get(
            "/v1/me/payment-methods",
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 200
        assert resp.json()["payment_methods"] == []

    @pytest.mark.asyncio
    async def test_list_payment_methods_with_cards(
        self, client: AsyncClient, consumer_key, db_session
    ):
        """Consumer with Stripe customer gets card list."""
        api_key, cdata = consumer_key

        # Set stripe_customer_id directly in DB
        from sqlalchemy import update

        from agentforge.models.consumer import Consumer

        await db_session.execute(
            update(Consumer)
            .where(Consumer.id == cdata["id"])
            .values(stripe_customer_id="cus_test_list")
        )
        await db_session.commit()

        mock_customer = MagicMock()
        mock_customer.invoice_settings.default_payment_method = "pm_default"

        mock_card = MagicMock()
        mock_card.brand = "visa"
        mock_card.last4 = "4242"
        mock_card.exp_month = 12
        mock_card.exp_year = 2028

        mock_pm = MagicMock()
        mock_pm.id = "pm_default"
        mock_pm.card = mock_card

        mock_methods = MagicMock()
        mock_methods.data = [mock_pm]

        with (
            patch("agentforge.billing.is_billing_enabled", return_value=True),
            patch("agentforge.api.routes_payment.is_billing_enabled", return_value=True),
            patch("agentforge.billing._init_stripe", return_value=True),
            patch("stripe.PaymentMethod.list", return_value=mock_methods),
            patch("stripe.Customer.retrieve", return_value=mock_customer),
        ):
            resp = await client.get(
                "/v1/me/payment-methods",
                headers={"X-API-Key": api_key},
            )

        assert resp.status_code == 200
        methods = resp.json()["payment_methods"]
        assert len(methods) == 1
        assert methods[0]["brand"] == "visa"
        assert methods[0]["last4"] == "4242"
        assert methods[0]["is_default"] is True

    @pytest.mark.asyncio
    async def test_delete_payment_method(
        self, client: AsyncClient, consumer_key, db_session
    ):
        """Consumer can delete a payment method."""
        api_key, cdata = consumer_key

        from sqlalchemy import update

        from agentforge.models.consumer import Consumer

        await db_session.execute(
            update(Consumer)
            .where(Consumer.id == cdata["id"])
            .values(stripe_customer_id="cus_test_del")
        )
        await db_session.commit()

        mock_pm = MagicMock()
        mock_pm.customer = "cus_test_del"

        with (
            patch("agentforge.api.routes_payment.is_billing_enabled", return_value=True),
            patch("agentforge.api.routes_payment.settings") as mock_settings,
            patch("stripe.PaymentMethod.retrieve", return_value=mock_pm),
            patch("agentforge.api.routes_payment.delete_payment_method", return_value=True),
        ):
            mock_settings.stripe_secret_key = "sk_test_123"
            resp = await client.delete(
                "/v1/me/payment-methods/pm_test123",
                headers={"X-API-Key": api_key},
            )

        assert resp.status_code == 200
        assert resp.json()["removed"] is True

    @pytest.mark.asyncio
    async def test_delete_other_users_pm_forbidden(
        self, client: AsyncClient, consumer_key, db_session
    ):
        """Cannot delete another consumer's payment method."""
        api_key, cdata = consumer_key

        from sqlalchemy import update

        from agentforge.models.consumer import Consumer

        await db_session.execute(
            update(Consumer)
            .where(Consumer.id == cdata["id"])
            .values(stripe_customer_id="cus_mine")
        )
        await db_session.commit()

        mock_pm = MagicMock()
        mock_pm.customer = "cus_other_user"

        with (
            patch("agentforge.api.routes_payment.is_billing_enabled", return_value=True),
            patch("agentforge.api.routes_payment.settings") as mock_settings,
            patch("stripe.PaymentMethod.retrieve", return_value=mock_pm),
        ):
            mock_settings.stripe_secret_key = "sk_test_123"
            resp = await client.delete(
                "/v1/me/payment-methods/pm_other",
                headers={"X-API-Key": api_key},
            )

        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "forbidden"

    @pytest.mark.asyncio
    async def test_set_default_payment_method(
        self, client: AsyncClient, consumer_key, db_session
    ):
        """Consumer can set a default payment method."""
        api_key, cdata = consumer_key

        from sqlalchemy import update

        from agentforge.models.consumer import Consumer

        await db_session.execute(
            update(Consumer)
            .where(Consumer.id == cdata["id"])
            .values(stripe_customer_id="cus_test_default")
        )
        await db_session.commit()

        mock_pm = MagicMock()
        mock_pm.customer = "cus_test_default"

        with (
            patch("agentforge.api.routes_payment.is_billing_enabled", return_value=True),
            patch("agentforge.api.routes_payment.settings") as mock_settings,
            patch("stripe.PaymentMethod.retrieve", return_value=mock_pm),
            patch("stripe.Customer.modify"),
        ):
            mock_settings.stripe_secret_key = "sk_test_123"
            resp = await client.post(
                "/v1/me/payment-methods/default",
                headers={"X-API-Key": api_key},
                json={"payment_method_id": "pm_test_def"},
            )

        assert resp.status_code == 200
        assert resp.json()["default_payment_method"] == "pm_test_def"


# --- Stripe Connect (Provider) ---


class TestStripeConnect:
    @pytest.mark.asyncio
    async def test_connect_onboard(self, client: AsyncClient, provider_key):
        """Provider can start Stripe Connect onboarding."""
        api_key, _ = provider_key

        with (
            patch("agentforge.api.routes_payment.is_billing_enabled", return_value=True),
            patch(
                "agentforge.api.routes_payment.create_connect_account",
                return_value={
                    "account_id": "acct_test123",
                    "onboarding_url": "https://connect.stripe.com/setup/acct_test123",
                },
            ),
        ):
            resp = await client.post(
                "/v1/me/connect/onboard",
                headers={"X-API-Key": api_key},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["account_id"] == "acct_test123"
        assert "stripe.com" in data["onboarding_url"]

    @pytest.mark.asyncio
    async def test_connect_status_no_account(self, client: AsyncClient, provider_key):
        """Provider without Connect account gets error."""
        api_key, _ = provider_key
        with patch("agentforge.api.routes_payment.is_billing_enabled", return_value=True):
            resp = await client.get(
                "/v1/me/connect/status",
                headers={"X-API-Key": api_key},
            )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "connect_not_ready"

    @pytest.mark.asyncio
    async def test_connect_status_with_account(
        self, client: AsyncClient, provider_key, db_session
    ):
        """Provider with Connect account gets status."""
        api_key, pdata = provider_key

        from sqlalchemy import update

        from agentforge.models.provider import Provider

        await db_session.execute(
            update(Provider)
            .where(Provider.id == pdata["id"])
            .values(
                stripe_connect_id="acct_test_status",
                stripe_connect_status="pending",
            )
        )
        await db_session.commit()

        with (
            patch("agentforge.api.routes_payment.is_billing_enabled", return_value=True),
            patch(
                "agentforge.api.routes_payment.get_connect_account_status",
                return_value={
                    "account_id": "acct_test_status",
                    "charges_enabled": True,
                    "payouts_enabled": True,
                    "details_submitted": True,
                    "requirements": {
                        "currently_due": [],
                        "eventually_due": [],
                        "disabled_reason": None,
                    },
                },
            ),
            patch(
                "agentforge.api.routes_payment.create_connect_login_link",
                return_value="https://connect.stripe.com/login/acct_test_status",
            ),
        ):
            resp = await client.get(
                "/v1/me/connect/status",
                headers={"X-API-Key": api_key},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["charges_enabled"] is True
        assert data["payouts_enabled"] is True
        assert data["dashboard_url"] is not None

    @pytest.mark.asyncio
    async def test_connect_consumer_forbidden(self, client: AsyncClient, consumer_key):
        """Consumer cannot access Connect endpoints."""
        api_key, _ = consumer_key
        with patch("agentforge.api.routes_payment.is_billing_enabled", return_value=True):
            resp = await client.post(
                "/v1/me/connect/onboard",
                headers={"X-API-Key": api_key},
            )
        assert resp.status_code == 403


# --- Solana Wallet ---


class TestSolanaWallet:
    @pytest.mark.asyncio
    async def test_register_wallet(self, client: AsyncClient, consumer_key):
        """Consumer can register a Solana wallet."""
        api_key, _ = consumer_key

        with patch(
            "agentforge.api.routes_payment.verify_wallet_signature",
            return_value=True,
        ):
            resp = await client.post(
                "/v1/me/wallet/solana",
                headers={"X-API-Key": api_key},
                json={
                    "wallet_address": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
                    "signature": "dGVzdHNpZw==",
                    "message": "Verify wallet ownership",
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["verified"] is True
        assert data["wallet_address"] == "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"

    @pytest.mark.asyncio
    async def test_register_wallet_invalid_signature(
        self, client: AsyncClient, consumer_key
    ):
        """Rejects wallet with invalid signature."""
        api_key, _ = consumer_key

        with patch(
            "agentforge.api.routes_payment.verify_wallet_signature",
            return_value=False,
        ):
            resp = await client.post(
                "/v1/me/wallet/solana",
                headers={"X-API-Key": api_key},
                json={
                    "wallet_address": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
                    "signature": "badsig",
                    "message": "Verify wallet ownership",
                },
            )

        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "solana_verification_failed"

    @pytest.mark.asyncio
    async def test_get_wallet_not_set(self, client: AsyncClient, consumer_key):
        """Returns configured=false when no wallet set."""
        api_key, _ = consumer_key
        resp = await client.get(
            "/v1/me/wallet/solana",
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 200
        assert resp.json()["configured"] is False

    @pytest.mark.asyncio
    async def test_get_wallet_after_register(self, client: AsyncClient, consumer_key):
        """Wallet is retrievable after registration."""
        api_key, _ = consumer_key

        with patch(
            "agentforge.api.routes_payment.verify_wallet_signature",
            return_value=True,
        ):
            await client.post(
                "/v1/me/wallet/solana",
                headers={"X-API-Key": api_key},
                json={
                    "wallet_address": "9xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
                    "signature": "dGVzdHNpZw==",
                    "message": "Verify wallet",
                },
            )

        resp = await client.get(
            "/v1/me/wallet/solana",
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["configured"] is True
        assert data["wallet_address"] == "9xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"

    @pytest.mark.asyncio
    async def test_remove_wallet(self, client: AsyncClient, consumer_key):
        """Consumer can remove their wallet."""
        api_key, _ = consumer_key

        # Register first
        with patch(
            "agentforge.api.routes_payment.verify_wallet_signature",
            return_value=True,
        ):
            await client.post(
                "/v1/me/wallet/solana",
                headers={"X-API-Key": api_key},
                json={
                    "wallet_address": "AxKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
                    "signature": "dGVzdHNpZw==",
                    "message": "Verify",
                },
            )

        resp = await client.delete(
            "/v1/me/wallet/solana",
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 200
        assert resp.json()["removed"] is True

        # Verify removed
        resp = await client.get(
            "/v1/me/wallet/solana",
            headers={"X-API-Key": api_key},
        )
        assert resp.json()["configured"] is False

    @pytest.mark.asyncio
    async def test_provider_wallet(self, client: AsyncClient, provider_key):
        """Provider can also register a Solana wallet for payouts."""
        api_key, _ = provider_key

        with patch(
            "agentforge.api.routes_payment.verify_wallet_signature",
            return_value=True,
        ):
            resp = await client.post(
                "/v1/me/wallet/solana",
                headers={"X-API-Key": api_key},
                json={
                    "wallet_address": "BxKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
                    "signature": "dGVzdHNpZw==",
                    "message": "Verify",
                },
            )

        assert resp.status_code == 200
        assert resp.json()["verified"] is True


# --- Solana Payment Verification ---


class TestSolanaPaymentVerify:
    @pytest.mark.asyncio
    async def test_verify_payment_success(self, client: AsyncClient, consumer_key):
        """Consumer can verify a USDC transfer."""
        api_key, _ = consumer_key

        with (
            patch(
                "agentforge.api.routes_payment.is_solana_enabled",
                return_value=True,
            ),
            patch(
                "agentforge.api.routes_payment.verify_usdc_transfer",
                new_callable=AsyncMock,
                return_value={
                    "verified": True,
                    "amount_lamports": 5_000_000,
                    "sender": "SenderWallet123",
                    "destination": "PlatformWallet",
                    "tx_signature": "5VERYlongTxSig" + "x" * 50,
                },
            ),
        ):
            resp = await client.post(
                "/v1/me/wallet/verify-payment",
                headers={"X-API-Key": api_key},
                json={"tx_signature": "5VERYlongTxSig" + "x" * 50},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["verified"] is True
        assert data["amount_usdc"] == 5.0

    @pytest.mark.asyncio
    async def test_verify_payment_failed(self, client: AsyncClient, consumer_key):
        """Failed verification returns error."""
        api_key, _ = consumer_key

        with (
            patch(
                "agentforge.api.routes_payment.is_solana_enabled",
                return_value=True,
            ),
            patch(
                "agentforge.api.routes_payment.verify_usdc_transfer",
                new_callable=AsyncMock,
                return_value={"verified": False, "error": "No matching transfer"},
            ),
        ):
            resp = await client.post(
                "/v1/me/wallet/verify-payment",
                headers={"X-API-Key": api_key},
                json={"tx_signature": "5FAILEDtxSignature" + "x" * 50},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["verified"] is False
        assert data["error"] is not None

    @pytest.mark.asyncio
    async def test_verify_payment_solana_disabled(
        self, client: AsyncClient, consumer_key
    ):
        """Returns 503 when Solana is not configured."""
        api_key, _ = consumer_key

        with patch(
            "agentforge.api.routes_payment.is_solana_enabled",
            return_value=False,
        ):
            resp = await client.post(
                "/v1/me/wallet/verify-payment",
                headers={"X-API-Key": api_key},
                json={"tx_signature": "5SomeTxSig" + "x" * 55},
            )

        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "wallet_not_configured"


# --- Dual-Rail Payment Selection ---


class TestDualRailPayment:
    @pytest.mark.asyncio
    async def test_task_with_stripe_rail(
        self, client: AsyncClient, consumer_key, seed_agent
    ):
        """Task submission with explicit stripe rail."""
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/tasks",
            headers={"X-API-Key": api_key},
            json={
                "agent_id": seed_agent["id"],
                "inputs": {"topic": "test"},
                "payment_rail": "stripe",
            },
        )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_task_with_solana_rail(
        self, client: AsyncClient, consumer_key, seed_agent
    ):
        """Task submission with solana rail."""
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/tasks",
            headers={"X-API-Key": api_key},
            json={
                "agent_id": seed_agent["id"],
                "inputs": {"topic": "test"},
                "payment_rail": "solana",
            },
        )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_task_invalid_rail(
        self, client: AsyncClient, consumer_key, seed_agent
    ):
        """Invalid payment rail is rejected by schema validation."""
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/tasks",
            headers={"X-API-Key": api_key},
            json={
                "agent_id": seed_agent["id"],
                "inputs": {"topic": "test"},
                "payment_rail": "bitcoin",
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_task_default_rail_is_none(
        self, client: AsyncClient, consumer_key, seed_agent
    ):
        """Task without payment_rail defaults to None (Stripe used at dispatch)."""
        api_key, _ = consumer_key
        resp = await client.post(
            "/v1/tasks",
            headers={"X-API-Key": api_key},
            json={
                "agent_id": seed_agent["id"],
                "inputs": {"topic": "test"},
            },
        )
        assert resp.status_code == 201


# --- Me Endpoint shows wallet/connect ---


class TestMePaymentInfo:
    @pytest.mark.asyncio
    async def test_me_shows_solana_wallet(self, client: AsyncClient, consumer_key):
        """Me endpoint includes solana_wallet field."""
        api_key, _ = consumer_key
        resp = await client.get(
            "/v1/me",
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "solana_wallet" in data

    @pytest.mark.asyncio
    async def test_me_shows_connect_status(self, client: AsyncClient, provider_key):
        """Me endpoint includes connect_status for providers."""
        api_key, _ = provider_key
        resp = await client.get(
            "/v1/me",
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "connect_status" in data
