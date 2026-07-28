"""QMS manual routes (Art. 17)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.api.auth import get_current_user
from agentforge.api.errors import APIError, ErrorCode
from agentforge.db import get_db
from agentforge.models.agent import Agent
from agentforge.pdf import markdown_to_pdf
from agentforge.qms import VARIANTS, build_qms_template, qms_to_markdown

router = APIRouter(prefix="/v1/qms", tags=["qms"])


class QMSRequest(BaseModel):
    variant: str = Field(default="full")
    agent_id: str | None = None

    # Organisation
    organisation_name: str | None = None
    organisation_contact: str | None = None
    sme_category: str | None = None

    # Section A
    regulatory_policy: str | None = None
    conformity_assessment_route: str | None = None
    substantial_modification_definition: str | None = None

    # Section B
    design_review_procedure: str | None = None
    change_control: str | None = None

    # Section C
    development_methodology: str | None = None
    quality_control: str | None = None

    # Section D
    validation_approach: str | None = None
    testing_environment: str | None = None

    # Section E
    baseline_standards: list[str] | None = None
    harmonised_standards_applied: list[str] | None = None

    # Section F
    deployer_data_policy: str | None = None
    gdpr_bridge: str | None = None

    # Section G
    risk_framework: str | None = None
    risk_review_cadence: str | None = None
    risk_owner: str | None = None

    # Section I
    authority_routing: str | None = None

    # Section J
    authority_contact: str | None = None
    customer_feedback: str | None = None

    # Section L
    infrastructure_security_of_supply: str | None = None
    training_and_competence: str | None = None
    budget_and_staffing: str | None = None

    # Section M
    accountability_owner: str | None = None
    management_review: str | None = None
    internal_audit_schedule: str | None = None
    board_reporting: str | None = None


def _validate_variant(variant: str) -> None:
    if variant not in VARIANTS:
        raise APIError(
            422,
            ErrorCode.INVALID_INPUT,
            f"variant must be one of {list(VARIANTS)}",
        )


async def _load_agent(agent_id: str | None, db: AsyncSession) -> Agent | None:
    if not agent_id:
        return None
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise APIError(404, ErrorCode.AGENT_NOT_FOUND, f"Agent '{agent_id}' not found")
    return agent


def _inputs(req: QMSRequest) -> dict[str, Any]:
    return {
        k: v
        for k, v in req.model_dump().items()
        if v is not None and k not in {"variant", "agent_id"}
    }


@router.get("/variants")
async def list_variants():
    return {
        "variants": [
            {"key": "full", "description": "Full QMS manual per Art. 17"},
            {
                "key": "simplified",
                "description": "Microenterprise simplified form under Art. 63",
            },
        ]
    }


@router.post("/template")
async def create_qms_template(
    req: QMSRequest,
    _: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _validate_variant(req.variant)
    agent = await _load_agent(req.agent_id, db)
    return build_qms_template(_inputs(req), variant=req.variant, agent=agent)


@router.post("/template/markdown", response_class=PlainTextResponse)
async def create_qms_markdown(
    req: QMSRequest,
    _: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _validate_variant(req.variant)
    agent = await _load_agent(req.agent_id, db)
    doc = build_qms_template(_inputs(req), variant=req.variant, agent=agent)
    md = qms_to_markdown(doc)
    suffix = f"-{req.agent_id}" if req.agent_id else ""
    return PlainTextResponse(
        content=md,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="qms-{req.variant}{suffix}.md"'
        },
    )


@router.post("/template/pdf")
async def create_qms_pdf(
    req: QMSRequest,
    _: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _validate_variant(req.variant)
    agent = await _load_agent(req.agent_id, db)
    doc = build_qms_template(_inputs(req), variant=req.variant, agent=agent)
    pdf_bytes = markdown_to_pdf(
        qms_to_markdown(doc),
        title=f"QMS ({req.variant})",
    )
    suffix = f"-{req.agent_id}" if req.agent_id else ""
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="qms-{req.variant}{suffix}.pdf"'
        },
    )


@router.get("/template/public")
async def public_qms_template(variant: str = "full"):
    _validate_variant(variant)
    return build_qms_template({}, variant=variant, agent=None)
