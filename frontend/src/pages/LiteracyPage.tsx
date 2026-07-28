import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  BookOpen,
  CheckCircle,
  Clock,
  Download,
  FileCheck,
  GraduationCap,
  Save,
  XCircle,
} from "lucide-react";
import { createComplianceDocument } from "../compliance-api";
import { useT } from "../i18n";

type ModuleListEntry = {
  id: string;
  title: string;
  summary: string;
  duration_minutes: number;
  slide_count: number;
  question_count: number;
};

type Slide = { title: string; body: string };

type Question = { id: string; prompt: string; options: string[] };

type ModuleDetail = {
  id: string;
  title: string;
  summary: string;
  duration_minutes: number;
  slides: Slide[];
  questions: Question[];
};

type CompletionRecord = {
  module_id: string;
  score_pct: number;
  passed: boolean;
  completed_at: string;
  certificate_id: string;
  learner_name: string;
  learner_organisation: string;
};

const COMPLETIONS_KEY = "af_literacy_completions_v1";
const LEARNER_KEY = "af_literacy_learner_v1";

function loadCompletions(): Record<string, CompletionRecord> {
  if (typeof window === "undefined") return {};
  try {
    return JSON.parse(localStorage.getItem(COMPLETIONS_KEY) || "{}");
  } catch {
    return {};
  }
}

function saveCompletion(record: CompletionRecord) {
  const all = loadCompletions();
  all[record.module_id] = record;
  localStorage.setItem(COMPLETIONS_KEY, JSON.stringify(all));
}

function loadLearner(): { name: string; organisation: string } {
  if (typeof window === "undefined") return { name: "", organisation: "" };
  try {
    return JSON.parse(localStorage.getItem(LEARNER_KEY) || "{}");
  } catch {
    return { name: "", organisation: "" };
  }
}

function saveLearner(name: string, organisation: string) {
  localStorage.setItem(LEARNER_KEY, JSON.stringify({ name, organisation }));
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

export function LiteracyPage() {
  const { moduleId } = useParams<{ moduleId?: string }>();
  if (moduleId) {
    return <ModuleRunner moduleId={moduleId} />;
  }
  return <ModuleCatalogue />;
}

function ModuleCatalogue() {
  const { t } = useT();
  const [modules, setModules] = useState<ModuleListEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const completions = loadCompletions();

  useEffect(() => {
    fetch("/v1/literacy/modules")
      .then((r) => r.json())
      .then((d) => setModules(d.modules))
      .catch(() => setError("Failed to load literacy modules"))
      .finally(() => setLoading(false));
  }, []);

  const completedCount = Object.values(completions).filter((c) => c.passed).length;

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
            {t("literacy.eyebrow")}
          </p>
          <h1 className="text-3xl sm:text-4xl font-semibold text-[#f1f5f9] mb-4 leading-[1.15] tracking-tight">
            {t("literacy.title1")}<br />
            <span className="text-[#00d4ff]">{t("literacy.title2")}</span>
          </h1>
          <p className="text-[15px] text-[#94a3b8] leading-relaxed max-w-lg mx-auto mb-4">
            {t("literacy.sub")}
          </p>
          <p className="text-xs text-[#64748b]">
            {t("literacy.progress")} · {completedCount} / {modules.length || 3}
          </p>
        </div>
      </section>

      {error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 flex items-start gap-2 mb-6">
          <AlertCircle size={14} className="text-red-400 shrink-0 mt-0.5" />
          <p className="text-xs text-red-300">{error}</p>
        </div>
      )}

      {loading ? (
        <p className="text-center text-sm text-[#64748b] py-10">Loading…</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {modules.map((m, idx) => {
            const completion = completions[m.id];
            return (
              <Link
                key={m.id}
                to={`/literacy/${m.id}`}
                className="group rounded-xl border border-white/[0.06] bg-[#111118] p-5 no-underline hover:border-[#00d4ff]/20 transition-colors flex flex-col"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2 text-xs text-[#64748b]">
                    <span className="font-mono">M{idx + 1}</span>
                    <span>·</span>
                    <Clock size={12} />
                    <span>{m.duration_minutes} min</span>
                  </div>
                  {completion?.passed ? (
                    <CheckCircle size={16} className="text-emerald-400" />
                  ) : completion ? (
                    <XCircle size={16} className="text-amber-400" />
                  ) : (
                    <BookOpen size={16} className="text-[#64748b]" />
                  )}
                </div>
                <h3 className="text-sm font-medium text-[#f1f5f9] mb-2 group-hover:text-[#00d4ff] transition-colors">
                  {m.title}
                </h3>
                <p className="text-xs text-[#94a3b8] leading-relaxed flex-1">{m.summary}</p>
                <div className="mt-4 flex items-center justify-between text-xs text-[#64748b]">
                  <span>{m.slide_count} slides · {m.question_count} questions</span>
                  {completion ? (
                    <span className={completion.passed ? "text-emerald-400" : "text-amber-400"}>
                      {completion.score_pct}%
                    </span>
                  ) : (
                    <ArrowRight size={12} />
                  )}
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </>
  );
}

type RunnerStage = "slides" | "quiz" | "result";

function ModuleRunner({ moduleId }: { moduleId: string }) {
  const navigate = useNavigate();
  const apiKey = typeof window !== "undefined" ? localStorage.getItem("af_api_key") : null;
  const [module, setModule] = useState<ModuleDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stage, setStage] = useState<RunnerStage>("slides");
  const [slideIdx, setSlideIdx] = useState(0);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [learner, setLearner] = useState(loadLearner());
  const [busy, setBusy] = useState(false);
  const [savedId, setSavedId] = useState<string | null>(null);
  const [result, setResult] = useState<{ score: { score_pct: number; passed: boolean; correct_count: number; total: number }; certificate: { certificate_id: string; result: { completed_at: string } } } | null>(null);

  useEffect(() => {
    fetch(`/v1/literacy/modules/${encodeURIComponent(moduleId)}`)
      .then((r) => {
        if (!r.ok) throw new Error("Module not found");
        return r.json();
      })
      .then(setModule)
      .catch(() => setError("Module not found"));
  }, [moduleId]);

  const answeredAll = useMemo(() => {
    if (!module) return false;
    return module.questions.every((q) => q.id in answers);
  }, [module, answers]);

  const handleSubmit = async () => {
    if (!module || !learner.name.trim() || !learner.organisation.trim()) {
      setError("Enter your name and organisation before submitting.");
      return;
    }
    setBusy(true);
    setError(null);
    saveLearner(learner.name.trim(), learner.organisation.trim());
    try {
      const res = await fetch("/v1/literacy/complete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          module_id: module.id,
          answers,
          learner_name: learner.name.trim(),
          learner_organisation: learner.organisation.trim(),
        }),
      });
      if (!res.ok) throw new Error("Submission failed");
      const data = await res.json();
      setResult(data);
      saveCompletion({
        module_id: module.id,
        score_pct: data.score.score_pct,
        passed: data.score.passed,
        completed_at: data.certificate.result.completed_at,
        certificate_id: data.certificate.certificate_id,
        learner_name: learner.name.trim(),
        learner_organisation: learner.organisation.trim(),
      });
      setStage("result");

      if (data.score.passed && apiKey) {
        try {
          const doc = await createComplianceDocument(apiKey, {
            doc_type: "literacy_completion",
            title: `Literacy · ${module.title} · ${learner.name.trim()}`,
            payload: data.certificate,
            status: "approved",
          });
          setSavedId(doc.id);
        } catch {
          // Silent fail; the certificate download still works offline.
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Submission failed");
    } finally {
      setBusy(false);
    }
  };

  const handleDownloadJSON = () => {
    if (!result) return;
    downloadBlob(
      `literacy-cert-${moduleId}-${result.certificate.certificate_id}.json`,
      JSON.stringify(result.certificate, null, 2),
      "application/json",
    );
  };

  const handleDownloadMarkdown = async () => {
    if (!module) return;
    try {
      const res = await fetch("/v1/literacy/certificate/markdown", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          module_id: module.id,
          answers,
          learner_name: learner.name.trim(),
          learner_organisation: learner.organisation.trim(),
        }),
      });
      if (!res.ok) throw new Error("Markdown export failed");
      const md = await res.text();
      downloadBlob(`literacy-cert-${moduleId}.md`, md, "text/markdown");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Markdown export failed");
    }
  };

  const handleDownloadPDF = async () => {
    if (!module) return;
    try {
      const res = await fetch("/v1/literacy/certificate/pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          module_id: module.id,
          answers,
          learner_name: learner.name.trim(),
          learner_organisation: learner.organisation.trim(),
        }),
      });
      if (!res.ok) throw new Error("PDF export failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `literacy-cert-${moduleId}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "PDF export failed");
    }
  };

  if (error && !module) {
    return (
      <div className="py-10 text-center">
        <p className="text-sm text-red-300 mb-4">{error}</p>
        <Link to="/literacy" className="text-xs text-[#00d4ff] no-underline hover:underline">
          Back to module list
        </Link>
      </div>
    );
  }

  if (!module) {
    return <p className="text-center text-sm text-[#64748b] py-10">Loading module…</p>;
  }

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <Link
          to="/literacy"
          className="inline-flex items-center gap-1.5 text-xs text-[#64748b] hover:text-[#f1f5f9] no-underline transition-colors"
        >
          <ArrowLeft size={12} />
          All modules
        </Link>
        <span className="text-xs text-[#64748b]">
          {stage === "slides"
            ? `Slide ${slideIdx + 1} / ${module.slides.length}`
            : stage === "quiz"
            ? `Quiz · ${Object.keys(answers).length} / ${module.questions.length}`
            : "Complete"}
        </span>
      </div>

      <header className="mb-8">
        <p className="text-xs text-[#64748b] mb-2 font-medium uppercase tracking-widest">
          {module.duration_minutes} minute module
        </p>
        <h1 className="text-2xl font-semibold text-[#f1f5f9] mb-2">{module.title}</h1>
        <p className="text-sm text-[#94a3b8]">{module.summary}</p>
      </header>

      {stage === "slides" && (
        <section className="rounded-xl border border-white/[0.06] bg-[#111118] p-6">
          <h2 className="text-base font-medium text-[#f1f5f9] mb-3">
            {module.slides[slideIdx].title}
          </h2>
          <p className="text-sm text-[#94a3b8] leading-relaxed whitespace-pre-line">
            {module.slides[slideIdx].body}
          </p>
          <div className="mt-6 flex items-center justify-between">
            <button
              onClick={() => setSlideIdx((i) => Math.max(0, i - 1))}
              disabled={slideIdx === 0}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-white/[0.08] text-sm text-[#94a3b8] hover:text-[#f1f5f9] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <ArrowLeft size={12} />
              Previous
            </button>
            {slideIdx < module.slides.length - 1 ? (
              <button
                onClick={() => setSlideIdx((i) => i + 1)}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-sm font-medium"
                style={{ transition: "background 0.2s cubic-bezier(0.16, 1, 0.3, 1)" }}
              >
                Next
                <ArrowRight size={12} />
              </button>
            ) : (
              <button
                onClick={() => setStage("quiz")}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-sm font-medium"
                style={{ transition: "background 0.2s cubic-bezier(0.16, 1, 0.3, 1)" }}
              >
                Start quiz
                <ArrowRight size={12} />
              </button>
            )}
          </div>
        </section>
      )}

      {stage === "quiz" && (
        <section className="rounded-xl border border-white/[0.06] bg-[#111118] p-6 space-y-6">
          {module.questions.map((q, idx) => (
            <div key={q.id}>
              <p className="text-sm text-[#f1f5f9] mb-3">
                <span className="text-[#64748b] mr-2">{idx + 1}.</span>
                {q.prompt}
              </p>
              <div className="space-y-2">
                {q.options.map((option, optIdx) => {
                  const checked = answers[q.id] === optIdx;
                  return (
                    <label
                      key={optIdx}
                      className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                        checked
                          ? "border-[#00d4ff]/30 bg-[#00d4ff]/5"
                          : "border-white/[0.06] hover:border-white/[0.12]"
                      }`}
                    >
                      <input
                        type="radio"
                        name={q.id}
                        checked={checked}
                        onChange={() => setAnswers((prev) => ({ ...prev, [q.id]: optIdx }))}
                        className="mt-0.5"
                      />
                      <span className="text-xs text-[#94a3b8] leading-relaxed">{option}</span>
                    </label>
                  );
                })}
              </div>
            </div>
          ))}

          <div className="border-t border-white/[0.06] pt-6 space-y-3">
            <input
              value={learner.name}
              onChange={(e) => setLearner((p) => ({ ...p, name: e.target.value }))}
              placeholder="Your name"
              className="w-full px-3 py-2 rounded-lg bg-[#0a0a0f] border border-white/[0.06] text-sm text-[#f1f5f9] placeholder-[#64748b] focus:outline-none focus:border-[#00d4ff]/30"
            />
            <input
              value={learner.organisation}
              onChange={(e) => setLearner((p) => ({ ...p, organisation: e.target.value }))}
              placeholder="Organisation"
              className="w-full px-3 py-2 rounded-lg bg-[#0a0a0f] border border-white/[0.06] text-sm text-[#f1f5f9] placeholder-[#64748b] focus:outline-none focus:border-[#00d4ff]/30"
            />
          </div>

          {error && (
            <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 flex items-start gap-2">
              <AlertCircle size={14} className="text-red-400 shrink-0 mt-0.5" />
              <p className="text-xs text-red-300">{error}</p>
            </div>
          )}

          <button
            onClick={handleSubmit}
            disabled={!answeredAll || busy || !learner.name.trim() || !learner.organisation.trim()}
            className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed"
            style={{ transition: "background 0.2s cubic-bezier(0.16, 1, 0.3, 1)" }}
          >
            <GraduationCap size={14} />
            Submit and issue certificate
          </button>
        </section>
      )}

      {stage === "result" && result && (
        <section className="rounded-xl border border-white/[0.06] bg-[#111118] p-6">
          <div className="text-center mb-6">
            {result.score.passed ? (
              <CheckCircle size={40} className="text-emerald-400 mx-auto mb-3" />
            ) : (
              <XCircle size={40} className="text-amber-400 mx-auto mb-3" />
            )}
            <h2 className="text-xl font-semibold text-[#f1f5f9] mb-1">
              {result.score.passed ? "Passed" : "Not passed"}
            </h2>
            <p className="text-sm text-[#94a3b8]">
              Score: {result.score.score_pct}% ({result.score.correct_count} /{" "}
              {result.score.total})
            </p>
            <p className="text-xs text-[#64748b] mt-2 font-mono">
              Certificate {result.certificate.certificate_id}
            </p>
          </div>

          {savedId && (
            <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3 flex items-start gap-2 mb-4">
              <Save size={14} className="text-emerald-400 shrink-0 mt-0.5" />
              <p className="text-xs text-emerald-200/90">
                Auto-saved to your organisation's compliance workspace as{" "}
                <a href="/compliance" className="underline hover:text-emerald-100">
                  document {savedId.slice(0, 8)}
                </a>
                .
              </p>
            </div>
          )}

          {result.score.passed ? (
            <div className="flex flex-wrap gap-2 justify-center">
              <button
                onClick={handleDownloadJSON}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-sm font-medium no-underline"
                style={{ transition: "background 0.2s cubic-bezier(0.16, 1, 0.3, 1)" }}
              >
                <Download size={14} />
                Download JSON
              </button>
              <button
                onClick={handleDownloadMarkdown}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-white/[0.08] text-sm text-[#94a3b8] hover:text-[#f1f5f9] transition-colors"
              >
                <FileCheck size={14} />
                Download Markdown
              </button>
              <button
                onClick={handleDownloadPDF}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-white/[0.08] text-sm text-[#94a3b8] hover:text-[#f1f5f9] transition-colors"
              >
                <FileCheck size={14} />
                Download PDF
              </button>
              <button
                onClick={() => navigate("/literacy")}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-white/[0.08] text-sm text-[#94a3b8] hover:text-[#f1f5f9] transition-colors"
              >
                Back to modules
              </button>
            </div>
          ) : (
            <div className="text-center">
              <p className="text-xs text-[#64748b] mb-4">
                Review the slides and try again. Pass threshold: 70%.
              </p>
              <button
                onClick={() => {
                  setStage("slides");
                  setSlideIdx(0);
                  setAnswers({});
                  setResult(null);
                }}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-sm font-medium"
                style={{ transition: "background 0.2s cubic-bezier(0.16, 1, 0.3, 1)" }}
              >
                Retry module
              </button>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
