import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  GitBranch,
  Key,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  ArrowRight,
  Layers,
  Filter,
  Database,
} from "lucide-react";
import { listPipelines, type Pipeline } from "../api";
import { StatusBadge } from "../components/StatusBadge";

function StepViz({ pipeline }: { pipeline: Pipeline }) {
  // Group steps by step_index
  const groups: Record<number, typeof pipeline.steps> = {};
  for (const step of pipeline.steps) {
    const idx = step.step_index ?? 0;
    if (!groups[idx]) groups[idx] = [];
    groups[idx].push(step);
  }

  const sortedIndices = Object.keys(groups)
    .map(Number)
    .sort((a, b) => a - b);

  return (
    <div className="flex items-center gap-1 overflow-x-auto py-1">
      {sortedIndices.map((idx, i) => {
        const stepsInGroup = groups[idx];
        const isActive = pipeline.current_step === idx;
        const isDone =
          pipeline.status === "completed" ||
          (pipeline.status === "running" && idx < pipeline.current_step);
        const isParallel = stepsInGroup.length > 1;

        // Find tasks for this step
        const tasksAtStep = pipeline.tasks.filter(
          (t) => t.step_index === idx
        );

        return (
          <div key={idx} className="flex items-center gap-1">
            {i > 0 && (
              <ArrowRight
                size={12}
                className={isDone ? "text-emerald-400" : "text-[#64748b]/40"}
              />
            )}
            <div
              className={`rounded-lg border px-2.5 py-1.5 text-[10px] ${
                isActive
                  ? "border-[#00d4ff]/30 bg-[#00d4ff]/5"
                  : isDone
                    ? "border-emerald-500/20 bg-emerald-500/5"
                    : "border-white/[0.04] bg-[#0a0a0f]"
              }`}
            >
              {isParallel && (
                <div className="flex items-center gap-1 text-[#64748b] mb-0.5">
                  <Layers size={8} />
                  <span>parallel</span>
                </div>
              )}
              {stepsInGroup.map((step, si) => (
                <div key={si} className="flex items-center gap-1">
                  {!!(step as unknown as Record<string, unknown>).condition && (
                    <span
                      className="text-amber-400"
                      title={`if ${((step as unknown as Record<string, unknown>).condition as Record<string, string>).field} ${((step as unknown as Record<string, unknown>).condition as Record<string, string>).op} ${((step as unknown as Record<string, unknown>).condition as Record<string, string>).value ?? ""}`}
                    >
                      <Filter size={8} />
                    </span>
                  )}
                  <Link
                    to={`/agents/${step.agent_id}`}
                    className="text-[#00d4ff] hover:underline no-underline truncate max-w-[100px]"
                  >
                    {step.agent_id}
                  </Link>
                  {tasksAtStep[si] && (
                    <StatusBadge status={tasksAtStep[si].status} />
                  )}
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function PipelinesPage() {
  const [apiKey, setApiKey] = useState(
    () => localStorage.getItem("af_api_key") || ""
  );
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);

  const loadPipelines = useCallback(async () => {
    if (!apiKey) return;
    setLoading(true);
    localStorage.setItem("af_api_key", apiKey);
    try {
      const data = await listPipelines(apiKey);
      setPipelines(data.pipelines);
    } catch {
      setPipelines([]);
    } finally {
      setLoading(false);
    }
  }, [apiKey]);

  useEffect(() => {
    if (apiKey) loadPipelines();
  }, []);

  // Auto-poll while any pipeline is active
  useEffect(() => {
    const hasActive = pipelines.some((p) =>
      ["pending", "running"].includes(p.status)
    );
    if (!hasActive || !apiKey) return;

    const interval = setInterval(loadPipelines, 5000);
    return () => clearInterval(interval);
  }, [pipelines, apiKey, loadPipelines]);

  const formatDate = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleDateString("de-DE", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const formatCost = (cents: number) =>
    cents > 0 ? `$${(cents / 100).toFixed(2)}` : "-";

  return (
    <>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-[#f1f5f9] mb-2">
          Pipelines
        </h1>
        <p className="text-sm text-[#94a3b8]">
          Multi-step agent chains with parallel execution.
        </p>
      </div>

      <div className="flex gap-2 mb-6">
        <div className="relative flex-1">
          <Key
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-[#64748b]"
          />
          <input
            type="password"
            placeholder="Your API Key (af_...)"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            className="w-full pl-9 pr-3 py-2 rounded-lg bg-[#111118] border border-white/[0.06] text-sm text-[#f1f5f9] placeholder-[#64748b] focus:outline-none focus:border-[#00d4ff]/30"
          />
        </div>
        <button
          onClick={loadPipelines}
          disabled={!apiKey || loading}
          className="px-4 py-2 rounded-lg bg-[#111118] border border-white/[0.06] text-sm text-[#94a3b8] hover:text-[#00d4ff] hover:border-[#00d4ff]/20 transition-colors disabled:opacity-40"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {!apiKey && (
        <div className="text-center py-16 text-[#64748b] text-sm">
          Enter your API key to view pipelines.
        </div>
      )}

      {apiKey && pipelines.length === 0 && !loading && (
        <div className="text-center py-16">
          <p className="text-[#64748b] text-sm mb-3">No pipelines yet.</p>
          <p className="text-xs text-[#64748b]">
            Create pipelines via the API:{" "}
            <code className="text-[#94a3b8]">POST /v1/pipelines</code>
          </p>
        </div>
      )}

      <div className="space-y-2">
        {pipelines.map((pl) => (
          <div
            key={pl.id}
            className="rounded-xl border border-white/[0.06] bg-[#111118] overflow-hidden"
          >
            <button
              onClick={() =>
                setExpanded(expanded === pl.id ? null : pl.id)
              }
              className="w-full px-5 py-4 flex items-center gap-4 text-left hover:bg-white/[0.02] transition-colors"
            >
              <div className="shrink-0">
                {expanded === pl.id ? (
                  <ChevronDown size={14} className="text-[#64748b]" />
                ) : (
                  <ChevronRight size={14} className="text-[#64748b]" />
                )}
              </div>
              <StatusBadge status={pl.status} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 text-sm text-[#f1f5f9] font-medium">
                  <GitBranch size={12} className="text-[#00d4ff]" />
                  <span className="font-mono text-xs">{pl.id}</span>
                </div>
                <div className="text-xs text-[#64748b] mt-1">
                  {pl.total_steps} steps, {pl.steps.length} agents
                  {pl.chain_trust_score !== null &&
                    ` · Trust: ${(pl.chain_trust_score * 100).toFixed(0)}%`}
                </div>
              </div>
              <div className="text-right shrink-0">
                <div className="text-xs text-[#64748b]">
                  {formatDate(pl.created_at)}
                </div>
                <div className="text-xs text-[#94a3b8]">
                  {formatCost(pl.total_captured_cents)}
                </div>
              </div>
            </button>

            {expanded === pl.id && (
              <div className="px-5 pb-5 border-t border-white/[0.04]">
                {/* Step Visualization */}
                <div className="mt-3 mb-4">
                  <h4 className="text-xs text-[#64748b] mb-2">
                    Pipeline Flow
                  </h4>
                  <StepViz pipeline={pl} />
                </div>

                {/* Tasks per step */}
                <div>
                  <h4 className="text-xs text-[#64748b] mb-2">Tasks</h4>
                  <div className="space-y-1.5">
                    {pl.tasks.map((task) => (
                      <div
                        key={task.id}
                        className="flex items-center gap-3 rounded-lg bg-[#0a0a0f] border border-white/[0.04] px-3 py-2 text-xs"
                      >
                        <StatusBadge status={task.status} />
                        <span className="text-[#64748b]">
                          Step {task.step_index ?? "?"}
                        </span>
                        <Link
                          to={`/agents/${task.agent_id}`}
                          className="text-[#00d4ff] hover:underline no-underline"
                        >
                          {task.agent_id}
                        </Link>
                        <span className="font-mono text-[#64748b] ml-auto">
                          {task.id}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Shared Context */}
                {pl.context && Object.keys(pl.context).length > 0 && (
                  <div className="mt-3">
                    <h4 className="text-xs text-[#64748b] mb-2 flex items-center gap-1">
                      <Database size={10} />
                      Shared Context
                    </h4>
                    <pre className="rounded-lg bg-[#0a0a0f] border border-white/[0.04] p-3 text-[10px] text-[#94a3b8] overflow-x-auto font-mono max-h-32 overflow-y-auto">
                      {JSON.stringify(pl.context, null, 2)}
                    </pre>
                  </div>
                )}

                {pl.callback_url && (
                  <div className="mt-3 text-xs text-[#64748b]">
                    Callback: {pl.callback_url}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </>
  );
}
