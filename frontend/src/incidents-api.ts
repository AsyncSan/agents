export type Severity =
  | "death_or_serious_health"
  | "critical_infrastructure"
  | "fundamental_rights"
  | "widespread_infringement"
  | "serious_property_harm"
  | "environmental_harm";

export type IncidentStatus =
  | "draft"
  | "confirmed"
  | "reported"
  | "under_investigation"
  | "resolved"
  | "withdrawn";

export interface Incident {
  id: string;
  org_id: string;
  agent_id: string | null;
  agent_version: number | null;
  task_id: string | null;
  title: string;
  summary: string;
  severity: Severity;
  status: IncidentStatus;
  detected_at: string;
  awareness_at: string;
  affected_persons_estimate: number | null;
  root_cause: string | null;
  mitigation_taken: string | null;
  mitigation_planned: string | null;
  reported_to_authority_at: string | null;
  authority_name: string | null;
  authority_reference: string | null;
  deadline_at: string;
  deadline_days: number;
  time_remaining_seconds: number;
  overdue: boolean;
  created_at: string;
  updated_at: string;
}

export interface IncidentListResponse {
  incidents: Incident[];
  total: number;
  overdue_count: number;
  open_count: number;
}

export interface SeverityCatalogEntry {
  key: Severity;
  deadline_days: number;
  description: string;
}

function headers(apiKey: string): Record<string, string> {
  return { "Content-Type": "application/json", "X-API-Key": apiKey };
}

export async function listSeverities(apiKey: string): Promise<SeverityCatalogEntry[]> {
  const res = await fetch("/v1/incidents/severities", { headers: headers(apiKey) });
  if (!res.ok) throw new Error("Failed to load severity catalog");
  const data = await res.json();
  return data.severities;
}

export async function listIncidents(
  apiKey: string,
  filters: { status?: string; severity?: string; agent_id?: string } = {},
): Promise<IncidentListResponse> {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.severity) params.set("severity", filters.severity);
  if (filters.agent_id) params.set("agent_id", filters.agent_id);
  const url = `/v1/incidents${params.toString() ? `?${params}` : ""}`;
  const res = await fetch(url, { headers: headers(apiKey) });
  if (!res.ok) throw new Error("Failed to list incidents");
  return res.json();
}

export async function createIncident(
  apiKey: string,
  body: {
    title: string;
    summary: string;
    severity: Severity;
    detected_at: string;
    awareness_at?: string;
    agent_id?: string | null;
    agent_version?: number | null;
    affected_persons_estimate?: number | null;
    root_cause?: string;
    mitigation_taken?: string;
    mitigation_planned?: string;
  },
): Promise<Incident> {
  const res = await fetch("/v1/incidents", {
    method: "POST",
    headers: headers(apiKey),
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(err?.error?.message || "Failed to create incident");
  }
  return res.json();
}

export async function getIncident(apiKey: string, id: string): Promise<Incident> {
  const res = await fetch(`/v1/incidents/${id}`, { headers: headers(apiKey) });
  if (!res.ok) throw new Error("Failed to fetch incident");
  return res.json();
}

export async function updateIncident(
  apiKey: string,
  id: string,
  body: Partial<{
    title: string;
    summary: string;
    severity: Severity;
    status: IncidentStatus;
    detected_at: string;
    awareness_at: string;
    affected_persons_estimate: number | null;
    root_cause: string;
    mitigation_taken: string;
    mitigation_planned: string;
  }>,
): Promise<Incident> {
  const res = await fetch(`/v1/incidents/${id}`, {
    method: "PATCH",
    headers: headers(apiKey),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error("Failed to update incident");
  return res.json();
}

export async function markReported(
  apiKey: string,
  id: string,
  body: { authority_name?: string; authority_reference?: string; reported_at?: string } = {},
): Promise<Incident> {
  const res = await fetch(`/v1/incidents/${id}/report`, {
    method: "POST",
    headers: headers(apiKey),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error("Failed to mark reported");
  return res.json();
}

export async function deleteIncident(apiKey: string, id: string): Promise<void> {
  const res = await fetch(`/v1/incidents/${id}`, {
    method: "DELETE",
    headers: headers(apiKey),
  });
  if (!res.ok && res.status !== 204) throw new Error("Failed to delete incident");
}

export async function fetchReportMarkdown(
  apiKey: string,
  id: string,
  contact: { organisation?: string; contact?: string } = {},
): Promise<string> {
  const res = await fetch(`/v1/incidents/${id}/report-template/markdown`, {
    method: "POST",
    headers: headers(apiKey),
    body: JSON.stringify(contact),
  });
  if (!res.ok) throw new Error("Failed to generate Markdown report");
  return res.text();
}

export async function fetchReportPDF(
  apiKey: string,
  id: string,
  contact: { organisation?: string; contact?: string } = {},
): Promise<Blob> {
  const res = await fetch(`/v1/incidents/${id}/report-template/pdf`, {
    method: "POST",
    headers: headers(apiKey),
    body: JSON.stringify(contact),
  });
  if (!res.ok) throw new Error("Failed to generate PDF report");
  return res.blob();
}
