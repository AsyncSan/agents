import { useState } from "react";
import {
  Copy,
  Check,
  ChevronRight,
  Book,
  AlertTriangle,
  CheckCircle,
  Info,
} from "lucide-react";
import { useT } from "../../i18n";

export function DEEnglishOnlyNotice() {
  const { lang } = useT();
  if (lang !== "de") return null;
  return (
    <div className="rounded-xl border border-amber-500/10 bg-amber-500/5 p-4 mb-6">
      <p className="text-xs text-amber-200/90 leading-relaxed">
        <strong className="text-amber-300">Noch keine Übersetzung.</strong>{" "}
        Diese Seite liegt aktuell nur auf Englisch vor. Die praktischen Assistenten
        sind komplett auf Deutsch: <a href="/fria" className="underline hover:text-amber-100">FRIA</a>,{" "}
        <a href="/annex-iv" className="underline hover:text-amber-100">Annex IV</a>,{" "}
        <a href="/pmm" className="underline hover:text-amber-100">PMM-Plan</a>,{" "}
        <a href="/qms" className="underline hover:text-amber-100">QMS-Handbuch</a>,{" "}
        <a href="/eu-db" className="underline hover:text-amber-100">EU-DB-Registrierung</a>,{" "}
        <a href="/data-governance" className="underline hover:text-amber-100">Data Governance</a>,{" "}
        <a href="/literacy" className="underline hover:text-amber-100">AI Literacy</a>.
      </p>
    </div>
  );
}

/* ── Code Block ─────────────────────────────────────────── */

export function CodeBlock({
  code,
  language = "bash",
  title,
}: {
  code: string;
  language?: string;
  title?: string;
}) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <div className="relative group rounded-lg bg-[#0a0a0f] border border-white/[0.06] overflow-hidden my-4">
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/[0.04] bg-white/[0.01]">
        <span className="text-[11px] font-mono text-[#64748b]">
          {title || language}
        </span>
        <button
          onClick={handleCopy}
          className="text-[#64748b] hover:text-[#94a3b8] transition-colors p-1 rounded hover:bg-white/[0.04]"
        >
          {copied ? (
            <Check size={13} className="text-emerald-400" />
          ) : (
            <Copy size={13} />
          )}
        </button>
      </div>
      <pre className="px-4 py-3 text-[13px] font-mono text-[#e2e8f0] overflow-x-auto leading-relaxed">
        {code}
      </pre>
    </div>
  );
}

/* ── Info / Warning / Success Box ───────────────────────── */

export function Callout({
  type = "info",
  title,
  children,
}: {
  type?: "info" | "warning" | "success";
  title?: string;
  children: React.ReactNode;
}) {
  const styles = {
    info: {
      border: "border-blue-500/20",
      bg: "bg-blue-500/[0.04]",
      text: "text-blue-200/90",
      icon: <Info size={15} className="text-blue-400" />,
      defaultTitle: "Note",
    },
    warning: {
      border: "border-amber-500/20",
      bg: "bg-amber-500/[0.04]",
      text: "text-amber-200/90",
      icon: <AlertTriangle size={15} className="text-amber-400" />,
      defaultTitle: "Warning",
    },
    success: {
      border: "border-emerald-500/20",
      bg: "bg-emerald-500/[0.04]",
      text: "text-emerald-200/90",
      icon: <CheckCircle size={15} className="text-emerald-400" />,
      defaultTitle: "Tip",
    },
  };
  const s = styles[type];
  return (
    <div
      className={`rounded-lg border ${s.border} ${s.bg} px-4 py-3 my-4`}
    >
      <div className="flex items-center gap-2 mb-1.5">
        {s.icon}
        <span className={`text-xs font-semibold ${s.text}`}>
          {title || s.defaultTitle}
        </span>
      </div>
      <div className={`text-sm leading-relaxed ${s.text} pl-[23px]`}>
        {children}
      </div>
    </div>
  );
}

/* ── API Endpoint ───────────────────────────────────────── */

export function Endpoint({
  method,
  path,
  description,
  auth,
  scope,
  body,
  response,
}: {
  method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  path: string;
  description: string;
  auth?: boolean;
  scope?: string;
  body?: string;
  response?: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const methodColors: Record<string, string> = {
    GET: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    POST: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    PUT: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    PATCH: "bg-orange-500/10 text-orange-400 border-orange-500/20",
    DELETE: "bg-red-500/10 text-red-400 border-red-500/20",
  };

  return (
    <div className="rounded-lg border border-white/[0.06] overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-white/[0.02] transition-colors text-left"
      >
        <span
          className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${methodColors[method]}`}
        >
          {method}
        </span>
        <code className="text-xs font-mono text-[#00d4ff] flex-1 truncate">
          {path}
        </code>
        {auth && (
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 shrink-0">
            {scope || "auth"}
          </span>
        )}
        <ChevronRight
          size={12}
          className={`text-[#64748b] transition-transform duration-200 shrink-0 ${expanded ? "rotate-90" : ""}`}
        />
      </button>
      {expanded && (
        <div className="px-4 pb-4 border-t border-white/[0.04] space-y-3 pt-3">
          <p className="text-sm text-[#94a3b8]">{description}</p>
          {body && (
            <div>
              <span className="text-[10px] uppercase tracking-wider text-[#64748b] font-medium">
                Request Body
              </span>
              <CodeBlock code={body} language="json" />
            </div>
          )}
          {response && (
            <div>
              <span className="text-[10px] uppercase tracking-wider text-[#64748b] font-medium">
                Response
              </span>
              <CodeBlock code={response} language="json" />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Table ──────────────────────────────────────────────── */

export function DocTable({
  headers,
  rows,
}: {
  headers: string[];
  rows: (string | React.ReactNode)[][];
}) {
  return (
    <div className="rounded-lg border border-white/[0.06] overflow-hidden my-4 overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-white/[0.06] bg-white/[0.02]">
            {headers.map((h, i) => (
              <th
                key={i}
                className="text-left px-4 py-2.5 text-[#64748b] font-medium text-xs"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="text-[#94a3b8] text-sm">
          {rows.map((row, i) => (
            <tr
              key={i}
              className={
                i < rows.length - 1 ? "border-b border-white/[0.04]" : ""
              }
            >
              {row.map((cell, j) => (
                <td key={j} className="px-4 py-2.5">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ── Typography helpers ─────────────────────────────────── */

export function H1({ children }: { children: React.ReactNode }) {
  return (
    <h1 className="text-2xl font-bold text-[#f1f5f9] mb-2">{children}</h1>
  );
}

export function H2({
  children,
  id,
}: {
  children: React.ReactNode;
  id?: string;
}) {
  return (
    <h2
      id={id}
      className="text-lg font-semibold text-[#f1f5f9] mt-10 mb-3 pb-2 border-b border-white/[0.06] scroll-mt-24"
    >
      {children}
    </h2>
  );
}

export function H3({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-sm font-semibold text-[#e2e8f0] mt-6 mb-2">
      {children}
    </h3>
  );
}

export function P({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-sm text-[#94a3b8] leading-relaxed mb-3">{children}</p>
  );
}

export function Lead({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[15px] text-[#b0bec5] leading-relaxed mb-6">
      {children}
    </p>
  );
}

export function InlineCode({ children }: { children: React.ReactNode }) {
  return (
    <code className="text-[13px] font-mono text-[#00d4ff] bg-[#00d4ff]/[0.06] px-1.5 py-0.5 rounded border border-[#00d4ff]/10">
      {children}
    </code>
  );
}

export function StepList({
  steps,
}: {
  steps: { title: string; detail: string }[];
}) {
  return (
    <div className="space-y-3 my-4">
      {steps.map((s, i) => (
        <div key={i} className="flex items-start gap-3">
          <span className="flex items-center justify-center w-6 h-6 rounded-full bg-[#00d4ff]/10 text-[#00d4ff] text-xs font-bold shrink-0 mt-0.5">
            {i + 1}
          </span>
          <div>
            <span className="text-sm font-medium text-[#e2e8f0]">
              {s.title}
            </span>
            <p className="text-sm text-[#64748b] mt-0.5">{s.detail}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

export function Badge({
  children,
  color = "cyan",
}: {
  children: React.ReactNode;
  color?: "cyan" | "emerald" | "amber" | "red" | "purple" | "blue" | "gray";
}) {
  const colors: Record<string, string> = {
    cyan: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
    emerald: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    amber: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    red: "bg-red-500/10 text-red-400 border-red-500/20",
    purple: "bg-purple-500/10 text-purple-400 border-purple-500/20",
    blue: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    gray: "bg-gray-500/10 text-gray-400 border-gray-500/20",
  };
  return (
    <span
      className={`text-[11px] font-mono font-medium px-2 py-0.5 rounded border ${colors[color]}`}
    >
      {children}
    </span>
  );
}
