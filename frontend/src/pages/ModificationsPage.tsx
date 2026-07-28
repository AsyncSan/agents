import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Download,
  FileCheck,
  GitBranch,
  History,
  Loader2,
  Plus,
} from "lucide-react";
import { listAgents, type Agent } from "../api";

const MOD_TYPES = [
  "version_bump",
  "card_update",
  "training_data",
  "intended_purpose",
  "oversight_measure",
  "security_control",
  "other",
] as const;

const CLASSIFICATIONS = ["unclassified", "substantial", "non_substantial"] as const;

type ModType = (typeof MOD_TYPES)[number];
type Classification = (typeof CLASSIFICATIONS)[number];

interface ModificationRecord {
  id: string;
  agent_id: string;
  version_from: number | null;
  version_to: number | null;
  modification_type: ModType;
  classification: Classification;
  summary: string;
  rationale: string | null;
  triggered_reassessment: boolean;
  reassessment_at: string | null;
  diff: Record<string, { old: unknown; new: unknown }> | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

const CLASSIFICATION_STYLE: Record<Classification, string> = {
  substantial: "bg-red-500/10 text-red-300 border-red-500/20",
  non_substantial: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20",
  unclassified: "bg-amber-500/10 text-amber-300 border-amber-500/20",
};

const CLASSIFICATION_ICON: Record<Classification, typeof AlertTriangle> = {
  substantial: AlertTriangle,
  non_substantial: CheckCircle2,
  unclassified: Clock,
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

export function ModificationsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const apiKey = typeof window !== "undefined" ? localStorage.getItem("af_api_key") : null;

  const [agents, setAgents] = useState<Agent[]>([]);
  const [agentId, setAgentId] = useState<string>(searchParams.get("agent_id") || "");
  const [records, setRecords] = useState<ModificationRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | Classification>("all");
  const [detail, setDetail] = useState<ModificationRecord | null>(null);
  const [newOpen, setNewOpen] = useState(false);

  useEffect(() => {
    listAgents().then((d) => setAgents(d.agents)).catch(() => setAgents([]));
  }, []);

  const refresh = useCallback(async () => {
    if (!apiKey || !agentId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `/v1/modifications?agent_id=${encodeURIComponent(agentId)}`,
        { headers: { "X-API-Key": apiKey } },
      );
      if (!res.ok) throw new Error(`Failed to load modifications (${res.status})`);
      setRecords(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Load failed");
    } finally {
      setLoading(false);
    }
  }, [apiKey, agentId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const filtered = useMemo(() => {
    if (filter === "all") return records;
    return records.filter((r) => r.classification === filter);
  }, [records, filter]);

  const stats = useMemo(() => {
    const s = { substantial: 0, non_substantial: 0, unclassified: 0 };
    for (const r of records) s[r.classification] += 1;
    return s;
  }, [records]);

  const selectAgent = (id: string) => {
    setAgentId(id);
    const next = new URLSearchParams(searchParams);
    if (id) next.set("agent_id", id); else next.delete("agent_id");
    setSearchParams(next, { replace: true });
  };

  const downloadMarkdown = async () => {
    if (!apiKey || !agentId) return;
    try {
      const res = await fetch(`/v1/modifications/export/markdown/${agentId}`, {
        headers: { "X-API-Key": apiKey },
      });
      if (!res.ok) throw new Error("Markdown export failed");
      downloadBlob(`modifications-${agentId}.md`, await res.text(), "text/markdown");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed");
    }
  };

  const downloadPDF = async () => {
    if (!apiKey || !agentId) return;
    try {
      const res = await fetch(`/v1/modifications/export/pdf/${agentId}`, {
        headers: { "X-API-Key": apiKey },
      });
      if (!res.ok) throw new Error("PDF export failed");
      downloadBlob(`modifications-${agentId}.pdf`, await res.blob());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed");
    }
  };

  const patchClassification = async (id: string, classification: Classification) => {
    if (!apiKey) return;
    const res = await fetch(`/v1/modifications/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
      body: JSON.stringify({ classification }),
    });
    if (!res.ok) {
      setError("Classification update failed");
      return;
    }
    const updated = await res.json();
    setRecords((prev) => prev.map((r) => (r.id === id ? updated : r)));
    if (detail?.id === id) setDetail(updated);
  };

  const markReassessed = async (id: string) => {
    if (!apiKey) return;
    const res = await fetch(`/v1/modifications/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
      body: JSON.stringify({
        triggered_reassessment: true,
        reassessment_at: new Date().toISOString(),
      }),
    });
    if (!res.ok) {
      setError("Mark as reassessed failed");
      return;
    }
    const updated = await res.json();
    setRecords((prev) => prev.map((r) => (r.id === id ? updated : r)));
    if (detail?.id === id) setDetail(updated);
  };

  return (
    <>
      <section className="relative mb-10 pt-8">
        <div className="absolute inset-0 -z-10 overflow-hidden">
          <div
            className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] rounded-full opacity-[0.03]"
            style={{ background: "radial-gradient(circle, #f472b6 0%, transparent 60%)" }}
          />
        </div>
        <div className="text-center max-w-2xl mx-auto">
          <p className="text-xs text-[#64748b] mb-3 font-medium uppercase tracking-widest">
            EU AI Act Art. 43 · Annex IV point 6
          </p>
          <h1 className="text-3xl sm:text-4xl font-semibold text-[#f1f5f9] mb-4 leading-[1.15] tracking-tight">
            Substantial modification<br />
            <span className="text-[#f472b6]">tracking.</span>
          </h1>
          <p className="text-[15px] text-[#94a3b8] leading-relaxed max-w-lg mx-auto">
            Every version bump is logged with an auto-classifier suggestion.
            Substantial modifications trigger a fresh conformity assessment.
            Non-substantial changes stay on the audit trail.
          </p>
        </div>
      </section>

      <div className="flex flex-wrap items-center gap-3 mb-6">
        <label className="flex items-center gap-2">
          <span className="text-xs text-[#64748b]">Agent</span>
          <select
            value={agentId}
            onChange={(e) => selectAgent(e.target.value)}
            className="px-3 py-2 rounded-lg bg-[#0a0a0f] border border-white/[0.06] text-sm text-[#f1f5f9] focus:outline-none focus:border-[#f472b6]/30"
          >
            <option value="">— select agent —</option>
            {agents.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name} · v{(a as unknown as { version?: number }).version || "?"}
              </option>
            ))}
          </select>
        </label>
        {agentId && (
          <>
            <button
              onClick={downloadMarkdown}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-white/[0.08] text-xs text-[#94a3b8] hover:text-[#f1f5f9] transition-colors"
            >
              <FileCheck size={12} />
              Markdown
            </button>
            <button
              onClick={downloadPDF}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-white/[0.08] text-xs text-[#94a3b8] hover:text-[#f1f5f9] transition-colors"
            >
              <Download size={12} />
              PDF addendum
            </button>
            <button
              onClick={() => setNewOpen(true)}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-[#f472b6] text-[#0a0a0f] text-xs font-medium hover:bg-[#f472b6]/90 transition-colors"
            >
              <Plus size={12} />
              Log manual change
            </button>
          </>
        )}
      </div>

      {agentId && (
        <>
          <div className="grid grid-cols-3 gap-3 mb-6">
            <Stat
              label="Substantial"
              value={stats.substantial}
              accent="text-red-300"
              icon={AlertTriangle}
            />
            <Stat
              label="Unclassified"
              value={stats.unclassified}
              accent="text-amber-300"
              icon={Clock}
            />
            <Stat
              label="Non-substantial"
              value={stats.non_substantial}
              accent="text-emerald-300"
              icon={CheckCircle2}
            />
          </div>

          <div className="flex gap-2 mb-4">
            {(["all", "substantial", "unclassified", "non_substantial"] as const).map(
              (f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`px-3 py-1.5 rounded-lg text-xs transition-colors ${
                    filter === f
                      ? "bg-white/[0.08] text-[#f1f5f9]"
                      : "text-[#64748b] hover:text-[#94a3b8]"
                  }`}
                >
                  {f === "all" ? "All" : f.replace("_", " ")}
                </button>
              ),
            )}
          </div>

          {error && (
            <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 flex items-start gap-2 mb-4">
              <AlertCircle size={14} className="text-red-400 shrink-0 mt-0.5" />
              <p className="text-xs text-red-300">{error}</p>
            </div>
          )}

          {loading ? (
            <div className="flex items-center gap-2 text-xs text-[#64748b] p-6 justify-center">
              <Loader2 size={14} className="animate-spin" />
              Loading modification records…
            </div>
          ) : filtered.length === 0 ? (
            <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-8 text-center">
              <History size={24} className="text-[#64748b] mx-auto mb-3" />
              <p className="text-sm text-[#94a3b8] mb-1">No modifications recorded yet.</p>
              <p className="text-xs text-[#64748b]">
                Version bumps via <code>PUT /agents/:id</code> are logged
                automatically. Manual changes can be added with the button above.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {filtered.map((r) => {
                const Icon = CLASSIFICATION_ICON[r.classification];
                return (
                  <button
                    key={r.id}
                    onClick={() => setDetail(r)}
                    className="w-full text-left rounded-xl border border-white/[0.06] bg-[#111118] p-4 hover:border-white/[0.12] transition-colors"
                  >
                    <div className="flex items-start gap-3">
                      <Icon
                        size={14}
                        className={`shrink-0 mt-0.5 ${
                          r.classification === "substantial"
                            ? "text-red-300"
                            : r.classification === "non_substantial"
                            ? "text-emerald-300"
                            : "text-amber-300"
                        }`}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap mb-1">
                          <span
                            className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded border ${CLASSIFICATION_STYLE[r.classification]}`}
                          >
                            {r.classification}
                          </span>
                          <span className="text-[10px] text-[#64748b] uppercase tracking-wider">
                            {r.modification_type.replace("_", " ")}
                          </span>
                          {r.version_from !== null && r.version_to !== null && (
                            <span className="text-[10px] text-[#64748b] flex items-center gap-1">
                              <GitBranch size={10} />
                              v{r.version_from} → v{r.version_to}
                            </span>
                          )}
                          {r.triggered_reassessment && (
                            <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded border bg-indigo-500/10 text-indigo-300 border-indigo-500/20">
                              reassessed
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-[#e2e8f0] mb-1">{r.summary}</p>
                        <p className="text-xs text-[#64748b]">
                          {new Date(r.created_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </>
      )}

      {!agentId && (
        <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-8 text-center">
          <History size={28} className="text-[#64748b] mx-auto mb-3" />
          <p className="text-sm text-[#94a3b8]">
            Select an agent above to view its modification log.
          </p>
        </div>
      )}

      {detail && (
        <DetailModal
          record={detail}
          onClose={() => setDetail(null)}
          onClassify={(cls) => patchClassification(detail.id, cls)}
          onMarkReassessed={() => markReassessed(detail.id)}
        />
      )}

      {newOpen && agentId && (
        <NewModificationModal
          agentId={agentId}
          apiKey={apiKey}
          onClose={() => setNewOpen(false)}
          onCreated={() => {
            setNewOpen(false);
            refresh();
          }}
        />
      )}
    </>
  );
}

function Stat({
  label,
  value,
  accent,
  icon: Icon,
}: {
  label: string;
  value: number;
  accent: string;
  icon: typeof AlertTriangle;
}) {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-4 flex items-center gap-3">
      <Icon size={20} className={accent} />
      <div>
        <p className="text-xs text-[#64748b] uppercase tracking-wider">{label}</p>
        <p className="text-2xl font-semibold text-[#f1f5f9]">{value}</p>
      </div>
    </div>
  );
}

function DetailModal({
  record,
  onClose,
  onClassify,
  onMarkReassessed,
}: {
  record: ModificationRecord;
  onClose: () => void;
  onClassify: (cls: Classification) => void;
  onMarkReassessed: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-xl border border-white/[0.08] bg-[#0a0a0f] p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 mb-5">
          <div>
            <p className="text-xs text-[#64748b] uppercase tracking-wider mb-1">
              {record.modification_type.replace("_", " ")}
            </p>
            <h2 className="text-xl font-semibold text-[#f1f5f9]">{record.summary}</h2>
          </div>
          <span
            className={`text-xs uppercase tracking-wider px-2 py-1 rounded border ${CLASSIFICATION_STYLE[record.classification]}`}
          >
            {record.classification}
          </span>
        </div>

        <div className="space-y-3 mb-5 text-xs">
          <Row
            k="Version"
            v={
              record.version_from !== null && record.version_to !== null
                ? `v${record.version_from} → v${record.version_to}`
                : "-"
            }
          />
          <Row k="Created" v={new Date(record.created_at).toLocaleString()} />
          <Row
            k="Reassessment"
            v={
              record.triggered_reassessment
                ? `Yes${record.reassessment_at ? ` · ${new Date(record.reassessment_at).toLocaleString()}` : ""}`
                : "No"
            }
          />
          {record.rationale && <Row k="Rationale" v={record.rationale} />}
        </div>

        {record.diff && Object.keys(record.diff).length > 0 && (
          <div className="mb-5">
            <h3 className="text-xs font-medium text-[#64748b] uppercase tracking-wider mb-2">
              Diff ({Object.keys(record.diff).length} fields)
            </h3>
            <div className="rounded-lg border border-white/[0.06] bg-[#111118] max-h-64 overflow-y-auto">
              <table className="w-full text-xs">
                <thead className="text-[#64748b] text-left">
                  <tr>
                    <th className="p-2 border-b border-white/[0.06]">Field</th>
                    <th className="p-2 border-b border-white/[0.06]">Old</th>
                    <th className="p-2 border-b border-white/[0.06]">New</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(record.diff).map(([key, val]) => (
                    <tr key={key} className="border-t border-white/[0.04]">
                      <td className="p-2 font-mono text-[#94a3b8]">{key}</td>
                      <td className="p-2 text-red-300/80 break-all max-w-[200px]">
                        {JSON.stringify(val.old)}
                      </td>
                      <td className="p-2 text-emerald-300/80 break-all max-w-[200px]">
                        {JSON.stringify(val.new)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        <div className="flex flex-wrap gap-2">
          {CLASSIFICATIONS.filter((c) => c !== record.classification).map((c) => (
            <button
              key={c}
              onClick={() => onClassify(c)}
              className="px-3 py-2 rounded-lg border border-white/[0.08] text-xs text-[#94a3b8] hover:text-[#f1f5f9] transition-colors"
            >
              Classify as {c.replace("_", " ")}
            </button>
          ))}
          {!record.triggered_reassessment && record.classification === "substantial" && (
            <button
              onClick={onMarkReassessed}
              className="px-3 py-2 rounded-lg border border-indigo-500/20 bg-indigo-500/5 text-indigo-300 hover:bg-indigo-500/10 text-xs transition-colors"
            >
              Mark conformity reassessment complete
            </button>
          )}
          <button
            onClick={onClose}
            className="px-3 py-2 rounded-lg border border-white/[0.08] text-xs text-[#64748b] hover:text-[#f1f5f9] transition-colors ml-auto"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

function NewModificationModal({
  agentId,
  apiKey,
  onClose,
  onCreated,
}: {
  agentId: string;
  apiKey: string | null;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [type, setType] = useState<ModType>("training_data");
  const [classification, setClassification] = useState<Classification>("unclassified");
  const [summary, setSummary] = useState("");
  const [rationale, setRationale] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const submit = async () => {
    if (!apiKey) return;
    if (!summary.trim()) {
      setErr("Summary is required.");
      return;
    }
    setBusy(true);
    setErr(null);
    try {
      const res = await fetch("/v1/modifications", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
        body: JSON.stringify({
          agent_id: agentId,
          modification_type: type,
          classification,
          summary,
          rationale: rationale || undefined,
        }),
      });
      if (!res.ok) throw new Error(`Create failed (${res.status})`);
      onCreated();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Create failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-xl border border-white/[0.08] bg-[#0a0a0f] p-6 space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold text-[#f1f5f9]">
          Log a manual modification
        </h2>

        <label className="block">
          <span className="block text-xs text-[#64748b] mb-1.5">Type</span>
          <select
            value={type}
            onChange={(e) => setType(e.target.value as ModType)}
            className="w-full px-3 py-2 rounded-lg bg-[#111118] border border-white/[0.06] text-sm text-[#f1f5f9]"
          >
            {MOD_TYPES.filter((t) => t !== "version_bump" && t !== "card_update").map(
              (t) => (
                <option key={t} value={t}>
                  {t.replace("_", " ")}
                </option>
              ),
            )}
          </select>
        </label>

        <label className="block">
          <span className="block text-xs text-[#64748b] mb-1.5">Classification</span>
          <select
            value={classification}
            onChange={(e) => setClassification(e.target.value as Classification)}
            className="w-full px-3 py-2 rounded-lg bg-[#111118] border border-white/[0.06] text-sm text-[#f1f5f9]"
          >
            {CLASSIFICATIONS.map((c) => (
              <option key={c} value={c}>
                {c.replace("_", " ")}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="block text-xs text-[#64748b] mb-1.5">Summary</span>
          <input
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
            placeholder="One-line description of what changed"
            className="w-full px-3 py-2 rounded-lg bg-[#111118] border border-white/[0.06] text-sm text-[#f1f5f9] placeholder-[#64748b]"
          />
        </label>

        <label className="block">
          <span className="block text-xs text-[#64748b] mb-1.5">Rationale</span>
          <textarea
            rows={3}
            value={rationale}
            onChange={(e) => setRationale(e.target.value)}
            placeholder="Why the change was made and why it is or isn't substantial"
            className="w-full px-3 py-2 rounded-lg bg-[#111118] border border-white/[0.06] text-sm text-[#f1f5f9] placeholder-[#64748b]"
          />
        </label>

        {err && (
          <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 flex items-start gap-2">
            <AlertCircle size={14} className="text-red-400 shrink-0 mt-0.5" />
            <p className="text-xs text-red-300">{err}</p>
          </div>
        )}

        <div className="flex gap-2 justify-end">
          <button
            onClick={onClose}
            className="px-3 py-2 rounded-lg border border-white/[0.08] text-xs text-[#64748b] hover:text-[#f1f5f9] transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={busy}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-[#f472b6] text-[#0a0a0f] text-xs font-medium disabled:opacity-40"
          >
            {busy ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />}
            Create record
          </button>
        </div>
      </div>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-3 border-b border-white/[0.04] pb-2">
      <dt className="text-[#64748b]">{k}</dt>
      <dd className="text-[#e2e8f0] text-right max-w-md">{v}</dd>
    </div>
  );
}
