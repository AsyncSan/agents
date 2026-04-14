"""Task model: contracts submitted by consumers."""

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agentforge.models.base import Base, TimestampMixin


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)  # "tc-20260410-abc123"
    consumer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("consumers.id"), nullable=False
    )
    agent_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("agents.id"), nullable=False
    )
    inputs: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    constraints: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default="pending"
    )  # pending, authorized, dispatching, running, completed, failed
    callback_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Compute tier override
    compute_tier: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # "container" or "vm" (overrides agent default)

    # Payment tracking
    payment_rail: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # "stripe" or "solana"
    payment_intent_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payment_status: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # authorized, captured, cancelled, refunded
    amount_authorized_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    amount_captured_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    platform_fee_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Solana-specific
    solana_tx_signature: Mapped[str | None] = mapped_column(String(128), nullable=True)
    solana_escrow_address: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Pipeline support
    pipeline_id: Mapped[str | None] = mapped_column(
        String(255), ForeignKey("pipelines.id"), nullable=True
    )
    step_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    consumer = relationship("Consumer", back_populates="tasks")
    agent = relationship("Agent", back_populates="tasks")
    executions = relationship("Execution", back_populates="task", lazy="selectin")
    pipeline = relationship("Pipeline", back_populates="tasks")
