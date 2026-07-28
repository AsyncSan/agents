import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  AlertCircle,
  CheckCircle,
  Download,
  FileCheck,
  Layers,
  Loader2,
  Save,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { listAgents, type Agent } from "../api";
import {
  createComplianceDocument,
  getComplianceDocument,
  listComplianceDocuments,
  type ComplianceDocument,
} from "../compliance-api";
import { useT } from "../i18n";
import {
  AgentOrManualSelector,
  EMPTY_MANUAL,
  manualAgentPayload,
  type ManualAgentState,
} from "../components/AgentOrManualSelector";
import { loadOrgProfile } from "../org-profile";

type AnnexIVDocument = Record<string, unknown>;

const DRAFT_KEY = "af_annex_iv_draft_v1";

interface DraftState {
  agent_id: string;
  variant: "full" | "simplified";
  provider_name: string;
  provider_contact: string;
  development_methodology: string;
  third_party_components: string;
  training_data_summary: string;
  validation_and_testing: string;
  known_limitations: string;
  foreseeable_unintended_outcomes: string;
  metric_rationale: string;
  robustness_testing: string;
  cybersecurity_testing: string;
  rms_owner: string;
  identified_risks: string;
  mitigation_measures: string;
  review_cadence: string;
  substantial_modification_definition: string;
  harmonised_standards_applied: string;
  other_adopted_solutions: string;
  declaration_of_conformity_reference: string;
  eu_database_registration: string;
  monitoring_plan_summary: string;
  incident_reporting_process: string;
  feedback_channels: string;
  third_country_variants: string;
}

const EMPTY_DRAFT: DraftState = {
  agent_id: "",
  variant: "full",
  provider_name: "",
  provider_contact: "",
  development_methodology: "",
  third_party_components: "",
  training_data_summary: "",
  validation_and_testing: "",
  known_limitations: "",
  foreseeable_unintended_outcomes: "",
  metric_rationale: "",
  robustness_testing: "",
  cybersecurity_testing: "",
  rms_owner: "",
  identified_risks: "",
  mitigation_measures: "",
  review_cadence: "",
  substantial_modification_definition: "",
  harmonised_standards_applied: "",
  other_adopted_solutions: "",
  declaration_of_conformity_reference: "",
  eu_database_registration: "",
  monitoring_plan_summary: "",
  incident_reporting_process: "",
  feedback_channels: "",
  third_country_variants: "",
};

function splitLines(value: string): string[] | undefined {
  const lines = value.split("\n").map((l) => l.trim()).filter(Boolean);
  return lines.length > 0 ? lines : undefined;
}

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

function buildPayload(
  d: DraftState,
  mode: "agent" | "manual",
  manual: ManualAgentState,
): Record<string, unknown> {
  const base: Record<string, unknown> = {
    variant: d.variant,
    provider_name: d.provider_name || undefined,
    provider_contact: d.provider_contact || undefined,
    development_methodology: d.development_methodology || undefined,
    third_party_components: splitLines(d.third_party_components),
    training_data_summary: d.training_data_summary || undefined,
    validation_and_testing: d.validation_and_testing || undefined,
    known_limitations: splitLines(d.known_limitations),
    foreseeable_unintended_outcomes: splitLines(d.foreseeable_unintended_outcomes),
    metric_rationale: d.metric_rationale || undefined,
    robustness_testing: d.robustness_testing || undefined,
    cybersecurity_testing: splitLines(d.cybersecurity_testing),
    rms_owner: d.rms_owner || undefined,
    identified_risks: splitLines(d.identified_risks),
    mitigation_measures: splitLines(d.mitigation_measures),
    review_cadence: d.review_cadence || undefined,
    substantial_modification_definition: d.substantial_modification_definition || undefined,
    harmonised_standards_applied: splitLines(d.harmonised_standards_applied),
    other_adopted_solutions: splitLines(d.other_adopted_solutions),
    declaration_of_conformity_reference: d.declaration_of_conformity_reference || undefined,
    eu_database_registration: d.eu_database_registration || undefined,
    monitoring_plan_summary: d.monitoring_plan_summary || undefined,
    incident_reporting_process: d.incident_reporting_process || undefined,
    feedback_channels: splitLines(d.feedback_channels),
    third_country_variants: d.third_country_variants || undefined,
  };
  if (mode === "manual") {
    base.manual_agent = manualAgentPayload(manual);
  } else {
    base.agent_id = d.agent_id;
  }
  return base;
}

export function AnnexIVPage() {
  const { t } = useT();
  const [searchParams, setSearchParams] = useSearchParams();
  const apiKey = typeof window !== "undefined" ? localStorage.getItem("af_api_key") : null;

  const [agents, setAgents] = useState<Agent[]>([]);
  const [draft, setDraft] = useState<DraftState>(() => {
    if (typeof window === "undefined") return EMPTY_DRAFT;
    const raw = localStorage.getItem(DRAFT_KEY);
    if (!raw) return EMPTY_DRAFT;
    try {
      return { ...EMPTY_DRAFT, ...JSON.parse(raw) };
    } catch {
      return EMPTY_DRAFT;
    }
  });
  const [preview, setPreview] = useState<AnnexIVDocument | null>(null);
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
      provider_name: prev.provider_name || profile.organisation,
      provider_contact: prev.provider_contact || profile.contact,
      rms_owner: prev.rms_owner || profile.accountability_owner,
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
    listComplianceDocuments(apiKey, { doc_type: "annex_iv", agent_id: draft.agent_id })
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
        const res = await fetch("/v1/annex-iv/template", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
          body: JSON.stringify(buildPayload(draft, mode, manual)),
        });
        if (!res.ok) throw new Error("Template generation failed");
        setPreview(await res.json());
      } else if (mode === "agent" && draft.agent_id) {
        const res = await fetch(
          `/v1/annex-iv/template/public/${encodeURIComponent(draft.agent_id)}?variant=${draft.variant}`,
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
      `annex-iv-${draft.agent_id || "draft"}-${draft.variant}.json`,
      JSON.stringify(preview, null, 2),
      "application/json",
    );
  };

  const handleDownloadMarkdown = async () => {
    if (!draft.agent_id) return;
    if (!apiKey) {
      setError("Log in to export Markdown. The JSON download works anonymously.");
      return;
    }
    try {
      const res = await fetch("/v1/annex-iv/template/markdown", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
        body: JSON.stringify(buildPayload(draft, mode, manual)),
      });
      if (!res.ok) throw new Error("Markdown export failed");
      const md = await res.text();
      downloadBlob(`annex-iv-${draft.agent_id}-${draft.variant}.md`, md, "text/markdown");
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
      const res = await fetch("/v1/annex-iv/template/pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
        body: JSON.stringify(buildPayload(draft, mode, manual)),
      });
      if (!res.ok) throw new Error("PDF export failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `annex-iv-${draft.agent_id}-${draft.variant}.pdf`;
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
      setPreview(doc.payload as AnnexIVDocument);
      const payload = doc.payload as Record<string, unknown>;
      const stripIfPlaceholder = (v: unknown, fallback: string): string => {
        if (typeof v !== "string") return fallback;
        if (v.includes("[PROVIDER")) return fallback;
        return v;
      };
      const joinLines = (v: unknown): string => {
        if (!Array.isArray(v)) return "";
        return (v as string[]).filter((x) => !x.includes("[PROVIDER")).join("\n");
      };
      const s1 = (payload.section_1_general_description || {}) as Record<string, unknown>;
      const s2 = (payload.section_2_detailed_description || {}) as Record<string, unknown>;
      const s3 = (payload.section_3_monitoring_information || {}) as Record<string, unknown>;
      const s4 = (payload.section_4_performance_metrics || {}) as Record<string, unknown>;
      const s5 = (payload.section_5_risk_management_system || {}) as Record<string, unknown>;
      const s6 = (payload.section_6_changes || {}) as Record<string, unknown>;
      const s7 = (payload.section_7_applied_standards || {}) as Record<string, unknown>;
      const s8 = (payload.section_8_declaration_of_conformity || {}) as Record<string, unknown>;
      const s9 = (payload.section_9_post_market_monitoring || {}) as Record<string, unknown>;
      setDraft((prev) => ({
        ...prev,
        variant: ((payload.variant as "full" | "simplified") || prev.variant),
        provider_name: stripIfPlaceholder(s1.provider_name, prev.provider_name),
        provider_contact: stripIfPlaceholder(s1.provider_contact, prev.provider_contact),
        development_methodology: stripIfPlaceholder(
          s2.development_methodology,
          prev.development_methodology,
        ),
        third_party_components: joinLines(s2.third_party_components) || prev.third_party_components,
        training_data_summary: stripIfPlaceholder(
          (s2.data_requirements as Record<string, unknown>)?.training_data_summary,
          prev.training_data_summary,
        ),
        validation_and_testing: stripIfPlaceholder(
          s2.validation_and_testing,
          prev.validation_and_testing,
        ),
        known_limitations: joinLines(s3.known_limitations) || prev.known_limitations,
        foreseeable_unintended_outcomes:
          joinLines(s3.foreseeable_unintended_outcomes) || prev.foreseeable_unintended_outcomes,
        metric_rationale: stripIfPlaceholder(s4.metric_rationale, prev.metric_rationale),
        robustness_testing: stripIfPlaceholder(s4.robustness_testing, prev.robustness_testing),
        cybersecurity_testing: joinLines(s4.cybersecurity_testing) || prev.cybersecurity_testing,
        rms_owner: stripIfPlaceholder(s5.rms_owner, prev.rms_owner),
        identified_risks: joinLines(s5.identified_risks) || prev.identified_risks,
        mitigation_measures: joinLines(s5.mitigation_measures) || prev.mitigation_measures,
        review_cadence: stripIfPlaceholder(s5.review_cadence, prev.review_cadence),
        substantial_modification_definition: stripIfPlaceholder(
          s6.substantial_modification_definition,
          prev.substantial_modification_definition,
        ),
        harmonised_standards_applied:
          joinLines(s7.harmonised_standards_applied) || prev.harmonised_standards_applied,
        other_adopted_solutions:
          joinLines(s7.other_adopted_solutions) || prev.other_adopted_solutions,
        declaration_of_conformity_reference: stripIfPlaceholder(
          s8.declaration_of_conformity_reference,
          prev.declaration_of_conformity_reference,
        ),
        eu_database_registration: stripIfPlaceholder(
          s8.eu_database_registration,
          prev.eu_database_registration,
        ),
        monitoring_plan_summary: stripIfPlaceholder(
          s9.monitoring_plan_summary,
          prev.monitoring_plan_summary,
        ),
        incident_reporting_process: stripIfPlaceholder(
          s9.incident_reporting_process,
          prev.incident_reporting_process,
        ),
        feedback_channels: joinLines(s9.feedback_channels) || prev.feedback_channels,
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
      const title = draft.provider_name
        ? `Annex IV · ${draft.provider_name} · ${draft.agent_id} (${draft.variant})`
        : `Annex IV · ${draft.agent_id} (${draft.variant})`;
      const doc = await createComplianceDocument(apiKey, {
        doc_type: "annex_iv",
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
            {t("annex.eyebrow")}
          </p>
          <h1 className="text-3xl sm:text-4xl font-semibold text-[#f1f5f9] mb-4 leading-[1.15] tracking-tight">
            {t("annex.title1")}<br />
            <span className="text-[#00d4ff]">{t("annex.title2")}</span>
          </h1>
          <p className="text-[15px] text-[#94a3b8] leading-relaxed max-w-lg mx-auto">
            {t("annex.sub")}
          </p>
        </div>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Form */}
        <div className="space-y-4">
          <Card title="Context" icon={<Layers size={14} className="text-[#00d4ff]" />}>
            <AgentOrManualSelector
              agents={agents}
              agentId={draft.agent_id}
              mode={mode}
              manual={manual}
              onAgentIdChange={(id) => setField("agent_id", id)}
              onModeChange={setMode}
              onManualChange={setManual}
            />
            <Field label="Documentation variant">
              <select
                value={draft.variant}
                onChange={(e) => setField("variant", e.target.value as "full" | "simplified")}
                className={inputClass}
              >
                <option value="full">Full (default)</option>
                <option value="simplified">Simplified (SME, Art. 11(1) sub. 3)</option>
              </select>
            </Field>
            <Field label="Provider (legal name and address)">
              <input
                value={draft.provider_name}
                onChange={(e) => setField("provider_name", e.target.value)}
                className={inputClass}
              />
            </Field>
            <Field label="Accountable contact">
              <input
                value={draft.provider_contact}
                onChange={(e) => setField("provider_contact", e.target.value)}
                placeholder="Name, role, email"
                className={inputClass}
              />
            </Field>
          </Card>

          <Card title="2. Detailed description">
            <Field label="Development methodology">
              <textarea
                rows={3}
                value={draft.development_methodology}
                onChange={(e) => setField("development_methodology", e.target.value)}
                className={inputClass}
              />
            </Field>
            <Field label="Third-party components (one per line)">
              <textarea
                rows={3}
                value={draft.third_party_components}
                onChange={(e) => setField("third_party_components", e.target.value)}
                className={inputClass}
              />
            </Field>
            <Field label="Training data summary">
              <textarea
                rows={3}
                value={draft.training_data_summary}
                onChange={(e) => setField("training_data_summary", e.target.value)}
                placeholder="Source, licensing, curation, bias analysis. Write 'not applicable' if no fine-tuning."
                className={inputClass}
              />
            </Field>
            <Field label="Validation and testing procedure">
              <textarea
                rows={3}
                value={draft.validation_and_testing}
                onChange={(e) => setField("validation_and_testing", e.target.value)}
                className={inputClass}
              />
            </Field>
          </Card>

          <Card title="3. Monitoring information">
            <Field label="Known limitations (one per line)">
              <textarea
                rows={3}
                value={draft.known_limitations}
                onChange={(e) => setField("known_limitations", e.target.value)}
                className={inputClass}
              />
            </Field>
            <Field label="Foreseeable unintended outcomes (one per line)">
              <textarea
                rows={3}
                value={draft.foreseeable_unintended_outcomes}
                onChange={(e) => setField("foreseeable_unintended_outcomes", e.target.value)}
                className={inputClass}
              />
            </Field>
          </Card>

          <Card title="4. Performance metrics">
            <Field label="Why the chosen metrics are appropriate">
              <textarea
                rows={3}
                value={draft.metric_rationale}
                onChange={(e) => setField("metric_rationale", e.target.value)}
                className={inputClass}
              />
            </Field>
            {draft.variant === "full" && (
              <>
                <Field label="Robustness testing">
                  <textarea
                    rows={2}
                    value={draft.robustness_testing}
                    onChange={(e) => setField("robustness_testing", e.target.value)}
                    className={inputClass}
                  />
                </Field>
                <Field label="Cybersecurity testing (one per line)">
                  <textarea
                    rows={3}
                    value={draft.cybersecurity_testing}
                    onChange={(e) => setField("cybersecurity_testing", e.target.value)}
                    className={inputClass}
                  />
                </Field>
              </>
            )}
          </Card>

          <Card title="5. Risk management system">
            <Field label="RMS owner">
              <input
                value={draft.rms_owner}
                onChange={(e) => setField("rms_owner", e.target.value)}
                placeholder="Role accountable for Art. 9 RMS"
                className={inputClass}
              />
            </Field>
            <Field label="Identified risks (one per line)">
              <textarea
                rows={3}
                value={draft.identified_risks}
                onChange={(e) => setField("identified_risks", e.target.value)}
                className={inputClass}
              />
            </Field>
            <Field label="Mitigation measures (one per line)">
              <textarea
                rows={3}
                value={draft.mitigation_measures}
                onChange={(e) => setField("mitigation_measures", e.target.value)}
                className={inputClass}
              />
            </Field>
            <Field label="Review cadence">
              <input
                value={draft.review_cadence}
                onChange={(e) => setField("review_cadence", e.target.value)}
                placeholder="e.g., quarterly"
                className={inputClass}
              />
            </Field>
          </Card>

          {draft.variant === "full" && (
            <Card title="6. Changes">
              <Field label="Substantial modification definition">
                <textarea
                  rows={2}
                  value={draft.substantial_modification_definition}
                  onChange={(e) => setField("substantial_modification_definition", e.target.value)}
                  className={inputClass}
                />
              </Field>
            </Card>
          )}

          <Card title="7. Applied standards">
            <Field label="Harmonised standards applied (one per line)">
              <textarea
                rows={2}
                value={draft.harmonised_standards_applied}
                onChange={(e) => setField("harmonised_standards_applied", e.target.value)}
                className={inputClass}
              />
            </Field>
            <Field label="Other adopted solutions (one per line)">
              <textarea
                rows={2}
                value={draft.other_adopted_solutions}
                onChange={(e) => setField("other_adopted_solutions", e.target.value)}
                className={inputClass}
              />
            </Field>
          </Card>

          <Card title="8. Declaration of conformity">
            <Field label="DoC reference (Annex V)">
              <input
                value={draft.declaration_of_conformity_reference}
                onChange={(e) => setField("declaration_of_conformity_reference", e.target.value)}
                className={inputClass}
              />
            </Field>
            <Field label="EU database registration (Art. 49)">
              <input
                value={draft.eu_database_registration}
                onChange={(e) => setField("eu_database_registration", e.target.value)}
                className={inputClass}
              />
            </Field>
          </Card>

          <Card title="9. Post-market monitoring">
            <Field label="Monitoring plan summary (Art. 72)">
              <textarea
                rows={3}
                value={draft.monitoring_plan_summary}
                onChange={(e) => setField("monitoring_plan_summary", e.target.value)}
                className={inputClass}
              />
            </Field>
            <Field label="Incident reporting process (Art. 73)">
              <textarea
                rows={2}
                value={draft.incident_reporting_process}
                onChange={(e) => setField("incident_reporting_process", e.target.value)}
                className={inputClass}
              />
            </Field>
            <Field label="Feedback channels (one per line)">
              <textarea
                rows={3}
                value={draft.feedback_channels}
                onChange={(e) => setField("feedback_channels", e.target.value)}
                className={inputClass}
              />
            </Field>
          </Card>
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
                      ? "Existing Annex IV is stale"
                      : "You have an existing Annex IV for this agent"}
                  </p>
                  <p className="text-xs text-[#94a3b8] mt-1 leading-relaxed">
                    {existingDocs.some((d) => d.is_stale)
                      ? "The agent advanced since the last review. Load the saved draft, reconcile sections 1-3, then re-approve."
                      : "Load the latest saved draft to continue editing."}
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
                <Row k="Agent" v={selectedAgent.name} />
                <Row k="Domain" v={selectedAgent.card?.capabilities?.domain || "-"} />
                <Row k="Model" v={selectedAgent.card?.runtime?.model || "-"} />
                <Row
                  k="Risk class"
                  v={(selectedAgent as unknown as { risk_class?: string }).risk_class || "minimal"}
                />
                <Row
                  k="Executions"
                  v={`${selectedAgent.total_executions ?? 0} (${selectedAgent.success_count ?? 0} success)`}
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
              Generate Annex IV draft
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
              onClick={handleSaveToWorkspace}
              disabled={!preview || !apiKey || busy}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-emerald-500/20 bg-emerald-500/5 text-emerald-300 hover:bg-emerald-500/10 text-sm disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              title={apiKey ? "Persist to the compliance workspace" : "Log in to save to workspace"}
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
                : "Generate a draft to see the pre-filled Annex IV document here."}
            </pre>
          </div>

          <p className="text-xs text-[#64748b] leading-relaxed">
            Sections marked <span className="text-[#94a3b8]">[PROVIDER: …]</span> in
            the output require completion by your team. The draft is stored in this
            browser only. Retain the final document for 10 years (Art. 18).
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
