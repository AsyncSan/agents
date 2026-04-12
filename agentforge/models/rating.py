"""Rating model: consumer feedback on completed tasks."""

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agentforge.models.base import Base, TimestampMixin


class Rating(Base, TimestampMixin):
    __tablename__ = "ratings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    task_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("tasks.id"), nullable=False, unique=True
    )
    consumer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("consumers.id"), nullable=False
    )
    agent_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("agents.id"), nullable=False, index=True
    )
    score: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # 1-5
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("score >= 1 AND score <= 5", name="ck_rating_score_range"),
    )

    task = relationship("Task", backref="rating")
    consumer = relationship("Consumer")
    agent = relationship("Agent")
