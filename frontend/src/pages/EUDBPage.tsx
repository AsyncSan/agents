import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  AlertCircle,
  CheckCircle,
  Database,
  Download,
  FileCheck,
  Loader2,
  Save,
  Sparkles,
} from "lucide-react";
import { listAgents, type Agent } from "../api";
import { createComplianceDocument } from "../compliance-api";
import {
  AgentOrManualSelector,
  EMPTY_MANUAL,
  manualAgentPayload,
  type ManualAgentState,
} from "../components/AgentOrManualSelector";
import { loadOrgProfile } from "../org-profile";

type RegistrationDoc = Record<string, unknown>;

const DRAFT_KEY = "af_eu_db_draft_v1";
const STATUSES = ["on_market", "no_longer_placed", "recalled", "withdrawn"] as const;

interface DraftState {
  agent_id: string;
  provider_name: string;
  provider_address: string;
  provider_contact: string;
  auth_rep_required: boolean;
  auth_rep_name: string;
  trade_name: string;
  status: (typeof STATUSES)[number];
  placed_on_market_date: string;
  member_states: string;
  doc_reference: string;
  ce_marking_affixed: boolean;
  ifu_url: string;
  non_high_risk_justification: string;
}

const EMPTY: DraftState = {
  agent_id: "",
  provider_name: "",
  provider_address: "",
  provider_contact: "",
  auth_rep_required: false,
  auth_rep_name: "",
  trade_name: "",
  status: "on_market",
  placed_on_market_date: "",
  member_states: "",
  doc_reference: "",
  ce_marking_affixed: false,
  ifu_url: "",
  non_high_risk_justification: "",
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
    provider_name: d.provider_name || undefined,
    provider_address: d.provider_address || undefined,
    provider_contact: d.provider_contact || undefined,
    auth_rep_required: d.auth_rep_required,
    auth_rep_name: d.auth_rep_name || undefined,
    trade_name: d.trade_name || undefined,
    status: d.status,
    placed_on_market_date: d.placed_on_market_date || undefined,
    member_states: splitLines(d.member_states),
    doc_reference: d.doc_reference || undefined,
    ce_marking_affixed: d.ce_marking_affixed,
    ifu_url: d.ifu_url || undefined,
    non_high_risk_justification: d.non_high_risk_justification || undefined,
  };
  if (mode === "manual") {
    base.manual_agent = manualAgentPayload(manual);
  } else {
    base.agent_id = d.agent_id;
  }
  return base;
}

export function EUDBPage() {
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
  const [preview, setPreview] = useState<RegistrationDoc | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedId, setSavedId] = useState<string | null>(null);
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
      provider_name: prev.provider_name || profile.organisation,
      provider_address: prev.provider_address || profile.address,
      provider_contact: prev.provider_contact || profile.contact,
      member_states: prev.member_states || profile.member_states,
      ce_marking_affixed: prev.ce_marking_affixed || profile.ce_marking_affixed,
    }));
  }, []);

  useEffect(() => {
    const urlAgent = searchParams.get("agent_id");
    if (urlAgent && urlAgent !== draft.agent_id) {
      setDraft((p) => ({ ...p, agent_id: urlAgent }));
    }
  }, [searchParams, draft.agent_id]);

  const selectedAgent = useMemo(
    () => agents.find((a) => a.id === draft.agent_id) || null,
    [agents, draft.agent_id],
  );

  const riskClass = selectedAgent
    ? (selectedAgent as unknown as { risk_class?: string }).risk_class || "minimal"
    : "minimal";
  const isHighRisk = riskClass === "high";

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
        const res = await fetch("/v1/eu-db/registration", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
          body: JSON.stringify(buildPayload(draft, mode, manual)),
        });
        if (!res.ok) throw new Error("Registration generation failed");
        setPreview(await res.json());
      } else if (mode === "agent" && draft.agent_id) {
        const res = await fetch(
          `/v1/eu-db/registration/public/${encodeURIComponent(draft.agent_id)}`,
        );
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
      `eu-db-${draft.agent_id || "draft"}.json`,
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
      const res = await fetch("/v1/eu-db/registration/markdown", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
        body: JSON.stringify(buildPayload(draft, mode, manual)),
      });
      if (!res.ok) throw new Error("Markdown export failed");
      downloadBlob(`eu-db-${draft.agent_id}.md`, await res.text(), "text/markdown");
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
      const res = await fetch("/v1/eu-db/registration/pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
        body: JSON.stringify(buildPayload(draft, mode, manual)),
      });
      if (!res.ok) throw new Error("PDF export failed");
      downloadBlob(`eu-db-${draft.agent_id}.pdf`, await res.blob());
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
      const title = draft.provider_name
        ? `EU DB · ${draft.provider_name} · ${draft.agent_id}`
        : `EU DB · ${draft.agent_id}`;
      const doc = await createComplianceDocument(apiKey, {
        doc_type: "eu_db_registration",
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
            EU AI Act Art. 49 · Annex VIII Section B
          </p>
          <h1 className="text-3xl sm:text-4xl font-semibold text-[#f1f5f9] mb-4 leading-[1.15] tracking-tight">
            EU Database<br />
            <span className="text-[#00d4ff]">registration.</span>
          </h1>
          <p className="text-[15px] text-[#94a3b8] leading-relaxed max-w-lg mx-auto">
            The 11 Annex VIII fields, pre-filled from the capability card and your
            provider record. The database opens with the high-risk application date
            on 2 August 2026. Prepare the submission draft now.
          </p>
        </div>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4">
          <Card title="System" icon={<Database size={14} className="text-[#00d4ff]" />}>
            <AgentOrManualSelector
              agents={agents}
              agentId={draft.agent_id}
              mode={mode}
              manual={manual}
              onAgentIdChange={(id) => setField("agent_id", id)}
              onModeChange={setMode}
              onManualChange={setManual}
            />
            <Field label="Trade name (§ B.4)">
              <input
                value={draft.trade_name}
                onChange={(e) => setField("trade_name", e.target.value)}
                placeholder="Public-facing product name (defaults to agent name)"
                className={inputClass}
              />
            </Field>
            <Field label="Status (§ B.6)">
              <select
                value={draft.status}
                onChange={(e) => setField("status", e.target.value as DraftState["status"])}
                className={inputClass}
              >
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s.replace(/_/g, " ")}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Placed on market (YYYY-MM-DD)">
              <input
                type="date"
                value={draft.placed_on_market_date}
                onChange={(e) => setField("placed_on_market_date", e.target.value)}
                className={inputClass}
              />
            </Field>
          </Card>

          <Card title="Provider (§ B.1)">
            <Field label="Legal name">
              <input
                value={draft.provider_name}
                onChange={(e) => setField("provider_name", e.target.value)}
                placeholder="Company legal name"
                className={inputClass}
              />
            </Field>
            <Field label="Registered address">
              <input
                value={draft.provider_address}
                onChange={(e) => setField("provider_address", e.target.value)}
                placeholder="Street, ZIP, City, Country"
                className={inputClass}
              />
            </Field>
            <Field label="Accountable contact">
              <input
                value={draft.provider_contact}
                onChange={(e) => setField("provider_contact", e.target.value)}
                placeholder="Name, role, email, phone"
                className={inputClass}
              />
            </Field>
          </Card>

          <Card title="Authorised representative (§ B.3)">
            <label className="flex items-center gap-2 text-xs text-[#94a3b8]">
              <input
                type="checkbox"
                checked={draft.auth_rep_required}
                onChange={(e) => setField("auth_rep_required", e.target.checked)}
              />
              Non-EU provider; authorised representative required under Art. 22
            </label>
            {draft.auth_rep_required && (
              <Field label="Representative name and address">
                <input
                  value={draft.auth_rep_name}
                  onChange={(e) => setField("auth_rep_name", e.target.value)}
                  placeholder="EU-established legal entity, address"
                  className={inputClass}
                />
              </Field>
            )}
          </Card>

          <Card title="Conformity (§ B.8–9)">
            <Field label="Member States on market (one per line)">
              <textarea
                rows={3}
                value={draft.member_states}
                onChange={(e) => setField("member_states", e.target.value)}
                placeholder={"Germany\nAustria\nFrance"}
                className={inputClass}
              />
            </Field>
            <Field label="Declaration of Conformity reference">
              <input
                value={draft.doc_reference}
                onChange={(e) => setField("doc_reference", e.target.value)}
                placeholder="DoC-ID or URL (per Annex V)"
                className={inputClass}
              />
            </Field>
            <label className="flex items-center gap-2 text-xs text-[#94a3b8]">
              <input
                type="checkbox"
                checked={draft.ce_marking_affixed}
                onChange={(e) => setField("ce_marking_affixed", e.target.checked)}
              />
              CE marking affixed (Art. 48)
            </label>
          </Card>

          <Card title="Instructions for use (§ B.10)">
            <Field label="Electronic IFU URL">
              <input
                value={draft.ifu_url}
                onChange={(e) => setField("ifu_url", e.target.value)}
                placeholder="https://… (public IFU location; platform default if empty)"
                className={inputClass}
              />
            </Field>
          </Card>

          {!isHighRisk && selectedAgent && (
            <Card title="Art. 6(3) non-high-risk declaration (optional)">
              <p className="text-xs text-[#94a3b8] mb-2">
                Only applicable for limited/minimal-risk systems. Must still be
                registered per Art. 49(2).
              </p>
              <Field label="Justification">
                <textarea
                  rows={3}
                  value={draft.non_high_risk_justification}
                  onChange={(e) => setField("non_high_risk_justification", e.target.value)}
                  placeholder="Why this system does not pose a significant risk of harm"
                  className={inputClass}
                />
              </Field>
            </Card>
          )}
        </div>

        <div className="space-y-4 lg:sticky lg:top-20 lg:self-start">
          {selectedAgent && (
            <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
              <h3 className="text-xs font-medium text-[#64748b] uppercase tracking-widest mb-3">
                Auto-filled from capability card
              </h3>
              <dl className="space-y-1.5 text-xs text-[#94a3b8]">
                <Row k="Agent" v={selectedAgent.name} />
                <Row k="Version" v={`v${(selectedAgent as unknown as { version?: number }).version || "?"}`} />
                <Row k="Risk class" v={riskClass} />
                <Row
                  k="Domain"
                  v={selectedAgent.card?.capabilities?.domain || "-"}
                />
                <Row
                  k="Model"
                  v={selectedAgent.card?.runtime?.model || "-"}
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
              Generate registration
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
                : "Generate a registration to see the pre-filled draft here."}
            </pre>
          </div>

          <p className="text-xs text-[#64748b] leading-relaxed">
            The EU database accepts submissions from 2 August 2026. Use this
            preview as the submission draft; retain for 10 years under Art. 18.
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
