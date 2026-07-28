"""Webhook model: subscriber endpoints for event delivery."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from agentforge.models.base import Base, TimestampMixin


class Webhook(Base, TimestampMixin):
    __tablename__ = "webhooks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )  # consumer or provider UUID
    owner_role: Mapped[str] = mapped_column(String(50), nullable=False)  # consumer, provider

    url: Mapped[str] = mapped_column(Text, nullable=False)
    webhook_type: Mapped[str] = mapped_column(
        String(50), default="generic"
    )  # generic, slack
    secret: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # HMAC signing secret for payload verification
    event_types: Mapped[list] = mapped_column(
        ARRAY(String(100)), nullable=False
    )  # ["task.completed", "agent.created", "*"]
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Delivery stats
    total_deliveries: Mapped[int] = mapped_column(default=0)
    total_failures: Mapped[int] = mapped_column(default=0)
    last_delivery_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
