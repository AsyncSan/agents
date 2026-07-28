import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  Clock,
  Key,
  RefreshCw,
  FileText,
  Terminal,
  ChevronDown,
  ChevronRight,
  Loader2,
  Server,
  Zap,
  Activity,
  ShieldAlert,
  CheckCircle,
} from "lucide-react";
import {
  listTasks,
  getExecutions,
  getTaskResult,
  approveTask,
  type Task,
  type Execution,
} from "../api";
import { StatusBadge } from "../components/StatusBadge";
import { ReportViewer } from "../components/ReportViewer";

function LiveDot({ status }: { status: string }) {
  if (status === "completed" || status === "failed") return null;
  const color =
    status === "dispatching"
      ? "bg-blue-400"
      : status === "running"
        ? "bg-cyan-400"
        : "bg-amber-400";
  return (
    <span className="relative flex h-2 w-2">
      <span
        className={`animate-ping absolute inline-flex h-full w-full rounded-full ${color} opacity-75`}
      />
      <span
        className={`relative inline-flex rounded-full h-2 w-2 ${color}`}
      />
    </span>
  );
}

function ElapsedTimer({ startedAt }: { startedAt: string }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const start = new Date(startedAt).getTime();
    const tick = () => setElapsed(Math.floor((Date.now() - start) / 1000));
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [startedAt]);

  const minutes = Math.floor(elapsed / 60);
  const seconds = elapsed % 60;

  return (
    <span className="text-xs font-mono text-cyan-400 tabular-nums">
      {minutes}:{seconds.toString().padStart(2, "0")}
    </span>
  );
}

function ProgressBar({ status }: { status: string }) {
  const stages = ["pending", "dispatching", "running", "completed"];
  const currentIndex = stages.indexOf(status);
  const isFailed = status === "failed";

  return (
    <div className="flex items-center gap-1 mt-2">
      {stages.map((stage, i) => {
        const isActive = i === currentIndex && !isFailed;
        const isDone = i < currentIndex && !isFailed;
        const isFail = isFailed && i === currentIndex;

        return (
          <div key={stage} className="flex items-center gap-1 flex-1">
            <div
              className={`h-1 flex-1 rounded-full transition-all duration-500 ${
                isDone
                  ? "bg-emerald-500/60"
                  : isActive
                    ? "bg-[#00d4ff]/60"
                    : isFail
                      ? "bg-red-500/60"
                      : "bg-white/[0.04]"
              }`}
              style={
                isActive
                  ? {
                      background:
                        "linear-gradient(90deg, rgba(0,212,255,0.6) 0%, rgba(0,212,255,0.1) 100%)",
                      animation:
                        "pulse-bar 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
                    }
                  : undefined
              }
            />
          </div>
        );
      })}
    </div>
  );
}

export function TasksPage() {
  const [apiKey, setApiKey] = useState(
    () => localStorage.getItem("af_api_key") || ""
  );
  const [tasks, setTasks] = useState<Task[]>([]);
  const [executions, setExecutions] = useState<
    Record<string, Execution[]>
  >({});
  const [results, setResults] = useState<Record<string, string>>({});
  const [resultTab, setResultTab] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<Record<string, "rich" | "raw">>({});

  const loadTasks = useCallback(async () => {
    if (!apiKey) return;
    setLoading(true);
    localStorage.setItem("af_api_key", apiKey);
    try {
      const data = await listTasks(apiKey);
      setTasks(data.tasks);
    } catch {
      setTasks([]);
    } finally {
      setLoading(false);
    }
  }, [apiKey]);

  useEffect(() => {
    if (apiKey) loadTasks();
  }, []);

  // Auto-poll while any task is active
  useEffect(() => {
    const hasActive = tasks.some((t) =>
      ["pending", "authorized", "dispatching", "running", "awaiting_approval"].includes(t.status)
    );
    if (!hasActive || !apiKey) return;
    const interval = setInterval(loadTasks, 5000);
    return () => clearInterval(interval);
  }, [tasks, apiKey, loadTasks]);

  const loadResult = async (taskId: string, file: string) => {
    const key = `${taskId}:${file}`;
    if (results[key]) return;
    try {
      const text = await getTaskResult(apiKey, taskId, file);
      setResults((prev) => ({ ...prev, [key]: text }));
    } catch {
      setResults((prev) => ({ ...prev, [key]: "(no result available)" }));
    }
  };

  const toggleExpand = async (taskId: string) => {
    if (expanded === taskId) {
      setExpanded(null);
      return;
    }
    setExpanded(taskId);
    if (!executions[taskId]) {
      try {
        const execs = await getExecutions(apiKey, taskId);
        setExecutions((prev) => ({ ...prev, [taskId]: execs }));
      } catch {
        /* ignore */
      }
    }
    const task = tasks.find((t) => t.id === taskId);
    if (task?.status === "completed") {
      loadResult(taskId, "output.md");
    }
  };

  const formatDate = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const activeCount = tasks.filter((t) =>
    ["pending", "dispatching", "running", "awaiting_approval"].includes(t.status)
  ).length;

  return (
    <>
      <style>{`
        @keyframes pulse-bar {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>

      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-[#f1f5f9] mb-1">
              Tasks
            </h1>
            <p className="text-sm text-[#94a3b8]">
              Track agent executions and view results.
            </p>
          </div>
          {activeCount > 0 && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#00d4ff]/5 border border-[#00d4ff]/10">
              <Loader2 size={14} className="animate-spin text-[#00d4ff]" />
              <span className="text-xs text-[#00d4ff]">
                {activeCount} active
              </span>
            </div>
          )}
        </div>
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
            className="w-full pl-9 pr-3 py-2 rounded-lg bg-[#111118] border border-white/[0.06] text-sm text-[#f1f5f9] placeholder-[#64748b] focus:outline-none focus:border-[#00d4ff]/30 transition-colors"
          />
        </div>
        <button
          onClick={loadTasks}
          disabled={!apiKey || loading}
          className="px-4 py-2 rounded-lg bg-[#111118] border border-white/[0.06] text-sm text-[#94a3b8] hover:text-[#00d4ff] hover:border-[#00d4ff]/20 transition-colors disabled:opacity-40"
        >
          <RefreshCw
            size={14}
            className={loading ? "animate-spin" : ""}
          />
        </button>
      </div>

      {!apiKey && (
        <div className="text-center py-16 text-[#64748b] text-sm">
          <Key size={24} className="mx-auto mb-3 opacity-30" />
          Enter your API key to view tasks.
        </div>
      )}

      {apiKey && tasks.length === 0 && !loading && (
        <div className="text-center py-16">
          <Activity size={24} className="mx-auto mb-3 text-[#334155]" />
          <p className="text-[#64748b] text-sm mb-3">No tasks yet.</p>
          <Link
            to="/"
            className="text-sm text-[#00d4ff] hover:underline"
          >
            Browse the catalog to submit your first task
          </Link>
        </div>
      )}

      <div className="space-y-3">
        {tasks.map((task) => {
          const isExpanded = expanded === task.id;
          const isActive = [
            "pending",
            "dispatching",
            "running",
          ].includes(task.status);
          const exec = executions[task.id]?.[0];
          const tab = resultTab[task.id] || "output.md";
          const mode = viewMode[task.id] || "rich";
          const resultKey = `${task.id}:${tab}`;

          return (
            <div
              key={task.id}
              className={`rounded-xl border overflow-hidden transition-all duration-300 ${
                isActive
                  ? "border-[#00d4ff]/15 bg-[#111118]"
                  : task.status === "failed"
                    ? "border-red-500/10 bg-[#111118]"
                    : "border-white/[0.06] bg-[#111118]"
              }`}
            >
              {/* Task Header */}
              <button
                onClick={() => toggleExpand(task.id)}
                className="w-full px-5 py-4 flex items-center gap-4 text-left hover:bg-white/[0.02] transition-colors"
              >
                <div className="flex items-center gap-2">
                  <LiveDot status={task.status} />
                  <StatusBadge status={task.status} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <Link
                      to={`/agents/${task.agent_id}`}
                      className="text-sm font-medium text-[#00d4ff] hover:underline no-underline"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {task.agent_id}
                    </Link>
                    {task.inputs && (
                      <span className="text-[10px] text-[#475569] truncate max-w-[200px]">
                        {Object.values(task.inputs)
                          .map(String)
                          .join(", ")
                          .slice(0, 60)}
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] text-[#475569] font-mono mt-0.5">
                    {task.id}
                  </div>
                  {isActive && <ProgressBar status={task.status} />}
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  {isActive && exec?.started_at && (
                    <ElapsedTimer startedAt={exec.started_at} />
                  )}
                  {exec?.elapsed_seconds !== null &&
                    exec?.elapsed_seconds !== undefined &&
                    !isActive && (
                      <span className="text-xs text-[#64748b] flex items-center gap-1">
                        <Zap size={11} />
                        {Math.floor(exec.elapsed_seconds / 60)}m{" "}
                        {exec.elapsed_seconds % 60}s
                      </span>
                    )}
                  <div className="flex items-center gap-1 text-xs text-[#475569]">
                    <Clock size={11} />
                    {formatDate(task.created_at)}
                  </div>
                  <div className="text-[#475569]">
                    {isExpanded ? (
                      <ChevronDown size={14} />
                    ) : (
                      <ChevronRight size={14} />
                    )}
                  </div>
                </div>
              </button>

              {/* Expanded Content */}
              {isExpanded && (
                <div className="border-t border-white/[0.04]">
                  {/* Awaiting Approval */}
                  {task.status === "awaiting_approval" && (
                    <div className="px-5 py-4">
                      <div className="flex items-start gap-3 p-4 rounded-xl bg-purple-500/5 border border-purple-500/10">
                        <ShieldAlert size={20} className="text-purple-400 shrink-0 mt-0.5" />
                        <div className="flex-1">
                          <p className="text-sm font-medium text-purple-300">
                            Human approval required (EU AI Act Art. 14)
                          </p>
                          <p className="text-xs text-[#94a3b8] mt-1">
                            This agent is classified as high-risk. Review the inputs below and approve to start execution.
                          </p>
                          {task.inputs && Object.keys(task.inputs).length > 0 && (
                            <div className="mt-3 flex flex-wrap gap-2">
                              {Object.entries(task.inputs).map(([k, v]) => (
                                <div key={k} className="flex items-center gap-1.5 text-[11px] bg-[#0a0a0f] rounded px-2 py-1 border border-white/[0.04]">
                                  <code className="text-[#00d4ff] font-mono">{k}</code>
                                  <span className="text-[#334155]">=</span>
                                  <span className="text-[#94a3b8] font-mono truncate max-w-[200px]">{String(v)}</span>
                                </div>
                              ))}
                            </div>
                          )}
                          <div className="mt-4 flex gap-2">
                            <button
                              onClick={async (e) => {
                                e.stopPropagation();
                                try {
                                  await approveTask(apiKey, task.id);
                                  loadTasks();
                                } catch { /* ignore */ }
                              }}
                              className="px-4 py-2 rounded-lg bg-emerald-500/20 border border-emerald-500/30 text-sm text-emerald-400 hover:bg-emerald-500/30 transition-colors flex items-center gap-1.5"
                            >
                              <CheckCircle size={14} />
                              Approve and Execute
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Active Task: Live Status */}
                  {isActive && task.status !== "awaiting_approval" && (
                    <div className="px-5 py-4">
                      <div className="flex items-center gap-3 p-4 rounded-xl bg-[#0a0a0f] border border-white/[0.04]">
                        <Loader2
                          size={20}
                          className="animate-spin text-[#00d4ff]"
                        />
                        <div>
                          <p className="text-sm text-[#f1f5f9]">
                            {task.status === "pending" &&
                              "Waiting for dispatch worker pickup..."}
                            {task.status === "dispatching" &&
                              "Provisioning ephemeral server, injecting secrets, executing agent..."}
                            {task.status === "running" &&
                              "Agent is running security scans on the target repository..."}
                          </p>
                          <p className="text-xs text-[#64748b] mt-1">
                            {task.status === "pending" &&
                              "Tasks are picked up within 5 seconds."}
                            {task.status === "dispatching" &&
                              "VM boot ~30s, then clone + scan + report generation."}
                            {task.status === "running" &&
                              "Scanning dependencies, secrets, SAST analysis, generating report."}
                          </p>
                        </div>
                      </div>

                      {/* Inputs */}
                      {task.inputs &&
                        Object.keys(task.inputs).length > 0 && (
                          <div className="mt-3">
                            <h4 className="text-[10px] uppercase tracking-wider text-[#64748b] mb-2">
                              Inputs
                            </h4>
                            <div className="flex flex-wrap gap-2">
                              {Object.entries(task.inputs).map(
                                ([k, v]) => (
                                  <div
                                    key={k}
                                    className="flex items-center gap-1.5 text-xs bg-[#0a0a0f] rounded-lg px-2.5 py-1.5 border border-white/[0.04]"
                                  >
                                    <code className="text-[#00d4ff] font-mono text-[11px]">
                                      {k}
                                    </code>
                                    <span className="text-[#334155]">
                                      =
                                    </span>
                                    <span className="text-[#94a3b8] font-mono text-[11px]">
                                      {String(v)}
                                    </span>
                                  </div>
                                )
                              )}
                            </div>
                          </div>
                        )}
                    </div>
                  )}

                  {/* Completed: Report Viewer */}
                  {task.status === "completed" && (
                    <div className="px-5 py-4">
                      {/* Inputs (collapsed) */}
                      {task.inputs &&
                        Object.keys(task.inputs).length > 0 && (
                          <div className="mb-4 flex flex-wrap gap-2">
                            {Object.entries(task.inputs).map(
                              ([k, v]) => (
                                <div
                                  key={k}
                                  className="flex items-center gap-1.5 text-[11px] bg-[#0a0a0f] rounded px-2 py-1 border border-white/[0.04]"
                                >
                                  <code className="text-[#00d4ff] font-mono">
                                    {k}
                                  </code>
                                  <span className="text-[#334155]">
                                    =
                                  </span>
                                  <span className="text-[#94a3b8] font-mono truncate max-w-[200px]">
                                    {String(v)}
                                  </span>
                                </div>
                              )
                            )}
                          </div>
                        )}

                      {/* Tab Bar */}
                      <div className="flex items-center gap-1 mb-3">
                        {["output.md", "stdout.log", "stderr.log"].map(
                          (file) => (
                            <button
                              key={file}
                              onClick={() => {
                                setResultTab((prev) => ({
                                  ...prev,
                                  [task.id]: file,
                                }));
                                loadResult(task.id, file);
                                if (file !== "output.md") {
                                  setViewMode((prev) => ({
                                    ...prev,
                                    [task.id]: "raw",
                                  }));
                                }
                              }}
                              className={`px-3 py-1.5 rounded-lg text-xs transition-colors flex items-center gap-1.5 ${
                                tab === file
                                  ? "bg-[#00d4ff]/10 text-[#00d4ff] border border-[#00d4ff]/20"
                                  : "text-[#64748b] hover:text-[#94a3b8] border border-transparent"
                              }`}
                            >
                              {file === "output.md" && (
                                <FileText size={11} />
                              )}
                              {file === "stdout.log" && (
                                <Terminal size={11} />
                              )}
                              {file === "stderr.log" && (
                                <Server size={11} />
                              )}
                              {file === "output.md"
                                ? "Report"
                                : file === "stdout.log"
                                  ? "Stdout"
                                  : "Stderr"}
                            </button>
                          )
                        )}
                      </div>

                      {/* Content */}
                      {!results[resultKey] ? (
                        <div className="flex items-center justify-center py-8">
                          <Loader2
                            size={16}
                            className="animate-spin text-[#64748b]"
                          />
                          <span className="ml-2 text-sm text-[#64748b]">
                            Loading result...
                          </span>
                        </div>
                      ) : tab === "output.md" && mode === "rich" ? (
                        <ReportViewer
                          markdown={results[resultKey]}
                          execution={
                            exec
                              ? {
                                  elapsed_seconds: exec.elapsed_seconds,
                                  server_id: exec.server_id,
                                  exit_code: exec.exit_code,
                                  metrics: exec.metrics,
                                  started_at: exec.started_at,
                                  completed_at: exec.completed_at,
                                }
                              : undefined
                          }
                          onShowRaw={() =>
                            setViewMode((prev) => ({
                              ...prev,
                              [task.id]: "raw",
                            }))
                          }
                        />
                      ) : (
                        <div>
                          {tab === "output.md" && (
                            <button
                              onClick={() =>
                                setViewMode((prev) => ({
                                  ...prev,
                                  [task.id]: "rich",
                                }))
                              }
                              className="mb-2 text-[10px] text-[#00d4ff] hover:underline"
                            >
                              Switch to rich view
                            </button>
                          )}
                          <pre className="rounded-xl bg-[#0a0a0f] border border-white/[0.04] p-4 text-xs text-[#94a3b8] overflow-x-auto max-h-[600px] overflow-y-auto font-mono leading-relaxed whitespace-pre-wrap">
                            {results[resultKey]}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Failed Task */}
                  {task.status === "failed" && (
                    <div className="px-5 py-4">
                      <div className="p-4 rounded-xl bg-red-500/5 border border-red-500/10">
                        <p className="text-sm text-red-400 font-medium mb-1">
                          Execution Failed
                        </p>
                        {exec && (
                          <p className="text-xs text-[#94a3b8]">
                            Exit code: {exec.exit_code}, Duration:{" "}
                            {exec.elapsed_seconds}s
                          </p>
                        )}
                      </div>
                      {/* Show stderr for failed tasks */}
                      <div className="mt-3">
                        <button
                          onClick={() =>
                            loadResult(task.id, "stderr.log")
                          }
                          className="text-xs text-[#64748b] hover:text-[#94a3b8] mb-2"
                        >
                          View error log
                        </button>
                        {results[`${task.id}:stderr.log`] && (
                          <pre className="rounded-xl bg-[#0a0a0f] border border-red-500/10 p-4 text-xs text-red-300/80 font-mono whitespace-pre-wrap max-h-64 overflow-y-auto">
                            {results[`${task.id}:stderr.log`]}
                          </pre>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </>
  );
}
