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
    signing_public_key: str | None = None  # providers only, for card verification


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
    version: int = 1
    card: dict
    signature: str | None = None
    signing_public_key: str | None = None
    trust_score: float | None
    total_executions: int
    success_count: int
    created_at: datetime
    updated_at: datetime


class AgentListResponse(BaseModel):
    agents: list[AgentResponse]
    total: int


class AgentVersionResponse(BaseModel):
    id: UUID
    agent_id: str
    version: int
    card: dict
    signature: str | None
    change_summary: str | None
    created_at: datetime


class AgentVersionListResponse(BaseModel):
    versions: list[AgentVersionResponse]
    current_version: int


class CategoryItem(BaseModel):
    name: str
    count: int


class CategoryListResponse(BaseModel):
    domains: list[CategoryItem]
    tags: list[CategoryItem]


# --- Task Contract ---


class TaskConstraints(BaseModel):
    timeout: int | None = None  # max seconds, overrides agent default
    max_cost_usd: float | None = None  # budget cap, reject if agent price exceeds


class TaskCreateRequest(BaseModel):
    agent_id: str
    inputs: dict = {}
    constraints: TaskConstraints = TaskConstraints()
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
    results_path: str | None = None
    created_at: datetime


# --- Pipeline ---


class PipelineStep(BaseModel):
    agent_id: str
    inputs: dict = {}
    output_map: dict[str, str] = {}
    constraints: TaskConstraints = TaskConstraints()


class PipelineCreateRequest(BaseModel):
    steps: list[PipelineStep] = Field(min_length=2)
    constraints: TaskConstraints = TaskConstraints()
    callback_url: str | None = None


class PipelineResponse(BaseModel):
    id: str
    consumer_id: UUID
    status: str
    current_step: int
    chain_trust_score: float | None
    steps: list[dict]
    tasks: list[TaskResponse]
    total_authorized_cents: int
    total_captured_cents: int
    max_cost_usd: float | None
    callback_url: str | None
    created_at: datetime
    updated_at: datetime


class PipelineListResponse(BaseModel):
    pipelines: list[PipelineResponse]
    total: int


# --- Agent Stats & Health ---


class RecentExecution(BaseModel):
    execution_id: str
    task_id: str
    status: str
    elapsed_seconds: int | None
    created_at: datetime


class AgentStatsResponse(BaseModel):
    agent_id: str
    total_executions: int
    success_count: int
    failure_count: int
    success_rate: float  # 0.0 - 1.0
    avg_duration_seconds: float | None
    total_revenue_cents: int
    trust_score: float | None
    recent_executions: list[RecentExecution]


class AgentHealthResponse(BaseModel):
    agent_id: str
    status: str  # healthy, degraded, unhealthy, dormant
    last_execution_at: datetime | None
    consecutive_failures: int
    success_rate_24h: float | None
    avg_duration_24h: float | None
    executions_24h: int
    uptime_status: str  # active, idle, new


# --- Featured / Trending ---


class FeaturedAgentResponse(BaseModel):
    agent: AgentResponse
    trending_score: float  # weighted score for ranking


class FeaturedListResponse(BaseModel):
    trending: list[FeaturedAgentResponse]
    top_rated: list[AgentResponse]
    newest: list[AgentResponse]


# --- Provider Profile ---


class ProviderProfileResponse(BaseModel):
    id: UUID
    name: str
    signing_public_key: str | None
    total_agents: int
    active_agents: int
    total_executions: int
    total_success: int
    avg_trust_score: float | None
    agents: list[AgentResponse]
    created_at: datetime


# --- Platform Health ---


class ComponentHealth(BaseModel):
    name: str
    status: str  # ok, degraded, down
    latency_ms: float | None = None
    details: str | None = None


class PlatformHealthResponse(BaseModel):
    status: str  # ok, degraded, down
    version: str
    components: list[ComponentHealth]
    active_workers: int
    pending_tasks: int
    total_agents: int
    total_executions_24h: int


# --- Webhooks ---


class WebhookCreateRequest(BaseModel):
    url: str
    event_types: list[str] = Field(
        min_length=1,
        description="Event types to subscribe to. Use '*' for all events.",
    )


class WebhookResponse(BaseModel):
    id: UUID
    url: str
    secret: str  # shown once on creation, masked after
    event_types: list[str]
    active: bool
    total_deliveries: int
    total_failures: int
    created_at: datetime


class WebhookListResponse(BaseModel):
    webhooks: list[WebhookResponse]


# --- Event Log ---


class EventLogEntry(BaseModel):
    id: UUID
    event_type: str
    actor_id: str | None
    actor_role: str | None
    resource_type: str | None
    resource_id: str | None
    payload: dict | None
    created_at: datetime


class EventLogResponse(BaseModel):
    events: list[EventLogEntry]
    total: int


# --- Ratings ---


class RatingCreateRequest(BaseModel):
    score: int = Field(ge=1, le=5)
    comment: str | None = None


class RatingResponse(BaseModel):
    id: UUID
    task_id: str
    agent_id: str
    consumer_id: UUID
    score: int
    comment: str | None
    created_at: datetime


class RatingListResponse(BaseModel):
    ratings: list[RatingResponse]
    average_score: float | None
    total: int


# --- Payment Setup ---


class PaymentSetupRequest(BaseModel):
    payment_method_id: str  # Stripe PaymentMethod ID from client-side


class PaymentSetupResponse(BaseModel):
    stripe_customer_id: str
    payment_method_attached: bool
    default_payment_method: str | None
