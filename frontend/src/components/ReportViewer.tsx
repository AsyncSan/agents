import { useState, useMemo } from "react";
import {
  Shield,
  AlertTriangle,
  AlertCircle,
  Info,
  ChevronDown,
  ChevronRight,
  FileText,
  Clock,
  Server,
  Cpu,
  Zap,
  CheckCircle,
  ExternalLink,
  Copy,
  Check,
} from "lucide-react";

interface Finding {
  id: string;
  title: string;
  severity: "critical" | "high" | "medium" | "low";
  file?: string;
  files?: string[];
  cwe?: string;
  impact: string;
  evidence?: string;
  detail?: string;
}

interface ParsedReport {
  title: string;
  date: string;
  repo: string;
  license?: string;
  riskRating: string;
  summary: string;
  findings: Finding[];
  recommendations: string[];
  disclaimer?: string;
  dependencyNote?: string;
  severityCounts: Record<string, number>;
}

function parseReport(markdown: string): ParsedReport | null {
  if (!markdown || !markdown.includes("# ")) return null;

  const lines = markdown.split("\n");

  // Title
  const titleLine = lines.find((l) => l.startsWith("# "));
  const title = titleLine?.replace("# ", "") || "Security Report";

  // Metadata
  const dateLine = lines.find((l) => l.startsWith("**Date:**"));
  const date = dateLine?.match(/\*\*Date:\*\*\s*(.+)/)?.[1]?.trim() || "";
  const repoLine = lines.find((l) => l.startsWith("**Repository:**"));
  const repo = repoLine?.match(/\*\*Repository:\*\*\s*(.+)/)?.[1]?.trim() || "";
  const licenseLine = lines.find((l) => l.startsWith("**License:**"));
  const license = licenseLine?.match(/\*\*License:\*\*\s*(.+)/)?.[1]?.trim();

  // Risk rating
  const riskLine = lines.find((l) => l.includes("Risk") && l.includes("**"));
  const riskRating =
    riskLine?.match(/\*\*(.*?)\*\*/g)?.[0]?.replace(/\*\*/g, "") || "Unknown";

  // Summary paragraph (after executive summary heading, before findings)
  const summaryStart = lines.findIndex((l) =>
    l.toLowerCase().includes("executive summary")
  );
  let summary = "";
  if (summaryStart >= 0) {
    for (let i = summaryStart + 1; i < lines.length; i++) {
      if (lines[i].startsWith("##") || lines[i].startsWith("---")) break;
      if (lines[i].startsWith("**Risk")) continue;
      const cleaned = lines[i].replace(/\*\*/g, "").trim();
      if (cleaned) summary += (summary ? " " : "") + cleaned;
    }
  }

  // Parse findings
  const findings: Finding[] = [];
  let currentSeverity: "critical" | "high" | "medium" | "low" = "medium";
  let currentFinding: Partial<Finding> | null = null;
  let inEvidence = false;
  let evidenceLines: string[] = [];
  let detailLines: string[] = [];

  const severityMap: Record<string, "critical" | "high" | "medium" | "low"> = {
    critical: "critical",
    high: "high",
    medium: "medium",
    low: "low",
  };

  const flushFinding = () => {
    if (currentFinding?.title) {
      findings.push({
        id: currentFinding.id || `F${findings.length + 1}`,
        title: currentFinding.title,
        severity: currentFinding.severity || currentSeverity,
        file: currentFinding.file,
        files: currentFinding.files,
        cwe: currentFinding.cwe,
        impact: currentFinding.impact || "",
        evidence:
          evidenceLines.length > 0 ? evidenceLines.join("\n") : undefined,
        detail: detailLines
          .filter((l) => l.trim())
          .join("\n")
          .trim() || undefined,
      });
    }
    currentFinding = null;
    evidenceLines = [];
    detailLines = [];
    inEvidence = false;
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Detect severity section
    const severityMatch = line.match(
      /###\s+.*?(CRITICAL|HIGH|MEDIUM|LOW)/i
    );
    if (severityMatch) {
      flushFinding();
      currentSeverity =
        severityMap[severityMatch[1].toLowerCase()] || "medium";
      continue;
    }

    // Detect finding header (#### pattern)
    const findingMatch = line.match(
      /####\s+(?:([A-Z]\d+):\s+)?(.+)/
    );
    if (findingMatch) {
      flushFinding();
      const rawTitle = findingMatch[2];
      const cweMatch = rawTitle.match(/\(CWE-(\d+)\)/);
      currentFinding = {
        id: findingMatch[1] || `${currentSeverity[0].toUpperCase()}${findings.length + 1}`,
        title: rawTitle.replace(/\s*\(CWE-\d+\)\s*/, "").trim(),
        severity: currentSeverity,
        cwe: cweMatch ? `CWE-${cweMatch[1]}` : undefined,
        files: [],
      };
      continue;
    }

    if (!currentFinding) continue;

    // Parse finding content
    if (line.startsWith("```")) {
      inEvidence = !inEvidence;
      continue;
    }

    if (inEvidence) {
      evidenceLines.push(line);
      continue;
    }

    const fileLine = line.match(
      /[-*]\s+\*\*Files?:\*\*\s*`?([^`\n]+)/
    );
    if (fileLine) {
      const files = fileLine[1].split(",").map((f) => f.trim().replace(/`/g, ""));
      currentFinding.files = [
        ...(currentFinding.files || []),
        ...files,
      ];
      if (!currentFinding.file) currentFinding.file = files[0];
      continue;
    }

    const singleFile = line.match(
      /[-*]\s+\*\*File:\*\*\s*`?([^`\n]+)/
    );
    if (singleFile) {
      const f = singleFile[1].trim().replace(/`/g, "");
      currentFinding.file = f;
      currentFinding.files = [
        ...(currentFinding.files || []),
        f,
      ];
      continue;
    }

    const impactLine = line.match(/[-*]\s+\*\*Impact:\*\*\s*(.+)/);
    if (impactLine) {
      currentFinding.impact = impactLine[1].trim();
      continue;
    }

    const detailLine = line.match(/[-*]\s+\*\*Detail:\*\*\s*(.+)/);
    if (detailLine) {
      detailLines.push(detailLine[1].trim());
      continue;
    }

    const evidenceLine = line.match(/[-*]\s+\*\*Evidence:\*\*\s*(.*)/);
    if (evidenceLine) {
      if (evidenceLine[1].trim()) detailLines.push(evidenceLine[1].trim());
      continue;
    }

    // Fallback: capture other bullet points as detail
    if (line.match(/^\s*[-*]\s+/) && !line.includes("**Location:**")) {
      const content = line.replace(/^\s*[-*]\s+/, "").trim();
      if (content && !content.startsWith("**")) {
        detailLines.push(content);
      }
    }

    // Location as file
    const locationLine = line.match(
      /[-*]\s+\*\*Location:\*\*\s*(.+)/
    );
    if (locationLine) {
      detailLines.push(locationLine[1].trim());
      continue;
    }
  }
  flushFinding();

  // Parse recommendations
  const recommendations: string[] = [];
  const recStart = lines.findIndex(
    (l) => l.match(/^##\s+Recommend/i) || l.match(/^##\s+\d+\.\s+Recommend/i)
  );
  if (recStart >= 0) {
    for (let i = recStart + 1; i < lines.length; i++) {
      if (lines[i].startsWith("## ") || lines[i].startsWith("---")) break;
      const recMatch = lines[i].match(/^\d+\.\s+\*\*(.+?)\*\*\s*[-—:]+\s*(.+)/);
      if (recMatch) {
        recommendations.push(`${recMatch[1]}: ${recMatch[2]}`);
      } else {
        const simpleRec = lines[i].match(/^\d+\.\s+(.+)/);
        if (simpleRec) recommendations.push(simpleRec[1].replace(/\*\*/g, ""));
      }
    }
  }

  // Disclaimer
  const disclaimerLine = lines.find(
    (l) => l.includes("Disclaimer") || l.includes("disclaimer") || l.includes("intentionally vulnerable")
  );
  const disclaimer = disclaimerLine?.replace(/^[#*\s]+/, "").replace(/\*\*/g, "").trim();

  // Dependency note
  const depNote = lines.find((l) => l.includes("npm audit") && l.includes("could not"));

  // Severity counts
  const severityCounts: Record<string, number> = {
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
  };
  findings.forEach((f) => {
    severityCounts[f.severity] = (severityCounts[f.severity] || 0) + 1;
  });

  return {
    title,
    date,
    repo,
    license,
    riskRating,
    summary,
    findings,
    recommendations,
    disclaimer,
    dependencyNote: depNote || undefined,
    severityCounts,
  };
}

const severityConfig = {
  critical: {
    color: "text-red-400",
    bg: "bg-red-500/10",
    border: "border-red-500/20",
    ringColor: "stroke-red-400",
    icon: AlertCircle,
    label: "Critical",
    gradient: "from-red-500/20 to-red-900/10",
  },
  high: {
    color: "text-orange-400",
    bg: "bg-orange-500/10",
    border: "border-orange-500/20",
    ringColor: "stroke-orange-400",
    icon: AlertTriangle,
    label: "High",
    gradient: "from-orange-500/20 to-orange-900/10",
  },
  medium: {
    color: "text-amber-400",
    bg: "bg-amber-500/10",
    border: "border-amber-500/20",
    ringColor: "stroke-amber-400",
    icon: Info,
    label: "Medium",
    gradient: "from-amber-500/20 to-amber-900/10",
  },
  low: {
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/20",
    ringColor: "stroke-emerald-400",
    icon: Shield,
    label: "Low",
    gradient: "from-emerald-500/20 to-emerald-900/10",
  },
};

function SeverityRing({
  counts,
  total,
}: {
  counts: Record<string, number>;
  total: number;
}) {
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const order: Array<"critical" | "high" | "medium" | "low"> = [
    "critical",
    "high",
    "medium",
    "low",
  ];
  const colors = {
    critical: "#ef4444",
    high: "#f97316",
    medium: "#f59e0b",
    low: "#10b981",
  };

  let offset = 0;
  const segments = order
    .filter((s) => counts[s] > 0)
    .map((s) => {
      const pct = counts[s] / total;
      const dashLength = pct * circumference;
      const seg = {
        severity: s,
        dashArray: `${dashLength} ${circumference - dashLength}`,
        dashOffset: -offset,
        color: colors[s],
      };
      offset += dashLength;
      return seg;
    });

  return (
    <svg viewBox="0 0 100 100" className="w-28 h-28">
      <circle
        cx="50"
        cy="50"
        r={radius}
        fill="none"
        stroke="rgba(255,255,255,0.04)"
        strokeWidth="8"
      />
      {segments.map((seg) => (
        <circle
          key={seg.severity}
          cx="50"
          cy="50"
          r={radius}
          fill="none"
          stroke={seg.color}
          strokeWidth="8"
          strokeDasharray={seg.dashArray}
          strokeDashoffset={seg.dashOffset}
          strokeLinecap="round"
          transform="rotate(-90 50 50)"
          className="transition-all duration-700"
          style={{
            animation: "ring-draw 0.8s cubic-bezier(0.23, 1, 0.32, 1) forwards",
          }}
        />
      ))}
      <text
        x="50"
        y="46"
        textAnchor="middle"
        className="fill-[#f1f5f9] text-2xl font-bold"
        style={{ fontSize: "22px", fontWeight: 700 }}
      >
        {total}
      </text>
      <text
        x="50"
        y="60"
        textAnchor="middle"
        className="fill-[#64748b]"
        style={{ fontSize: "8px" }}
      >
        findings
      </text>
    </svg>
  );
}

function FindingCard({
  finding,
  index,
}: {
  finding: Finding;
  index: number;
}) {
  const [expanded, setExpanded] = useState(false);
  const config = severityConfig[finding.severity];
  const Icon = config.icon;

  return (
    <div
      className={`rounded-xl border ${config.border} bg-gradient-to-br ${config.gradient} overflow-hidden transition-all duration-300`}
      style={{
        animation: `fade-slide-up 0.4s cubic-bezier(0.23, 1, 0.32, 1) ${index * 60}ms both`,
      }}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-start gap-3 text-left hover:bg-white/[0.02] transition-colors"
      >
        <div className={`mt-0.5 ${config.color}`}>
          <Icon size={16} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${config.bg} ${config.color}`}
            >
              {finding.id}
            </span>
            {finding.cwe && (
              <span className="text-[10px] font-mono text-[#64748b] px-1.5 py-0.5 rounded bg-white/5">
                {finding.cwe}
              </span>
            )}
          </div>
          <h4 className="text-sm font-medium text-[#f1f5f9] mt-1">
            {finding.title}
          </h4>
        </div>
        <div className="text-[#64748b] mt-1 shrink-0">
          {expanded ? (
            <ChevronDown size={14} />
          ) : (
            <ChevronRight size={14} />
          )}
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 border-t border-white/[0.04] space-y-3">
          {/* Impact */}
          {finding.impact && (
            <div className="mt-3">
              <span className="text-[10px] uppercase tracking-wider text-[#64748b]">
                Impact
              </span>
              <p className="text-xs text-[#94a3b8] mt-1 leading-relaxed">
                {finding.impact}
              </p>
            </div>
          )}
          {/* Files */}
          {finding.files && finding.files.length > 0 && (
            <div className="mt-3">
              <span className="text-[10px] uppercase tracking-wider text-[#64748b]">
                Affected Files
              </span>
              <div className="mt-1 space-y-0.5">
                {finding.files.map((f, i) => (
                  <div
                    key={i}
                    className="text-xs font-mono text-[#00d4ff] bg-[#00d4ff]/5 rounded px-2 py-1 inline-block mr-1 mb-1"
                  >
                    {f}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Detail */}
          {finding.detail && (
            <div>
              <span className="text-[10px] uppercase tracking-wider text-[#64748b]">
                Detail
              </span>
              <p className="text-xs text-[#94a3b8] mt-1 leading-relaxed">
                {finding.detail}
              </p>
            </div>
          )}

          {/* Evidence */}
          {finding.evidence && (
            <div>
              <span className="text-[10px] uppercase tracking-wider text-[#64748b]">
                Evidence
              </span>
              <pre className="mt-1 text-[11px] font-mono text-[#e2e8f0] bg-[#0a0a0f] rounded-lg p-3 overflow-x-auto border border-white/[0.04] leading-relaxed">
                {finding.evidence}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function ReportViewer({
  markdown,
  execution,
  onShowRaw,
}: {
  markdown: string;
  execution?: {
    elapsed_seconds: number | null;
    server_id: string | null;
    exit_code: number | null;
    metrics: Record<string, unknown> | null;
    started_at: string | null;
    completed_at: string | null;
  };
  onShowRaw: () => void;
}) {
  const report = useMemo(() => parseReport(markdown), [markdown]);
  const [copied, setCopied] = useState(false);
  const [findingsOpen, setFindingsOpen] = useState(false);
  const [recsOpen, setRecsOpen] = useState(false);

  if (!report || report.findings.length === 0) {
    return (
      <div className="space-y-3">
        <div className="rounded-xl border border-white/[0.06] bg-[#0a0a0f] p-4">
          <pre className="text-xs text-[#94a3b8] font-mono whitespace-pre-wrap leading-relaxed">
            {markdown}
          </pre>
        </div>
      </div>
    );
  }

  const total = Object.values(report.severityCounts).reduce(
    (a, b) => a + b,
    0
  );
  const maxSeverity = report.severityCounts.critical > 0
    ? "critical"
    : report.severityCounts.high > 0
      ? "high"
      : report.severityCounts.medium > 0
        ? "medium"
        : "low";
  const maxConfig = severityConfig[maxSeverity as keyof typeof severityConfig];

  const handleCopy = () => {
    navigator.clipboard.writeText(markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-4">
      <style>{`
        @keyframes fade-slide-up {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes ring-draw {
          from { stroke-dashoffset: 251; }
        }
        @keyframes count-up {
          from { opacity: 0; transform: scale(0.8); }
          to { opacity: 1; transform: scale(1); }
        }
        .line-clamp-2 {
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
      `}</style>

      {/* Report Header */}
      <div
        className={`rounded-xl border ${maxConfig.border} bg-gradient-to-r ${maxConfig.gradient} p-5`}
        style={{ animation: "fade-slide-up 0.4s cubic-bezier(0.23, 1, 0.32, 1) both" }}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <Shield size={18} className={maxConfig.color} />
              <h2 className="text-lg font-semibold text-[#f1f5f9]">
                {report.title}
              </h2>
            </div>
            <div className="flex items-center gap-3 flex-wrap text-xs text-[#94a3b8]">
              {report.date && (
                <span className="flex items-center gap-1">
                  <Clock size={11} /> {report.date}
                </span>
              )}
              {report.repo && (
                <a
                  href={report.repo}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-[#00d4ff] hover:underline"
                >
                  <ExternalLink size={11} />
                  {report.repo.replace("https://github.com/", "")}
                </a>
              )}
              {report.license && (
                <span className="px-1.5 py-0.5 rounded bg-white/5 text-[#64748b]">
                  {report.license}
                </span>
              )}
            </div>
            {report.summary && (
              <p className="text-xs text-[#94a3b8] mt-3 leading-relaxed max-w-2xl">
                {report.summary.slice(0, 300)}
                {report.summary.length > 300 ? "..." : ""}
              </p>
            )}
          </div>
          <div className="flex flex-col items-center gap-1">
            <span
              className={`text-[10px] font-bold uppercase tracking-wider ${maxConfig.color}`}
            >
              {report.riskRating}
            </span>
          </div>
        </div>
      </div>

      {/* Severity Dashboard + Execution Stats */}
      <div className="grid grid-cols-1 md:grid-cols-[auto_1fr] gap-4">
        {/* Severity Ring + Counts */}
        <div
          className="rounded-xl border border-white/[0.06] bg-[#111118] p-4 flex items-center gap-5"
          style={{ animation: "fade-slide-up 0.4s cubic-bezier(0.23, 1, 0.32, 1) 100ms both" }}
        >
          <SeverityRing counts={report.severityCounts} total={total} />
          <div className="space-y-2">
            {(["critical", "high", "medium", "low"] as const).map((sev) => {
              const c = severityConfig[sev];
              const count = report.severityCounts[sev];
              return (
                <div key={sev} className="flex items-center gap-2">
                  <div
                    className={`w-2 h-2 rounded-full`}
                    style={{
                      backgroundColor:
                        sev === "critical"
                          ? "#ef4444"
                          : sev === "high"
                            ? "#f97316"
                            : sev === "medium"
                              ? "#f59e0b"
                              : "#10b981",
                    }}
                  />
                  <span className="text-xs text-[#94a3b8] w-14">
                    {c.label}
                  </span>
                  <span
                    className={`text-sm font-bold ${count > 0 ? c.color : "text-[#334155]"}`}
                    style={{ animation: `count-up 0.3s cubic-bezier(0.23, 1, 0.32, 1) ${200 + (["critical", "high", "medium", "low"].indexOf(sev)) * 80}ms both` }}
                  >
                    {count}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Execution Stats */}
        {execution && (
          <div
            className="rounded-xl border border-white/[0.06] bg-[#111118] p-4"
            style={{ animation: "fade-slide-up 0.4s cubic-bezier(0.23, 1, 0.32, 1) 200ms both" }}
          >
            <h3 className="text-[10px] uppercase tracking-wider text-[#64748b] mb-3">
              Execution Details
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {execution.elapsed_seconds !== null && (
                <div>
                  <div className="flex items-center gap-1 text-[#64748b] mb-1">
                    <Clock size={11} />
                    <span className="text-[10px]">Duration</span>
                  </div>
                  <span className="text-sm font-bold text-[#f1f5f9]">
                    {Math.floor(execution.elapsed_seconds / 60)}m{" "}
                    {execution.elapsed_seconds % 60}s
                  </span>
                </div>
              )}
              {execution.exit_code !== null && (
                <div>
                  <div className="flex items-center gap-1 text-[#64748b] mb-1">
                    {execution.exit_code === 0 ? (
                      <CheckCircle size={11} className="text-emerald-400" />
                    ) : (
                      <AlertCircle size={11} className="text-red-400" />
                    )}
                    <span className="text-[10px]">Exit Code</span>
                  </div>
                  <span
                    className={`text-sm font-bold ${execution.exit_code === 0 ? "text-emerald-400" : "text-red-400"}`}
                  >
                    {execution.exit_code}
                  </span>
                </div>
              )}
              {execution.server_id && (
                <div>
                  <div className="flex items-center gap-1 text-[#64748b] mb-1">
                    <Server size={11} />
                    <span className="text-[10px]">Server</span>
                  </div>
                  <span className="text-sm font-mono text-[#94a3b8]">
                    {execution.server_id}
                  </span>
                </div>
              )}
              {execution.metrics &&
                typeof (execution.metrics as Record<string, string>).model === "string" && (
                  <div>
                    <div className="flex items-center gap-1 text-[#64748b] mb-1">
                      <Cpu size={11} />
                      <span className="text-[10px]">Model</span>
                    </div>
                    <span className="text-xs text-[#94a3b8]">
                      {((execution.metrics as Record<string, string>).model)
                        .replace("anthropic/", "")
                        .replace("claude-", "Claude ")}
                    </span>
                  </div>
                )}
              {execution.metrics &&
                (execution.metrics as Record<string, number>).output_bytes >
                  0 && (
                  <div>
                    <div className="flex items-center gap-1 text-[#64748b] mb-1">
                      <FileText size={11} />
                      <span className="text-[10px]">Output</span>
                    </div>
                    <span className="text-sm text-[#94a3b8]">
                      {(
                        (execution.metrics as Record<string, number>)
                          .output_bytes / 1024
                      ).toFixed(1)}{" "}
                      KB
                    </span>
                  </div>
                )}
              {execution.metrics &&
                (execution.metrics as Record<string, number>)
                  .output_tokens_est > 0 && (
                  <div>
                    <div className="flex items-center gap-1 text-[#64748b] mb-1">
                      <Zap size={11} />
                      <span className="text-[10px]">Tokens</span>
                    </div>
                    <span className="text-sm text-[#94a3b8]">
                      ~
                      {(
                        execution.metrics as Record<string, number>
                      ).output_tokens_est.toLocaleString()}
                    </span>
                  </div>
                )}
            </div>
          </div>
        )}
      </div>

      {/* Findings */}
      <div
        className="rounded-xl border border-white/[0.06] overflow-hidden"
        style={{ animation: "fade-slide-up 0.4s cubic-bezier(0.23, 1, 0.32, 1) 300ms both" }}
      >
        <button
          onClick={() => setFindingsOpen(!findingsOpen)}
          className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/[0.02] transition-colors"
        >
          <h3 className="text-xs font-medium text-[#64748b] uppercase tracking-wider flex items-center gap-2">
            {findingsOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            Findings ({total})
          </h3>
          <div className="flex items-center gap-2">
            <button
              onClick={(e) => { e.stopPropagation(); handleCopy(); }}
              className="flex items-center gap-1 text-[10px] text-[#64748b] hover:text-[#94a3b8] transition-colors px-2 py-1 rounded bg-white/5"
            >
              {copied ? (
                <>
                  <Check size={10} className="text-emerald-400" /> Copied
                </>
              ) : (
                <>
                  <Copy size={10} /> Copy Markdown
                </>
              )}
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); onShowRaw(); }}
              className="flex items-center gap-1 text-[10px] text-[#64748b] hover:text-[#94a3b8] transition-colors px-2 py-1 rounded bg-white/5"
            >
              <FileText size={10} /> Raw
            </button>
          </div>
        </button>
        {findingsOpen && (
          <div className="px-4 pb-4 space-y-2">
            {report.findings.map((f, i) => (
              <FindingCard key={f.id + i} finding={f} index={i} />
            ))}
          </div>
        )}
      </div>

      {/* Recommendations */}
      {report.recommendations.length > 0 && (
        <div
          className="rounded-xl border border-white/[0.06] bg-[#111118] overflow-hidden"
          style={{
            animation: `fade-slide-up 0.4s cubic-bezier(0.23, 1, 0.32, 1) ${400 + report.findings.length * 30}ms both`,
          }}
        >
          <button
            onClick={() => setRecsOpen(!recsOpen)}
            className="w-full flex items-center gap-2 px-5 py-3 hover:bg-white/[0.02] transition-colors text-left"
          >
            {recsOpen ? <ChevronDown size={12} className="text-[#64748b]" /> : <ChevronRight size={12} className="text-[#64748b]" />}
            <h3 className="text-xs font-medium text-[#64748b] uppercase tracking-wider">
              Recommendations ({report.recommendations.length})
            </h3>
          </button>
          {recsOpen && (
            <div className="px-5 pb-4 space-y-2">
              {report.recommendations.map((rec, i) => (
                <div
                  key={i}
                  className="flex items-start gap-2 text-xs"
                >
                  <span className="text-[#00d4ff] font-mono font-bold shrink-0 mt-0.5 w-4 text-right">
                    {i + 1}.
                  </span>
                  <span className="text-[#94a3b8] leading-relaxed">
                    {rec}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Disclaimer */}
      {report.disclaimer && (
        <div className="rounded-xl border border-amber-500/10 bg-amber-500/5 px-4 py-3">
          <p className="text-[11px] text-amber-200/70 leading-relaxed italic">
            {report.disclaimer}
          </p>
        </div>
      )}
    </div>
  );
}
