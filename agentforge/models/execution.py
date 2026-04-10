"""Execution model: actual runs on ephemeral compute."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agentforge.models.base import Base, TimestampMixin


class Execution(Base, TimestampMixin):
    __tablename__ = "executions"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)  # run_id from dispatcher
    task_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("tasks.id"), nullable=False
    )
    server_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    server_ip: Mapped[str | None] = mapped_column(INET, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default="provisioning"
    )  # provisioning, ready, running, collecting, completed, failed, destroyed
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    elapsed_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    results_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    task = relationship("Task", back_populates="executions")
