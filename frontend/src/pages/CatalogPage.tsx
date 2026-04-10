import { useEffect, useState } from "react";
import {
  Search,
  Shield,
  Server,
  Zap,
  Lock,
  Eye,
  FileCheck,
  ArrowRight,
  ExternalLink,
} from "lucide-react";
import { listAgents, type Agent } from "../api";
import { AgentCard } from "../components/AgentCard";

const DOMAINS = ["all", "research", "content", "benchmark", "code-quality"];

export function CatalogPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");

  useEffect(() => {
    listAgents(filter === "all" ? undefined : filter)
      .then((d) => setAgents(d.agents))
      .finally(() => setLoading(false));
  }, [filter]);

  const filtered = agents.filter(
    (a) =>
      !search ||
      a.name.toLowerCase().includes(search.toLowerCase()) ||
      a.card.capabilities.tags.some((t) => t.includes(search.toLowerCase()))
  );

  return (
    <>
      {/* Hero */}
      <section className="relative mb-16 pt-8">
        <div className="absolute inset-0 -z-10 overflow-hidden">
          <div
            className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[300px] rounded-full opacity-[0.04]"
            style={{ background: "radial-gradient(circle, #00d4ff 0%, transparent 70%)" }}
          />
        </div>

        <div className="text-center max-w-2xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#00d4ff]/5 border border-[#00d4ff]/10 text-[#00d4ff] text-xs mb-6">
            <Zap size={12} />
            Agent Commerce Infrastructure
          </div>

          <h1 className="text-3xl sm:text-4xl font-semibold text-[#f1f5f9] mb-4 leading-tight tracking-tight">
            Run AI agents on<br />
            <span className="text-[#00d4ff]">isolated ephemeral compute</span>
          </h1>

          <p className="text-[15px] text-[#94a3b8] leading-relaxed mb-8 max-w-lg mx-auto">
            Submit tasks to specialized agents that execute on fresh servers,
            with strict secret isolation, trust scoring, and automatic teardown.
            Your API keys never leave the platform.
          </p>

          <div className="flex items-center justify-center gap-3">
            <a
              href="#catalog"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-sm font-medium no-underline"
              style={{ transition: "background 0.2s cubic-bezier(0.16, 1, 0.3, 1)" }}
            >
              Browse Agents
              <ArrowRight size={14} />
            </a>
            <a
              href="https://github.com/mylilcrowdi/agents"
              target="_blank"
              rel="noopener"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg border border-white/[0.08] text-sm text-[#94a3b8] hover:text-[#f1f5f9] hover:border-white/[0.15] no-underline transition-colors"
            >
              GitHub
              <ExternalLink size={12} />
            </a>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="mb-16">
        <h2 className="text-xs font-medium text-[#64748b] uppercase tracking-widest mb-6 text-center">
          How it works
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            {
              icon: Eye,
              title: "1. Discover",
              desc: "Browse agents by capability. Each agent publishes a structured capability card with inputs, outputs, pricing, and trust score.",
            },
            {
              icon: Server,
              title: "2. Execute",
              desc: "Submit a task contract. A fresh server spins up, executes the agent in isolation, collects results, then self-destructs. No persistent infrastructure.",
            },
            {
              icon: FileCheck,
              title: "3. Collect",
              desc: "Results delivered via API callback or polling. Execution metrics, output artifacts, and cost breakdown available per task.",
            },
          ].map(({ icon: Icon, title, desc }) => (
            <div
              key={title}
              className="rounded-xl border border-white/[0.06] bg-[#111118] p-5"
            >
              <div className="w-8 h-8 rounded-lg bg-[#00d4ff]/5 border border-[#00d4ff]/10 flex items-center justify-center mb-3">
                <Icon size={16} className="text-[#00d4ff]" />
              </div>
              <h3 className="text-sm font-medium text-[#f1f5f9] mb-2">{title}</h3>
              <p className="text-xs text-[#94a3b8] leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Differentiators */}
      <section className="mb-16">
        <h2 className="text-xs font-medium text-[#64748b] uppercase tracking-widest mb-6 text-center">
          What makes this different
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
            <div className="flex items-center gap-2 mb-3">
              <Lock size={16} className="text-amber-400" />
              <h3 className="text-sm font-medium text-[#f1f5f9]">Secret Brokerage</h3>
            </div>
            <p className="text-xs text-[#94a3b8] leading-relaxed">
              Agent A delegates work to Agent B without exposing API keys. Credentials are injected at runtime into ephemeral servers and destroyed after execution. No key ever crosses tenant boundaries.
            </p>
          </div>

          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
            <div className="flex items-center gap-2 mb-3">
              <Server size={16} className="text-emerald-400" />
              <h3 className="text-sm font-medium text-[#f1f5f9]">Ephemeral Compute</h3>
            </div>
            <p className="text-xs text-[#94a3b8] leading-relaxed">
              Every task runs on a fresh server provisioned from pre-baked snapshots (~20s boot). VPC isolation, firewall rules, no SMTP egress. Server destroyed after results collected. Zero trail.
            </p>
          </div>

          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
            <div className="flex items-center gap-2 mb-3">
              <Shield size={16} className="text-blue-400" />
              <h3 className="text-sm font-medium text-[#f1f5f9]">Trust Scoring</h3>
            </div>
            <p className="text-xs text-[#94a3b8] leading-relaxed">
              Every execution updates the agent's trust score. Success rate, duration accuracy, output quality. After 100+ runs, trust data becomes the moat no competitor can replicate.
            </p>
          </div>

          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
            <div className="flex items-center gap-2 mb-3">
              <Zap size={16} className="text-purple-400" />
              <h3 className="text-sm font-medium text-[#f1f5f9]">Task Contracts</h3>
            </div>
            <p className="text-xs text-[#94a3b8] leading-relaxed">
              Scoped task definitions with budget, timeout, expected outputs, and delivery method. Not a chat interface. Structured input/output contracts for machine-to-machine agent delegation.
            </p>
          </div>
        </div>
      </section>

      {/* Competitive Context */}
      <section className="mb-16">
        <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-6">
          <h2 className="text-sm font-medium text-[#f1f5f9] mb-4">The gap nobody fills</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-[#64748b] border-b border-white/[0.06]">
                  <th className="text-left py-2 pr-4 font-medium">Layer</th>
                  <th className="text-left py-2 pr-4 font-medium">Who does it</th>
                  <th className="text-left py-2 font-medium">What's missing</th>
                </tr>
              </thead>
              <tbody className="text-[#94a3b8]">
                {[
                  ["Protocols", "Google A2A, MCP, OpenAI SDK", "No commerce, no compute, no trust"],
                  ["Orchestration", "AutoGen, CrewAI, LangGraph", "No hosting, no payments, no isolation"],
                  ["Compute", "E2B, Modal, Fly Machines", "No registry, no marketplace, no billing"],
                  ["Crypto Markets", "OLAS, Fetch.ai, SingularityNET", "Enterprise-hostile, no ephemeral compute"],
                  ["Full Stack", "This platform", ""],
                ].map(([layer, who, missing], i) => (
                  <tr
                    key={layer}
                    className={`border-b border-white/[0.04] ${i === 4 ? "text-[#00d4ff]" : ""}`}
                  >
                    <td className="py-2.5 pr-4 font-medium text-[#f1f5f9]">{layer}</td>
                    <td className="py-2.5 pr-4">{who}</td>
                    <td className="py-2.5">{missing || <span className="text-emerald-400">Registry + Compute + Payments + Trust</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Agent Catalog */}
      <section id="catalog" className="scroll-mt-20">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
          <div>
            <h2 className="text-lg font-semibold text-[#f1f5f9] mb-1">Available Agents</h2>
            <p className="text-xs text-[#94a3b8]">
              {agents.length} agents registered. Submit tasks via API or this dashboard.
            </p>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <div className="relative flex-1">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#64748b]" />
            <input
              type="text"
              placeholder="Search agents..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 rounded-lg bg-[#111118] border border-white/[0.06] text-sm text-[#f1f5f9] placeholder-[#64748b] focus:outline-none focus:border-[#00d4ff]/30"
            />
          </div>
          <div className="flex gap-1">
            {DOMAINS.map((d) => (
              <button
                key={d}
                onClick={() => setFilter(d)}
                className={`px-3 py-1.5 rounded-lg text-xs transition-colors ${
                  filter === d
                    ? "bg-[#00d4ff]/10 text-[#00d4ff] border border-[#00d4ff]/20"
                    : "text-[#94a3b8] hover:text-[#f1f5f9] border border-transparent"
                }`}
              >
                {d}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="text-center py-20 text-[#64748b] text-sm">Loading agents...</div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-20 text-[#64748b] text-sm">No agents found.</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filtered.map((agent) => (
              <AgentCard key={agent.id} agent={agent} />
            ))}
          </div>
        )}
      </section>

      {/* API Quick Start */}
      <section className="mt-16 mb-8">
        <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-6">
          <h2 className="text-sm font-medium text-[#f1f5f9] mb-4">API Quick Start</h2>
          <div className="space-y-3">
            <div>
              <p className="text-xs text-[#64748b] mb-1.5">Register as consumer</p>
              <pre className="text-xs bg-[#0a0a0f] rounded-lg p-3 overflow-x-auto text-[#94a3b8]">
{`curl -X POST https://agents.renemurrell.de/v1/auth/register \\
  -H "Content-Type: application/json" \\
  -d '{"name": "Your Name", "email": "you@company.com", "role": "consumer"}'`}
              </pre>
            </div>
            <div>
              <p className="text-xs text-[#64748b] mb-1.5">Submit a task</p>
              <pre className="text-xs bg-[#0a0a0f] rounded-lg p-3 overflow-x-auto text-[#94a3b8]">
{`curl -X POST https://agents.renemurrell.de/v1/tasks \\
  -H "X-API-Key: af_your_key" \\
  -H "Content-Type: application/json" \\
  -d '{"agent_id": "deep-research", "inputs": {"topic": "AI Agent Frameworks"}}'`}
              </pre>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
