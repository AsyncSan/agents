import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  AlertCircle,
  CheckCircle,
  Download,
  FileCheck,
  FileSignature,
  Loader2,
  Save,
  ShieldCheck,
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

type DeclarationDoc = Record<string, unknown>;

const DRAFT_KEY = "af_declaration_draft_v1";

interface DraftState {
  agent_id: string;
  provider_name: string;
  provider_address: string;
  auth_rep_required: boolean;
  auth_rep_name: string;
  auth_rep_address: string;
  processes_personal_data: boolean | null;
  dpo_contact: string;
  harmonised_standards: string;
  common_specifications: string;
  standards_notes: string;
  notified_body_required: boolean;
  notified_body_name: string;
  notified_body_id: string;
  assessment_procedure: string;
  certificate_reference: string;
  signature_place: string;
  signature_date: string;
  signatory_name: string;
  signatory_function: string;
  language: string;
  translations_available: string;
  ce_marking_affixed: boolean;
  ce_marking_affixed_electronically: boolean;
}

const EMPTY: DraftState = {
  agent_id: "",
  provider_name: "",
  provider_address: "",
  auth_rep_required: false,
  auth_rep_name: "",
  auth_rep_address: "",
  processes_personal_data: null,
  dpo_contact: "",
  harmonised_standards: "",
  common_specifications: "",
  standards_notes: "",
  notified_body_required: false,
  notified_body_name: "",
  notified_body_id: "",
  assessment_procedure: "",
  certificate_reference: "",
  signature_place: "",
  signature_date: "",
  signatory_name: "",
  signatory_function: "",
  language: "en",
  translations_available: "de",
  ce_marking_affixed: true,
  ce_marking_affixed_electronically: true,
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
    auth_rep_required: d.auth_rep_required,
    auth_rep_name: d.auth_rep_name || undefined,
    auth_rep_address: d.auth_rep_address || undefined,
    processes_personal_data:
      d.processes_personal_data === null ? undefined : d.processes_personal_data,
    dpo_contact: d.dpo_contact || undefined,
    harmonised_standards: splitLines(d.harmonised_standards),
    common_specifications: splitLines(d.common_specifications),
    standards_notes: d.standards_notes || undefined,
    notified_body_required: d.notified_body_required,
    notified_body_name: d.notified_body_name || undefined,
    notified_body_id: d.notified_body_id || undefined,
    assessment_procedure: d.assessment_procedure || undefined,
    certificate_reference: d.certificate_reference || undefined,
    signature_place: d.signature_place || undefined,
    signature_date: d.signature_date || undefined,
    signatory_name: d.signatory_name || undefined,
    signatory_function: d.signatory_function || undefined,
    signed_on_behalf_of: d.provider_name || undefined,
    language: d.language || undefined,
    translations_available: splitLines(d.translations_available),
    ce_marking_affixed: d.ce_marking_affixed,
    ce_marking_affixed_electronically: d.ce_marking_affixed_electronically,
  };
  if (mode === "manual") {
    base.manual_agent = manualAgentPayload(manual);
  } else {
    base.agent_id = d.agent_id;
  }
  return base;
}

export function DeclarationPage() {
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
  const [preview, setPreview] = useState<DeclarationDoc | null>(null);
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
      signature_place: prev.signature_place || (profile.address.split(",").pop() || "").trim(),
      signatory_name: prev.signatory_name || profile.accountability_owner,
      signatory_function:
        prev.signatory_function || (profile.accountability_owner ? "Accountable person" : ""),
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
    : mode === "manual"
    ? manual.risk_class
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
        const res = await fetch("/v1/declaration/template", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
          body: JSON.stringify(buildPayload(draft, mode, manual)),
        });
        if (!res.ok) throw new Error("Declaration generation failed");
        setPreview(await res.json());
      } else if (mode === "agent" && draft.agent_id) {
        const res = await fetch(
          `/v1/declaration/template/public/${encodeURIComponent(draft.agent_id)}`,
        );
        if (!res.ok) throw new Error("Preview failed");
        setPreview(await res.json());
      } else {
        setError("Log in to generate a declaration for an externally-described system.");
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
      `declaration-${draft.agent_id || "draft"}.json`,
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
      const res = await fetch("/v1/declaration/template/markdown", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
        body: JSON.stringify(buildPayload(draft, mode, manual)),
      });
      if (!res.ok) throw new Error("Markdown export failed");
      downloadBlob(`declaration-${draft.agent_id}.md`, await res.text(), "text/markdown");
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
      const res = await fetch("/v1/declaration/template/pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
        body: JSON.stringify(buildPayload(draft, mode, manual)),
      });
      if (!res.ok) throw new Error("PDF export failed");
      downloadBlob(`declaration-${draft.agent_id}.pdf`, await res.blob());
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
        ? `Declaration · ${draft.provider_name} · ${draft.agent_id}`
        : `Declaration · ${draft.agent_id}`;
      const doc = await createComplianceDocument(apiKey, {
        doc_type: "declaration_of_conformity",
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
            EU AI Act Art. 47 · Annex V · Art. 48 CE
          </p>
          <h1 className="text-3xl sm:text-4xl font-semibold text-[#f1f5f9] mb-4 leading-[1.15] tracking-tight">
            Declaration of<br />
            <span className="text-[#00d4ff]">conformity.</span>
          </h1>
          <p className="text-[15px] text-[#94a3b8] leading-relaxed max-w-lg mx-auto">
            The 9 Annex V data points plus CE-marking evidence, pre-filled from
            the capability card and your organisation profile. Sign, retain for
            10 years, hand to the competent authority on request.
          </p>
        </div>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4">
          <Card title="System (§ 1)" icon={<FileSignature size={14} className="text-[#00d4ff]" />}>
            <AgentOrManualSelector
              agents={agents}
              agentId={draft.agent_id}
              mode={mode}
              manual={manual}
              onAgentIdChange={(id) => setField("agent_id", id)}
              onModeChange={setMode}
              onManualChange={setManual}
            />
          </Card>

          <Card title="Provider (§ 2)">
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
            <label className="flex items-center gap-2 text-xs text-[#94a3b8]">
              <input
                type="checkbox"
                checked={draft.auth_rep_required}
                onChange={(e) => setField("auth_rep_required", e.target.checked)}
              />
              Non-EU provider; authorised representative required under Art. 22
            </label>
            {draft.auth_rep_required && (
              <>
                <Field label="Representative name">
                  <input
                    value={draft.auth_rep_name}
                    onChange={(e) => setField("auth_rep_name", e.target.value)}
                    placeholder="EU-established legal entity"
                    className={inputClass}
                  />
                </Field>
                <Field label="Representative address">
                  <input
                    value={draft.auth_rep_address}
                    onChange={(e) => setField("auth_rep_address", e.target.value)}
                    placeholder="Street, ZIP, City, Country"
                    className={inputClass}
                  />
                </Field>
              </>
            )}
          </Card>

          <Card title="Data protection (§ 5)">
            <Field label="Processes personal data (Art. 3 GDPR)">
              <select
                value={
                  draft.processes_personal_data === null
                    ? "auto"
                    : draft.processes_personal_data
                    ? "yes"
                    : "no"
                }
                onChange={(e) => {
                  const v = e.target.value;
                  setField(
                    "processes_personal_data",
                    v === "auto" ? null : v === "yes",
                  );
                }}
                className={inputClass}
              >
                <option value="auto">Auto-detect from agent domain</option>
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </select>
            </Field>
            {draft.processes_personal_data !== false && (
              <Field label="DPO contact (required where Art. 37 GDPR applies)">
                <input
                  value={draft.dpo_contact}
                  onChange={(e) => setField("dpo_contact", e.target.value)}
                  placeholder="Name, email of Data Protection Officer"
                  className={inputClass}
                />
              </Field>
            )}
          </Card>

          <Card title="Standards (§ 6)">
            <Field label="Harmonised standards applied (one per line)">
              <textarea
                rows={3}
                value={draft.harmonised_standards}
                onChange={(e) => setField("harmonised_standards", e.target.value)}
                placeholder={"Leave empty for platform defaults (ISO/IEC 42001, 23894, 5259)"}
                className={inputClass}
              />
            </Field>
            <Field label="Common specifications (one per line)">
              <textarea
                rows={2}
                value={draft.common_specifications}
                onChange={(e) => setField("common_specifications", e.target.value)}
                placeholder="Optional Art. 41 common specifications"
                className={inputClass}
              />
            </Field>
            <Field label="Notes">
              <input
                value={draft.standards_notes}
                onChange={(e) => setField("standards_notes", e.target.value)}
                placeholder="Context about standard selection"
                className={inputClass}
              />
            </Field>
          </Card>

          {isHighRisk && (
            <Card title="Notified body (§ 7)" icon={<ShieldCheck size={14} className="text-amber-300" />}>
              <p className="text-xs text-[#94a3b8] mb-2">
                Only mandatory for biometric Annex III systems (Art. 43). Most
                high-risk systems follow Annex VI internal control. Enable only
                if a notified body was actually involved.
              </p>
              <label className="flex items-center gap-2 text-xs text-[#94a3b8]">
                <input
                  type="checkbox"
                  checked={draft.notified_body_required}
                  onChange={(e) => setField("notified_body_required", e.target.checked)}
                />
                Notified body assessment performed
              </label>
              {draft.notified_body_required && (
                <>
                  <Field label="Notified body name">
                    <input
                      value={draft.notified_body_name}
                      onChange={(e) => setField("notified_body_name", e.target.value)}
                      placeholder="e.g. TÜV Nord"
                      className={inputClass}
                    />
                  </Field>
                  <Field label="Identification number (4-digit)">
                    <input
                      value={draft.notified_body_id}
                      onChange={(e) => setField("notified_body_id", e.target.value)}
                      placeholder="e.g. 0044"
                      className={inputClass}
                    />
                  </Field>
                  <Field label="Assessment procedure">
                    <input
                      value={draft.assessment_procedure}
                      onChange={(e) => setField("assessment_procedure", e.target.value)}
                      placeholder="Annex VII (QMS + tech doc assessment)"
                      className={inputClass}
                    />
                  </Field>
                  <Field label="Certificate reference">
                    <input
                      value={draft.certificate_reference}
                      onChange={(e) => setField("certificate_reference", e.target.value)}
                      placeholder="Certificate number and issue date"
                      className={inputClass}
                    />
                  </Field>
                </>
              )}
            </Card>
          )}

          <Card title="Signature (§ 8)">
            <Field label="Place of issue">
              <input
                value={draft.signature_place}
                onChange={(e) => setField("signature_place", e.target.value)}
                placeholder="e.g. Berlin"
                className={inputClass}
              />
            </Field>
            <Field label="Date (YYYY-MM-DD)">
              <input
                type="date"
                value={draft.signature_date}
                onChange={(e) => setField("signature_date", e.target.value)}
                className={inputClass}
              />
            </Field>
            <Field label="Signatory name">
              <input
                value={draft.signatory_name}
                onChange={(e) => setField("signatory_name", e.target.value)}
                placeholder="Full name of signing person"
                className={inputClass}
              />
            </Field>
            <Field label="Signatory function">
              <input
                value={draft.signatory_function}
                onChange={(e) => setField("signatory_function", e.target.value)}
                placeholder="e.g. Managing Director, Head of Compliance"
                className={inputClass}
              />
            </Field>
          </Card>

          <Card title="Language (§ 9)">
            <Field label="Drawn up in">
              <select
                value={draft.language}
                onChange={(e) => setField("language", e.target.value)}
                className={inputClass}
              >
                <option value="en">English</option>
                <option value="de">Deutsch</option>
                <option value="fr">Français</option>
                <option value="es">Español</option>
                <option value="it">Italiano</option>
                <option value="nl">Nederlands</option>
              </select>
            </Field>
            <Field label="Translations available (one per line)">
              <textarea
                rows={2}
                value={draft.translations_available}
                onChange={(e) => setField("translations_available", e.target.value)}
                placeholder={"de\nfr"}
                className={inputClass}
              />
            </Field>
          </Card>

          <Card title="CE marking (Art. 48)">
            <label className="flex items-center gap-2 text-xs text-[#94a3b8]">
              <input
                type="checkbox"
                checked={draft.ce_marking_affixed}
                onChange={(e) => setField("ce_marking_affixed", e.target.checked)}
              />
              CE marking affixed to the system
            </label>
            <label className="flex items-center gap-2 text-xs text-[#94a3b8]">
              <input
                type="checkbox"
                checked={draft.ce_marking_affixed_electronically}
                onChange={(e) => setField("ce_marking_affixed_electronically", e.target.checked)}
              />
              Affixed electronically per Art. 48(4) (digital-only system)
            </label>
          </Card>
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
                <Row k="Domain" v={selectedAgent.card?.capabilities?.domain || "-"} />
                <Row k="Model" v={selectedAgent.card?.runtime?.model || "-"} />
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
              Generate declaration
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
                : "Generate a declaration to see the pre-filled draft here."}
            </pre>
          </div>

          <p className="text-xs text-[#64748b] leading-relaxed">
            Retain this declaration at the disposal of national competent
            authorities for 10 years per Art. 47(1). Electronic signatures
            qualify where recognised under eIDAS.
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
    <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5 space-y-3">
      <h3 className="flex items-center gap-2 text-xs font-medium text-[#64748b] uppercase tracking-widest">
        {icon}
        {title}
      </h3>
      {children}
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-[#64748b]">{k}</dt>
      <dd className="text-[#e2e8f0] text-right">{v}</dd>
    </div>
  );
}
