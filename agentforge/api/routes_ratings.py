"""Rating routes: consumer feedback on completed tasks."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.api.auth import require_role
from agentforge.api.errors import APIError, ErrorCode
from agentforge.api.schemas import (
    RatingCreateRequest,
    RatingListResponse,
    RatingResponse,
)
from agentforge.db import get_db
from agentforge.events import emit_event
from agentforge.models.agent import Agent
from agentforge.models.rating import Rating
from agentforge.models.task import Task
from agentforge.trust import compute_trust_score

router = APIRouter(tags=["ratings"])


@router.post(
    "/v1/tasks/{task_id}/rating", response_model=RatingResponse, status_code=201
)
async def rate_task(
    task_id: str,
    req: RatingCreateRequest,
    user: dict = Depends(require_role("consumer")),
    db: AsyncSession = Depends(get_db),
):
    """Rate a completed task. Only the consumer who submitted the task can rate it."""
    # Load task
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise APIError(404, ErrorCode.TASK_NOT_FOUND, "Task not found")

    if task.consumer_id != user["id"]:
        raise APIError(403, ErrorCode.FORBIDDEN, "Not your task")

    if task.status != "completed":
        raise APIError(422, ErrorCode.TASK_NOT_COMPLETED, "Can only rate completed tasks")

    # Check for existing rating
    existing = await db.execute(select(Rating).where(Rating.task_id == task_id))
    if existing.scalar_one_or_none():
        raise APIError(409, ErrorCode.ALREADY_RATED, "Task already rated")

    rating = Rating(
        task_id=task_id,
        consumer_id=user["id"],
        agent_id=task.agent_id,
        score=req.score,
        comment=req.comment,
    )
    db.add(rating)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise APIError(409, ErrorCode.ALREADY_RATED, "Task already rated")

    # Recompute trust score with rating factor
    agent_result = await db.execute(select(Agent).where(Agent.id == task.agent_id))
    agent = agent_result.scalar_one_or_none()
    if agent:
        await _update_trust_with_ratings(db, agent)

    await emit_event(
        db,
        "rating.created",
        actor_id=str(user["id"]),
        actor_role="consumer",
        resource_type="rating",
        resource_id=str(rating.id),
        payload={
            "task_id": task_id,
            "agent_id": task.agent_id,
            "score": req.score,
        },
    )
    await db.commit()
    await db.refresh(rating)

    return RatingResponse(
        id=rating.id,
        task_id=rating.task_id,
        agent_id=rating.agent_id,
        consumer_id=rating.consumer_id,
        score=rating.score,
        comment=rating.comment,
        created_at=rating.created_at,
    )


@router.get("/v1/agents/{agent_id}/ratings", response_model=RatingListResponse)
async def list_agent_ratings(
    agent_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List ratings for an agent. Public endpoint."""
    # Verify agent exists
    agent_result = await db.execute(select(Agent).where(Agent.id == agent_id))
    if not agent_result.scalar_one_or_none():
        raise APIError(404, ErrorCode.AGENT_NOT_FOUND, "Agent not found")

    # Count + average
    stats = await db.execute(
        select(
            func.count(Rating.id).label("total"),
            func.avg(Rating.score).label("avg"),
        ).where(Rating.agent_id == agent_id)
    )
    row = stats.one()
    total = row[0] or 0
    avg_score = round(float(row[1]), 2) if row[1] else None

    # Paginated ratings
    result = await db.execute(
        select(Rating)
        .where(Rating.agent_id == agent_id)
        .order_by(Rating.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    ratings = [
        RatingResponse(
            id=r.id,
            task_id=r.task_id,
            agent_id=r.agent_id,
            consumer_id=r.consumer_id,
            score=r.score,
            comment=r.comment,
            created_at=r.created_at,
        )
        for r in result.scalars().all()
    ]

    return RatingListResponse(
        ratings=ratings,
        average_score=avg_score,
        total=total,
    )


async def _update_trust_with_ratings(db: AsyncSession, agent: Agent) -> None:
    """Recompute trust score incorporating rating data.

    Rating contributes 10% to trust score by reallocating weights:
    - Success Rate: 35% (was 40%)
    - Duration Accuracy: 25% (was 30%)
    - Volume Confidence: 20% (unchanged)
    - Recency: 10% (unchanged)
    - Rating: 10% (new)
    """
    # Get average rating for this agent
    rating_result = await db.execute(
        select(func.avg(Rating.score)).where(Rating.agent_id == agent.id)
    )
    avg_rating = rating_result.scalar()

    # Base trust score (without ratings)
    base_trust = compute_trust_score(
        total_executions=agent.total_executions,
        success_count=agent.success_count,
        avg_duration=float(agent.avg_duration_seconds or 0),
        expected_duration=agent.card.get("runtime", {}).get(
            "estimated_duration_seconds", 300
        ),
    )

    if avg_rating is not None:
        # Rating factor: normalize 1-5 to 0-1
        rating_factor = (float(avg_rating) - 1) / 4.0
        # Blend: 90% base trust + 10% rating
        new_trust = round(base_trust * 0.9 + rating_factor * 0.1, 2)
    else:
        new_trust = base_trust

    agent.trust_score = max(0.0, min(1.0, new_trust))
