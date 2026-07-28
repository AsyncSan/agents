import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { AlertCircle, CheckCircle, Download, FileCheck, Loader2, Save, Shield, ShieldAlert, Sparkles } from "lucide-react";
import { listAgents, type Agent } from "../api";
import { createComplianceDocument, listComplianceDocuments, getComplianceDocument, type ComplianceDocument } from "../compliance-api";
import { useT } from "../i18n";
import {
  AgentOrManualSelector,
  EMPTY_MANUAL,
  manualAgentPayload,
  type ManualAgentState,
} from "../components/AgentOrManualSelector";
import { loadOrgProfile } from "../org-profile";

type TriggerCategory = { key: string; description: string };

type FRIADocument = Record<string, unknown>;

const DRAFT_STORAGE_KEY = "af_fria_draft_v1";

function downloadBlob(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

async function fetchTriggerCategories(apiKey: string): Promise<TriggerCategory[]> {
  const res = await fetch("/v1/fria/trigger-categories", {
    headers: { "X-API-Key": apiKey },
  });
  if (!res.ok) throw new Error("Failed to load trigger categories");
  const data = await res.json();
  return data.categories;
}

async function fetchPublicTemplate(agentId: string): Promise<FRIADocument> {
  const res = await fetch(`/v1/fria/template/public/${encodeURIComponent(agentId)}`);
  if (!res.ok) throw new Error("Failed to preview FRIA template");
  return res.json();
}

async function postTemplate(
  apiKey: string,
  payload: Record<string, unknown>,
): Promise<FRIADocument> {
  const res = await fetch("/v1/fria/template", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(err?.error?.message || "Template generation failed");
  }
  return res.json();
}

async function fetchMarkdown(
  apiKey: string,
  payload: Record<string, unknown>,
): Promise<string> {
  const res = await fetch("/v1/fria/template/markdown", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Markdown export failed");
  return res.text();
}

async function fetchPDF(
  apiKey: string,
  payload: Record<string, unknown>,
): Promise<Blob> {
  const res = await fetch("/v1/fria/template/pdf", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("PDF export failed");
  return res.blob();
}

interface DraftState {
  agent_id: string;
  use_case_key: string;
  deployer_organisation: string;
  deployer_contact: string;
  deployer_process_summary: string;
  intended_duration: string;
  frequency: string;
  estimated_volume_per_month: string;
  affected_categories: string;
  vulnerable_groups: string;
  potential_harms: string;
  deployer_oversight_measures: string;
  internal_governance: string;
  complaint_mechanism: string;
  authority_reporting: string;
  dpia_reference: string;
}

const EMPTY_DRAFT: DraftState = {
  agent_id: "",
  use_case_key: "",
  deployer_organisation: "",
  deployer_contact: "",
  deployer_process_summary: "",
  intended_duration: "",
  frequency: "",
  estimated_volume_per_month: "",
  affected_categories: "",
  vulnerable_groups: "",
  potential_harms: "",
  deployer_oversight_measures: "",
  internal_governance: "",
  complaint_mechanism: "",
  authority_reporting: "",
  dpia_reference: "",
};

function splitLines(value: string): string[] | undefined {
  const lines = value
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);
  return lines.length > 0 ? lines : undefined;
}

function buildPayload(
  draft: DraftState,
  mode: "agent" | "manual",
  manual: ManualAgentState,
): Record<string, unknown> {
  const base: Record<string, unknown> = {
    use_case_key: draft.use_case_key || undefined,
    deployer_organisation: draft.deployer_organisation || undefined,
    deployer_contact: draft.deployer_contact || undefined,
    deployer_process_summary: draft.deployer_process_summary || undefined,
    intended_duration: draft.intended_duration || undefined,
    frequency: draft.frequency || undefined,
    estimated_volume_per_month: draft.estimated_volume_per_month || undefined,
    affected_categories: splitLines(draft.affected_categories),
    vulnerable_groups: splitLines(draft.vulnerable_groups),
    potential_harms: splitLines(draft.potential_harms),
    deployer_oversight_measures: splitLines(draft.deployer_oversight_measures),
    internal_governance: splitLines(draft.internal_governance),
    complaint_mechanism: draft.complaint_mechanism || undefined,
    authority_reporting: draft.authority_reporting || undefined,
    dpia_reference: draft.dpia_reference || undefined,
  };
  if (mode === "manual") {
    base.manual_agent = manualAgentPayload(manual);
  } else {
    base.agent_id = draft.agent_id;
  }
  return base;
}

export function FRIAPage() {
  const { t } = useT();
  const [searchParams, setSearchParams] = useSearchParams();
  const apiKey = typeof window !== "undefined" ? localStorage.getItem("af_api_key") : null;

  const [agents, setAgents] = useState<Agent[]>([]);
  const [categories, setCategories] = useState<TriggerCategory[]>([]);
  const [draft, setDraft] = useState<DraftState>(() => {
    if (typeof window === "undefined") return EMPTY_DRAFT;
    const raw = localStorage.getItem(DRAFT_STORAGE_KEY);
    if (!raw) return EMPTY_DRAFT;
    try {
      return { ...EMPTY_DRAFT, ...JSON.parse(raw) };
    } catch {
      return EMPTY_DRAFT;
    }
  });
  const [preview, setPreview] = useState<FRIADocument | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedId, setSavedId] = useState<string | null>(null);
  const [existingDocs, setExistingDocs] = useState<ComplianceDocument[]>([]);
  const [mode, setMode] = useState<"agent" | "manual">("agent");
  const [manual, setManual] = useState<ManualAgentState>(EMPTY_MANUAL);

  useEffect(() => {
    localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(draft));
  }, [draft]);

  useEffect(() => {
    listAgents().then((d) => setAgents(d.agents)).catch(() => setAgents([]));
  }, []);

  // Pre-fill from org profile, only for fields the user has not touched yet.
  useEffect(() => {
    const profile = loadOrgProfile();
    if (!profile.organisation) return;
    setDraft((prev) => ({
      ...prev,
      deployer_organisation: prev.deployer_organisation || profile.organisation,
      deployer_contact: prev.deployer_contact || profile.contact,
    }));
  }, []);

  useEffect(() => {
    if (!apiKey) return;
    fetchTriggerCategories(apiKey)
      .then(setCategories)
      .catch(() => {
        setCategories([
          { key: "credit_scoring", description: "Credit scoring of natural persons (Annex III §5(b))" },
          { key: "insurance_pricing", description: "Risk assessment for life or health insurance (Annex III §5(c))" },
          { key: "public_service", description: "Public body or public service deployment" },
          { key: "other_high_risk", description: "Other Annex III high-risk deployment" },
        ]);
      });
  }, [apiKey]);

  useEffect(() => {
    const urlAgent = searchParams.get("agent_id");
    if (urlAgent && urlAgent !== draft.agent_id) {
      setDraft((prev) => ({ ...prev, agent_id: urlAgent }));
    }
  }, [searchParams, draft.agent_id]);

  useEffect(() => {
    if (!apiKey || !draft.agent_id) {
      setExistingDocs([]);
      return;
    }
    listComplianceDocuments(apiKey, { doc_type: "fria", agent_id: draft.agent_id })
      .then((r) => setExistingDocs(r.documents.filter((d) => d.status !== "archived")))
      .catch(() => setExistingDocs([]));
  }, [apiKey, draft.agent_id, savedId]);

  const selectedAgent = useMemo(
    () => agents.find((a) => a.id === draft.agent_id) || null,
    [agents, draft.agent_id],
  );

  const setField = <K extends keyof DraftState>(key: K, value: DraftState[K]) => {
    setDraft((prev) => ({ ...prev, [key]: value }));
    if (key === "agent_id" && typeof value === "string") {
      const next = new URLSearchParams(searchParams);
      if (value) next.set("agent_id", value); else next.delete("agent_id");
      setSearchParams(next, { replace: true });
    }
  };

  const readyToGenerate =
    (mode === "agent" && !!draft.agent_id) ||
    (mode === "manual" && manual.name.trim().length > 0);

  const handleGenerate = async () => {
    if (!readyToGenerate) {
      setError(
        mode === "manual"
          ? "Give the system a name before generating."
          : "Select an agent or describe one manually.",
      );
      return;
    }
    setBusy(true);
    setError(null);
    try {
      if (apiKey) {
        const doc = await postTemplate(apiKey, buildPayload(draft, mode, manual));
        setPreview(doc);
      } else if (mode === "agent" && draft.agent_id) {
        const doc = await fetchPublicTemplate(draft.agent_id);
        setPreview(doc);
      } else {
        setError("Log in to generate a draft for an externally-described system.");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setBusy(false);
    }
  };

  const handleDownloadJSON = () => {
    if (!preview) return;
    downloadBlob(
      `fria-${draft.agent_id || "draft"}.json`,
      JSON.stringify(preview, null, 2),
      "application/json",
    );
  };

  const handleDownloadMarkdown = async () => {
    if (!draft.agent_id) return;
    try {
      if (apiKey) {
        const md = await fetchMarkdown(apiKey, buildPayload(draft, mode, manual));
        downloadBlob(`fria-${draft.agent_id}.md`, md, "text/markdown");
      } else {
        setError("Log in to export Markdown. The JSON download works anonymously.");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Markdown export failed");
    }
  };

  const handleDownloadPDF = async () => {
    if (!draft.agent_id) return;
    if (!apiKey) {
      setError("Log in to export PDF. The JSON download works anonymously.");
      return;
    }
    setBusy(true);
    try {
      const blob = await fetchPDF(apiKey, buildPayload(draft, mode, manual));
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `fria-${draft.agent_id}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "PDF export failed");
    } finally {
      setBusy(false);
    }
  };

  const handleLoadSaved = async (docId: string) => {
    if (!apiKey) return;
    setBusy(true);
    setError(null);
    try {
      const doc = await getComplianceDocument(apiKey, docId);
      setPreview(doc.payload as FRIADocument);
      const payload = doc.payload as Record<string, unknown>;
      const deployer = (payload.deployer || {}) as Record<string, string>;
      const useCase = (payload.use_case || {}) as Record<string, string>;
      const s1 = (payload.section_1_process_description || {}) as Record<string, string>;
      const s2 = (payload.section_2_duration_frequency || {}) as Record<string, string>;
      const s3 = (payload.section_3_affected_persons || {}) as Record<string, unknown>;
      const s4 = (payload.section_4_harm_risks || {}) as Record<string, unknown>;
      const s5 = (payload.section_5_human_oversight || {}) as Record<string, unknown>;
      const s6 = (payload.section_6_mitigation_governance || {}) as Record<string, string>;
      const joinLines = (v: unknown): string =>
        Array.isArray(v)
          ? (v as string[]).filter((x) => !x.includes("[DEPLOYER")).join("\n")
          : "";
      setDraft((prev) => ({
        ...prev,
        use_case_key: useCase.trigger_category || prev.use_case_key,
        deployer_organisation: stripPlaceholder(deployer.organisation, prev.deployer_organisation),
        deployer_contact: stripPlaceholder(deployer.contact, prev.deployer_contact),
        deployer_process_summary: stripPlaceholder(
          s1.deployer_process_summary,
          prev.deployer_process_summary,
        ),
        intended_duration: stripPlaceholder(s2.intended_duration, prev.intended_duration),
        frequency: stripPlaceholder(s2.frequency, prev.frequency),
        estimated_volume_per_month: stripPlaceholder(
          s2.estimated_volume_per_month,
          prev.estimated_volume_per_month,
        ),
        affected_categories: joinLines(s3.primary_categories) || prev.affected_categories,
        vulnerable_groups: joinLines(s3.vulnerable_groups_considered) || prev.vulnerable_groups,
        potential_harms: joinLines(s4.potential_harms) || prev.potential_harms,
        deployer_oversight_measures:
          joinLines(s5.deployer_measures) || prev.deployer_oversight_measures,
        internal_governance:
          joinLines(s6.internal_governance) || prev.internal_governance,
        complaint_mechanism: stripPlaceholder(s6.complaint_mechanism, prev.complaint_mechanism),
        authority_reporting: stripPlaceholder(s6.authority_reporting, prev.authority_reporting),
        dpia_reference: stripPlaceholder(s6.dpia_reference, prev.dpia_reference),
      }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load saved document");
    } finally {
      setBusy(false);
    }
  };

  const handleSaveToWorkspace = async () => {
    if (!preview) {
      setError("Generate the draft first.");
      return;
    }
    if (!apiKey) {
      setError("Log in to save to the compliance workspace.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const title = draft.deployer_organisation
        ? `FRIA · ${draft.deployer_organisation} · ${draft.agent_id}`
        : `FRIA · ${draft.agent_id}`;
      const doc = await createComplianceDocument(apiKey, {
        doc_type: "fria",
        title,
        payload: preview as Record<string, unknown>,
        agent_id: draft.agent_id || undefined,
        agent_version: selectedAgent
          ? (selectedAgent as unknown as { version?: number }).version ?? null
          : undefined,
      });
      setSavedId(doc.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  };

  const handleClear = () => {
    setDraft(EMPTY_DRAFT);
    setPreview(null);
    setSavedId(null);
    setError(null);
    localStorage.removeItem(DRAFT_STORAGE_KEY);
    setSearchParams({}, { replace: true });
  };

  return (
    <>
      <section className="relative mb-10 pt-8">
        <div className="absolute inset-0 -z-10 overflow-hidden">
          <div
            className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] rounded-full opacity-[0.03]"
            style={{ background: "radial-gradient(circle, #00d4ff 0%, transparent 60%)" }}
          />
        </div>
        <div className="text-center max-w-2xl mx-auto">
          <p className="text-xs text-[#64748b] mb-3 font-medium uppercase tracking-widest">
            {t("fria.eyebrow")}
          </p>
          <h1 className="text-3xl sm:text-4xl font-semibold text-[#f1f5f9] mb-4 leading-[1.15] tracking-tight">
            {t("fria.title1")}<br />
            <span className="text-[#00d4ff]">{t("fria.title2")}</span>
          </h1>
          <p className="text-[15px] text-[#94a3b8] leading-relaxed max-w-lg mx-auto">
            {t("fria.sub")}
          </p>
        </div>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Form */}
        <div className="space-y-4">
          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5 space-y-4">
            <h2 className="text-sm font-medium text-[#f1f5f9] flex items-center gap-2">
              <Shield size={14} className="text-[#00d4ff]" />
              Context
            </h2>

            <AgentOrManualSelector
              agents={agents}
              agentId={draft.agent_id}
              mode={mode}
              manual={manual}
              onAgentIdChange={(id) => setField("agent_id", id)}
              onModeChange={setMode}
              onManualChange={setManual}
            />
            {mode === "manual" && (
              <p className="text-xs text-[#64748b] -mt-1">
                The FRIA will reference your system by name. No platform registration
                required; you stay the owner of the document.
              </p>
            )}

            <Field label="Trigger category (why Art. 27 applies)">
              <select
                value={draft.use_case_key}
                onChange={(e) => setField("use_case_key", e.target.value)}
                className={inputClass}
              >
                <option value="">Select…</option>
                {categories.map((c) => (
                  <option key={c.key} value={c.key}>
                    {c.description}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Deployer organisation">
              <input
                value={draft.deployer_organisation}
                onChange={(e) => setField("deployer_organisation", e.target.value)}
                placeholder="Legal name of the deploying organisation"
                className={inputClass}
              />
            </Field>

            <Field label="Accountable contact">
              <input
                value={draft.deployer_contact}
                onChange={(e) => setField("deployer_contact", e.target.value)}
                placeholder="Name, role, email"
                className={inputClass}
              />
            </Field>
          </div>

          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5 space-y-4">
            <h2 className="text-sm font-medium text-[#f1f5f9]">1. Process description</h2>
            <Field label="How is the agent used in your process?">
              <textarea
                rows={3}
                value={draft.deployer_process_summary}
                onChange={(e) => setField("deployer_process_summary", e.target.value)}
                placeholder="Describe the business process, which steps are automated, which stay human."
                className={inputClass}
              />
            </Field>
          </div>

          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5 space-y-4">
            <h2 className="text-sm font-medium text-[#f1f5f9]">2. Duration and frequency</h2>
            <Field label="Intended duration">
              <input
                value={draft.intended_duration}
                onChange={(e) => setField("intended_duration", e.target.value)}
                placeholder="e.g., 'from 2026-09-01, ongoing'"
                className={inputClass}
              />
            </Field>
            <Field label="Frequency">
              <input
                value={draft.frequency}
                onChange={(e) => setField("frequency", e.target.value)}
                placeholder="e.g., 'every incoming credit application'"
                className={inputClass}
              />
            </Field>
            <Field label="Estimated affected persons per month">
              <input
                value={draft.estimated_volume_per_month}
                onChange={(e) => setField("estimated_volume_per_month", e.target.value)}
                placeholder="e.g., '~12,000'"
                className={inputClass}
              />
            </Field>
          </div>

          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5 space-y-4">
            <h2 className="text-sm font-medium text-[#f1f5f9]">3. Affected persons</h2>
            <Field label="Primary categories (one per line)">
              <textarea
                rows={3}
                value={draft.affected_categories}
                onChange={(e) => setField("affected_categories", e.target.value)}
                placeholder={"Consumer credit applicants\nExisting card holders under review"}
                className={inputClass}
              />
            </Field>
            <Field label="Vulnerable groups considered (one per line)">
              <textarea
                rows={2}
                value={draft.vulnerable_groups}
                onChange={(e) => setField("vulnerable_groups", e.target.value)}
                placeholder={"Minors\nApplicants with language barriers"}
                className={inputClass}
              />
            </Field>
          </div>

          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5 space-y-4">
            <h2 className="text-sm font-medium text-[#f1f5f9]">4. Specific risks of harm</h2>
            <Field label="Potential harms (one per line)">
              <textarea
                rows={3}
                value={draft.potential_harms}
                onChange={(e) => setField("potential_harms", e.target.value)}
                placeholder={"Discriminatory denial on protected characteristics\nErroneous credit rejection leading to economic harm"}
                className={inputClass}
              />
            </Field>
          </div>

          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5 space-y-4">
            <h2 className="text-sm font-medium text-[#f1f5f9]">5. Human oversight (deployer-side)</h2>
            <Field label="Oversight measures (one per line)">
              <textarea
                rows={3}
                value={draft.deployer_oversight_measures}
                onChange={(e) => setField("deployer_oversight_measures", e.target.value)}
                placeholder={"Named oversight officer reviews 10% of outcomes daily\nAll 'decline' decisions require human sign-off"}
                className={inputClass}
              />
            </Field>
          </div>

          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5 space-y-4">
            <h2 className="text-sm font-medium text-[#f1f5f9]">6. Governance and mitigation</h2>
            <Field label="Internal governance (one per line)">
              <textarea
                rows={3}
                value={draft.internal_governance}
                onChange={(e) => setField("internal_governance", e.target.value)}
                placeholder={"Monthly review with compliance\nStop-deployment authority: Head of Risk"}
                className={inputClass}
              />
            </Field>
            <Field label="Complaint mechanism">
              <input
                value={draft.complaint_mechanism}
                onChange={(e) => setField("complaint_mechanism", e.target.value)}
                placeholder="How affected persons contest an outcome, SLA"
                className={inputClass}
              />
            </Field>
            <Field label="Authority reporting (Art. 73)">
              <input
                value={draft.authority_reporting}
                onChange={(e) => setField("authority_reporting", e.target.value)}
                placeholder="Process for reporting serious incidents to the MSA"
                className={inputClass}
              />
            </Field>
            <Field label="DPIA reference (Art. 27(4))">
              <input
                value={draft.dpia_reference}
                onChange={(e) => setField("dpia_reference", e.target.value)}
                placeholder="Link or identifier of the GDPR DPIA"
                className={inputClass}
              />
            </Field>
          </div>
        </div>

        {/* Preview + actions */}
        <div className="space-y-4 lg:sticky lg:top-20 lg:self-start">
          {existingDocs.length > 0 && (
            <div
              className={`rounded-xl border p-4 ${
                existingDocs.some((d) => d.is_stale)
                  ? "border-amber-500/20 bg-amber-500/5"
                  : "border-white/[0.06] bg-[#111118]"
              }`}
            >
              <div className="flex items-start gap-2 mb-3">
                {existingDocs.some((d) => d.is_stale) ? (
                  <ShieldAlert size={14} className="text-amber-400 shrink-0 mt-0.5" />
                ) : (
                  <CheckCircle size={14} className="text-emerald-400 shrink-0 mt-0.5" />
                )}
                <div>
                  <p className="text-xs text-[#f1f5f9] font-medium">
                    {existingDocs.some((d) => d.is_stale)
                      ? "Existing FRIA is stale"
                      : "You have an existing FRIA for this agent"}
                  </p>
                  <p className="text-xs text-[#94a3b8] mt-1 leading-relaxed">
                    {existingDocs.some((d) => d.is_stale)
                      ? "The agent was updated since your last review. Load the saved draft, reconcile, and re-approve."
                      : "Load the latest saved draft to continue editing, or start fresh below."}
                  </p>
                </div>
              </div>
              <div className="space-y-1.5">
                {existingDocs.slice(0, 3).map((d) => (
                  <div
                    key={d.id}
                    className="flex items-center justify-between gap-2 text-xs"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-[#94a3b8] truncate">{d.title}</p>
                      <p className="text-[10px] text-[#64748b]">
                        v{d.agent_version} · {d.status}
                        {d.is_stale && d.current_agent_version != null && (
                          <span className="text-amber-400 ml-1">
                            (current v{d.current_agent_version})
                          </span>
                        )}
                      </p>
                    </div>
                    <button
                      onClick={() => handleLoadSaved(d.id)}
                      disabled={busy}
                      className="shrink-0 px-2 py-1 rounded border border-white/[0.08] text-[10px] text-[#94a3b8] hover:text-[#f1f5f9] disabled:opacity-40 transition-colors"
                    >
                      Load
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {selectedAgent && (
            <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
              <h3 className="text-xs font-medium text-[#64748b] uppercase tracking-widest mb-3">
                Auto-filled from agent card
              </h3>
              <dl className="space-y-1.5 text-xs text-[#94a3b8]">
                <Row k="Agent" v={`${selectedAgent.name} (v${selectedAgent.card ? "" : ""})`} />
                <Row k="Domain" v={selectedAgent.card?.capabilities?.domain || "-"} />
                <Row
                  k="Risk class"
                  v={(selectedAgent as unknown as { risk_class?: string }).risk_class || "minimal"}
                />
                <Row k="Description" v={selectedAgent.description || "-"} />
              </dl>
            </div>
          )}

          <div className="flex flex-wrap gap-2">
            <button
              onClick={handleGenerate}
              disabled={!readyToGenerate || busy}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed"
              style={{ transition: "background 0.2s cubic-bezier(0.16, 1, 0.3, 1)" }}
            >
              {busy ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
              {t("fria.cta.generate")}
            </button>
            <button
              onClick={handleDownloadJSON}
              disabled={!preview}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-white/[0.08] text-sm text-[#94a3b8] hover:text-[#f1f5f9] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <Download size={14} />
              {t("fria.cta.json")}
            </button>
            <button
              onClick={handleDownloadMarkdown}
              disabled={!readyToGenerate || busy}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-white/[0.08] text-sm text-[#94a3b8] hover:text-[#f1f5f9] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <FileCheck size={14} />
              {t("fria.cta.md")}
            </button>
            <button
              onClick={handleDownloadPDF}
              disabled={!readyToGenerate || busy}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-white/[0.08] text-sm text-[#94a3b8] hover:text-[#f1f5f9] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <FileCheck size={14} />
              {t("fria.cta.pdf")}
            </button>
            <button
              onClick={handleSaveToWorkspace}
              disabled={!preview || !apiKey || busy}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-emerald-500/20 bg-emerald-500/5 text-emerald-300 hover:bg-emerald-500/10 text-sm disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              title={apiKey ? "Persist to the compliance workspace" : "Log in to save to workspace"}
            >
              <Save size={14} />
              {t("fria.cta.save")}
            </button>
            <button
              onClick={handleClear}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-white/[0.08] text-sm text-[#64748b] hover:text-red-400 transition-colors"
            >
              {t("fria.cta.clear")}
            </button>
          </div>

          {error && (
            <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 flex items-start gap-2">
              <AlertCircle size={14} className="text-red-400 shrink-0 mt-0.5" />
              <p className="text-xs text-red-300">{error}</p>
            </div>
          )}

          {savedId && (
            <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3 flex items-start gap-2">
              <CheckCircle size={14} className="text-emerald-400 shrink-0 mt-0.5" />
              <p className="text-xs text-emerald-200/90">
                Saved to workspace as{" "}
                <a href="/compliance" className="underline hover:text-emerald-100">
                  document {savedId.slice(0, 8)}
                </a>
                .
              </p>
            </div>
          )}

          <div className="rounded-xl border border-white/[0.06] bg-[#0a0a0f] overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-2 border-b border-white/[0.06] text-xs text-[#64748b]">
              Preview (JSON)
            </div>
            <pre className="text-xs text-[#94a3b8] p-4 overflow-x-auto max-h-[600px] overflow-y-auto whitespace-pre-wrap break-words">
              {preview
                ? JSON.stringify(preview, null, 2)
                : "Generate a draft to see the pre-filled FRIA document here."}
            </pre>
          </div>

          <p className="text-xs text-[#64748b] leading-relaxed">
            This scaffold covers the six sections required by Art. 27(1). Sections
            marked <span className="text-[#94a3b8]">[DEPLOYER: …]</span> in the
            output need completion by your team. The draft is stored in this
            browser only, never on our servers.
          </p>
        </div>
      </div>
    </>
  );
}

const inputClass =
  "w-full px-3 py-2 rounded-lg bg-[#0a0a0f] border border-white/[0.06] text-sm text-[#f1f5f9] placeholder-[#64748b] focus:outline-none focus:border-[#00d4ff]/30";

function stripPlaceholder(value: unknown, fallback: string): string {
  if (typeof value !== "string") return fallback;
  if (value.includes("[DEPLOYER")) return fallback;
  return value;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="block text-xs text-[#64748b] mb-1.5">{label}</span>
      {children}
    </label>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex gap-2">
      <dt className="text-[#64748b] w-24 shrink-0">{k}</dt>
      <dd className="text-[#94a3b8]">{v}</dd>
    </div>
  );
}
