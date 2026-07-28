"""AI Literacy (Art. 4) training module routes.

Stateless: the backend serves modules, scores submitted answers, and issues
certificates. Completion tracking lives on the learner's device; the
downloaded certificate is the evidence artefact.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field

from agentforge.api.errors import APIError, ErrorCode
from agentforge.literacy import (
    build_certificate,
    certificate_to_markdown,
    get_module,
    list_modules,
    score_answers,
)
from agentforge.pdf import markdown_to_pdf

router = APIRouter(prefix="/v1/literacy", tags=["literacy"])


class CompleteRequest(BaseModel):
    module_id: str
    answers: dict[str, int] = Field(default_factory=dict)
    learner_name: str
    learner_organisation: str


@router.get("/modules")
async def get_modules():
    """Public listing of available literacy modules."""
    return {"modules": list_modules()}


@router.get("/modules/{module_id}")
async def get_module_detail(module_id: str):
    """Full module content: slides and questions (without the correct answers)."""
    module = get_module(module_id)
    if module is None:
        raise APIError(404, ErrorCode.MODULE_NOT_FOUND, f"Module '{module_id}' not found")
    return module


@router.post("/complete")
async def complete_module(req: CompleteRequest):
    """Score submitted answers and issue a completion certificate."""
    if not req.learner_name.strip() or not req.learner_organisation.strip():
        raise APIError(
            422,
            ErrorCode.INVALID_INPUT,
            "learner_name and learner_organisation are required",
        )
    try:
        score = score_answers(req.module_id, req.answers)
    except ValueError as exc:
        raise APIError(404, ErrorCode.MODULE_NOT_FOUND, str(exc)) from exc

    certificate = build_certificate(
        req.learner_name.strip(),
        req.learner_organisation.strip(),
        req.module_id,
        score,
    )
    return {"score": score, "certificate": certificate}


@router.post("/certificate/markdown", response_class=PlainTextResponse)
async def certificate_markdown(req: CompleteRequest):
    """Render the completion certificate as a downloadable Markdown document."""
    try:
        score = score_answers(req.module_id, req.answers)
    except ValueError as exc:
        raise APIError(404, ErrorCode.MODULE_NOT_FOUND, str(exc)) from exc

    certificate = build_certificate(
        req.learner_name.strip(),
        req.learner_organisation.strip(),
        req.module_id,
        score,
    )
    md = certificate_to_markdown(certificate)
    return PlainTextResponse(
        content=md,
        media_type="text/markdown",
        headers={
            "Content-Disposition": (
                f'attachment; filename="literacy-cert-{req.module_id}-'
                f'{certificate["certificate_id"]}.md"'
            ),
        },
    )


@router.post("/certificate/pdf")
async def certificate_pdf(req: CompleteRequest):
    """Render the completion certificate as a printable PDF."""
    try:
        score = score_answers(req.module_id, req.answers)
    except ValueError as exc:
        raise APIError(404, ErrorCode.MODULE_NOT_FOUND, str(exc)) from exc

    certificate = build_certificate(
        req.learner_name.strip(),
        req.learner_organisation.strip(),
        req.module_id,
        score,
    )
    pdf_bytes = markdown_to_pdf(
        certificate_to_markdown(certificate),
        title=f"Literacy certificate · {certificate['module']['title']}",
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="literacy-cert-{req.module_id}-'
                f'{certificate["certificate_id"]}.pdf"'
            ),
        },
    )
