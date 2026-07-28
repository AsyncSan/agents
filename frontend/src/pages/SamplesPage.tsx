import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Briefcase, Download, FileCheck, Sparkles } from "lucide-react";

interface SampleScenario {
  slug: string;
  title: string;
  fria: string;
  annex_iv: string;
}

const DOMAIN_ICON: Record<string, typeof Sparkles> = {
  "credit-scoring": Sparkles,
  "hr-hiring": Briefcase,
  "insurance-pricing": FileCheck,
  "security-audit": FileCheck,
};

const DOMAIN_BLURB: Record<string, string> = {
  "credit-scoring":
    "Retail bank consumer credit scoring. Annex III §5(b) trigger. High-risk. Contains filled Deployer process summary, bias assessment, and governance cadence.",
  "hr-hiring":
    "CV pre-screening for HR-Tech SME. Annex III §4 trigger. Human approval mandatory on shortlists. Works-council integration pattern included.",
  "insurance-pricing":
    "Premium-tier recommender at renewal. Annex III §5(c) trigger. Human underwriter in the loop. Vulnerable-group mitigations documented.",
  "security-audit":
    "Internal engineering use-case. Limited-risk classification demonstrates how a non-Annex-III system's documentation stays proportionate.",
};

export function SamplesPage() {
  const [scenarios, setScenarios] = useState<SampleScenario[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/samples/index.json")
      .then((r) => {
        if (!r.ok) throw new Error("Samples not found");
        return r.json();
      })
      .then(setScenarios)
      .catch(() => setError("Samples index could not be loaded."));
  }, []);

  return (
    <div className="max-w-3xl mx-auto py-8">
      <div className="mb-8">
        <p className="text-xs text-[#64748b] mb-1 font-medium uppercase tracking-widest">
          Sample documents
        </p>
        <h1 className="text-2xl font-semibold text-[#f1f5f9] mb-2">
          Fully-filled compliance samples
        </h1>
        <p className="text-sm text-[#94a3b8] max-w-xl">
          Download a fully-filled FRIA and Annex IV document for four use-cases that
          map to Annex III of the EU AI Act. These are not scaffold PDFs; realistic
          organisational inputs are filled in. Use them to see what a finished
          document from this platform looks like before signing up.
        </p>
      </div>

      {error && (
        <p className="text-sm text-red-300 mb-6">{error}</p>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-10">
        {scenarios.map((s) => {
          const Icon = DOMAIN_ICON[s.slug] || Sparkles;
          return (
            <div
              key={s.slug}
              className="rounded-xl border border-white/[0.06] bg-[#111118] p-5"
            >
              <Icon size={18} className="text-[#00d4ff] mb-3" />
              <h3 className="text-sm font-medium text-[#f1f5f9] mb-2">{s.title}</h3>
              <p className="text-xs text-[#94a3b8] leading-relaxed mb-4">
                {DOMAIN_BLURB[s.slug] || ""}
              </p>
              <div className="flex flex-col gap-1.5">
                <a
                  href={`/samples/${s.fria}`}
                  download
                  className="inline-flex items-center gap-1.5 text-xs text-[#00d4ff] no-underline hover:underline"
                >
                  <Download size={12} />
                  FRIA (Art. 27) · {s.fria}
                </a>
                <a
                  href={`/samples/${s.annex_iv}`}
                  download
                  className="inline-flex items-center gap-1.5 text-xs text-[#00d4ff] no-underline hover:underline"
                >
                  <Download size={12} />
                  Annex IV (Art. 11) · {s.annex_iv}
                </a>
              </div>
            </div>
          );
        })}
      </div>

      <div className="rounded-xl border border-[#00d4ff]/10 bg-[#00d4ff]/[0.03] p-5 flex items-start gap-3">
        <Sparkles size={16} className="text-[#00d4ff] shrink-0 mt-0.5" />
        <div className="flex-1">
          <p className="text-sm text-[#f1f5f9] mb-1 font-medium">
            Generate your own, with your own inputs
          </p>
          <p className="text-xs text-[#94a3b8] mb-3">
            The samples above use fictional inputs for realism. Your version pulls from
            your organisation profile plus the system you describe in the wizard.
          </p>
          <div className="flex flex-wrap gap-2">
            <Link
              to="/fria"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-xs font-medium no-underline"
            >
              Open FRIA wizard
              <ArrowRight size={12} />
            </Link>
            <Link
              to="/annex-iv"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-white/[0.08] text-xs text-[#94a3b8] hover:text-[#f1f5f9] no-underline transition-colors"
            >
              Open Annex IV wizard
              <ArrowRight size={12} />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
