import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { Clock, Key, RefreshCw, FileText, Terminal } from "lucide-react";
import { listTasks, getExecutions, getTaskResult, type Task, type Execution } from "../api";
import { StatusBadge } from "../components/StatusBadge";

export function TasksPage() {
  const [apiKey, setApiKey] = useState(() => localStorage.getItem("af_api_key") || "");
  const [tasks, setTasks] = useState<Task[]>([]);
  const [executions, setExecutions] = useState<Record<string, Execution[]>>({});
  const [results, setResults] = useState<Record<string, string>>({});
  const [resultTab, setResultTab] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);

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
      ["pending", "authorized", "dispatching", "running"].includes(t.status)
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
        setExecutions({ ...executions, [taskId]: execs });
      } catch {
        /* ignore */
      }
    }
    // Auto-load result for completed tasks
    const task = tasks.find((t) => t.id === taskId);
    if (task?.status === "completed") {
      loadResult(taskId, "output.md");
    }
  };

  const formatDate = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleDateString("de-DE", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-[#f1f5f9] mb-2">Your Tasks</h1>
        <p className="text-sm text-[#94a3b8]">Track submitted agent tasks and their executions.</p>
      </div>

      <div className="flex gap-2 mb-6">
        <div className="relative flex-1">
          <Key size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#64748b]" />
          <input
            type="password"
            placeholder="Your API Key (af_...)"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            className="w-full pl-9 pr-3 py-2 rounded-lg bg-[#111118] border border-white/[0.06] text-sm text-[#f1f5f9] placeholder-[#64748b] focus:outline-none focus:border-[#00d4ff]/30"
          />
        </div>
        <button
          onClick={loadTasks}
          disabled={!apiKey || loading}
          className="px-4 py-2 rounded-lg bg-[#111118] border border-white/[0.06] text-sm text-[#94a3b8] hover:text-[#00d4ff] hover:border-[#00d4ff]/20 transition-colors disabled:opacity-40"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {!apiKey && (
        <div className="text-center py-16 text-[#64748b] text-sm">
          Enter your API key to view tasks.
        </div>
      )}

      {apiKey && tasks.length === 0 && !loading && (
        <div className="text-center py-16">
          <p className="text-[#64748b] text-sm mb-3">No tasks yet.</p>
          <Link to="/" className="text-sm text-[#00d4ff] hover:underline">
            Browse the catalog to submit your first task →
          </Link>
        </div>
      )}

      <div className="space-y-2">
        {tasks.map((task) => (
          <div key={task.id} className="rounded-xl border border-white/[0.06] bg-[#111118] overflow-hidden">
            <button
              onClick={() => toggleExpand(task.id)}
              className="w-full px-5 py-4 flex items-center gap-4 text-left hover:bg-white/[0.02] transition-colors"
            >
              <StatusBadge status={task.status} />
              <div className="flex-1 min-w-0">
                <div className="text-sm text-[#f1f5f9] font-medium">
                  <Link
                    to={`/agents/${task.agent_id}`}
                    className="text-[#00d4ff] hover:underline no-underline"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {task.agent_id}
                  </Link>
                </div>
                <div className="text-xs text-[#64748b] font-mono mt-0.5">{task.id}</div>
              </div>
              <div className="flex items-center gap-1 text-xs text-[#64748b]">
                <Clock size={12} />
                {formatDate(task.created_at)}
              </div>
            </button>

            {expanded === task.id && (
              <div className="px-5 pb-4 border-t border-white/[0.04]">
                {/* Inputs */}
                {task.inputs && Object.keys(task.inputs).length > 0 && (
                  <div className="mt-3">
                    <h4 className="text-xs text-[#64748b] mb-2">Inputs</h4>
                    <div className="space-y-1">
                      {Object.entries(task.inputs).map(([k, v]) => (
                        <div key={k} className="flex gap-2 text-xs">
                          <code className="text-[#00d4ff] font-mono">{k}:</code>
                          <span className="text-[#94a3b8] truncate">{String(v)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Executions */}
                {executions[task.id] && executions[task.id].length > 0 && (
                  <div className="mt-3">
                    <h4 className="text-xs text-[#64748b] mb-2">Executions</h4>
                    {executions[task.id].map((exec) => (
                      <div
                        key={exec.id}
                        className="rounded-lg bg-[#0a0a0f] border border-white/[0.04] p-3 text-xs space-y-1"
                      >
                        <div className="flex items-center gap-2">
                          <StatusBadge status={exec.status} />
                          <span className="font-mono text-[#64748b]">{exec.id}</span>
                        </div>
                        {exec.elapsed_seconds !== null && (
                          <div className="text-[#94a3b8]">
                            Duration: {exec.elapsed_seconds}s, Exit: {exec.exit_code}
                          </div>
                        )}
                        {exec.metrics && (
                          <div className="text-[#64748b]">
                            Output: {(exec.metrics as Record<string, number>).output_bytes || 0} bytes
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {executions[task.id]?.length === 0 && (
                  <p className="mt-3 text-xs text-[#64748b]">No executions yet.</p>
                )}

                {/* Result Viewer */}
                {task.status === "completed" && (
                  <div className="mt-3">
                    <div className="flex items-center gap-2 mb-2">
                      <h4 className="text-xs text-[#64748b]">Result</h4>
                      <div className="flex gap-1">
                        {["output.md", "stdout.log", "stderr.log"].map((file) => {
                          const tab = resultTab[task.id] || "output.md";
                          return (
                            <button
                              key={file}
                              onClick={() => {
                                setResultTab((prev) => ({ ...prev, [task.id]: file }));
                                loadResult(task.id, file);
                              }}
                              className={`px-2 py-0.5 rounded text-[10px] transition-colors ${
                                tab === file
                                  ? "bg-[#00d4ff]/10 text-[#00d4ff]"
                                  : "text-[#64748b] hover:text-[#94a3b8]"
                              }`}
                            >
                              {file === "output.md" && <FileText size={9} className="inline mr-0.5" />}
                              {file === "stdout.log" && <Terminal size={9} className="inline mr-0.5" />}
                              {file.replace(".log", "").replace(".md", "")}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                    <pre className="rounded-lg bg-[#0a0a0f] border border-white/[0.04] p-3 text-xs text-[#94a3b8] overflow-x-auto max-h-64 overflow-y-auto font-mono leading-relaxed whitespace-pre-wrap">
                      {results[`${task.id}:${resultTab[task.id] || "output.md"}`] || "Loading..."}
                    </pre>
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
