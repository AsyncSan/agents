"""Provider model: developers who publish agents."""

import uuid

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agentforge.models.base import Base, TimestampMixin


class Provider(Base, TimestampMixin):
    __tablename__ = "providers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    api_key_hash: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Ed25519 keypair for signing agent cards
    signing_public_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    signing_private_key: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Stripe Connect (provider payouts)
    stripe_connect_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_connect_status: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # pending, active, restricted, disabled

    # Solana wallet for crypto payouts
    solana_wallet: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Provider secrets injected into ephemeral servers at /workspace/secrets/provider/
    # Format: {"ANTHROPIC_API_KEY": "sk-...", "GH_TOKEN": "ghp_..."}
    secrets: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    agents = relationship("Agent", back_populates="provider", lazy="selectin")
