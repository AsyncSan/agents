export interface ComplianceDocument {
  id: string;
  org_id: string;
  org_role: string;
  doc_type:
    | "fria"
    | "annex_iv"
    | "literacy_completion"
    | "pmm_plan"
    | "qms_manual"
    | "eu_db_registration"
    | "declaration_of_conformity";
  title: string;
  agent_id: string | null;
  agent_version: number | null;
  current_agent_version: number | null;
  is_stale: boolean;
  status: "draft" | "submitted" | "approved" | "archived";
  created_by: string;
  approved_by: string | null;
  approved_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ComplianceDocumentDetail extends ComplianceDocument {
  payload: Record<string, unknown>;
}

export interface ComplianceListResponse {
  documents: ComplianceDocument[];
  total: number;
  stale_count: number;
}

export interface ComplianceSummary {
  by_doc_type: Record<string, number>;
  by_status: Record<string, number>;
}

function authHeaders(apiKey: string | null): Record<string, string> {
  const h: Record<string, string> = { "Content-Type": "application/json" };
  if (apiKey) h["X-API-Key"] = apiKey;
  return h;
}

export async function createComplianceDocument(
  apiKey: string,
  body: {
    doc_type: ComplianceDocument["doc_type"];
    title: string;
    payload: Record<string, unknown>;
    agent_id?: string | null;
    agent_version?: number | null;
    status?: ComplianceDocument["status"];
    notes?: string;
  },
): Promise<ComplianceDocumentDetail> {
  const res = await fetch("/v1/compliance/documents", {
    method: "POST",
    headers: authHeaders(apiKey),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error("Failed to save document");
  return res.json();
}

export async function listComplianceDocuments(
  apiKey: string,
  filters: { doc_type?: string; status?: string; agent_id?: string } = {},
): Promise<ComplianceListResponse> {
  const params = new URLSearchParams();
  if (filters.doc_type) params.set("doc_type", filters.doc_type);
  if (filters.status) params.set("status", filters.status);
  if (filters.agent_id) params.set("agent_id", filters.agent_id);
  const url = `/v1/compliance/documents${params.toString() ? `?${params}` : ""}`;
  const res = await fetch(url, { headers: authHeaders(apiKey) });
  if (!res.ok) throw new Error("Failed to list documents");
  return res.json();
}

export async function getComplianceDocument(
  apiKey: string,
  id: string,
): Promise<ComplianceDocumentDetail> {
  const res = await fetch(`/v1/compliance/documents/${id}`, {
    headers: authHeaders(apiKey),
  });
  if (!res.ok) throw new Error("Failed to fetch document");
  return res.json();
}

export async function updateComplianceDocument(
  apiKey: string,
  id: string,
  body: {
    title?: string;
    payload?: Record<string, unknown>;
    status?: ComplianceDocument["status"];
    notes?: string;
    agent_version?: number | null;
  },
): Promise<ComplianceDocumentDetail> {
  const res = await fetch(`/v1/compliance/documents/${id}`, {
    method: "PATCH",
    headers: authHeaders(apiKey),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error("Failed to update document");
  return res.json();
}

export async function approveComplianceDocument(
  apiKey: string,
  id: string,
  notes?: string,
): Promise<ComplianceDocumentDetail> {
  const res = await fetch(`/v1/compliance/documents/${id}/approve`, {
    method: "POST",
    headers: authHeaders(apiKey),
    body: JSON.stringify({ notes }),
  });
  if (!res.ok) throw new Error("Failed to approve document");
  return res.json();
}

export async function archiveComplianceDocument(
  apiKey: string,
  id: string,
): Promise<ComplianceDocumentDetail> {
  const res = await fetch(`/v1/compliance/documents/${id}/archive`, {
    method: "POST",
    headers: authHeaders(apiKey),
  });
  if (!res.ok) throw new Error("Failed to archive document");
  return res.json();
}

export async function deleteComplianceDocument(apiKey: string, id: string): Promise<void> {
  const res = await fetch(`/v1/compliance/documents/${id}`, {
    method: "DELETE",
    headers: authHeaders(apiKey),
  });
  if (!res.ok && res.status !== 204) throw new Error("Failed to delete document");
}

export async function getComplianceSummary(apiKey: string): Promise<ComplianceSummary> {
  const res = await fetch("/v1/compliance/documents/summary", {
    headers: authHeaders(apiKey),
  });
  if (!res.ok) throw new Error("Failed to load summary");
  return res.json();
}
