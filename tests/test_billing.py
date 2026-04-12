"""Tests for the billing service."""

from unittest.mock import MagicMock, patch

from agentforge.billing import (
    compute_platform_fee,
    is_billing_enabled,
    price_to_cents,
)


class TestPriceToCents:
    def test_basic_conversion(self):
        assert price_to_cents(1.00) == 100

    def test_decimal_rounds_up(self):
        assert price_to_cents(2.99) == 299

    def test_small_amount_rounds_up(self):
        assert price_to_cents(0.01) == 50  # minimum $0.50

    def test_zero_returns_minimum(self):
        assert price_to_cents(0) == 50

    def test_large_amount(self):
        assert price_to_cents(99.99) == 9999

    def test_fractional_cents(self):
        assert price_to_cents(1.005) == 101  # rounds up


class TestBillingEnabled:
    @patch("agentforge.billing.settings")
    def test_disabled_when_no_key(self, mock_settings):
        mock_settings.stripe_secret_key = ""
        assert is_billing_enabled() is False

    @patch("agentforge.billing.settings")
    def test_enabled_when_key_set(self, mock_settings):
        mock_settings.stripe_secret_key = "sk_test_123"
        assert is_billing_enabled() is True


class TestPlatformFee:
    @patch("agentforge.billing.settings")
    def test_default_20_percent(self, mock_settings):
        mock_settings.stripe_platform_fee_percent = 20
        assert compute_platform_fee(500) == 100

    @patch("agentforge.billing.settings")
    def test_rounds_correctly(self, mock_settings):
        mock_settings.stripe_platform_fee_percent = 20
        assert compute_platform_fee(299) == 60  # 59.8 -> 60

    @patch("agentforge.billing.settings")
    def test_zero_amount(self, mock_settings):
        mock_settings.stripe_platform_fee_percent = 20
        assert compute_platform_fee(0) == 0

    @patch("agentforge.billing.settings")
    def test_custom_percentage(self, mock_settings):
        mock_settings.stripe_platform_fee_percent = 10
        assert compute_platform_fee(1000) == 100


class TestAuthorizePayment:
    @patch("agentforge.billing.settings")
    def test_skips_when_not_configured(self, mock_settings):
        mock_settings.stripe_secret_key = ""
        from agentforge.billing import authorize_task_payment

        result = authorize_task_payment("tc-test-001", 5.00)
        assert result["payment_intent_id"] is None
        assert result["amount_cents"] is None

    @patch("agentforge.billing.stripe")
    @patch("agentforge.billing.settings")
    def test_creates_intent_with_manual_capture(self, mock_settings, mock_stripe):
        mock_settings.stripe_secret_key = "sk_test_123"

        mock_intent = MagicMock()
        mock_intent.id = "pi_test_123"
        mock_intent.client_secret = "pi_test_123_secret"
        mock_stripe.PaymentIntent.create.return_value = mock_intent

        from agentforge.billing import authorize_task_payment

        result = authorize_task_payment("tc-test-001", 5.00)

        assert result["payment_intent_id"] == "pi_test_123"
        assert result["amount_cents"] == 500

        call_kwargs = mock_stripe.PaymentIntent.create.call_args
        assert call_kwargs.kwargs["amount"] == 500
        assert call_kwargs.kwargs["capture_method"] == "manual"
        assert call_kwargs.kwargs["currency"] == "usd"


class TestCapturePayment:
    @patch("agentforge.billing.settings")
    def test_noop_when_not_configured(self, mock_settings):
        mock_settings.stripe_secret_key = ""
        from agentforge.billing import capture_payment

        result = capture_payment("tc-test", "pi_test")
        assert result["captured"] is True
        assert result["fee_cents"] == 0

    @patch("agentforge.billing.stripe")
    @patch("agentforge.billing.settings")
    def test_captures_successfully(self, mock_settings, mock_stripe):
        mock_settings.stripe_secret_key = "sk_test_123"
        mock_settings.stripe_platform_fee_percent = 20

        mock_intent = MagicMock()
        mock_intent.status = "succeeded"
        mock_intent.amount = 500
        mock_stripe.PaymentIntent.capture.return_value = mock_intent

        from agentforge.billing import capture_payment

        result = capture_payment("tc-test", "pi_test", amount_cents=500)
        assert result["captured"] is True
        assert result["fee_cents"] == 100


class TestCancelPayment:
    @patch("agentforge.billing.stripe")
    @patch("agentforge.billing.settings")
    def test_cancels_successfully(self, mock_settings, mock_stripe):
        mock_settings.stripe_secret_key = "sk_test_123"

        mock_intent = MagicMock()
        mock_intent.status = "canceled"
        mock_stripe.PaymentIntent.cancel.return_value = mock_intent

        from agentforge.billing import cancel_payment

        assert cancel_payment("tc-test", "pi_test") is True


class TestWebhookVerification:
    @patch("agentforge.billing.settings")
    def test_returns_none_when_no_secret(self, mock_settings):
        mock_settings.stripe_webhook_secret = ""
        from agentforge.billing import verify_webhook_signature

        assert verify_webhook_signature(b"payload", "sig") is None
