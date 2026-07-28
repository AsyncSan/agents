"""OversightAssignment: Art. 14 + Art. 26(2) human-oversight role tracking.

Art. 14 requires that high-risk systems are effectively overseen by
natural persons during the period in which they are in use. Art. 26(2)
extends this to deployers: they must assign oversight to natural persons
who have the necessary competence, training, and authority, plus the
necessary support.

An auditor asking "who exactly is responsible for overseeing this
system, and what is their training evidence?" needs a single, printable
answer. This table is that answer.

One OversightAssignment links one named staff member to one oversight
role, scoped to one or more agents, and references the training
certificates that back their competence.
"""

import uuid

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from agentforge.models.base import Base, TimestampMixin

OVERSIGHT_ROLES = (
    "approver",       # Approves awaiting_approval tasks; has authority to reject
    "reviewer",       # Reviews outputs post-hoc; can flag for re-run
    "operator",       # Day-to-day user of the system
    "overseer",       # Formal Art. 14 human-oversight officer
    "incident_owner", # Responsible for incident response (Art. 73)
)

AUTHORITY_LEVELS = (
    "read_only",       # Can view, cannot act
    "review",          # Can flag, cannot approve/reject
    "approve",         # Can approve or reject awaiting tasks
    "override",        # Can override system outputs / halt operation
    "deputy_provider", # Can act on behalf of the provider
)


class OversightAssignment(Base, TimestampMixin):
    __tablename__ = "oversight_assignments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    org_role: Mapped[str] = mapped_column(String(20), nullable=False)

    staff_name: Mapped[str] = mapped_column(String(255), nullable=False)
    staff_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    staff_role_title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    oversight_role: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    authority_level: Mapped[str] = mapped_column(String(40), nullable=False)

    # Optional: pin assignment to specific agents. Empty list / null => org-wide.
    assigned_agent_ids: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(255)), nullable=True
    )

    # References to Art. 4 literacy completions (certificate_id fingerprints
    # or ComplianceDocument IDs of literacy_completion docs).
    training_certificates: Mapped[list[dict] | None] = mapped_column(
        JSONB, nullable=True
    )

    # Free-text record of competence, prior experience, other training.
    competence_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Rationale for why this person is qualified for this role.
    authority_source: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Optional: who assigned this person (for accountability).
    assigned_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    active: Mapped[bool] = mapped_column(default=True, nullable=False)

    __mapper_args__ = {"eager_defaults": True}
