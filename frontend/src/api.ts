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
