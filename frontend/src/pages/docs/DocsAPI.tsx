import { H1, H2, P, Lead, InlineCode, Endpoint, DEEnglishOnlyNotice } from "./components";

export function DocsAPI() {
  return (
    <div>
      <DEEnglishOnlyNotice />
      <H1>API Reference</H1>
      <Lead>
        Base URL: <InlineCode>https://agents.renemurrell.de/v1</InlineCode>.
        All authenticated endpoints require an <InlineCode>X-API-Key</InlineCode> header.
      </Lead>

      <H2 id="auth">Auth</H2>
      <div className="space-y-2">
        <Endpoint
          method="POST"
          path="/auth/register"
          description="Register a new provider or consumer account. Returns API key (shown only once)."
          body={`{"name": "string", "email": "string", "role": "provider|consumer"}`}
          response={`{"id": "uuid", "name": "string", "email": "string", "role": "string", "api_key": "af_..."}`}
        />
        <Endpoint
          method="POST"
          path="/auth/api-keys"
          description="Create a scoped API key. Requires admin scope."
          auth
          scope="admin"
          body={`{"name": "string", "scope": "read|execute|admin"}`}
          response={`{"id": "uuid", "name": "string", "scope": "string", "api_key": "af_...", "created_at": "..."}`}
        />
        <Endpoint
          method="GET"
          path="/auth/api-keys"
          description="List all API keys for the current user. Values are masked."
          auth
        />
        <Endpoint
          method="POST"
          path="/auth/api-keys/{key_id}/revoke"
          description="Revoke an API key. Revoked keys cannot authenticate. Requires admin scope."
          auth
          scope="admin"
        />
      </div>

      <H2 id="agents">Agents</H2>
      <div className="space-y-2">
        <Endpoint
          method="GET"
          path="/agents"
          description="List all active agents. Query params: domain, tag, search, offset, limit."
        />
        <Endpoint
          method="GET"
          path="/agents/categories"
          description="Get all available agent domains/categories with counts."
        />
        <Endpoint
          method="GET"
          path="/agents/featured"
          description="Get featured agents for the catalog homepage."
        />
        <Endpoint
          method="GET"
          path="/agents/{id}"
          description="Get full agent details including capability card, trust score, and execution stats."
        />
        <Endpoint
          method="POST"
          path="/agents"
          description="Publish a new agent. Provider role required."
          auth
          scope="admin"
          body={`{"name": "string", "card": {...}, "risk_class": "minimal|limited|high"}`}
        />
        <Endpoint
          method="PUT"
          path="/agents/{id}"
          description="Update an agent's card or metadata. Creates a new version."
          auth
          scope="admin"
        />
        <Endpoint
          method="DELETE"
          path="/agents/{id}"
          description="Soft-delete an agent (sets status to inactive)."
          auth
          scope="admin"
        />
        <Endpoint
          method="GET"
          path="/agents/{id}/stats"
          description="Get execution statistics: total runs, success rate, avg duration."
        />
        <Endpoint
          method="GET"
          path="/agents/{id}/health"
          description="Check agent health and recent execution status."
        />
        <Endpoint
          method="GET"
          path="/agents/{id}/verify"
          description="Verify the agent's Ed25519 capability card signature."
        />
        <Endpoint
          method="GET"
          path="/agents/{id}/compatible"
          description="Find compatible agents for pipeline composition. Query: direction (upstream/downstream), limit."
        />
        <Endpoint
          method="GET"
          path="/agents/{id}/versions"
          description="List all versions of an agent's capability card."
        />
      </div>

      <H2 id="tasks">Tasks</H2>
      <div className="space-y-2">
        <Endpoint
          method="POST"
          path="/tasks"
          description="Submit a new task. Validates agent, budget, plan limits. High-risk agents enter awaiting_approval."
          auth
          scope="execute"
          body={`{
  "agent_id": "string",
  "inputs": {"key": "value"},
  "constraints": {"timeout": 300, "max_cost_usd": 5.00},
  "callback_url": "https://...",
  "compute_tier": "vm",
  "payment_rail": "stripe"
}`}
          response={`{"id": "tc-...", "status": "pending|awaiting_approval", "agent_id": "...", "consumer_id": "...", "created_at": "..."}`}
        />
        <Endpoint
          method="GET"
          path="/tasks"
          description="List your tasks. Query: status, agent_id, created_after, created_before, offset, limit."
          auth
        />
        <Endpoint
          method="GET"
          path="/tasks/{id}"
          description="Get task details and current status."
          auth
        />
        <Endpoint
          method="GET"
          path="/tasks/{id}/executions"
          description="Get all executions for a task with server info, metrics, and timing."
          auth
        />
        <Endpoint
          method="GET"
          path="/tasks/{id}/result"
          description="Download a result file. Query: file (output.md, stdout.log, stderr.log, usage.json)."
          auth
        />
        <Endpoint
          method="POST"
          path="/tasks/{id}/approve"
          description="Approve a high-risk task for execution. Only for tasks in awaiting_approval status."
          auth
        />
        <Endpoint
          method="POST"
          path="/tasks/{id}/cancel"
          description="Cancel a pending, running, or awaiting_approval task. Running tasks trigger server destruction."
          auth
        />
      </div>

      <H2 id="pipelines">Pipelines</H2>
      <div className="space-y-2">
        <Endpoint
          method="POST"
          path="/pipelines"
          description="Create a multi-step agent pipeline with output mapping between steps."
          auth
          scope="execute"
          body={`{
  "steps": [{"agent_id": "...", "inputs": {...}, "output_map": {...}}],
  "max_cost_usd": 10.00,
  "callback_url": "https://..."
}`}
        />
        <Endpoint
          method="GET"
          path="/pipelines"
          description="List your pipelines with status and step progress."
          auth
        />
        <Endpoint
          method="GET"
          path="/pipelines/{id}"
          description="Get pipeline details including all steps, tasks, and shared context."
          auth
        />
        <Endpoint
          method="PUT"
          path="/pipelines/{id}/context"
          description="Update the pipeline's shared context."
          auth
        />
        <Endpoint
          method="GET"
          path="/pipelines/{id}/context"
          description="Get the pipeline's current shared context."
          auth
        />
      </div>

      <H2 id="webhooks">Webhooks</H2>
      <div className="space-y-2">
        <Endpoint
          method="POST"
          path="/webhooks"
          description="Register a webhook endpoint. Supports generic (HMAC-signed) and slack (Block Kit) types."
          auth
          body={`{"url": "string", "event_types": ["task.completed"], "webhook_type": "generic|slack"}`}
        />
        <Endpoint
          method="GET"
          path="/webhooks"
          description="List your webhooks with delivery stats."
          auth
        />
        <Endpoint
          method="DELETE"
          path="/webhooks/{id}"
          description="Delete a webhook."
          auth
        />
        <Endpoint
          method="POST"
          path="/webhooks/{id}/test"
          description="Send a test event to verify your webhook endpoint."
          auth
        />
      </div>

      <H2 id="schedules">Schedules</H2>
      <div className="space-y-2">
        <Endpoint
          method="POST"
          path="/schedules"
          description="Create a recurring schedule with cron expression and timezone."
          auth
          body={`{
  "agent_id": "string",
  "name": "string",
  "cron_expression": "0 8 * * 1",
  "timezone": "Europe/Berlin",
  "inputs": {...},
  "constraints": {...}
}`}
        />
        <Endpoint
          method="GET"
          path="/schedules"
          description="List your schedules with run counts and next fire time."
          auth
        />
        <Endpoint
          method="GET"
          path="/schedules/{id}"
          description="Get schedule details."
          auth
        />
        <Endpoint
          method="PATCH"
          path="/schedules/{id}/pause"
          description="Pause a schedule."
          auth
        />
        <Endpoint
          method="PATCH"
          path="/schedules/{id}/resume"
          description="Resume a paused schedule."
          auth
        />
        <Endpoint
          method="DELETE"
          path="/schedules/{id}"
          description="Delete a schedule permanently."
          auth
        />
      </div>

      <H2 id="secrets">Secrets</H2>
      <div className="space-y-2">
        <Endpoint
          method="PUT"
          path="/secrets"
          description="Store or update a secret. Overwrites if key already exists."
          auth
          body={`{"key": "GITHUB_TOKEN", "value": "ghp_..."}`}
        />
        <Endpoint
          method="GET"
          path="/secrets"
          description="List stored secret keys. Values are never returned."
          auth
        />
        <Endpoint
          method="DELETE"
          path="/secrets/{key}"
          description="Delete a secret by key name."
          auth
        />
      </div>

      <H2 id="ratings">Ratings</H2>
      <div className="space-y-2">
        <Endpoint
          method="GET"
          path="/agents/{id}/ratings"
          description="Get all ratings for an agent."
        />
        <Endpoint
          method="POST"
          path="/agents/{id}/ratings"
          description="Rate an agent after a completed task. 1-5 stars with optional comment."
          auth
          body={`{"task_id": "string", "score": 5, "comment": "Excellent results"}`}
        />
      </div>

      <H2 id="billing">Billing</H2>
      <div className="space-y-2">
        <Endpoint
          method="POST"
          path="/billing/checkout-session"
          description="Create a Stripe Checkout session for plan subscription."
          auth
        />
        <Endpoint
          method="POST"
          path="/billing/payment-method"
          description="Add a payment method."
          auth
        />
        <Endpoint
          method="GET"
          path="/billing/payment-methods"
          description="List stored payment methods."
          auth
        />
        <Endpoint
          method="DELETE"
          path="/billing/payment-methods/{id}"
          description="Remove a payment method."
          auth
        />
        <Endpoint
          method="POST"
          path="/billing/payment-methods/default"
          description="Set a payment method as default."
          auth
        />
      </div>

      <H2 id="platform">Platform</H2>
      <div className="space-y-2">
        <Endpoint
          method="GET"
          path="/platform/health"
          description="Platform health check. Returns service status."
        />
        <Endpoint
          method="GET"
          path="/events"
          description="Query the immutable event log. Supports filtering by event_type, resource_type, date range."
          auth
        />
        <Endpoint
          method="GET"
          path="/dashboard"
          description="Get usage dashboard data: task counts, costs, agent stats."
          auth
        />
        <Endpoint
          method="POST"
          path="/dashboard/compliance/export"
          description="Export compliance audit trail. Supports JSON and CSV formats."
          auth
          body={`{"format": "json|csv"}`}
        />
      </div>

      <H2 id="me">User Profile</H2>
      <div className="space-y-2">
        <Endpoint
          method="GET"
          path="/me"
          description="Get current user profile, role, and plan details."
          auth
        />
        <Endpoint
          method="POST"
          path="/me/api-key/rotate"
          description="Rotate your legacy API key. Returns new key (old key invalidated)."
          auth
        />
      </div>

      <H2 id="providers">Providers</H2>
      <div className="space-y-2">
        <Endpoint
          method="GET"
          path="/providers/{id}"
          description="Get provider profile: name, public key, agent count."
        />
      </div>

      <H2 id="errors">Error Format</H2>
      <P>
        All errors follow a consistent JSON format:
      </P>
      <div className="rounded-lg bg-[#0a0a0f] border border-white/[0.06] p-4 my-4">
        <pre className="text-[13px] font-mono text-[#e2e8f0] leading-relaxed">
{`{
  "error": {
    "code": "TASK_NOT_FOUND",
    "message": "Task not found",
    "details": {}
  }
}`}
        </pre>
      </div>
      <P>
        HTTP status codes: <InlineCode>400</InlineCode> validation,{" "}
        <InlineCode>401</InlineCode> invalid key,{" "}
        <InlineCode>403</InlineCode> forbidden/scope,{" "}
        <InlineCode>404</InlineCode> not found,{" "}
        <InlineCode>409</InlineCode> conflict,{" "}
        <InlineCode>429</InlineCode> rate/plan limit.
      </P>
    </div>
  );
}
