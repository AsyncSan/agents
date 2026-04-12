"""Pipeline routes: create and track agent composition chains."""

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.api.auth import get_current_user, require_role
from agentforge.api.schemas import (
    PipelineCreateRequest,
    PipelineListResponse,
    PipelineResponse,
    TaskResponse,
)
from agentforge.db import get_db
from agentforge.models.agent import Agent
from agentforge.models.pipeline import Pipeline
from agentforge.models.task import Task

router = APIRouter(prefix="/v1/pipelines", tags=["pipelines"])


def _generate_pipeline_id() -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%d")
    suffix = secrets.token_hex(4)
    return f"pl-{now}-{suffix}"


def _generate_task_id() -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%d")
    suffix = secrets.token_hex(4)
    return f"tc-{now}-{suffix}"


def _pipeline_to_response(pipeline: Pipeline) -> PipelineResponse:
    tasks = [
        TaskResponse(
            id=t.id,
            agent_id=t.agent_id,
            consumer_id=t.consumer_id,
            status=t.status,
            inputs=t.inputs,
            constraints=t.constraints,
            callback_url=t.callback_url,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in (pipeline.tasks or [])
    ]
    return PipelineResponse(
        id=pipeline.id,
        consumer_id=pipeline.consumer_id,
        status=pipeline.status,
        current_step=pipeline.current_step,
        chain_trust_score=float(pipeline.chain_trust_score)
        if pipeline.chain_trust_score is not None
        else None,
        steps=pipeline.steps,
        tasks=tasks,
        total_authorized_cents=pipeline.total_authorized_cents,
        total_captured_cents=pipeline.total_captured_cents,
        max_cost_usd=float(pipeline.max_cost_usd)
        if pipeline.max_cost_usd is not None
        else None,
        callback_url=pipeline.callback_url,
        created_at=pipeline.created_at,
        updated_at=pipeline.updated_at,
    )


@router.post("", response_model=PipelineResponse, status_code=201)
async def create_pipeline(
    req: PipelineCreateRequest,
    user: dict = Depends(require_role("consumer")),
    db: AsyncSession = Depends(get_db),
):
    """Create a linear pipeline of agent tasks."""
    # Validate all agents exist and are active
    agent_ids = [step.agent_id for step in req.steps]
    result = await db.execute(select(Agent).where(Agent.id.in_(agent_ids)))
    agents = {a.id: a for a in result.scalars().all()}

    for step in req.steps:
        if step.agent_id not in agents:
            raise HTTPException(
                status_code=404,
                detail=f"Agent '{step.agent_id}' not found",
            )
        if agents[step.agent_id].status != "active":
            raise HTTPException(
                status_code=400,
                detail=f"Agent '{step.agent_id}' is not active",
            )

    # Budget enforcement: sum of all agent base prices
    total_price = sum(
        agents[s.agent_id].card.get("pricing", {}).get("base_price_usd", 0)
        for s in req.steps
    )
    budget_cap = req.constraints.max_cost_usd
    if budget_cap is not None and total_price > budget_cap:
        raise HTTPException(
            status_code=400,
            detail=f"Pipeline total ${total_price:.2f} exceeds budget ${budget_cap:.2f}",
        )

    # Chain trust = min of all agent trust scores
    trust_scores = [
        float(agents[s.agent_id].trust_score or 0) for s in req.steps
    ]
    chain_trust = min(trust_scores) if trust_scores else 0.0

    # Serialize steps
    steps_data = [
        {
            "agent_id": step.agent_id,
            "inputs": step.inputs,
            "output_map": step.output_map,
            "constraints": step.constraints.model_dump(),
        }
        for step in req.steps
    ]

    pipeline = Pipeline(
        id=_generate_pipeline_id(),
        consumer_id=user["id"],
        status="pending",
        callback_url=req.callback_url,
        max_cost_usd=req.constraints.max_cost_usd,
        steps=steps_data,
        current_step=0,
        chain_trust_score=chain_trust,
    )
    db.add(pipeline)

    # Create only the first task
    first_step = req.steps[0]
    first_task = Task(
        id=_generate_task_id(),
        consumer_id=user["id"],
        agent_id=first_step.agent_id,
        inputs=first_step.inputs,
        constraints=first_step.constraints.model_dump(),
        pipeline_id=pipeline.id,
        step_index=0,
        status="pending",
    )
    db.add(first_task)

    await db.commit()
    await db.refresh(pipeline)

    return _pipeline_to_response(pipeline)


@router.get("/{pipeline_id}", response_model=PipelineResponse)
async def get_pipeline(
    pipeline_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get pipeline status with all task statuses."""
    result = await db.execute(
        select(Pipeline).where(Pipeline.id == pipeline_id)
    )
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    if user["role"] == "consumer" and pipeline.consumer_id != user["id"]:
        raise HTTPException(status_code=403, detail="Not your pipeline")

    return _pipeline_to_response(pipeline)


@router.get("", response_model=PipelineListResponse)
async def list_pipelines(
    status: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(require_role("consumer")),
    db: AsyncSession = Depends(get_db),
):
    """List pipelines for the current consumer."""
    query = select(Pipeline).where(Pipeline.consumer_id == user["id"])
    if status:
        query = query.where(Pipeline.status == status)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    query = query.order_by(Pipeline.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    pipelines = result.scalars().all()

    return PipelineListResponse(
        pipelines=[_pipeline_to_response(p) for p in pipelines],
        total=total,
    )
