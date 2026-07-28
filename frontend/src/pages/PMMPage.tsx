import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  AlertCircle,
  CheckCircle,
  Download,
  FileCheck,
  Gauge,
  Loader2,
  Save,
  Sparkles,
} from "lucide-react";
import { listAgents, type Agent } from "../api";
import {
  createComplianceDocument,
  getComplianceDocument,
  listComplianceDocuments,
  type ComplianceDocument,
} from "../compliance-api";
import {
  AgentOrManualSelector,
  EMPTY_MANUAL,
  manualAgentPayload,
  type ManualAgentState,
} from "../components/AgentOrManualSelector";
import { loadOrgProfile } from "../org-profile";

type PMMDocument = Record<string, unknown>;

const DRAFT_KEY = "af_pmm_draft_v1";
const CADENCES = ["weekly", "monthly", "quarterly", "annual"] as const;

interface DraftState {
  agent_id: string;
  review_cadence: (typeof CADENCES)[number];
  pmm_owner: string;
  escalation_chain: string;
  analysis_methodology: string;
  re_assessment_triggers: string;
  corrective_action_procedure: string;
}

const EMPTY: DraftState = {
  agent_id: "",
  review_cadence: "monthly",
  pmm_owner: "",
  escalation_chain: "",
  analysis_methodology: "",
  re_assessment_triggers: "",
  corrective_action_procedure: "",
};

function splitLines(value: string): string[] | undefined {
  const lines = value.split("\n").map((l) => l.trim()).filter(Boolean);
  return lines.length > 0 ? lines : undefined;
}

function downloadBlob(filename: string, content: string | Blob, mime?: string) {
  const blob = typeof content === "string" ? new Blob([content], { type: mime }) : content;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function buildPayload(
  d: DraftState,
  mode: "agent" | "manual",
  manual: ManualAgentState,
): Record<string, unknown> {
  const base: Record<string, unknown> = {
    review_cadence: d.review_cadence,
    pmm_owner: d.pmm_owner || undefined,
    escalation_chain: splitLines(d.escalation_chain),
    analysis_methodology: d.analysis_methodology || undefined,
    re_assessment_triggers: splitLines(d.re_assessment_triggers),
    corrective_action_procedure: splitLines(d.corrective_action_procedure),
  };
  if (mode === "manual") {
    base.manual_agent = manualAgentPayload(manual);
  } else {
    base.agent_id = d.agent_id;
  }
  return base;
}

export function PMMPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const apiKey = typeof window !== "undefined" ? localStorage.getItem("af_api_key") : null;

  const [agents, setAgents] = useState<Agent[]>([]);
  const [draft, setDraft] = useState<DraftState>(() => {
    if (typeof window === "undefined") return EMPTY;
    const raw = localStorage.getItem(DRAFT_KEY);
    if (!raw) return EMPTY;
    try {
      return { ...EMPTY, ...JSON.parse(raw) };
    } catch {
      return EMPTY;
    }
  });
  const [preview, setPreview] = useState<PMMDocument | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedId, setSavedId] = useState<string | null>(null);
  const [existingDocs, setExistingDocs] = useState<ComplianceDocument[]>([]);
  const [mode, setMode] = useState<"agent" | "manual">("agent");
  const [manual, setManual] = useState<ManualAgentState>(EMPTY_MANUAL);

  const readyToGenerate =
    (mode === "agent" && !!draft.agent_id) ||
    (mode === "manual" && manual.name.trim().length > 0);

  useEffect(() => {
    localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
  }, [draft]);

  useEffect(() => {
    listAgents().then((d) => setAgents(d.agents)).catch(() => setAgents([]));
  }, []);

  useEffect(() => {
    const profile = loadOrgProfile();
    if (!profile.organisation) return;
    setDraft((prev) => ({
      ...prev,
      pmm_owner: prev.pmm_owner || profile.pmm_owner || profile.accountability_owner,
    }));
  }, []);

  useEffect(() => {
    const urlAgent = searchParams.get("agent_id");
    if (urlAgent && urlAgent !== draft.agent_id) {
      setDraft((p) => ({ ...p, agent_id: urlAgent }));
    }
  }, [searchParams, draft.agent_id]);

  useEffect(() => {
    if (!apiKey || !draft.agent_id) {
      setExistingDocs([]);
      return;
    }
    listComplianceDocuments(apiKey, { doc_type: "pmm_plan", agent_id: draft.agent_id })
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
        const res = await fetch("/v1/pmm/template", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
          body: JSON.stringify(buildPayload(draft, mode, manual)),
        });
        if (!res.ok) throw new Error("Template generation failed");
        setPreview(await res.json());
      } else if (mode === "agent" && draft.agent_id) {
        const res = await fetch(`/v1/pmm/template/public/${encodeURIComponent(draft.agent_id)}`);
        if (!res.ok) throw new Error("Preview failed");
        setPreview(await res.json());
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
      `pmm-plan-${draft.agent_id || "draft"}.json`,
      JSON.stringify(preview, null, 2),
      "application/json",
    );
  };

  const handleDownloadMarkdown = async () => {
    if (!readyToGenerate || !apiKey) {
      setError("Log in to export Markdown. JSON works anonymously.");
      return;
    }
    try {
      const res = await fetch("/v1/pmm/template/markdown", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
        body: JSON.stringify(buildPayload(draft, mode, manual)),
      });
      if (!res.ok) throw new Error("Markdown export failed");
      const md = await res.text();
      downloadBlob(`pmm-plan-${draft.agent_id}.md`, md, "text/markdown");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Markdown export failed");
    }
  };

  const handleDownloadPDF = async () => {
    if (!readyToGenerate || !apiKey) {
      setError("Log in to export PDF. JSON works anonymously.");
      return;
    }
    setBusy(true);
    try {
      const res = await fetch("/v1/pmm/template/pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
        body: JSON.stringify(buildPayload(draft, mode, manual)),
      });
      if (!res.ok) throw new Error("PDF export failed");
      downloadBlob(`pmm-plan-${draft.agent_id}.pdf`, await res.blob());
    } catch (e) {
      setError(e instanceof Error ? e.message : "PDF export failed");
    } finally {
      setBusy(false);
    }
  };

  const handleSave = async () => {
    if (!preview || !apiKey) {
      setError("Generate and log in first.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const title = draft.pmm_owner
        ? `PMM · ${draft.agent_id} · owned by ${draft.pmm_owner}`
        : `PMM · ${draft.agent_id}`;
      const doc = await createComplianceDocument(apiKey, {
        doc_type: "pmm_plan",
        title,
        payload: preview as Record<string, unknown>,
        agent_id: draft.agent_id,
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

  const handleLoadSaved = async (docId: string) => {
    if (!apiKey) return;
    setBusy(true);
    setError(null);
    try {
      const doc = await getComplianceDocument(apiKey, docId);
      setPreview(doc.payload as PMMDocument);
      const payload = doc.payload as Record<string, unknown>;
      const ownership = (payload.ownership || {}) as Record<string, unknown>;
      const joinLines = (v: unknown): string =>
        Array.isArray(v)
          ? (v as string[]).filter((x) => !x.includes("[PROVIDER")).join("\n")
          : "";
      const strip = (v: unknown, fallback: string): string => {
        if (typeof v !== "string") return fallback;
        if (v.includes("[PROVIDER")) return fallback;
        return v;
      };
      setDraft((prev) => ({
        ...prev,
        review_cadence:
          (payload.review_cadence as DraftState["review_cadence"]) || prev.review_cadence,
        pmm_owner: strip(ownership.pmm_owner, prev.pmm_owner),
        escalation_chain: joinLines(ownership.escalation_chain) || prev.escalation_chain,
        analysis_methodology: strip(payload.analysis_methodology, prev.analysis_methodology),
        re_assessment_triggers:
          joinLines(payload.re_assessment_triggers) || prev.re_assessment_triggers,
        corrective_action_procedure:
          joinLines(payload.corrective_action_procedure) || prev.corrective_action_procedure,
      }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Load failed");
    } finally {
      setBusy(false);
    }
  };

  const handleClear = () => {
    setDraft(EMPTY);
    setPreview(null);
    setSavedId(null);
    setError(null);
    localStorage.removeItem(DRAFT_KEY);
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
            EU AI Act Art. 72
          </p>
          <h1 className="text-3xl sm:text-4xl font-semibold text-[#f1f5f9] mb-4 leading-[1.15] tracking-tight">
            Post-Market<br />
            <span className="text-[#00d4ff]">Monitoring Plan.</span>
          </h1>
          <p className="text-[15px] text-[#94a3b8] leading-relaxed max-w-lg mx-auto">
            Platform-native metrics, baseline values observed on the real agent,
            alert thresholds, and the corrective-action playbook. Exports as JSON,
            Markdown, or PDF; saves to the compliance workspace.
          </p>
        </div>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4">
          <Card title="Context" icon={<Gauge size={14} className="text-[#00d4ff]" />}>
            <AgentOrManualSelector
              agents={agents}
              agentId={draft.agent_id}
              mode={mode}
              manual={manual}
              onAgentIdChange={(id) => setField("agent_id", id)}
              onModeChange={setMode}
              onManualChange={setManual}
            />
            <Field label="Review cadence">
              <select
                value={draft.review_cadence}
                onChange={(e) => setField("review_cadence", e.target.value as DraftState["review_cadence"])}
                className={inputClass}
              >
                {CADENCES.map((c) => (
                  <option key={c} value={c}>
                    {c.charAt(0).toUpperCase() + c.slice(1)}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="PMM owner (role)">
              <input
                value={draft.pmm_owner}
                onChange={(e) => setField("pmm_owner", e.target.value)}
                placeholder="e.g., Head of AI Governance"
                className={inputClass}
              />
            </Field>
            <Field label="Escalation chain (one per line)">
              <textarea
                rows={3}
                value={draft.escalation_chain}
                onChange={(e) => setField("escalation_chain", e.target.value)}
                placeholder={"L1: on-call engineer\nL2: Head of AI\nL3: Compliance officer"}
                className={inputClass}
              />
            </Field>
          </Card>

          <Card title="Analysis methodology">
            <Field label="How will you aggregate and review?">
              <textarea
                rows={4}
                value={draft.analysis_methodology}
                onChange={(e) => setField("analysis_methodology", e.target.value)}
                placeholder="Which dashboards, aggregation windows, sampling strategies. Leave empty to inherit the platform default."
                className={inputClass}
              />
            </Field>
          </Card>

          <Card title="Triggers and actions">
            <Field label="Re-assessment triggers (one per line)">
              <textarea
                rows={4}
                value={draft.re_assessment_triggers}
                onChange={(e) => setField("re_assessment_triggers", e.target.value)}
                placeholder="Leave empty to inherit the platform default list."
                className={inputClass}
              />
            </Field>
            <Field label="Corrective-action procedure (one per line)">
              <textarea
                rows={4}
                value={draft.corrective_action_procedure}
                onChange={(e) => setField("corrective_action_procedure", e.target.value)}
                placeholder="Leave empty to inherit the platform default playbook."
                className={inputClass}
              />
            </Field>
          </Card>
        </div>

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
                <CheckCircle
                  size={14}
                  className={`shrink-0 mt-0.5 ${
                    existingDocs.some((d) => d.is_stale) ? "text-amber-400" : "text-emerald-400"
                  }`}
                />
                <div>
                  <p className="text-xs text-[#f1f5f9] font-medium">
                    {existingDocs.some((d) => d.is_stale)
                      ? "Existing PMM plan is stale"
                      : "Existing PMM plan for this agent"}
                  </p>
                  <p className="text-xs text-[#94a3b8] mt-1 leading-relaxed">
                    Load the latest to continue editing.
                  </p>
                </div>
              </div>
              <div className="space-y-1.5">
                {existingDocs.slice(0, 3).map((d) => (
                  <div key={d.id} className="flex items-center justify-between gap-2 text-xs">
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
                Observed baseline (platform)
              </h3>
              <dl className="space-y-1.5 text-xs text-[#94a3b8]">
                <Row k="Agent" v={selectedAgent.name} />
                <Row
                  k="Risk class"
                  v={(selectedAgent as unknown as { risk_class?: string }).risk_class || "minimal"}
                />
                <Row
                  k="Executions"
                  v={`${selectedAgent.total_executions ?? 0} (${selectedAgent.success_count ?? 0} success)`}
                />
                <Row
                  k="Trust score"
                  v={selectedAgent.trust_score != null ? String(selectedAgent.trust_score) : "-"}
                />
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
              Generate PMM plan
            </button>
            <button
              onClick={handleDownloadJSON}
              disabled={!preview}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-white/[0.08] text-sm text-[#94a3b8] hover:text-[#f1f5f9] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <Download size={14} />
              Download JSON
            </button>
            <button
              onClick={handleDownloadMarkdown}
              disabled={!readyToGenerate || busy}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-white/[0.08] text-sm text-[#94a3b8] hover:text-[#f1f5f9] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <FileCheck size={14} />
              Download Markdown
            </button>
            <button
              onClick={handleDownloadPDF}
              disabled={!readyToGenerate || busy}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-white/[0.08] text-sm text-[#94a3b8] hover:text-[#f1f5f9] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <FileCheck size={14} />
              Download PDF
            </button>
            <button
              onClick={handleSave}
              disabled={!preview || !apiKey || busy}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-emerald-500/20 bg-emerald-500/5 text-emerald-300 hover:bg-emerald-500/10 text-sm disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <Save size={14} />
              Save to workspace
            </button>
            <button
              onClick={handleClear}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-white/[0.08] text-sm text-[#64748b] hover:text-red-400 transition-colors"
            >
              Clear draft
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
                Saved as{" "}
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
                : "Generate a plan to see the pre-filled document here."}
            </pre>
          </div>

          <p className="text-xs text-[#64748b] leading-relaxed">
            Platform-native data sources and baseline metrics are pre-filled. Override the
            cadence and ownership above. Sections marked{" "}
            <span className="text-[#94a3b8]">[PROVIDER: …]</span> still need completion.
          </p>
        </div>
      </div>
    </>
  );
}

const inputClass =
  "w-full px-3 py-2 rounded-lg bg-[#0a0a0f] border border-white/[0.06] text-sm text-[#f1f5f9] placeholder-[#64748b] focus:outline-none focus:border-[#00d4ff]/30";

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

function Card({
  title,
  icon,
  children,
}: {
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5 space-y-4">
      <h2 className="text-sm font-medium text-[#f1f5f9] flex items-center gap-2">
        {icon}
        {title}
      </h2>
      {children}
    </div>
  );
}
