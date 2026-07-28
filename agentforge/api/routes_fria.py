"""FRIA (Fundamental Rights Impact Assessment) routes.

Art. 27 requires deployers of certain high-risk systems to complete a FRIA
before first use. This module exposes a stateless template generator: given
an agent id plus the deployer's contextual inputs, it returns a pre-filled
FRIA document. Persistence is intentionally left to the deployer so they
keep control of the regulatory record.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.api.auth import get_current_user
from agentforge.api.errors import APIError, ErrorCode
from agentforge.db import get_db
from agentforge.fria import TRIGGER_USE_CASES, build_fria_template, fria_to_markdown
from agentforge.manual_agent import ManualAgentInput, build_manual_agent
from agentforge.models.agent import Agent
from agentforge.pdf import markdown_to_pdf

router = APIRouter(prefix="/v1/fria", tags=["fria"])


class FRIATemplateRequest(BaseModel):
    agent_id: str | None = Field(
        default=None,
        description="Agent registered on the platform. Mutually exclusive with manual_agent.",
    )
    manual_agent: ManualAgentInput | None = Field(
        default=None,
        description="Describe an external system manually (no platform agent required).",
    )
    use_case_key: str | None = Field(
        default=None,
        description=f"One of: {', '.join(sorted(TRIGGER_USE_CASES))}",
    )
    deployer_organisation: str | None = None
    deployer_contact: str | None = None
    deployer_process_summary: str | None = None
    intended_duration: str | None = None
    frequency: str | None = None
    estimated_volume_per_month: str | None = None
    affected_categories: list[str] | None = None
    vulnerable_groups: list[str] | None = None
    special_categories_of_data: str | None = None
    potential_harms: list[str] | None = None
    severity_assessment: str | None = None
    likelihood_assessment: str | None = None
    deployer_oversight_measures: list[str] | None = None
    ifu_version: str | None = None
    internal_governance: list[str] | None = None
    complaint_mechanism: str | None = None
    authority_reporting: str | None = None
    dpia_reference: str | None = None


async def _load_agent(agent_id: str, db: AsyncSession) -> Agent:
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise APIError(404, ErrorCode.AGENT_NOT_FOUND, f"Agent '{agent_id}' not found")
    return agent


async def _resolve_agent(req: FRIATemplateRequest, db: AsyncSession):
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


def _deployer_inputs_from_request(req: FRIATemplateRequest) -> dict[str, Any]:
    skip = {"agent_id", "manual_agent"}
    return {k: v for k, v in req.model_dump().items() if v is not None and k not in skip}


@router.get("/trigger-categories")
async def list_trigger_categories(_: dict = Depends(get_current_user)):
    """Return the FRIA trigger categories recognised under Art. 27."""
    return {
        "categories": [
            {"key": key, "description": description}
            for key, description in TRIGGER_USE_CASES.items()
        ]
    }


@router.post("/template")
async def create_fria_template(
    req: FRIATemplateRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a FRIA draft pre-filled from the agent card and deployer inputs."""
    agent = await _resolve_agent(req, db)
    fria = build_fria_template(agent, _deployer_inputs_from_request(req))
    return fria


@router.post("/template/markdown", response_class=PlainTextResponse)
async def create_fria_markdown(
    req: FRIATemplateRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Same as /template but rendered as a downloadable Markdown document."""
    agent = await _resolve_agent(req, db)
    fria = build_fria_template(agent, _deployer_inputs_from_request(req))
    md = fria_to_markdown(fria)
    slug = req.agent_id or "manual"
    return PlainTextResponse(
        content=md,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="fria-{slug}.md"'},
    )


@router.post("/template/pdf")
async def create_fria_pdf(
    req: FRIATemplateRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """FRIA rendered as a printable PDF."""
    agent = await _resolve_agent(req, db)
    fria = build_fria_template(agent, _deployer_inputs_from_request(req))
    pdf_bytes = markdown_to_pdf(
        fria_to_markdown(fria), title=f"FRIA · {agent.name}"
    )
    slug = req.agent_id or "manual"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="fria-{slug}.pdf"'
        },
    )


@router.get("/template/public/{agent_id}")
async def public_fria_template(agent_id: str, db: AsyncSession = Depends(get_db)):
    """Public, unauthenticated preview used by the landing page wizard.

    Returns the scaffold with no deployer inputs. Useful for marketing
    demos and for deployers evaluating the platform before signup.
    """
    agent = await _load_agent(agent_id, db)
    fria = build_fria_template(agent, {})
    return JSONResponse(content=fria)
