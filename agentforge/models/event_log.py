"""EventLog model: immutable audit trail for platform events."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from agentforge.models.base import Base


class EventLog(Base):
    __tablename__ = "event_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # agent.created, task.completed, payment.captured, etc.
    actor_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )  # user/system that triggered it
    actor_role: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # provider, consumer, system
    resource_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # agent, task, execution, pipeline, webhook
    resource_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
