"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

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
    timeout_max: int = Field(default=3600, ge=60, le=3600)
    max_repo_size_mb: int | None = Field(None, ge=1)
    languages: list[str] | None = None


class AgentRuntime(BaseModel):
    snapshot_profile: str = "base"
    server_type: str = "cax11"
    compute_tier: str = Field(
        default="container",
        pattern="^(container|vm)$",
        description="container (~100ms boot, shared kernel) or vm (~20s boot, full isolation)",
    )
    model: str = "anthropic/claude-sonnet-4-6"
    tools: list[str] = ["shell"]
    estimated_duration_seconds: int = Field(default=300, ge=10, le=3600)
    estimated_cost_usd: float = Field(default=0.50, ge=0)


class AgentPricing(BaseModel):
    model: str = "per_execution"
    base_price_usd: float = Field(default=1.00, ge=0)


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
    timeout: int | None = Field(None, ge=60, le=3600)
    max_cost_usd: float | None = Field(None, ge=0)


class TaskCreateRequest(BaseModel):
    agent_id: str
    inputs: dict = {}
    constraints: TaskConstraints = TaskConstraints()
    callback_url: str | None = None
    compute_tier: str | None = Field(
        None, pattern="^(container|vm)$",
        description="Override agent's compute tier for this task",
    )
    payment_rail: str | None = Field(
        None, pattern="^(stripe|solana)$",
        description="Payment rail: 'stripe' (default) or 'solana'",
    )

    @field_validator("callback_url")
    @classmethod
    def validate_callback_url(cls, v: str | None) -> str | None:
        if v is not None and not v.startswith(("https://", "http://")):
            raise ValueError("callback_url must be a valid HTTP(S) URL")
        return v


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


class StepCondition(BaseModel):
    """Condition for conditional branching. Step runs only if condition is met."""

    field: str  # key in pipeline context to check
    op: str = Field(pattern="^(eq|ne|gt|lt|gte|lte|in|contains|exists)$")
    value: str | int | float | bool | list | None = None


class PipelineStep(BaseModel):
    agent_id: str
    inputs: dict = {}
    output_map: dict[str, str] = {}
    constraints: TaskConstraints = TaskConstraints()
    step_index: int | None = None  # explicit index for parallel grouping
    condition: StepCondition | None = None  # skip step if condition not met


class PipelineCreateRequest(BaseModel):
    steps: list[PipelineStep] = Field(min_length=2)
    constraints: TaskConstraints = TaskConstraints()
    callback_url: str | None = None

    @field_validator("callback_url")
    @classmethod
    def validate_callback_url(cls, v: str | None) -> str | None:
        if v is not None and not v.startswith(("https://", "http://")):
            raise ValueError("callback_url must be a valid HTTP(S) URL")
        return v


class PipelineResponse(BaseModel):
    id: str
    consumer_id: UUID
    status: str
    current_step: int
    total_steps: int
    chain_trust_score: float | None
    steps: list[dict]
    tasks: list[TaskResponse]
    context: dict | None = None
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
    url: str = Field(min_length=10, max_length=2048)
    event_types: list[str] = Field(
        min_length=1,
        description="Event types to subscribe to. Use '*' for all events.",
    )

    @field_validator("url")
    @classmethod
    def validate_webhook_url(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError("Webhook URL must use HTTPS")
        return v


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


# --- Checkout Session ---


class CheckoutSessionRequest(BaseModel):
    success_url: str | None = None
    cancel_url: str | None = None


class CheckoutSessionResponse(BaseModel):
    session_id: str
    url: str


# --- Payment Method Management ---


class PaymentMethodItem(BaseModel):
    id: str
    brand: str
    last4: str
    exp_month: int
    exp_year: int
    is_default: bool


class PaymentMethodListResponse(BaseModel):
    payment_methods: list[PaymentMethodItem]


class SetDefaultPaymentMethodRequest(BaseModel):
    payment_method_id: str


# --- Stripe Connect (Provider) ---


class ConnectOnboardRequest(BaseModel):
    """No fields needed, uses provider's existing email/name."""
    pass


class ConnectOnboardResponse(BaseModel):
    account_id: str
    onboarding_url: str


class ConnectStatusResponse(BaseModel):
    account_id: str
    charges_enabled: bool
    payouts_enabled: bool
    details_submitted: bool
    requirements: dict
    dashboard_url: str | None = None


# --- Solana Wallet ---


class WalletRegisterRequest(BaseModel):
    wallet_address: str = Field(min_length=32, max_length=64)
    signature: str  # base64 Ed25519 sig of challenge message
    message: str  # the challenge message that was signed


class WalletRegisterResponse(BaseModel):
    wallet_address: str
    verified: bool


class SolanaPaymentVerifyRequest(BaseModel):
    tx_signature: str = Field(min_length=64, max_length=128)


class SolanaPaymentVerifyResponse(BaseModel):
    verified: bool
    amount_usdc: float | None = None
    tx_signature: str | None = None
    error: str | None = None


# --- Schedules ---


class ScheduleCreateRequest(BaseModel):
    agent_id: str
    name: str = Field(min_length=2, max_length=255)
    cron_expression: str = Field(
        min_length=9, max_length=100,
        description="Cron expression (5 fields): '0 9 * * 1' = Monday 9am UTC",
    )
    timezone: str = "UTC"
    inputs: dict = {}
    constraints: TaskConstraints = TaskConstraints()
    callback_url: str | None = None


class ScheduleResponse(BaseModel):
    id: UUID
    consumer_id: UUID
    agent_id: str
    name: str
    cron_expression: str
    timezone: str
    inputs: dict | None
    constraints: dict | None
    callback_url: str | None
    active: bool
    total_runs: int
    last_run_at: str | None
    next_run_at: str | None
    created_at: datetime
    updated_at: datetime


class ScheduleListResponse(BaseModel):
    schedules: list[ScheduleResponse]
    total: int


# --- Dashboard ---


class DailyUsage(BaseModel):
    date: str  # YYYY-MM-DD
    executions: int
    success: int
    failed: int
    total_cost_cents: int
    total_duration_seconds: int


class AgentUsageSummary(BaseModel):
    agent_id: str
    agent_name: str
    executions: int
    total_cost_cents: int
    avg_duration_seconds: float | None


class DashboardResponse(BaseModel):
    period_days: int
    total_executions: int
    total_success: int
    total_failed: int
    total_cost_cents: int
    avg_cost_per_run_cents: float | None
    daily_usage: list[DailyUsage]
    top_agents: list[AgentUsageSummary]


# --- Compliance Export ---


class ComplianceExportRequest(BaseModel):
    start_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$", description="ISO date: YYYY-MM-DD")
    end_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$", description="ISO date: YYYY-MM-DD")
    format: str = Field(default="json", pattern="^(json|csv)$")
