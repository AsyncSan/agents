"""Consumer model: users who run agent tasks."""

import uuid

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agentforge.models.base import Base, TimestampMixin


class Consumer(Base, TimestampMixin):
    __tablename__ = "consumers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    api_key_hash: Mapped[str] = mapped_column(Text, nullable=False)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Solana wallet for crypto payments
    solana_wallet: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Encrypted secrets injected into ephemeral servers at /workspace/secrets/consumer/
    # Format: {"OPENAI_API_KEY": "sk-...", "SERPER_API_KEY": "..."}
    secrets: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    tasks = relationship("Task", back_populates="consumer", lazy="selectin")
