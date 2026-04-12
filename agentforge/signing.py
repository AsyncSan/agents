"""Ed25519 agent card signing and verification.

Provides deterministic canonical JSON serialization and Ed25519 signatures
for agent capability cards. This ensures cards can be verified as authentic
and untampered by anyone with the provider's public key.
"""

import json

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)


def generate_keypair() -> tuple[str, str]:
    """Generate an Ed25519 keypair. Returns (public_key_hex, private_key_hex)."""
    private_key = Ed25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(
        Encoding.Raw, PrivateFormat.Raw, NoEncryption()
    )
    public_bytes = private_key.public_key().public_bytes(
        Encoding.Raw, PublicFormat.Raw
    )
    return public_bytes.hex(), private_bytes.hex()


def canonicalize_card(card: dict) -> bytes:
    """Produce a deterministic JSON representation of a card for signing.

    Strips the 'instructions' field (secret) and any existing 'signature'
    before serialization. Uses sorted keys and no whitespace.
    """
    signable = {k: v for k, v in card.items() if k not in ("instructions", "signature")}
    return json.dumps(signable, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def sign_card(card: dict, private_key_hex: str) -> str:
    """Sign a card's canonical form with Ed25519. Returns hex signature."""
    private_bytes = bytes.fromhex(private_key_hex)
    private_key = Ed25519PrivateKey.from_private_bytes(private_bytes)
    canonical = canonicalize_card(card)
    signature = private_key.sign(canonical)
    return signature.hex()


def verify_card(card: dict, signature_hex: str, public_key_hex: str) -> bool:
    """Verify a card's signature against the provider's public key."""
    try:
        public_bytes = bytes.fromhex(public_key_hex)
        public_key = Ed25519PublicKey.from_public_bytes(public_bytes)
        canonical = canonicalize_card(card)
        signature = bytes.fromhex(signature_hex)
        public_key.verify(signature, canonical)
        return True
    except Exception:
        return False
