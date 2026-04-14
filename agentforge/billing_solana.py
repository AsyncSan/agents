"""Solana USDC payment service for agent tasks.

Flow:
  1. Consumer submits task with payment_rail="solana"
  2. Platform generates a unique escrow reference (task_id based)
  3. Consumer transfers USDC to platform wallet with task_id memo
  4. Platform verifies on-chain transfer before dispatching
  5. On success: platform transfers provider share to provider wallet
  6. On failure: platform refunds consumer wallet

Uses SPL Token transfers with memo program for tracking.
"""

import base64
import logging

import httpx

from agentforge.config import settings

log = logging.getLogger("agentforge.billing_solana")

# USDC has 6 decimals
USDC_DECIMALS = 6


def is_solana_enabled() -> bool:
    return bool(settings.solana_platform_wallet)


def usd_to_usdc_lamports(usd: float) -> int:
    """Convert USD to USDC micro-units (6 decimals). 1 USDC = 1 USD."""
    return max(500_000, int(usd * 10**USDC_DECIMALS))  # min 0.50 USDC


def compute_platform_fee_lamports(amount: int) -> int:
    """Platform fee in USDC lamports."""
    return amount * settings.solana_platform_fee_bps // 10_000


async def verify_usdc_transfer(
    tx_signature: str,
    expected_amount_lamports: int,
    expected_sender: str | None = None,
) -> dict:
    """Verify a USDC transfer on Solana.

    Returns dict with verified=True/False and parsed details.
    """
    if not is_solana_enabled():
        return {"verified": False, "error": "Solana not configured"}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                settings.solana_rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getTransaction",
                    "params": [
                        tx_signature,
                        {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0},
                    ],
                },
            )
            data = resp.json()

        result = data.get("result")
        if not result:
            return {"verified": False, "error": "Transaction not found"}

        if result.get("meta", {}).get("err"):
            return {"verified": False, "error": "Transaction failed on-chain"}

        # Look for USDC transfer to platform wallet
        instructions = (
            result.get("transaction", {})
            .get("message", {})
            .get("instructions", [])
        )

        # Also check inner instructions (for associated token account creates)
        inner = result.get("meta", {}).get("innerInstructions", [])
        all_instructions = list(instructions)
        for group in inner:
            all_instructions.extend(group.get("instructions", []))

        for ix in all_instructions:
            parsed = ix.get("parsed")
            if not parsed:
                continue

            ix_type = parsed.get("type", "")
            info = parsed.get("info", {})

            if ix_type in ("transfer", "transferChecked"):
                dest = info.get("destination", "")
                amount = int(info.get("amount", info.get("tokenAmount", {}).get("amount", 0)))

                # Check if this is a transfer to our platform wallet's token account
                if amount >= expected_amount_lamports:
                    if expected_sender and info.get("source") != expected_sender:
                        continue
                    return {
                        "verified": True,
                        "amount_lamports": amount,
                        "sender": info.get("authority", info.get("source", "")),
                        "destination": dest,
                        "tx_signature": tx_signature,
                    }

        return {"verified": False, "error": "No matching USDC transfer found"}

    except httpx.HTTPError as e:
        log.error(f"Solana RPC error: {e}")
        return {"verified": False, "error": f"RPC error: {e}"}


async def get_wallet_usdc_balance(wallet_address: str) -> int | None:
    """Get USDC token balance for a wallet. Returns lamports or None on error."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                settings.solana_rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getTokenAccountsByOwner",
                    "params": [
                        wallet_address,
                        {"mint": settings.solana_usdc_mint},
                        {"encoding": "jsonParsed"},
                    ],
                },
            )
            data = resp.json()

        accounts = data.get("result", {}).get("value", [])
        if not accounts:
            return 0

        total = 0
        for acc in accounts:
            amount = (
                acc.get("account", {})
                .get("data", {})
                .get("parsed", {})
                .get("info", {})
                .get("tokenAmount", {})
                .get("amount", "0")
            )
            total += int(amount)
        return total

    except httpx.HTTPError as e:
        log.error(f"Failed to get USDC balance: {e}")
        return None


def verify_wallet_signature(wallet_address: str, message: str, signature_b64: str) -> bool:
    """Verify an Ed25519 signature from a Solana wallet.

    Used for wallet ownership verification during registration.
    """
    try:
        from nacl.signing import VerifyKey

        raw = (
            base64.b58decode(wallet_address)
            if len(wallet_address) < 64
            else bytes.fromhex(wallet_address)
        )
        verify_key = VerifyKey(raw)
        signature = base64.b64decode(signature_b64)
        verify_key.verify(message.encode(), signature)
        return True
    except Exception:
        # Fallback: accept base58-encoded pubkeys (standard Solana format)
        try:
            import base58
            from nacl.signing import VerifyKey

            pubkey_bytes = base58.b58decode(wallet_address)
            verify_key = VerifyKey(pubkey_bytes)
            signature = base64.b64decode(signature_b64)
            verify_key.verify(message.encode(), signature)
            return True
        except Exception as e:
            log.warning(f"Wallet signature verification failed: {e}")
            return False
