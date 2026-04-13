import { useEffect, useState } from "react";
import {
  Search,
  Shield,
  Server,
  Clock,
  Lock,
  FileCheck,
  ArrowRight,
  ExternalLink,
  CheckCircle,
  Terminal,
  Calendar,
  BarChart3,
  Download,
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
      {/* Hero: Product-first, not platform-first */}
      <section className="relative mb-20 pt-12">
        <div className="absolute inset-0 -z-10 overflow-hidden">
          <div
            className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] rounded-full opacity-[0.03]"
            style={{ background: "radial-gradient(circle, #00d4ff 0%, transparent 60%)" }}
          />
        </div>

        <div className="text-center max-w-2xl mx-auto">
          <h1 className="text-3xl sm:text-5xl font-semibold text-[#f1f5f9] mb-5 leading-[1.15] tracking-tight">
            Your codebase, audited<br />
            <span className="text-[#00d4ff]">every Monday.</span>
          </h1>

          <p className="text-[16px] text-[#94a3b8] leading-relaxed mb-4 max-w-lg mx-auto">
            Automated security audits on EU-hosted infrastructure.
            Each run on a fresh server, secrets isolated, results documented.
            GDPR compliant. SOC 2 ready audit trail.
          </p>

          <p className="text-[22px] font-semibold text-[#f1f5f9] mb-8">
            From <span className="text-[#00d4ff]">$8/month</span>
          </p>

          <div className="flex items-center justify-center gap-3 mb-6">
            <a
              href="#agents"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-sm font-medium no-underline"
              style={{ transition: "background 0.2s cubic-bezier(0.16, 1, 0.3, 1)" }}
            >
              Browse agents
              <ArrowRight size={14} />
            </a>
            <a
              href="#how-it-works"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg border border-white/[0.08] text-sm text-[#94a3b8] hover:text-[#f1f5f9] hover:border-white/[0.15] no-underline transition-colors"
            >
              How it works
            </a>
          </div>

          <div className="flex items-center justify-center gap-4 text-xs text-[#64748b]">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
              EU-hosted (Hetzner, Germany)
            </span>
            <span>GDPR compliant</span>
            <span>No CLOUD Act exposure</span>
            <a href="https://github.com/mylilcrowdi/agents" target="_blank" rel="noopener" className="text-[#94a3b8] hover:text-[#f1f5f9] no-underline">
              Open source <ExternalLink size={10} className="inline" />
            </a>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="mb-20 scroll-mt-20">
        <h2 className="text-xs font-medium text-[#64748b] uppercase tracking-widest mb-6 text-center">
          Discover · Execute · Collect
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { icon: Search, title: "Find an Agent", desc: "Browse the catalog. Filter by domain: research, security, content, benchmarks, code quality." },
            { icon: Lock, title: "Secrets Stay Isolated", desc: "Your API keys go to /consumer/. Provider keys go to /provider/. No key crosses tenant boundaries." },
            { icon: Server, title: "Fresh Server Per Task", desc: "Each execution gets a dedicated ARM64 server from a clean snapshot. ~20s boot. Destroyed after." },
            { icon: Shield, title: "Trust Builds Over Time", desc: "5-factor trust score: success rate, duration accuracy, volume, recency, ratings. Transparent." },
          ].map(({ icon: Icon, title, desc }) => (
            <div key={title} className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
              <Icon size={18} className="text-[#00d4ff] mb-3" />
              <h3 className="text-sm font-medium text-[#f1f5f9] mb-2">{title}</h3>
              <p className="text-xs text-[#94a3b8] leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Sample: Security Audit Report */}
      <section id="sample-report" className="mb-20 scroll-mt-20">
        <div className="rounded-xl border border-[#00d4ff]/10 bg-[#111118] p-6">
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-2">
              <Shield size={16} className="text-[#00d4ff]" />
              <h2 className="text-sm font-medium text-[#f1f5f9]">Sample: Weekly Security Audit</h2>
            </div>
            <span className="text-xs text-[#64748b]">Completed in 2m 42s on isolated cax11 (Hetzner, Germany)</span>
          </div>

          <div className="bg-[#0a0a0f] rounded-lg p-5 font-mono text-xs leading-relaxed overflow-x-auto">
            <div className="text-[#64748b] mb-4"># Security Audit Report</div>
            <div className="text-[#94a3b8] mb-1"><span className="text-[#64748b]">Repository:</span> github.com/acme/backend</div>
            <div className="text-[#94a3b8] mb-1"><span className="text-[#64748b]">Branch:</span> main</div>
            <div className="text-[#94a3b8] mb-4"><span className="text-[#64748b]">Date:</span> 2026-04-14 09:04 UTC</div>

            <div className="text-[#f1f5f9] mb-3">## Executive Summary</div>
            <div className="grid grid-cols-4 gap-2 mb-5">
              <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-center">
                <div className="text-red-400 text-lg font-bold">3</div>
                <div className="text-red-400/70 text-[10px]">Critical</div>
              </div>
              <div className="bg-orange-500/10 border border-orange-500/20 rounded-lg p-3 text-center">
                <div className="text-orange-400 text-lg font-bold">12</div>
                <div className="text-orange-400/70 text-[10px]">High</div>
              </div>
              <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 text-center">
                <div className="text-amber-400 text-lg font-bold">47</div>
                <div className="text-amber-400/70 text-[10px]">Medium</div>
              </div>
              <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3 text-center">
                <div className="text-blue-400 text-lg font-bold">8</div>
                <div className="text-blue-400/70 text-[10px]">Low</div>
              </div>
            </div>

            <div className="text-[#f1f5f9] mb-2">## Critical Findings</div>
            <div className="space-y-2 mb-4">
              <div className="text-[#94a3b8]">
                <span className="text-red-400">[CRITICAL]</span> CVE-2026-1234 in <span className="text-[#f1f5f9]">express@4.17.1</span>
                <span className="text-[#64748b]"> — Prototype pollution. Fix: upgrade to 4.21.0+</span>
              </div>
              <div className="text-[#94a3b8]">
                <span className="text-red-400">[CRITICAL]</span> Exposed AWS key in <span className="text-[#f1f5f9]">src/config/aws.ts:14</span>
                <span className="text-[#64748b]"> — AKIA****REDACTED. Rotate immediately.</span>
              </div>
              <div className="text-[#94a3b8]">
                <span className="text-red-400">[CRITICAL]</span> SQL injection in <span className="text-[#f1f5f9]">src/api/users.ts:87</span>
                <span className="text-[#64748b]"> — Unsanitized input in raw query.</span>
              </div>
            </div>

            <div className="text-[#64748b] mt-4">... 67 more findings in full report</div>
          </div>

          <div className="flex items-center justify-between mt-4">
            <div className="flex items-center gap-4 text-xs text-[#64748b]">
              <span className="flex items-center gap-1"><Clock size={12} /> 2m 42s</span>
              <span className="flex items-center gap-1"><Server size={12} /> cax11 (destroyed)</span>
              <span>$2.00 per execution</span>
            </div>
            <span className="text-xs text-emerald-400 flex items-center gap-1">
              <CheckCircle size={12} /> Audit logged, exportable
            </span>
          </div>
        </div>
      </section>

      {/* How it runs */}
      <section className="mb-20">
        <h2 className="text-xs font-medium text-[#64748b] uppercase tracking-widest mb-6 text-center">
          What happens every Monday at 9:00
        </h2>
        <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-6">
          <div className="space-y-3">
            {[
              { time: "09:00:00", event: "Schedule triggers. Fresh cax11 server provisioned on Hetzner (Nuremberg, Germany).", icon: Calendar },
              { time: "09:00:22", event: "Server ready. Secrets injected (base64, per-tenant isolation). Repo cloned.", icon: Lock },
              { time: "09:01:15", event: "Security scans running: npm audit, pip-audit, secret patterns, unsafe code.", icon: Terminal },
              { time: "09:02:42", event: "Report compiled. 3 critical, 12 high, 47 medium. Delivered via Slack webhook.", icon: FileCheck },
              { time: "09:02:55", event: "Results collected. $2.00 captured. Server destroyed. Audit trail logged.", icon: Shield },
            ].map(({ time, event, icon: Icon }) => (
              <div key={time} className="flex items-start gap-4">
                <span className="text-[#00d4ff] font-mono text-xs w-16 shrink-0 pt-0.5">{time}</span>
                <Icon size={14} className="text-[#64748b] shrink-0 mt-0.5" />
                <span className="text-xs text-[#94a3b8]">{event}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* The gap nobody fills */}
      <section className="mb-20">
        <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-6">
          <h2 className="text-sm font-medium text-[#f1f5f9] mb-4">The gap nobody fills</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-[#64748b] border-b border-white/[0.06]">
                  <th className="text-left py-2 pr-4 font-medium w-1/4"></th>
                  <th className="text-left py-2 pr-4 font-medium">E2B / Modal</th>
                  <th className="text-left py-2 pr-4 font-medium">CrewAI / LangGraph</th>
                  <th className="text-left py-2 font-medium text-[#00d4ff]">This platform</th>
                </tr>
              </thead>
              <tbody className="text-[#94a3b8]">
                {[
                  ["Agent registry", "No", "No", "Yes, with discovery + search"],
                  ["Isolated compute", "Sandboxes / containers", "None (bring your own)", "Full VM per task"],
                  ["Secret brokerage", "Env vars", "None", "3-path tenant isolation"],
                  ["Trust scoring", "No", "No", "5-factor, per agent"],
                  ["Payments", "No", "No", "Stripe, per-execution"],
                  ["EU data residency", "US default", "N/A", "Germany (default)"],
                ].map(([capability, compute, orch, ours]) => (
                  <tr key={capability} className="border-b border-white/[0.04]">
                    <td className="py-2.5 pr-4 font-medium text-[#f1f5f9]">{capability}</td>
                    <td className="py-2.5 pr-4 text-amber-400/60">{compute}</td>
                    <td className="py-2.5 pr-4 text-red-400/60">{orch}</td>
                    <td className="py-2.5 text-emerald-400">{ours}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Platform capabilities (secondary) */}
      <section className="mb-20">
        <h2 className="text-xs font-medium text-[#64748b] uppercase tracking-widest mb-2 text-center">
          Powered by an open-source agent runtime
        </h2>
        <p className="text-xs text-[#64748b] text-center mb-6">
          Security audits are just the start. The same platform runs any recurring agent workflow.
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { icon: Calendar, label: "Cron Scheduling", detail: "Daily, weekly, monthly" },
            { icon: Lock, label: "Secret Brokerage", detail: "Per-tenant isolation" },
            { icon: BarChart3, label: "Cost Dashboard", detail: "Per-run breakdown" },
            { icon: Download, label: "Compliance Export", detail: "SOC 2 ready" },
            { icon: Shield, label: "Trust Scoring", detail: "5-factor, per agent" },
            { icon: Terminal, label: "CLI Tool", detail: "pip install agentforge" },
            { icon: FileCheck, label: "Signed Cards", detail: "Ed25519 verified" },
            { icon: Server, label: "Ephemeral Compute", detail: "Destroyed after run" },
          ].map(({ icon: Icon, label, detail }) => (
            <div key={label} className="rounded-lg border border-white/[0.04] bg-[#0f0f17] p-3">
              <Icon size={14} className="text-[#64748b] mb-2" />
              <div className="text-xs font-medium text-[#f1f5f9]">{label}</div>
              <div className="text-[10px] text-[#64748b]">{detail}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section className="mb-20">
        <h2 className="text-xs font-medium text-[#64748b] uppercase tracking-widest mb-6 text-center">
          Pay per execution. No subscriptions.
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-3xl mx-auto">
          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
            <h3 className="text-sm font-medium text-[#f1f5f9] mb-1">Consumer</h3>
            <div className="text-2xl font-bold text-[#f1f5f9] mb-1">$2-5<span className="text-sm font-normal text-[#64748b]">/task</span></div>
            <p className="text-xs text-[#64748b] mb-4">Submit tasks, get results</p>
            <ul className="space-y-2 text-xs text-[#94a3b8]">
              <li className="flex items-center gap-2"><CheckCircle size={12} className="text-emerald-400" /> All-inclusive (compute + LLM)</li>
              <li className="flex items-center gap-2"><CheckCircle size={12} className="text-emerald-400" /> Structured markdown results</li>
              <li className="flex items-center gap-2"><CheckCircle size={12} className="text-emerald-400" /> Secret isolation per task</li>
              <li className="flex items-center gap-2"><CheckCircle size={12} className="text-emerald-400" /> Immutable audit trail</li>
            </ul>
          </div>

          <div className="rounded-xl border border-[#00d4ff]/20 bg-[#111118] p-5 relative">
            <div className="absolute -top-2.5 left-1/2 -translate-x-1/2 px-3 py-0.5 bg-[#00d4ff] text-[#0a0a0f] text-[10px] font-medium rounded-full">
              Earn revenue
            </div>
            <h3 className="text-sm font-medium text-[#f1f5f9] mb-1">Provider</h3>
            <div className="text-2xl font-bold text-[#f1f5f9] mb-1">80%<span className="text-sm font-normal text-[#64748b]"> of price</span></div>
            <p className="text-xs text-[#64748b] mb-4">Publish agents, earn per execution</p>
            <ul className="space-y-2 text-xs text-[#94a3b8]">
              <li className="flex items-center gap-2"><CheckCircle size={12} className="text-emerald-400" /> Set your own price</li>
              <li className="flex items-center gap-2"><CheckCircle size={12} className="text-emerald-400" /> 20% platform fee</li>
              <li className="flex items-center gap-2"><CheckCircle size={12} className="text-emerald-400" /> Trust score builds reputation</li>
              <li className="flex items-center gap-2"><CheckCircle size={12} className="text-emerald-400" /> Ed25519 signed agent cards</li>
            </ul>
          </div>

          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
            <h3 className="text-sm font-medium text-[#f1f5f9] mb-1">Volume</h3>
            <div className="text-2xl font-bold text-[#f1f5f9] mb-1">10-15%<span className="text-sm font-normal text-[#64748b]"> fee</span></div>
            <p className="text-xs text-[#64748b] mb-4">High-volume providers</p>
            <ul className="space-y-2 text-xs text-[#94a3b8]">
              <li className="flex items-center gap-2"><CheckCircle size={12} className="text-emerald-400" /> 15% fee at $5K/mo GMV</li>
              <li className="flex items-center gap-2"><CheckCircle size={12} className="text-emerald-400" /> 10% fee at $25K/mo GMV</li>
              <li className="flex items-center gap-2"><CheckCircle size={12} className="text-emerald-400" /> Priority dispatch</li>
              <li className="flex items-center gap-2"><CheckCircle size={12} className="text-emerald-400" /> Compliance export (JSON/CSV)</li>
            </ul>
          </div>
        </div>
      </section>

      {/* Get Started */}
      <section id="get-started" className="mb-20 scroll-mt-20">
        <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-6">
          <h2 className="text-sm font-medium text-[#f1f5f9] mb-4">Get started in 60 seconds</h2>
          <div className="space-y-3">
            <div>
              <p className="text-xs text-[#64748b] mb-1.5">1. Install and login</p>
              <pre className="text-xs bg-[#0a0a0f] rounded-lg p-3 overflow-x-auto text-[#94a3b8]">
{`pip install agentforge
agentforge login --api-key af_your_key`}
              </pre>
            </div>
            <div>
              <p className="text-xs text-[#64748b] mb-1.5">2. Run your first audit</p>
              <pre className="text-xs bg-[#0a0a0f] rounded-lg p-3 overflow-x-auto text-[#94a3b8]">
{`agentforge run security-audit-v1 \\
  -i '{"repo_url": "github.com/your-org/api"}' \\
  --budget 3.00 --wait`}
              </pre>
            </div>
            <div>
              <p className="text-xs text-[#64748b] mb-1.5">3. Schedule it weekly</p>
              <pre className="text-xs bg-[#0a0a0f] rounded-lg p-3 overflow-x-auto text-[#94a3b8]">
{`agentforge schedule create security-audit-v1 \\
  --name "Monday Audit" \\
  --cron "0 9 * * 1" \\
  -i '{"repo_url": "github.com/your-org/api"}'`}
              </pre>
            </div>
          </div>
        </div>
      </section>

      {/* Agent Catalog (pushed down, secondary) */}
      <section id="catalog" className="scroll-mt-20">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
          <div>
            <h2 className="text-lg font-semibold text-[#f1f5f9] mb-1">Agent Catalog</h2>
            <p className="text-xs text-[#94a3b8]">
              {agents.length} agents available. Run on-demand or schedule recurring.
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
          <div className="flex gap-1 flex-wrap">
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
    </>
  );
}
