import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  Briefcase,
  CheckCircle,
  Download,
  FileCheck,
  GraduationCap,
  Loader2,
  Scale,
  Shield,
  Sparkles,
} from "lucide-react";
import { listAgents, type Agent } from "../api";
import {
  AgentOrManualSelector,
  EMPTY_MANUAL,
  manualAgentPayload,
  type ManualAgentState,
} from "../components/AgentOrManualSelector";
import { loadOrgProfile } from "../org-profile";
import { useT } from "../i18n";

interface UseCase {
  key: string;
  description: string;
  triggers_fria: boolean;
}

const USE_CASE_ICON: Record<string, typeof Sparkles> = {
  credit_scoring: Briefcase,
  insurance_pricing: Shield,
  public_service: Scale,
  other_high_risk: GraduationCap,
};

const STEPS = ["Use-case", "System", "Review"] as const;
type Step = (typeof STEPS)[number];

const STEP_LABELS_DE: Record<Step, string> = {
  "Use-case": "Use-Case",
  System: "System",
  Review: "Prüfen",
};

function downloadBlob(filename: string, content: Blob) {
  const url = URL.createObjectURL(content);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function ComplianceSetupPage() {
  const { lang } = useT();
  const de = lang === "de";
  const navigate = useNavigate();
  const apiKey = typeof window !== "undefined" ? localStorage.getItem("af_api_key") : null;

  const [step, setStep] = useState<Step>("Use-case");
  const [useCases, setUseCases] = useState<UseCase[]>([]);
  const [selectedUseCase, setSelectedUseCase] = useState<string>("");
  const [agents, setAgents] = useState<Agent[]>([]);
  const [mode, setMode] = useState<"agent" | "manual">("manual");
  const [agentId, setAgentId] = useState<string>("");
  const [manual, setManual] = useState<ManualAgentState>(EMPTY_MANUAL);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const orgProfile = loadOrgProfile();

  useEffect(() => {
    if (!apiKey) return;
    fetch("/v1/compliance/bundle/use-cases", { headers: { "X-API-Key": apiKey } })
      .then((r) => {
        if (!r.ok) throw new Error("Failed to load use-cases");
        return r.json();
      })
      .then((d) => setUseCases(d.use_cases))
      .catch(() => setUseCases([
        { key: "credit_scoring", description: "Credit scoring (Annex III §5(b))", triggers_fria: true },
        { key: "insurance_pricing", description: "Insurance pricing (Annex III §5(c))", triggers_fria: true },
        { key: "public_service", description: "Public body / public service", triggers_fria: true },
        { key: "other_high_risk", description: "Other Annex III high-risk deployment", triggers_fria: false },
      ]));
    listAgents().then((d) => setAgents(d.agents)).catch(() => setAgents([]));
  }, [apiKey]);

  const selectedUC = useMemo(
    () => useCases.find((u) => u.key === selectedUseCase),
    [useCases, selectedUseCase],
  );

  const ready = (() => {
    if (step === "Use-case") return !!selectedUseCase;
    if (step === "System") {
      if (mode === "agent") return !!agentId;
      return manual.name.trim().length > 0;
    }
    return true;
  })();

  const handleGenerate = async () => {
    if (!apiKey) return;
    setBusy(true);
    setError(null);
    try {
      const payload: Record<string, unknown> = {
        use_case_key: selectedUseCase,
        deployer_organisation: orgProfile.organisation || undefined,
        deployer_contact: orgProfile.contact || undefined,
        provider_name: orgProfile.organisation || undefined,
        provider_address: orgProfile.address || undefined,
        provider_contact: orgProfile.contact || undefined,
        pmm_owner: orgProfile.pmm_owner || undefined,
        accountability_owner: orgProfile.accountability_owner || undefined,
        rms_owner: orgProfile.accountability_owner || undefined,
        member_states: orgProfile.member_states
          ? orgProfile.member_states.split("\n").map((s) => s.trim()).filter(Boolean)
          : undefined,
      };
      if (mode === "agent") {
        payload.agent_id = agentId;
      } else {
        payload.manual_agent = manualAgentPayload(manual);
      }

      const res = await fetch("/v1/compliance/bundle", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.error?.message || "Bundle generation failed");
      }
      const artefacts = (res.headers.get("X-Bundle-Artefacts") || "").split(",");
      const blob = await res.blob();
      const slug = mode === "agent" ? agentId : "manual";
      downloadBlob(
        `compliance-bundle-${slug}-${selectedUseCase}.zip`,
        blob,
      );
      setDone(true);
      console.info("Bundle artefacts:", artefacts);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setBusy(false);
    }
  };

  if (!apiKey) {
    return (
      <div className="max-w-xl mx-auto py-16 text-center">
        <Sparkles size={40} className="text-[#00d4ff] mx-auto mb-4" />
        <h1 className="text-2xl font-semibold text-[#f1f5f9] mb-2">Compliance setup</h1>
        <p className="text-sm text-[#94a3b8] mb-6">
          Log in to generate your full EU AI Act document set in one go.
        </p>
        <Link
          to="/auth"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-sm font-medium no-underline"
        >
          Log in
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto py-8">
      <div className="mb-6">
        <p className="text-xs text-[#64748b] mb-1 font-medium uppercase tracking-widest">
          {de ? "Compliance-Setup" : "Compliance setup"}
        </p>
        <h1 className="text-2xl font-semibold text-[#f1f5f9]">
          {de
            ? "Ein Ablauf, alle benötigten Dokumente"
            : "One flow, every document you need"}
        </h1>
        <p className="text-xs text-[#94a3b8] mt-1 max-w-xl">
          {de
            ? "Use-Case auswählen, KI-System beschreiben, ZIP mit allen einschlägigen EU-AI-Act-Artefakten laden (FRIA, Annex IV, PMM, Data Sheet, EU-DB-Registrierung). Organisationsprofil füllt den Rest automatisch."
            : "Pick a use-case, describe the AI system, download a ZIP containing every EU AI Act artefact that applies (FRIA, Annex IV, PMM, data sheet, EU-DB registration). Your organisation profile fills the rest automatically."}
        </p>
      </div>

      {!orgProfile.organisation && (
        <div className="rounded-xl border border-amber-500/15 bg-amber-500/5 p-3 mb-6 flex items-start gap-2">
          <AlertCircle size={14} className="text-amber-300 shrink-0 mt-0.5" />
          <p className="text-xs text-amber-200/90 flex-1">
            Organisation profile not set. The bundle will still generate, but with
            <code className="mx-1">[PROVIDER: …]</code>placeholders.{" "}
            <Link to="/settings/org" className="underline hover:text-amber-100">
              Set it up first (60s)
            </Link>
          </p>
        </div>
      )}

      <ol className="flex items-center gap-2 mb-8 text-xs">
        {STEPS.map((name, idx) => {
          const active = step === name;
          const passed = STEPS.indexOf(step) > idx;
          return (
            <li key={name} className="flex items-center gap-2 flex-1">
              <span
                className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-medium ${
                  active
                    ? "bg-[#00d4ff] text-[#0a0a0f]"
                    : passed
                    ? "bg-emerald-500/20 text-emerald-300"
                    : "bg-white/[0.05] text-[#64748b]"
                }`}
              >
                {passed ? <CheckCircle size={12} /> : idx + 1}
              </span>
              <span
                className={active ? "text-[#f1f5f9]" : passed ? "text-[#94a3b8]" : "text-[#64748b]"}
              >
                {de ? STEP_LABELS_DE[name] : name}
              </span>
              {idx < STEPS.length - 1 && (
                <span className="flex-1 h-px bg-white/[0.05] mx-2" />
              )}
            </li>
          );
        })}
      </ol>

      {error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 flex items-start gap-2 mb-6">
          <AlertCircle size={14} className="text-red-400 shrink-0 mt-0.5" />
          <p className="text-xs text-red-300">{error}</p>
        </div>
      )}

      {step === "Use-case" && (
        <section className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
          <h2 className="text-sm font-medium text-[#f1f5f9] mb-3">
            1. What is the use-case?
          </h2>
          <p className="text-xs text-[#94a3b8] mb-4">
            Drives which artefacts are generated. FRIA (Art. 27) is only included for
            use-cases that trigger it.
          </p>
          <div className="space-y-2">
            {useCases.map((uc) => {
              const Icon = USE_CASE_ICON[uc.key] || Sparkles;
              const active = selectedUseCase === uc.key;
              return (
                <button
                  key={uc.key}
                  onClick={() => setSelectedUseCase(uc.key)}
                  className={`w-full text-left flex items-start gap-3 p-3 rounded-lg border transition-colors ${
                    active
                      ? "border-[#00d4ff]/30 bg-[#00d4ff]/5"
                      : "border-white/[0.06] hover:border-white/[0.12]"
                  }`}
                >
                  <Icon size={16} className="text-[#00d4ff] shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <div className="text-sm text-[#f1f5f9]">{uc.description}</div>
                    <div className="text-[10px] text-[#64748b] mt-0.5">
                      {uc.triggers_fria ? "Includes FRIA (Art. 27)" : "FRIA not required"}
                    </div>
                  </div>
                  {active && <CheckCircle size={14} className="text-[#00d4ff]" />}
                </button>
              );
            })}
          </div>
        </section>
      )}

      {step === "System" && (
        <section className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
          <h2 className="text-sm font-medium text-[#f1f5f9] mb-3">
            2. Which AI system?
          </h2>
          <p className="text-xs text-[#94a3b8] mb-4">
            Registered on this platform or something external you describe here. Either
            works.
          </p>
          <AgentOrManualSelector
            agents={agents}
            agentId={agentId}
            mode={mode}
            manual={manual}
            onAgentIdChange={setAgentId}
            onModeChange={setMode}
            onManualChange={setManual}
          />
        </section>
      )}

      {step === "Review" && selectedUC && (
        <section className="rounded-xl border border-white/[0.06] bg-[#111118] p-5 space-y-4">
          <div>
            <h2 className="text-sm font-medium text-[#f1f5f9] mb-3">
              3. Review and generate
            </h2>
            <dl className="text-xs space-y-1.5">
              <Row k="Use-case" v={selectedUC.description} />
              <Row
                k="System"
                v={
                  mode === "agent"
                    ? agents.find((a) => a.id === agentId)?.name || agentId
                    : manual.name
                }
              />
              <Row
                k="Organisation"
                v={orgProfile.organisation || "not set (will use placeholders)"}
              />
            </dl>
          </div>

          <div className="rounded-lg border border-white/[0.04] bg-[#0a0a0f] p-3">
            <p className="text-xs text-[#94a3b8] mb-2">
              ZIP will contain:
            </p>
            <ul className="text-xs text-[#94a3b8] space-y-0.5">
              {selectedUC.triggers_fria && (
                <li>• <span className="text-[#f1f5f9]">FRIA</span> (Art. 27)</li>
              )}
              <li>• <span className="text-[#f1f5f9]">Annex IV</span> technical documentation (Art. 11)</li>
              <li>• <span className="text-[#f1f5f9]">PMM plan</span> (Art. 72)</li>
              <li>• <span className="text-[#f1f5f9]">Data sheet</span> (Art. 10)</li>
              <li>• <span className="text-[#f1f5f9]">EU-DB registration draft</span> (Art. 49, Annex VIII)</li>
              <li>• All PDFs plus Markdown source plus JSON payloads plus README</li>
            </ul>
          </div>

          {done ? (
            <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3 flex items-start gap-2">
              <CheckCircle size={14} className="text-emerald-400 shrink-0 mt-0.5" />
              <p className="text-xs text-emerald-200/90">
                Bundle downloaded. Review the PDFs, fill the remaining
                <code className="mx-1">[DEPLOYER: …]</code>placeholders, then route
                finalised documents through <Link to="/compliance" className="underline hover:text-emerald-100">the workspace</Link>.
              </p>
            </div>
          ) : (
            <button
              onClick={handleGenerate}
              disabled={busy}
              className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed"
              style={{ transition: "background 0.2s cubic-bezier(0.16, 1, 0.3, 1)" }}
            >
              {busy ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
              Generate and download bundle
            </button>
          )}
        </section>
      )}

      <div className="flex items-center justify-between mt-6">
        <button
          onClick={() => {
            if (step === "Use-case") navigate("/compliance");
            else if (step === "System") setStep("Use-case");
            else if (step === "Review") setStep("System");
          }}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs text-[#64748b] hover:text-[#f1f5f9] transition-colors"
        >
          <ArrowLeft size={12} />
          {step === "Use-case" ? "Back to workspace" : "Previous"}
        </button>
        {step !== "Review" && (
          <button
            onClick={() => setStep(step === "Use-case" ? "System" : "Review")}
            disabled={!ready}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Next
            <ArrowRight size={12} />
          </button>
        )}
        {step === "Review" && done && (
          <Link
            to="/compliance"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-white/[0.08] text-sm text-[#94a3b8] hover:text-[#f1f5f9] no-underline transition-colors"
          >
            Open workspace
            <FileCheck size={12} />
          </Link>
        )}
      </div>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex gap-2">
      <dt className="text-[#64748b] w-28 shrink-0">{k}</dt>
      <dd className="text-[#94a3b8]">{v}</dd>
    </div>
  );
}
