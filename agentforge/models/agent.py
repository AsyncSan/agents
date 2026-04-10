"""Agent model: capability cards registered by providers."""

import uuid

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agentforge.models.base import Base, TimestampMixin


class Agent(Base, TimestampMixin):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)  # slug: "code-review-python"
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    card: Mapped[dict] = mapped_column(JSONB, nullable=False)  # full AgentCapabilityCard
    status: Mapped[str] = mapped_column(String(50), default="active")

    # Trust metrics (platform-computed)
    trust_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    total_executions: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)

    provider = relationship("Provider", back_populates="agents")
    tasks = relationship("Task", back_populates="agent", lazy="selectin")
