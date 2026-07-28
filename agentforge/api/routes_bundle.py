"""Compliance-bundle routes: one-shot EU AI Act document set per use-case."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.api.auth import get_current_user
from agentforge.api.errors import APIError, ErrorCode
from agentforge.compliance_bundle import build_compliance_bundle
from agentforge.db import get_db
from agentforge.fria import TRIGGER_USE_CASES
from agentforge.manual_agent import ManualAgentInput, build_manual_agent
from agentforge.models.agent import Agent

router = APIRouter(prefix="/v1/compliance/bundle", tags=["compliance-bundle"])


class BundleRequest(BaseModel):
    use_case_key: str
    agent_id: str | None = None
    manual_agent: ManualAgentInput | None = None
    # Shared inputs (lazily applied to each generator that understands them)
    deployer_organisation: str | None = None
    deployer_contact: str | None = None
    provider_name: str | None = None
    provider_address: str | None = None
    provider_contact: str | None = None
    pmm_owner: str | None = None
    accountability_owner: str | None = None
    rms_owner: str | None = None
    member_states: list[str] | None = None


def _validate_use_case(key: str) -> None:
    if key not in TRIGGER_USE_CASES:
        raise APIError(
            422,
            ErrorCode.INVALID_INPUT,
            f"use_case_key must be one of {list(TRIGGER_USE_CASES)}",
        )


async def _resolve_agent(req: BundleRequest, db: AsyncSession):
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
    result = await db.execute(select(Agent).where(Agent.id == req.agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise APIError(404, ErrorCode.AGENT_NOT_FOUND, f"Agent '{req.agent_id}' not found")
    return agent


def _deployer_inputs(req: BundleRequest) -> dict[str, Any]:
    return {
        k: v
        for k, v in {
            "deployer_organisation": req.deployer_organisation,
            "deployer_contact": req.deployer_contact,
        }.items()
        if v is not None
    }


def _provider_inputs(req: BundleRequest) -> dict[str, Any]:
    return {
        k: v
        for k, v in {
            "provider_name": req.provider_name,
            "provider_address": req.provider_address,
            "provider_contact": req.provider_contact,
            "pmm_owner": req.pmm_owner,
            "accountability_owner": req.accountability_owner,
            "rms_owner": req.rms_owner,
            "member_states": req.member_states,
        }.items()
        if v is not None
    }


@router.get("/use-cases")
async def list_use_cases(_: dict = Depends(get_current_user)):
    """Use-case catalog with labels and FRIA-trigger flag."""
    from agentforge.compliance_bundle import FRIA_TRIGGERING

    return {
        "use_cases": [
            {
                "key": key,
                "description": description,
                "triggers_fria": key in FRIA_TRIGGERING,
            }
            for key, description in TRIGGER_USE_CASES.items()
        ]
    }


@router.post("")
async def generate_bundle(
    req: BundleRequest,
    _: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate the full compliance artefact set as a ZIP."""
    _validate_use_case(req.use_case_key)
    agent = await _resolve_agent(req, db)

    zip_bytes, manifest = build_compliance_bundle(
        agent,
        req.use_case_key,
        deployer_inputs=_deployer_inputs(req),
        provider_inputs=_provider_inputs(req),
    )
    slug = (req.agent_id or "manual").replace("/", "-")
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f'attachment; filename="compliance-bundle-{slug}-{req.use_case_key}.zip"'
            ),
            "X-Bundle-Artefacts": ",".join(manifest["included_artefacts"]),
        },
    )
