"""Annex IV technical documentation routes (Art. 11)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.annex_iv import (
    VARIANTS,
    annex_iv_to_markdown,
    build_annex_iv_template,
)
from agentforge.api.auth import get_current_user
from agentforge.api.errors import APIError, ErrorCode
from agentforge.db import get_db
from agentforge.manual_agent import ManualAgentInput, build_manual_agent
from agentforge.models.agent import Agent
from agentforge.pdf import markdown_to_pdf

router = APIRouter(prefix="/v1/annex-iv", tags=["annex-iv"])


class AnnexIVRequest(BaseModel):
    agent_id: str | None = None
    manual_agent: ManualAgentInput | None = None
    variant: str = Field(default="full")
    provider_name: str | None = None
    provider_contact: str | None = None
    development_methodology: str | None = None
    third_party_components: list[str] | None = None
    training_data_summary: str | None = None
    validation_and_testing: str | None = None
    pre_determined_changes: str | None = None
    continuous_learning_behaviour: str | None = None
    known_limitations: list[str] | None = None
    foreseeable_unintended_outcomes: list[str] | None = None
    metric_rationale: str | None = None
    robustness_testing: str | None = None
    cybersecurity_testing: list[str] | None = None
    rms_owner: str | None = None
    identified_risks: list[str] | None = None
    mitigation_measures: list[str] | None = None
    review_cadence: str | None = None
    substantial_modification_definition: str | None = None
    harmonised_standards_applied: list[str] | None = None
    common_specifications_applied: list[str] | None = None
    other_adopted_solutions: list[str] | None = None
    declaration_of_conformity_reference: str | None = None
    ce_marking_affixed: bool | None = None
    eu_database_registration: str | None = None
    monitoring_plan_summary: str | None = None
    incident_reporting_process: str | None = None
    feedback_channels: list[str] | None = None
    third_country_variants: str | None = None


async def _load_agent(agent_id: str, db: AsyncSession) -> Agent:
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise APIError(404, ErrorCode.AGENT_NOT_FOUND, f"Agent '{agent_id}' not found")
    return agent


async def _resolve_agent(req: AnnexIVRequest, db: AsyncSession):
    if req.manual_agent is not None:
        try:
            return build_manual_agent(req.manual_agent)
        except ValueError as exc:
            raise APIError(422, ErrorCode.INVALID_INPUT, str(exc)) from exc
    if not req.agent_id:
        raise APIError(
            422,
            ErrorCode.INVALID_INPUT,
            "Provide either agent_id (platform agent) or manual_agent (external system).",
        )
    return await _load_agent(req.agent_id, db)


def _provider_inputs(req: AnnexIVRequest) -> dict[str, Any]:
    skip = {"agent_id", "variant", "manual_agent"}
    return {k: v for k, v in req.model_dump().items() if v is not None and k not in skip}


def _validate_variant(variant: str) -> None:
    if variant not in VARIANTS:
        raise APIError(
            422,
            ErrorCode.INVALID_INPUT,
            f"variant must be one of {list(VARIANTS)}",
        )


@router.get("/variants")
async def list_variants():
    """Supported Annex IV variants."""
    return {
        "variants": [
            {"key": "full", "description": "Full Annex IV documentation (default)"},
            {
                "key": "simplified",
                "description": "SME simplified form under Art. 11(1) subpara. 3",
            },
        ]
    }


@router.post("/template")
async def create_annex_iv_template(
    req: AnnexIVRequest,
    _: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate an Annex IV draft pre-filled from the agent card and provider inputs."""
    _validate_variant(req.variant)
    agent = await _resolve_agent(req, db)
    return build_annex_iv_template(agent, _provider_inputs(req), variant=req.variant)


@router.post("/template/markdown", response_class=PlainTextResponse)
async def create_annex_iv_markdown(
    req: AnnexIVRequest,
    _: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Same as /template but rendered as a Markdown download."""
    _validate_variant(req.variant)
    agent = await _resolve_agent(req, db)
    doc = build_annex_iv_template(agent, _provider_inputs(req), variant=req.variant)
    md = annex_iv_to_markdown(doc)
    slug = req.agent_id or "manual"
    return PlainTextResponse(
        content=md,
        media_type="text/markdown",
        headers={
            "Content-Disposition": (
                f'attachment; filename="annex-iv-{slug}-{req.variant}.md"'
            ),
        },
    )


@router.post("/template/pdf")
async def create_annex_iv_pdf(
    req: AnnexIVRequest,
    _: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Annex IV rendered as a printable PDF."""
    _validate_variant(req.variant)
    agent = await _resolve_agent(req, db)
    doc = build_annex_iv_template(agent, _provider_inputs(req), variant=req.variant)
    pdf_bytes = markdown_to_pdf(
        annex_iv_to_markdown(doc),
        title=f"Annex IV · {agent.name} ({req.variant})",
    )
    slug = req.agent_id or "manual"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="annex-iv-{slug}-{req.variant}.pdf"'
            ),
        },
    )


@router.get("/template/public/{agent_id}")
async def public_annex_iv_template(
    agent_id: str,
    variant: str = "full",
    db: AsyncSession = Depends(get_db),
):
    """Unauthenticated preview for the landing page and marketing demos."""
    _validate_variant(variant)
    agent = await _load_agent(agent_id, db)
    return build_annex_iv_template(agent, {}, variant=variant)
