import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertCircle,
  Database,
  Download,
  FileCheck,
  Layers,
  Loader2,
  Save,
  ShieldAlert,
  X,
} from "lucide-react";
import { listAgents, type Agent } from "../api";
import { createComplianceDocument } from "../compliance-api";

interface InventoryResponse {
  schema_version: string;
  regulation: string;
  generated_at: string;
  agent_count: number;
  total_executions_observed: number;
  by_domain: Record<string, number>;
  by_risk_class: Record<string, number>;
  input_type_distribution: Record<string, number>;
  output_type_distribution: Record<string, number>;
  tool_distribution: Record<string, number>;
  model_distribution: Record<string, number>;
  platform_controls: string[];
}

interface AgentSheetDetail extends Record<string, unknown> {
  agent: { id: string; name: string; version: number; risk_class: string };
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

export function DataGovernancePage() {
  const apiKey = typeof window !== "undefined" ? localStorage.getItem("af_api_key") : null;

  const [inventory, setInventory] = useState<InventoryResponse | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [sheet, setSheet] = useState<AgentSheetDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [savedId, setSavedId] = useState<string | null>(null);

  useEffect(() => {
    if (!apiKey) {
      setLoading(false);
      return;
    }
    Promise.all([
      fetch("/v1/data-governance/inventory", {
        headers: { "X-API-Key": apiKey },
      }).then((r) => {
        if (!r.ok) throw new Error("Failed to load inventory");
        return r.json();
      }),
      listAgents(),
    ])
      .then(([inv, list]) => {
        setInventory(inv);
        setAgents(list.agents);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Load failed"))
      .finally(() => setLoading(false));
  }, [apiKey]);

  const handleGenerate = async (agentId: string) => {
    if (!apiKey) return;
    setSelectedAgentId(agentId);
    setSavedId(null);
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/v1/data-governance/agent-sheet", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
        body: JSON.stringify({ agent_id: agentId }),
      });
      if (!res.ok) throw new Error("Failed to generate sheet");
      setSheet(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setBusy(false);
    }
  };

  const handleDownload = async (format: "json" | "md" | "pdf") => {
    if (!apiKey || !selectedAgentId || !sheet) return;
    try {
      if (format === "json") {
        downloadBlob(
          `data-sheet-${selectedAgentId}.json`,
          JSON.stringify(sheet, null, 2),
          "application/json",
        );
        return;
      }
      const res = await fetch(`/v1/data-governance/agent-sheet/${format === "md" ? "markdown" : "pdf"}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
        body: JSON.stringify({ agent_id: selectedAgentId }),
      });
      if (!res.ok) throw new Error(`${format.toUpperCase()} export failed`);
      if (format === "md") {
        downloadBlob(`data-sheet-${selectedAgentId}.md`, await res.text(), "text/markdown");
      } else {
        downloadBlob(`data-sheet-${selectedAgentId}.pdf`, await res.blob());
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Download failed");
    }
  };

  const handleSave = async () => {
    if (!apiKey || !selectedAgentId || !sheet) return;
    setBusy(true);
    try {
      const title = `Data sheet · ${selectedAgentId}`;
      const agent = agents.find((a) => a.id === selectedAgentId);
      const doc = await createComplianceDocument(apiKey, {
        doc_type: "annex_iv", // data sheet rolls up into Annex IV Section F
        title,
        payload: sheet as Record<string, unknown>,
        agent_id: selectedAgentId,
        agent_version: agent
          ? (agent as unknown as { version?: number }).version ?? null
          : undefined,
      });
      setSavedId(doc.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  };

  const topDomains = useMemo(() => {
    if (!inventory) return [];
    return Object.entries(inventory.by_domain)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6);
  }, [inventory]);

  if (!apiKey) {
    return (
      <div className="max-w-xl mx-auto py-16 text-center">
        <Database size={40} className="text-[#00d4ff] mx-auto mb-4" />
        <h1 className="text-2xl font-semibold text-[#f1f5f9] mb-2">Data governance</h1>
        <p className="text-sm text-[#94a3b8] mb-6">
          Log in to see the organisation inventory and generate per-agent data
          sheets under EU AI Act Art. 10.
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
    <>
      <section className="mb-8 pt-6">
        <div className="mb-6">
          <p className="text-xs text-[#64748b] mb-1 font-medium uppercase tracking-widest">
            EU AI Act Art. 10
          </p>
          <h1 className="text-2xl font-semibold text-[#f1f5f9]">Data governance</h1>
          <p className="text-xs text-[#94a3b8] mt-1 max-w-2xl">
            Inventory of what flows through the agents under your organisation and
            the data sheet artefact per agent. The foundation-model providers cover
            Art. 10 for the model weights; this view covers the deployer data surface.
          </p>
        </div>

        {error && (
          <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 flex items-start gap-2 mb-4">
            <AlertCircle size={14} className="text-red-400 shrink-0 mt-0.5" />
            <p className="text-xs text-red-300">{error}</p>
          </div>
        )}

        {loading ? (
          <p className="text-center text-sm text-[#64748b] py-10">Loading…</p>
        ) : !inventory ? (
          <p className="text-center text-sm text-[#64748b] py-10">No inventory available.</p>
        ) : (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
              <Stat label="Agents in scope" value={inventory.agent_count} />
              <Stat label="Total executions" value={inventory.total_executions_observed} />
              <Stat
                label="High-risk agents"
                value={inventory.by_risk_class["high"] || 0}
                tone={inventory.by_risk_class["high"] ? "amber" : "neutral"}
              />
              <Stat label="Models in use" value={Object.keys(inventory.model_distribution).length} />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
              <DistributionCard
                title="Agents by domain"
                icon={<Layers size={14} className="text-[#00d4ff]" />}
                rows={topDomains}
              />
              <DistributionCard
                title="Agents by risk class"
                icon={<ShieldAlert size={14} className="text-[#00d4ff]" />}
                rows={Object.entries(inventory.by_risk_class).sort((a, b) => b[1] - a[1])}
              />
              <DistributionCard
                title="Input types"
                icon={<Database size={14} className="text-[#00d4ff]" />}
                rows={Object.entries(inventory.input_type_distribution).sort((a, b) => b[1] - a[1])}
              />
              <DistributionCard
                title="Output types"
                icon={<Database size={14} className="text-[#00d4ff]" />}
                rows={Object.entries(inventory.output_type_distribution).sort((a, b) => b[1] - a[1])}
              />
            </div>

            <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5 mb-6">
              <h3 className="text-xs font-medium text-[#64748b] uppercase tracking-widest mb-3">
                Platform-level data controls
              </h3>
              <ul className="space-y-1.5 text-xs text-[#94a3b8]">
                {inventory.platform_controls.map((c, i) => (
                  <li key={i}>• {c}</li>
                ))}
              </ul>
            </div>

            <div className="rounded-xl border border-white/[0.06] bg-[#111118] overflow-hidden">
              <div className="px-4 py-3 border-b border-white/[0.06]">
                <h3 className="text-sm font-medium text-[#f1f5f9]">Per-agent data sheets</h3>
                <p className="text-xs text-[#64748b] mt-0.5">
                  Click an agent to generate its Art. 10 data sheet. Download as JSON,
                  Markdown, or PDF; save to the workspace with the other compliance records.
                </p>
              </div>
              <table className="w-full text-sm">
                <thead className="border-b border-white/[0.06] bg-[#0a0a0f]">
                  <tr className="text-xs text-[#64748b]">
                    <th className="text-left py-2.5 px-4 font-medium">Agent</th>
                    <th className="text-left py-2.5 px-4 font-medium">Domain</th>
                    <th className="text-left py-2.5 px-4 font-medium">Risk</th>
                    <th className="text-right py-2.5 px-4 font-medium">Executions</th>
                    <th className="text-right py-2.5 px-4 font-medium"></th>
                  </tr>
                </thead>
                <tbody>
                  {agents.map((a) => (
                    <tr
                      key={a.id}
                      className="border-b border-white/[0.04] hover:bg-white/[0.02]"
                    >
                      <td className="py-3 px-4">
                        <div>
                          <div className="text-[#f1f5f9]">{a.name}</div>
                          <div className="text-[10px] text-[#64748b] font-mono">{a.id}</div>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-xs text-[#94a3b8]">
                        {a.card?.capabilities?.domain || "-"}
                      </td>
                      <td className="py-3 px-4 text-xs text-[#94a3b8]">
                        {(a as unknown as { risk_class?: string }).risk_class || "minimal"}
                      </td>
                      <td className="py-3 px-4 text-xs text-[#94a3b8] text-right">
                        {a.total_executions}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => handleGenerate(a.id)}
                          disabled={busy}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-white/[0.08] text-xs text-[#94a3b8] hover:text-[#f1f5f9] disabled:opacity-40 transition-colors"
                        >
                          <FileCheck size={12} />
                          Data sheet
                        </button>
                      </td>
                    </tr>
                  ))}
                  {agents.length === 0 && (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-xs text-[#64748b]">
                        No agents visible to your role.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>

      {sheet && selectedAgentId && (
        <div
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm p-4 flex items-center justify-center"
          onClick={() => {
            setSheet(null);
            setSelectedAgentId(null);
            setSavedId(null);
          }}
        >
          <div
            className="rounded-xl border border-white/[0.08] bg-[#111118] w-full max-w-3xl max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between p-5 border-b border-white/[0.06]">
              <div>
                <p className="text-xs text-[#64748b] mb-1 font-medium uppercase tracking-widest">
                  Art. 10 data sheet
                </p>
                <h2 className="text-base font-semibold text-[#f1f5f9]">
                  {sheet.agent.name} · v{sheet.agent.version}
                </h2>
                <p className="text-[10px] text-[#64748b] font-mono mt-1">
                  {sheet.agent.id} · risk class {sheet.agent.risk_class}
                </p>
              </div>
              <button
                onClick={() => {
                  setSheet(null);
                  setSelectedAgentId(null);
                  setSavedId(null);
                }}
                className="p-1.5 rounded-lg text-[#64748b] hover:text-[#f1f5f9] transition-colors"
              >
                <X size={16} />
              </button>
            </div>

            <div className="p-5 space-y-4">
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => handleDownload("json")}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-white/[0.08] text-xs text-[#94a3b8] hover:text-[#f1f5f9] transition-colors"
                >
                  <Download size={12} />
                  JSON
                </button>
                <button
                  onClick={() => handleDownload("md")}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-white/[0.08] text-xs text-[#94a3b8] hover:text-[#f1f5f9] transition-colors"
                >
                  <FileCheck size={12} />
                  Markdown
                </button>
                <button
                  onClick={() => handleDownload("pdf")}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-white/[0.08] text-xs text-[#94a3b8] hover:text-[#f1f5f9] transition-colors"
                >
                  <FileCheck size={12} />
                  PDF
                </button>
                <button
                  onClick={handleSave}
                  disabled={busy}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-emerald-500/20 bg-emerald-500/5 text-emerald-300 hover:bg-emerald-500/10 text-xs disabled:opacity-40 transition-colors"
                >
                  {busy ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
                  Save to workspace
                </button>
              </div>

              {savedId && (
                <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-2.5 text-xs text-emerald-200/90">
                  Saved to workspace as{" "}
                  <a href="/compliance" className="underline hover:text-emerald-100">
                    document {savedId.slice(0, 8)}
                  </a>
                  .
                </div>
              )}

              <div className="rounded-xl border border-white/[0.06] bg-[#0a0a0f] overflow-hidden">
                <pre className="text-xs text-[#94a3b8] p-4 overflow-x-auto max-h-[60vh] overflow-y-auto whitespace-pre-wrap break-words">
                  {JSON.stringify(sheet, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone?: "amber" | "neutral";
}) {
  const toneClass = tone === "amber" ? "text-amber-300" : "text-[#f1f5f9]";
  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-4">
      <div className="text-xs text-[#64748b] mb-2">{label}</div>
      <div className={`text-2xl font-semibold ${toneClass}`}>{value}</div>
    </div>
  );
}

function DistributionCard({
  title,
  icon,
  rows,
}: {
  title: string;
  icon: React.ReactNode;
  rows: [string, number][];
}) {
  const max = Math.max(...rows.map(([, v]) => v), 1);
  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
      <h3 className="text-xs font-medium text-[#64748b] uppercase tracking-widest mb-3 flex items-center gap-2">
        {icon}
        {title}
      </h3>
      {rows.length === 0 ? (
        <p className="text-xs text-[#64748b]">No data</p>
      ) : (
        <div className="space-y-2">
          {rows.map(([key, value]) => (
            <div key={key} className="flex items-center gap-3">
              <div className="text-xs text-[#94a3b8] w-28 truncate font-mono">{key}</div>
              <div className="flex-1 h-1.5 bg-white/[0.04] rounded-full overflow-hidden">
                <div
                  className="h-full bg-[#00d4ff]/60 rounded-full"
                  style={{ width: `${(value / max) * 100}%` }}
                />
              </div>
              <div className="text-xs text-[#f1f5f9] w-8 text-right">{value}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
