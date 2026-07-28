import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  AlertCircle,
  Building2,
  CheckCircle,
  Download,
  FileCheck,
  Loader2,
  Save,
  Sparkles,
} from "lucide-react";
import { listAgents, type Agent } from "../api";
import { createComplianceDocument } from "../compliance-api";
import { loadOrgProfile } from "../org-profile";

type QMSDocument = Record<string, unknown>;

const DRAFT_KEY = "af_qms_draft_v1";

interface DraftState {
  variant: "full" | "simplified";
  agent_id: string;
  organisation_name: string;
  organisation_contact: string;
  sme_category: string;
  regulatory_policy: string;
  substantial_modification_definition: string;
  development_methodology: string;
  quality_control: string;
  deployer_data_policy: string;
  risk_owner: string;
  risk_review_cadence: string;
  authority_contact: string;
  accountability_owner: string;
  management_review: string;
  internal_audit_schedule: string;
  infrastructure_security_of_supply: string;
}

const EMPTY: DraftState = {
  variant: "full",
  agent_id: "",
  organisation_name: "",
  organisation_contact: "",
  sme_category: "",
  regulatory_policy: "",
  substantial_modification_definition: "",
  development_methodology: "",
  quality_control: "",
  deployer_data_policy: "",
  risk_owner: "",
  risk_review_cadence: "",
  authority_contact: "",
  accountability_owner: "",
  management_review: "",
  internal_audit_schedule: "",
  infrastructure_security_of_supply: "",
};

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

function buildPayload(d: DraftState): Record<string, unknown> {
  const pick = (keys: (keyof DraftState)[]) => {
    const out: Record<string, unknown> = {};
    for (const k of keys) {
      if (d[k]) out[k] = d[k];
    }
    return out;
  };
  return {
    variant: d.variant,
    agent_id: d.agent_id || undefined,
    ...pick([
      "organisation_name",
      "organisation_contact",
      "sme_category",
      "regulatory_policy",
      "substantial_modification_definition",
      "development_methodology",
      "quality_control",
      "deployer_data_policy",
      "risk_owner",
      "risk_review_cadence",
      "authority_contact",
      "accountability_owner",
      "management_review",
      "internal_audit_schedule",
      "infrastructure_security_of_supply",
    ]),
  };
}

export function QMSPage() {
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
  const [preview, setPreview] = useState<QMSDocument | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedId, setSavedId] = useState<string | null>(null);

  useEffect(() => {
    localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
  }, [draft]);

  useEffect(() => {
    listAgents().then((d) => setAgents(d.agents)).catch(() => setAgents([]));
  }, []);

  useEffect(() => {
    const profile = loadOrgProfile();
    if (!profile.organisation) return;
    const sizeMap = {
      microenterprise: "microenterprise",
      sme: "SME",
      large: "large",
      public_body: "public body",
      "": "",
    } as const;
    setDraft((prev) => ({
      ...prev,
      organisation_name: prev.organisation_name || profile.organisation,
      organisation_contact: prev.organisation_contact || profile.contact,
      sme_category: prev.sme_category || sizeMap[profile.size_category],
      accountability_owner: prev.accountability_owner || profile.accountability_owner,
      authority_contact: prev.authority_contact || profile.authority_contact,
      variant:
        profile.size_category === "microenterprise" ? "simplified" : prev.variant,
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

  const setField = <K extends keyof DraftState>(key: K, value: DraftState[K]) => {
    setDraft((prev) => ({ ...prev, [key]: value }));
    if (key === "agent_id" && typeof value === "string") {
      const next = new URLSearchParams(searchParams);
      if (value) next.set("agent_id", value); else next.delete("agent_id");
      setSearchParams(next, { replace: true });
    }
  };

  const handleGenerate = async () => {
    setBusy(true);
    setError(null);
    try {
      if (apiKey) {
        const res = await fetch("/v1/qms/template", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
          body: JSON.stringify(buildPayload(draft)),
        });
        if (!res.ok) throw new Error("Template generation failed");
        setPreview(await res.json());
      } else {
        const res = await fetch(`/v1/qms/template/public?variant=${draft.variant}`);
        if (!res.ok) throw new Error("Preview failed");
        setPreview(await res.json());
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setBusy(false);
    }
  };

  const handleDownloadJSON = () => {
    if (!preview) return;
    const suffix = draft.agent_id ? `-${draft.agent_id}` : "";
    downloadBlob(
      `qms-${draft.variant}${suffix}.json`,
      JSON.stringify(preview, null, 2),
      "application/json",
    );
  };

  const handleDownloadMarkdown = async () => {
    if (!apiKey) {
      setError("Log in to export Markdown. JSON works anonymously.");
      return;
    }
    try {
      const res = await fetch("/v1/qms/template/markdown", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
        body: JSON.stringify(buildPayload(draft)),
      });
      if (!res.ok) throw new Error("Markdown export failed");
      const md = await res.text();
      const suffix = draft.agent_id ? `-${draft.agent_id}` : "";
      downloadBlob(`qms-${draft.variant}${suffix}.md`, md, "text/markdown");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Markdown export failed");
    }
  };

  const handleDownloadPDF = async () => {
    if (!apiKey) {
      setError("Log in to export PDF. JSON works anonymously.");
      return;
    }
    setBusy(true);
    try {
      const res = await fetch("/v1/qms/template/pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
        body: JSON.stringify(buildPayload(draft)),
      });
      if (!res.ok) throw new Error("PDF export failed");
      const suffix = draft.agent_id ? `-${draft.agent_id}` : "";
      downloadBlob(`qms-${draft.variant}${suffix}.pdf`, await res.blob());
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
      const title = draft.organisation_name
        ? `QMS · ${draft.organisation_name} (${draft.variant})`
        : `QMS (${draft.variant})`;
      const doc = await createComplianceDocument(apiKey, {
        doc_type: "qms_manual",
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
            EU AI Act Art. 17 · ISO/IEC 42001 baseline
          </p>
          <h1 className="text-3xl sm:text-4xl font-semibold text-[#f1f5f9] mb-4 leading-[1.15] tracking-tight">
            Quality Management<br />
            <span className="text-[#00d4ff]">System manual.</span>
          </h1>
          <p className="text-[15px] text-[#94a3b8] leading-relaxed max-w-lg mx-auto">
            All thirteen Art. 17 elements, with platform-native controls pre-filled
            and the simplified variant for microenterprises (Art. 63). Scoped to the
            provider organisation; optionally extended with a system-specific addendum.
          </p>
        </div>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4">
          <Card title="Organisation" icon={<Building2 size={14} className="text-[#00d4ff]" />}>
            <Field label="Variant">
              <select
                value={draft.variant}
                onChange={(e) => setField("variant", e.target.value as "full" | "simplified")}
                className={inputClass}
              >
                <option value="full">Full QMS (Art. 17)</option>
                <option value="simplified">Simplified (Art. 63, microenterprise)</option>
              </select>
            </Field>
            <Field label="Legal name">
              <input
                value={draft.organisation_name}
                onChange={(e) => setField("organisation_name", e.target.value)}
                placeholder="Company name and address"
                className={inputClass}
              />
            </Field>
            <Field label="Accountable contact">
              <input
                value={draft.organisation_contact}
                onChange={(e) => setField("organisation_contact", e.target.value)}
                placeholder="Name, role, email"
                className={inputClass}
              />
            </Field>
            <Field label="Size category">
              <input
                value={draft.sme_category}
                onChange={(e) => setField("sme_category", e.target.value)}
                placeholder="microenterprise / SME / large"
                className={inputClass}
              />
            </Field>
            <Field label="System-specific addendum (optional)">
              <select
                value={draft.agent_id}
                onChange={(e) => setField("agent_id", e.target.value)}
                className={inputClass}
              >
                <option value="">No addendum (org-wide QMS)</option>
                {agents.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name} ({a.id})
                  </option>
                ))}
              </select>
            </Field>
          </Card>

          <Card title="Regulatory strategy (A)">
            <Field label="Regulatory policy">
              <textarea
                rows={3}
                value={draft.regulatory_policy}
                onChange={(e) => setField("regulatory_policy", e.target.value)}
                placeholder="Classification, conformity assessment approach, substantial modification policy. Leave empty for platform default."
                className={inputClass}
              />
            </Field>
            <Field label="Substantial modification definition">
              <textarea
                rows={2}
                value={draft.substantial_modification_definition}
                onChange={(e) => setField("substantial_modification_definition", e.target.value)}
                className={inputClass}
              />
            </Field>
          </Card>

          <Card title="Development and quality control (C)">
            <Field label="Development methodology">
              <textarea
                rows={3}
                value={draft.development_methodology}
                onChange={(e) => setField("development_methodology", e.target.value)}
                placeholder="SDLC, review gates, coverage targets"
                className={inputClass}
              />
            </Field>
            <Field label="Quality control">
              <textarea
                rows={3}
                value={draft.quality_control}
                onChange={(e) => setField("quality_control", e.target.value)}
                placeholder="Code review, tests, human evaluation cadence"
                className={inputClass}
              />
            </Field>
          </Card>

          <Card title="Data management (F)">
            <Field label="Deployer data policy">
              <textarea
                rows={3}
                value={draft.deployer_data_policy}
                onChange={(e) => setField("deployer_data_policy", e.target.value)}
                placeholder="Data classification, minimisation, retention across the lifecycle"
                className={inputClass}
              />
            </Field>
          </Card>

          <Card title="Risk management (G)">
            <Field label="Risk owner">
              <input
                value={draft.risk_owner}
                onChange={(e) => setField("risk_owner", e.target.value)}
                placeholder="Role accountable for the Art. 9 RMS"
                className={inputClass}
              />
            </Field>
            <Field label="Review cadence">
              <input
                value={draft.risk_review_cadence}
                onChange={(e) => setField("risk_review_cadence", e.target.value)}
                placeholder="e.g., quarterly"
                className={inputClass}
              />
            </Field>
          </Card>

          <Card title="Authority liaison (J)">
            <Field label="Authority contact">
              <input
                value={draft.authority_contact}
                onChange={(e) => setField("authority_contact", e.target.value)}
                placeholder="Named liaison for MSA communication"
                className={inputClass}
              />
            </Field>
          </Card>

          <Card title="Resources (L)">
            <Field label="Infrastructure security of supply">
              <textarea
                rows={2}
                value={draft.infrastructure_security_of_supply}
                onChange={(e) => setField("infrastructure_security_of_supply", e.target.value)}
                placeholder="Primary + failover regions, backup LLM providers"
                className={inputClass}
              />
            </Field>
          </Card>

          <Card title="Accountability (M)">
            <Field label="Accountability owner">
              <input
                value={draft.accountability_owner}
                onChange={(e) => setField("accountability_owner", e.target.value)}
                placeholder="Named person / role accountable for the QMS"
                className={inputClass}
              />
            </Field>
            <Field label="Management review">
              <input
                value={draft.management_review}
                onChange={(e) => setField("management_review", e.target.value)}
                placeholder="Cadence and attendees"
                className={inputClass}
              />
            </Field>
            {draft.variant === "full" && (
              <Field label="Internal audit schedule">
                <input
                  value={draft.internal_audit_schedule}
                  onChange={(e) => setField("internal_audit_schedule", e.target.value)}
                  placeholder="e.g., annual against ISO/IEC 42001"
                  className={inputClass}
                />
              </Field>
            )}
          </Card>
        </div>

        <div className="space-y-4 lg:sticky lg:top-20 lg:self-start">
          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
            <h3 className="text-xs font-medium text-[#64748b] uppercase tracking-widest mb-3">
              Platform-native controls
            </h3>
            <ul className="space-y-1.5 text-xs text-[#94a3b8]">
              <li>• Immutable event log (Art. 12)</li>
              <li>• Three-path secret isolation</li>
              <li>• Ephemeral compute per task</li>
              <li>• Risk-class tagging + approval gates (Art. 14)</li>
              <li>• PMM plan template + incident pipeline (Art. 72-73)</li>
              <li>• 180-day log retention, 10-year docs</li>
              <li>• Ed25519-signed capability cards</li>
            </ul>
            <p className="text-[10px] text-[#64748b] mt-3">
              These controls are pre-filled in sections F/G/H/I/J/K of the manual.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              onClick={handleGenerate}
              disabled={busy}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed"
              style={{ transition: "background 0.2s cubic-bezier(0.16, 1, 0.3, 1)" }}
            >
              {busy ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
              Generate QMS manual
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
              disabled={busy}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-white/[0.08] text-sm text-[#94a3b8] hover:text-[#f1f5f9] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <FileCheck size={14} />
              Download Markdown
            </button>
            <button
              onClick={handleDownloadPDF}
              disabled={busy}
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
                : "Generate a manual to see the pre-filled document here."}
            </pre>
          </div>

          <p className="text-xs text-[#64748b] leading-relaxed">
            The manual is scoped to the provider organisation. Retain for 10 years
            (Art. 18). Microenterprises satisfying Art. 63 should select the simplified
            variant; the document includes the exemption banner.
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
    <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5 space-y-4">
      <h2 className="text-sm font-medium text-[#f1f5f9] flex items-center gap-2">
        {icon}
        {title}
      </h2>
      {children}
    </div>
  );
}
