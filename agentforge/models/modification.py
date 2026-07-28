"""ModificationRecord: Art. 43 substantial modification tracking.

Art. 43(4) defines a substantial modification as a change to a
high-risk AI system that is not foreseen by the provider in the initial
conformity assessment, and that affects compliance with the requirements
of Chapter III Section 2, or modifies the intended purpose. When a
substantial modification is made, the conformity assessment procedure
must be repeated.

This table tracks every version change (auto-inserted on agent update)
plus any manual entry a provider records for non-versioned changes
(e.g. updated training data, new oversight measures). Each record
carries a classifier (substantial / non_substantial / unclassified)
which the provider sets after assessment.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from agentforge.models.base import Base, TimestampMixin

MODIFICATION_TYPES = (
    "version_bump",          # Auto: agent.version incremented via PUT /agents
    "card_update",           # Auto: capability card fields changed
    "training_data",         # Manual: new/retrained dataset
    "intended_purpose",      # Manual: changed scope of use
    "oversight_measure",     # Manual: new/changed human oversight control
    "security_control",      # Manual: new/changed security mitigation
    "other",                 # Manual: free-text
)

CLASSIFICATIONS = (
    "unclassified",          # Default for auto-inserted rows; provider must assess
    "substantial",           # Triggers new conformity assessment
    "non_substantial",       # Logged for audit, no reassessment required
)


class ModificationRecord(Base, TimestampMixin):
    __tablename__ = "modification_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    version_to: Mapped[int | None] = mapped_column(Integer, nullable=True)
    modification_type: Mapped[str] = mapped_column(String(40), nullable=False)
    classification: Mapped[str] = mapped_column(
        String(40), nullable=False, default="unclassified"
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    impact_assessment: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    triggered_reassessment: Mapped[bool] = mapped_column(default=False, nullable=False)
    reassessment_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    diff: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)

    __mapper_args__ = {"eager_defaults": True}
