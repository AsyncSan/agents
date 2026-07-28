"""AuditShare: read-only share tokens for external auditors.

Every organisation needs to let an outside auditor inspect their
compliance posture without handing over an API key. An AuditShare is a
scoped, time-limited, revokable token that unlocks read-only endpoints
for a subset of the org's data (all agents, or a single one).

The token itself is stored as a SHA-256 hash on the server. The raw
token is returned only once, at creation, so an accidental DB leak does
not expose active shares.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from agentforge.models.base import Base, TimestampMixin


class AuditShare(Base, TimestampMixin):
    __tablename__ = "audit_shares"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    org_role: Mapped[str] = mapped_column(String(20), nullable=False)

    # Label shown to the owner; never exposed to the auditor.
    label: Mapped[str] = mapped_column(String(255), nullable=False)

    # SHA-256 hex digest of the raw token.
    token_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    token_prefix: Mapped[str] = mapped_column(String(12), nullable=False)

    # Optional scope: single agent_id, or null for all agents in the org.
    scope_agent_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Auditor contact (optional, for the owner's records).
    auditor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    auditor_organisation: Mapped[str | None] = mapped_column(String(255), nullable=True)
    auditor_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    access_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_accessed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)

    __mapper_args__ = {"eager_defaults": True}
