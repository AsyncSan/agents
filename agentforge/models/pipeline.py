"""Pipeline model: linear chains of agent tasks."""

import uuid

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agentforge.models.base import Base, TimestampMixin


class Pipeline(Base, TimestampMixin):
    __tablename__ = "pipelines"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)  # "pl-20260411-abc123"
    consumer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("consumers.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50), default="pending"
    )  # pending, running, completed, failed, cancelled
    callback_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Budget tracking across the chain
    max_cost_usd: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    total_authorized_cents: Mapped[int] = mapped_column(Integer, default=0)
    total_captured_cents: Mapped[int] = mapped_column(Integer, default=0)

    # Chain definition and progress
    steps: Mapped[list] = mapped_column(JSONB, nullable=False)
    current_step: Mapped[int] = mapped_column(Integer, default=0)
    chain_trust_score: Mapped[float | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )

    tasks = relationship(
        "Task", back_populates="pipeline", lazy="selectin", order_by="Task.step_index"
    )
