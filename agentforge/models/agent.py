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

    # EU AI Act risk classification (Art. 6/9): minimal, limited, high
    risk_class: Mapped[str] = mapped_column(String(50), default="minimal")

    # Ed25519 signature of the canonical card (hex)
    signature: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Versioning
    version: Mapped[int] = mapped_column(Integer, default=1)

    # Trust metrics (platform-computed)
    trust_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    total_executions: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_duration_seconds: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    provider = relationship("Provider", back_populates="agents")
    tasks = relationship("Task", back_populates="agent", lazy="selectin")
    versions = relationship("AgentVersion", back_populates="agent", lazy="noload")
