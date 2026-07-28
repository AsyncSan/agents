"""IncidentReport: Art. 73 serious incident tracking.

Art. 73 requires providers of high-risk AI systems to report serious
incidents to the national market surveillance authority. This model tracks
incidents from detection through resolution, with deadline metadata
derived from the assigned severity category.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from agentforge.models.base import Base, TimestampMixin

# Art. 3(49) categories of serious incident
SEVERITIES = (
    "death_or_serious_health",  # 15 days
    "critical_infrastructure",  # 10 days (shortest under Art. 73.4 subpara 2)
    "fundamental_rights",        # 10 days
    "widespread_infringement",   # 2 days
    "serious_property_harm",     # 15 days
    "environmental_harm",        # 15 days
)

STATUSES = (
    "draft",
    "confirmed",
    "reported",
    "under_investigation",
    "resolved",
    "withdrawn",
)


class IncidentReport(Base, TimestampMixin):
    __tablename__ = "incident_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    org_role: Mapped[str] = mapped_column(String(20), nullable=False)

    agent_id: Mapped[str | None] = mapped_column(
        String(255), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    agent_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    task_id: Mapped[str | None] = mapped_column(
        String(255), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )

    severity: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft", index=True)

    # Event timing
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    awareness_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )  # when provider became aware; deadline counts from here

    # Narrative
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    affected_persons_estimate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    mitigation_taken: Mapped[str | None] = mapped_column(Text, nullable=True)
    mitigation_planned: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Reporting
    reported_to_authority_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    authority_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    authority_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Audit
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    extra: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __mapper_args__ = {"eager_defaults": True}
