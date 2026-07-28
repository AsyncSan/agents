"""ComplianceDocument: polymorphic store for FRIA, Annex IV, and Literacy artefacts.

One table, three document types. The ``doc_type`` discriminator selects
which wizard produces the payload. ``org_id`` + ``org_role`` identifies
the owning organisation (consumer or provider) without a hard foreign key,
because the two lookup tables are distinct.

Versioning approach for now is simple: every update writes over the
payload but increments ``updated_at``. Snapshots live in the event log and
downloadable artefacts. A future migration can introduce a history table
if formal audit trails of edits are needed.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from agentforge.models.base import Base, TimestampMixin

DOC_TYPES = (
    "fria",
    "annex_iv",
    "literacy_completion",
    "pmm_plan",
    "qms_manual",
    "eu_db_registration",
    "declaration_of_conformity",
)
STATUSES = ("draft", "submitted", "approved", "archived")


class ComplianceDocument(Base, TimestampMixin):
    __tablename__ = "compliance_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    org_role: Mapped[str] = mapped_column(String(20), nullable=False)  # consumer | provider
    doc_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    # Optional agent linkage (literacy is agent-agnostic)
    agent_id: Mapped[str | None] = mapped_column(
        String(255), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    agent_version: Mapped[int | None] = mapped_column(Integer, nullable=True)

    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __mapper_args__ = {"eager_defaults": True}
