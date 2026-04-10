"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

# --- Auth ---


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    role: str = Field(pattern="^(provider|consumer)$")


class RegisterResponse(BaseModel):
    id: UUID
    name: str
    email: str
    role: str
    api_key: str  # returned only once on registration


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Agent Capability Card ---


class AgentInput(BaseModel):
    name: str
    type: str
    required: bool = True
    default: str | None = None


class AgentOutput(BaseModel):
    name: str
    type: str
    guaranteed: bool = True


class AgentConstraints(BaseModel):
    timeout_max: int = 3600
    max_repo_size_mb: int | None = None
    languages: list[str] | None = None


class AgentRuntime(BaseModel):
    snapshot_profile: str = "base"
    server_type: str = "cax11"
    model: str = "anthropic/claude-sonnet-4-6"
    tools: list[str] = ["shell"]
    estimated_duration_seconds: int = 300
    estimated_cost_usd: float = 0.50


class AgentPricing(BaseModel):
    model: str = "per_execution"
    base_price_usd: float = 1.00


class AgentCreateRequest(BaseModel):
    id: str = Field(min_length=3, max_length=255, pattern="^[a-z0-9][a-z0-9-]*[a-z0-9]$")
    name: str = Field(min_length=3, max_length=255)
    description: str | None = None
    domain: str
    tags: list[str] = []
    inputs: list[AgentInput] = []
    outputs: list[AgentOutput] = []
    constraints: AgentConstraints = AgentConstraints()
    runtime: AgentRuntime = AgentRuntime()
    pricing: AgentPricing = AgentPricing()
    instructions: str  # the actual agent prompt/instructions


class AgentResponse(BaseModel):
    id: str
    name: str
    description: str | None
    provider_id: UUID
    provider_name: str | None = None
    status: str
    card: dict
    trust_score: float | None
    total_executions: int
    success_count: int
    created_at: datetime
    updated_at: datetime


class AgentListResponse(BaseModel):
    agents: list[AgentResponse]
    total: int


# --- Task Contract ---


class TaskCreateRequest(BaseModel):
    agent_id: str
    inputs: dict = {}
    constraints: dict = {}
    callback_url: str | None = None


class TaskResponse(BaseModel):
    id: str
    agent_id: str
    consumer_id: UUID
    status: str
    inputs: dict | None
    constraints: dict | None
    callback_url: str | None
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
    total: int


# --- Execution ---


class ExecutionResponse(BaseModel):
    id: str
    task_id: str
    server_id: str | None
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    elapsed_seconds: int | None
    exit_code: int | None
    metrics: dict | None
    created_at: datetime
