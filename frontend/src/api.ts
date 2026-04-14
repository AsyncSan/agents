const BASE = "";

export interface Agent {
  id: string;
  name: string;
  description: string | null;
  provider_id: string;
  provider_name: string | null;
  status: string;
  card: {
    capabilities: {
      domain: string;
      tags: string[];
      description: string | null;
      inputs: { name: string; type: string; required: boolean; default?: string }[];
      outputs: { name: string; type: string; guaranteed: boolean }[];
      constraints: Record<string, unknown>;
    };
    runtime: {
      snapshot_profile: string;
      server_type: string;
      compute_tier: "container" | "vm";
      model: string;
      tools: string[];
      estimated_duration_seconds: number;
      estimated_cost_usd: number;
    };
    pricing: {
      model: string;
      base_price_usd: number;
    };
  };
  trust_score: number | null;
  total_executions: number;
  success_count: number;
  created_at: string;
}

export interface Task {
  id: string;
  agent_id: string;
  consumer_id: string;
  status: string;
  inputs: Record<string, unknown> | null;
  constraints: Record<string, unknown> | null;
  callback_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface Execution {
  id: string;
  task_id: string;
  server_id: string | null;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  elapsed_seconds: number | null;
  exit_code: number | null;
  metrics: Record<string, unknown> | null;
  created_at: string;
}

function headers(apiKey?: string): HeadersInit {
  const h: HeadersInit = { "Content-Type": "application/json" };
  if (apiKey) h["X-API-Key"] = apiKey;
  return h;
}

export async function listAgents(domain?: string, tag?: string): Promise<{ agents: Agent[]; total: number }> {
  const params = new URLSearchParams();
  if (domain) params.set("domain", domain);
  if (tag) params.set("tag", tag);
  const res = await fetch(`${BASE}/v1/agents?${params}`);
  return res.json();
}

export async function getAgent(id: string): Promise<Agent> {
  const res = await fetch(`${BASE}/v1/agents/${id}`);
  if (!res.ok) throw new Error("Agent not found");
  return res.json();
}

export async function register(name: string, email: string, role: "provider" | "consumer") {
  const res = await fetch(`${BASE}/v1/auth/register`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ name, email, role }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: { message: "Registration failed" } }));
    throw new Error(err.error?.message || err.detail || "Registration failed");
  }
  return res.json();
}

export async function submitTask(
  apiKey: string,
  agentId: string,
  inputs: Record<string, string>
): Promise<Task> {
  const res = await fetch(`${BASE}/v1/tasks`, {
    method: "POST",
    headers: headers(apiKey),
    body: JSON.stringify({ agent_id: agentId, inputs }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail || "Failed to submit task");
  }
  return res.json();
}

export async function listTasks(apiKey: string): Promise<{ tasks: Task[]; total: number }> {
  const res = await fetch(`${BASE}/v1/tasks`, { headers: headers(apiKey) });
  return res.json();
}

export async function getTask(apiKey: string, id: string): Promise<Task> {
  const res = await fetch(`${BASE}/v1/tasks/${id}`, { headers: headers(apiKey) });
  return res.json();
}

export async function getExecutions(apiKey: string, taskId: string): Promise<Execution[]> {
  const res = await fetch(`${BASE}/v1/tasks/${taskId}/executions`, { headers: headers(apiKey) });
  return res.json();
}

// --- Agent Compatibility ---

export interface CompatibleAgent {
  agent: Agent;
  compatibility_score: number;
  matching_fields: string[];
}

export async function getCompatibleAgents(
  agentId: string,
  direction: "downstream" | "upstream" = "downstream",
  limit: number = 5
): Promise<{ compatible: CompatibleAgent[]; total: number }> {
  const res = await fetch(
    `${BASE}/v1/agents/${agentId}/compatible?direction=${direction}&limit=${limit}`
  );
  if (!res.ok) return { compatible: [], total: 0 };
  return res.json();
}

// --- Task Results ---

export async function getTaskResult(
  apiKey: string,
  taskId: string,
  file: string = "output.md"
): Promise<string> {
  const res = await fetch(
    `${BASE}/v1/tasks/${taskId}/result?file=${encodeURIComponent(file)}`,
    { headers: headers(apiKey) }
  );
  if (!res.ok) throw new Error("Result not available");
  return res.text();
}

// --- Pipelines ---

export interface PipelineStep {
  agent_id: string;
  inputs: Record<string, unknown>;
  output_map: Record<string, string>;
  step_index: number;
  constraints: Record<string, unknown>;
}

export interface Pipeline {
  id: string;
  consumer_id: string;
  status: string;
  current_step: number;
  total_steps: number;
  chain_trust_score: number | null;
  steps: PipelineStep[];
  tasks: Task[];
  total_authorized_cents: number;
  total_captured_cents: number;
  max_cost_usd: number | null;
  callback_url: string | null;
  created_at: string;
  updated_at: string;
}

export async function listPipelines(apiKey: string): Promise<{ pipelines: Pipeline[]; total: number }> {
  const res = await fetch(`${BASE}/v1/pipelines`, { headers: headers(apiKey) });
  return res.json();
}

export async function getPipeline(apiKey: string, id: string): Promise<Pipeline> {
  const res = await fetch(`${BASE}/v1/pipelines/${id}`, { headers: headers(apiKey) });
  if (!res.ok) throw new Error("Pipeline not found");
  return res.json();
}
