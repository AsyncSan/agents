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

const DOMAINS = ["all", "security", "research", "content", "benchmark", "code-quality"];

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
            <Shield size={12} />
            Managed Agent Runtime
          </div>

          <h1 className="text-3xl sm:text-4xl font-semibold text-[#f1f5f9] mb-4 leading-tight tracking-tight">
            AI agents that run themselves.<br />
            <span className="text-[#00d4ff]">You get the results.</span>
          </h1>

          <p className="text-[15px] text-[#94a3b8] leading-relaxed mb-8 max-w-lg mx-auto">
            Scheduled, isolated, audited. Deploy recurring agent workflows
            with built-in cost control, secret isolation, and SOC 2 ready
            compliance exports. Every run on a fresh server, destroyed after.
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
              title: "1. Schedule",
              desc: "Define what agent runs when. Cron-based scheduling: 'Every Monday 9am, audit our codebase.' Or trigger on-demand via API.",
            },
            {
              icon: Server,
              title: "2. Isolate",
              desc: "Every run gets a fresh server. Your secrets injected at runtime, isolated per tenant. Server destroyed after execution. Zero trail, zero risk.",
            },
            {
              icon: FileCheck,
              title: "3. Audit",
              desc: "Every action logged. Cost per run tracked. Compliance export as JSON/CSV. Your agents run with full accountability, SOC 2 ready.",
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

      {/* Enterprise Features */}
      <section className="mb-16">
        <h2 className="text-xs font-medium text-[#64748b] uppercase tracking-widest mb-6 text-center">
          Built for production
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
            <div className="flex items-center gap-2 mb-3">
              <Lock size={16} className="text-amber-400" />
              <h3 className="text-sm font-medium text-[#f1f5f9]">Secret Isolation</h3>
            </div>
            <p className="text-xs text-[#94a3b8] leading-relaxed">
              API keys injected at runtime into ephemeral servers, destroyed after execution. Consumer and provider secrets never cross tenant boundaries. Base64-encoded transport, no shell exposure.
            </p>
          </div>

          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
            <div className="flex items-center gap-2 mb-3">
              <Server size={16} className="text-emerald-400" />
              <h3 className="text-sm font-medium text-[#f1f5f9]">Ephemeral Sandbox</h3>
            </div>
            <p className="text-xs text-[#94a3b8] leading-relaxed">
              Every task runs on a fresh server from pre-baked snapshots (~20s boot). VPC isolation, firewall rules, no SMTP egress. Server destroyed after results collected. Your code never touches shared infrastructure.
            </p>
          </div>

          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
            <div className="flex items-center gap-2 mb-3">
              <Zap size={16} className="text-purple-400" />
              <h3 className="text-sm font-medium text-[#f1f5f9]">Budget Caps</h3>
            </div>
            <p className="text-xs text-[#94a3b8] leading-relaxed">
              Set max_cost_usd per task, per schedule, per pipeline. No token spirals, no surprise bills. Execution dashboard with daily cost trends and per-agent breakdown. You control the spend.
            </p>
          </div>

          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
            <div className="flex items-center gap-2 mb-3">
              <FileCheck size={16} className="text-blue-400" />
              <h3 className="text-sm font-medium text-[#f1f5f9]">Compliance Ready</h3>
            </div>
            <p className="text-xs text-[#94a3b8] leading-relaxed">
              Immutable audit trail for every action. Export as JSON or CSV for SOC 2, ISO 27001. Every event logged: who did what, when, on which resource. Ed25519 signed agent cards for verified identity.
            </p>
          </div>
        </div>
      </section>

      {/* Demo: Security Audit */}
      <section className="mb-16">
        <div className="rounded-xl border border-[#00d4ff]/10 bg-[#111118] p-6">
          <div className="flex items-center gap-2 mb-4">
            <Shield size={16} className="text-[#00d4ff]" />
            <h2 className="text-sm font-medium text-[#f1f5f9]">Example: Weekly Security Audit</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div>
              <p className="text-xs text-[#64748b] mb-3">Schedule configuration</p>
              <pre className="text-xs bg-[#0a0a0f] rounded-lg p-4 overflow-x-auto text-[#94a3b8]">
{`agentforge run security-audit-v1 \\
  -i '{"repo_url": "github.com/acme/api"}' \\
  --budget 3.00 --timeout 300

# Or schedule it:
curl -X POST /v1/schedules \\
  -d '{
    "agent_id": "security-audit-v1",
    "name": "Weekly Security Audit",
    "cron_expression": "0 9 * * 1",
    "inputs": {"repo_url": "..."},
    "constraints": {"max_cost_usd": 3.00}
  }'`}
              </pre>
            </div>
            <div>
              <p className="text-xs text-[#64748b] mb-3">What happens</p>
              <div className="space-y-2 text-xs text-[#94a3b8]">
                <div className="flex items-start gap-2">
                  <span className="text-[#00d4ff] font-mono">09:00</span>
                  <span>Fresh cax11 server provisioned (~20s)</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-[#00d4ff] font-mono">09:01</span>
                  <span>Secrets injected, repo cloned</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-[#00d4ff] font-mono">09:02</span>
                  <span>npm audit + semgrep + trufflehog running</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-[#00d4ff] font-mono">09:04</span>
                  <span>Report compiled: 3 critical, 12 high, 47 medium</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-[#00d4ff] font-mono">09:04</span>
                  <span>Results delivered via Slack webhook</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-[#00d4ff] font-mono">09:05</span>
                  <span>Server destroyed. $1.60 captured. Audit logged.</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Competitive Context */}
      <section className="mb-16">
        <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-6">
          <h2 className="text-sm font-medium text-[#f1f5f9] mb-4">Why not just use Claude Code / ChatGPT?</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-[#64748b] border-b border-white/[0.06]">
                  <th className="text-left py-2 pr-4 font-medium">Capability</th>
                  <th className="text-left py-2 pr-4 font-medium">Chat / IDE Tools</th>
                  <th className="text-left py-2 font-medium">This Platform</th>
                </tr>
              </thead>
              <tbody className="text-[#94a3b8]">
                {[
                  ["Scheduled recurring runs", "Manual, every time", "Cron-based, fully automated"],
                  ["Secret isolation", "Your keys in the prompt", "Injected at runtime, per-tenant isolation"],
                  ["Budget control", "No limits, hope for the best", "max_cost_usd per task, dashboard tracking"],
                  ["Audit trail", "Chat history (not exportable)", "Immutable event log, SOC 2 export"],
                  ["Sandbox isolation", "Runs on your machine", "Fresh server per run, destroyed after"],
                  ["Compliance", "Not addressable", "JSON/CSV export, signed agent cards"],
                ].map(([capability, chatTools, thisPlatform]) => (
                  <tr
                    key={capability}
                    className="border-b border-white/[0.04]"
                  >
                    <td className="py-2.5 pr-4 font-medium text-[#f1f5f9]">{capability}</td>
                    <td className="py-2.5 pr-4 text-red-400/70">{chatTools}</td>
                    <td className="py-2.5 text-emerald-400">{thisPlatform}</td>
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
          <h2 className="text-sm font-medium text-[#f1f5f9] mb-4">Get started in 60 seconds</h2>
          <div className="space-y-3">
            <div>
              <p className="text-xs text-[#64748b] mb-1.5">Install CLI and login</p>
              <pre className="text-xs bg-[#0a0a0f] rounded-lg p-3 overflow-x-auto text-[#94a3b8]">
{`pip install agentforge
agentforge login --api-key af_your_key`}
              </pre>
            </div>
            <div>
              <p className="text-xs text-[#64748b] mb-1.5">Run a security audit</p>
              <pre className="text-xs bg-[#0a0a0f] rounded-lg p-3 overflow-x-auto text-[#94a3b8]">
{`agentforge run security-audit-v1 \\
  -i '{"repo_url": "github.com/your-org/api"}' \\
  --budget 3.00 --wait`}
              </pre>
            </div>
            <div>
              <p className="text-xs text-[#64748b] mb-1.5">Schedule it weekly</p>
              <pre className="text-xs bg-[#0a0a0f] rounded-lg p-3 overflow-x-auto text-[#94a3b8]">
{`curl -X POST /v1/schedules -H "X-API-Key: af_..." \\
  -d '{"agent_id": "security-audit-v1", "name": "Monday Audit",
       "cron_expression": "0 9 * * 1",
       "inputs": {"repo_url": "github.com/your-org/api"}}'`}
              </pre>
            </div>
            <div>
              <p className="text-xs text-[#64748b] mb-1.5">Export compliance log</p>
              <pre className="text-xs bg-[#0a0a0f] rounded-lg p-3 overflow-x-auto text-[#94a3b8]">
{`agentforge compliance-export --start 2026-01-01 --end 2026-12-31 --format csv`}
              </pre>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
