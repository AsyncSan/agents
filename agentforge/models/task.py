"""Task model: contracts submitted by consumers."""

import uuid

from sqlalchemy import ForeignKey, String, Text
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
    )  # pending, dispatching, running, completed, failed
    callback_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    consumer = relationship("Consumer", back_populates="tasks")
    agent = relationship("Agent", back_populates="tasks")
    executions = relationship("Execution", back_populates="task", lazy="selectin")
