"""Consumer model: users who run agent tasks."""

import uuid

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agentforge.models.base import Base, TimestampMixin


class Consumer(Base, TimestampMixin):
    __tablename__ = "consumers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    api_key_hash: Mapped[str] = mapped_column(Text, nullable=False)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    tasks = relationship("Task", back_populates="consumer", lazy="selectin")
