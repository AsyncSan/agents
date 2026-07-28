import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  Clock,
  Container,
  Cpu,
  GitBranch,
  Play,
  Server,
  Shield,
  Tag,
  Zap,
} from "lucide-react";
import {
  getAgent,
  getCompatibleAgents,
  submitTask,
  type Agent,
  type CompatibleAgent,
} from "../api";
import { StatusBadge } from "../components/StatusBadge";
import { TrustRing } from "../components/TrustRing";

export function AgentPage() {
  const { id } = useParams<{ id: string }>();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [loading, setLoading] = useState(true);
  const [downstream, setDownstream] = useState<CompatibleAgent[]>([]);
  const [upstream, setUpstream] = useState<CompatibleAgent[]>([]);
  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [apiKey, setApiKey] = useState(() => localStorage.getItem("af_api_key") || "");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ id: string } | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) return;
    getAgent(id)
      .then((a) => {
        setAgent(a);
        const defaults: Record<string, string> = {};
        for (const inp of a.card.capabilities.inputs) {
          defaults[inp.name] = inp.default || "";
        }
        setInputs(defaults);
        // Load compatible agents
        getCompatibleAgents(id, "downstream", 4).then((d) =>
          setDownstream(d.compatible)
        );
        getCompatibleAgents(id, "upstream", 4).then((d) =>
          setUpstream(d.compatible)
        );
      })
      .catch(() => setError("Agent not found"))
      .finally(() => setLoading(false));
  }, [id]);

  const handleSubmit = async () => {
    if (!agent || !apiKey) return;
    setSubmitting(true);
    setError("");
    try {
      localStorage.setItem("af_api_key", apiKey);
      const task = await submitTask(apiKey, agent.id, inputs);
      setResult(task);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to submit");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className="text-center py-20 text-[#64748b] text-sm">Loading...</div>;
  if (!agent) return <div className="text-center py-20 text-red-400 text-sm">{error || "Agent not found"}</div>;

  const { capabilities, runtime } = agent.card;
  const successRate =
    agent.total_executions > 0
      ? Math.round((agent.success_count / agent.total_executions) * 100)
      : null;

  return (
    <>
      <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-[#94a3b8] hover:text-[#00d4ff] mb-6 no-underline transition-colors">
        <ArrowLeft size={14} />
        Back to Catalog
      </Link>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Details */}
        <div className="lg:col-span-2 space-y-6">
          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-start gap-3">
                <TrustRing score={agent.trust_score} size={48} />
                <div>
                  <h1 className="text-xl font-semibold text-[#f1f5f9] mb-1">{agent.name}</h1>
                  <p className="text-sm text-[#94a3b8]">
                    by {agent.provider_name || "Unknown"} <StatusBadge status={agent.status} />
                  </p>
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm font-medium text-emerald-400">Included</div>
                <div className="text-xs text-[#64748b]">in your plan</div>
              </div>
            </div>
            <p className="text-sm text-[#94a3b8] leading-relaxed">
              {agent.description || capabilities.description}
            </p>
            <div className="flex flex-wrap gap-1.5 mt-4">
              {capabilities.tags.map((t) => (
                <span key={t} className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-white/5 text-[#94a3b8]">
                  <Tag size={10} />
                  {t}
                </span>
              ))}
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            {[
              { icon: Zap, label: "Executions", value: agent.total_executions },
              { icon: Shield, label: "Success Rate", value: successRate !== null ? `${successRate}%` : "N/A" },
              { icon: Clock, label: "Est. Duration", value: `~${Math.round(runtime.estimated_duration_seconds / 60)}min` },
              { icon: Cpu, label: "Model", value: runtime.model.split("/").pop() },
              {
                icon: runtime.compute_tier === "container" ? Container : Server,
                label: "Compute",
                value: runtime.compute_tier === "container" ? "Container (~100ms)" : "VM (~20s)",
              },
            ].map(({ icon: Icon, label, value }) => (
              <div key={label} className="rounded-lg border border-white/[0.06] bg-[#111118] p-3">
                <div className="flex items-center gap-1.5 text-[#64748b] text-xs mb-1">
                  <Icon size={12} />
                  {label}
                </div>
                <div className="text-sm font-medium text-[#f1f5f9]">{value}</div>
              </div>
            ))}
          </div>

          {/* Inputs/Outputs */}
          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-6">
            <h2 className="text-sm font-medium text-[#f1f5f9] mb-3">Inputs</h2>
            <div className="space-y-2">
              {capabilities.inputs.map((inp) => (
                <div key={inp.name} className="flex items-center gap-3 text-xs">
                  <code className="px-2 py-0.5 rounded bg-white/5 text-[#00d4ff] font-mono">{inp.name}</code>
                  <span className="text-[#64748b]">{inp.type}</span>
                  {inp.required && <span className="text-amber-400">required</span>}
                </div>
              ))}
            </div>
            <h2 className="text-sm font-medium text-[#f1f5f9] mt-5 mb-3">Outputs</h2>
            <div className="space-y-2">
              {capabilities.outputs.map((out) => (
                <div key={out.name} className="flex items-center gap-3 text-xs">
                  <code className="px-2 py-0.5 rounded bg-white/5 text-emerald-400 font-mono">{out.name}</code>
                  <span className="text-[#64748b]">{out.type}</span>
                  {out.guaranteed && <span className="text-emerald-400">guaranteed</span>}
                </div>
              ))}
            </div>
          </div>

          {/* Compatible Agents */}
          {(downstream.length > 0 || upstream.length > 0) && (
            <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-6">
              <h2 className="text-sm font-medium text-[#f1f5f9] mb-4 flex items-center gap-2">
                <GitBranch size={14} className="text-[#00d4ff]" />
                Pipeline Composition
              </h2>

              {upstream.length > 0 && (
                <div className="mb-4">
                  <h3 className="text-xs text-[#64748b] mb-2">
                    Works well before this agent
                  </h3>
                  <div className="space-y-1.5">
                    {upstream.map((c) => (
                      <Link
                        key={c.agent.id}
                        to={`/agents/${c.agent.id}`}
                        className="flex items-center gap-2 rounded-lg bg-[#0a0a0f] border border-white/[0.04] px-3 py-2 no-underline hover:border-[#00d4ff]/20 transition-colors"
                      >
                        <TrustRing score={c.agent.trust_score} size={24} />
                        <div className="flex-1 min-w-0">
                          <div className="text-xs text-[#f1f5f9] font-medium truncate">
                            {c.agent.name}
                          </div>
                          <div className="text-[10px] text-[#64748b] truncate">
                            {c.matching_fields.join(", ")}
                          </div>
                        </div>
                        <ArrowRight size={10} className="text-[#64748b]" />
                        <span className="text-[10px] text-[#64748b]">
                          {Math.round(c.compatibility_score * 100)}%
                        </span>
                      </Link>
                    ))}
                  </div>
                </div>
              )}

              {downstream.length > 0 && (
                <div>
                  <h3 className="text-xs text-[#64748b] mb-2">
                    Works well after this agent
                  </h3>
                  <div className="space-y-1.5">
                    {downstream.map((c) => (
                      <Link
                        key={c.agent.id}
                        to={`/agents/${c.agent.id}`}
                        className="flex items-center gap-2 rounded-lg bg-[#0a0a0f] border border-white/[0.04] px-3 py-2 no-underline hover:border-[#00d4ff]/20 transition-colors"
                      >
                        <TrustRing score={c.agent.trust_score} size={24} />
                        <div className="flex-1 min-w-0">
                          <div className="text-xs text-[#f1f5f9] font-medium truncate">
                            {c.agent.name}
                          </div>
                          <div className="text-[10px] text-[#64748b] truncate">
                            {c.matching_fields.join(", ")}
                          </div>
                        </div>
                        <ArrowRight size={10} className="text-[#64748b]" />
                        <span className="text-[10px] text-[#64748b]">
                          {Math.round(c.compatibility_score * 100)}%
                        </span>
                      </Link>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right: Submit Form */}
        <div className="space-y-4">
          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5 sticky top-20">
            <h2 className="text-sm font-medium text-[#f1f5f9] mb-4 flex items-center gap-2">
              <Play size={14} className="text-[#00d4ff]" />
              Run Agent
            </h2>

            <div className="space-y-3 mb-4">
              <div>
                <label className="block text-xs text-[#64748b] mb-1">API Key</label>
                <input
                  type="password"
                  placeholder="af_..."
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-[#0a0a0f] border border-white/[0.06] text-sm text-[#f1f5f9] placeholder-[#64748b] focus:outline-none focus:border-[#00d4ff]/30"
                />
              </div>

              {capabilities.inputs.map((inp) => (
                <div key={inp.name}>
                  <label className="block text-xs text-[#64748b] mb-1">
                    {inp.name} {inp.required && <span className="text-amber-400">*</span>}
                  </label>
                  <input
                    type="text"
                    placeholder={inp.default || `Enter ${inp.name}...`}
                    value={inputs[inp.name] || ""}
                    onChange={(e) => setInputs({ ...inputs, [inp.name]: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-[#0a0a0f] border border-white/[0.06] text-sm text-[#f1f5f9] placeholder-[#64748b] focus:outline-none focus:border-[#00d4ff]/30"
                  />
                </div>
              ))}
            </div>

            <div className="flex items-center justify-between text-xs text-[#64748b] mb-4 px-1">
              <span>Est. duration</span>
              <span className="text-[#f1f5f9] font-medium">
                ~{Math.round(runtime.estimated_duration_seconds / 60)}min
              </span>
            </div>

            <button
              onClick={handleSubmit}
              disabled={submitting || !apiKey}
              className="w-full py-2.5 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-sm font-medium transition-all hover:bg-[#00bfea] disabled:opacity-40 disabled:cursor-not-allowed"
              style={{ transition: "background 0.2s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.2s" }}
            >
              {submitting ? "Submitting..." : "Submit Task"}
            </button>

            {error && (
              <p className="mt-3 text-xs text-red-400 text-center">{error}</p>
            )}

            {result && (
              <div className="mt-4 rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3">
                <p className="text-xs text-emerald-400 mb-1">Task submitted!</p>
                <Link
                  to="/tasks"
                  className="text-xs text-[#00d4ff] hover:underline"
                >
                  View in Tasks →
                </Link>
                <p className="text-[10px] text-[#64748b] mt-1 font-mono">{result.id}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
