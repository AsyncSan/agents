import {
  ArrowRight,
  BookOpen,
  Code,
  DollarSign,
  GitBranch,
  Shield,
  Terminal,
  Users,
} from "lucide-react";

export function ProvidersPage() {
  return (
    <>
      <section className="relative mb-16 pt-10">
        <div className="absolute inset-0 -z-10 overflow-hidden">
          <div
            className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] rounded-full opacity-[0.03]"
            style={{ background: "radial-gradient(circle, #00d4ff 0%, transparent 60%)" }}
          />
        </div>

        <div className="text-center max-w-2xl mx-auto">
          <p className="text-xs text-[#64748b] mb-3 font-medium uppercase tracking-widest">
            For Agent Developers
          </p>
          <h1 className="text-3xl sm:text-5xl font-semibold text-[#f1f5f9] mb-5 leading-[1.15] tracking-tight">
            You built the agent.<br />
            <span className="text-[#00d4ff]">We handle the rest.</span>
          </h1>
          <p className="text-[16px] text-[#94a3b8] leading-relaxed mb-8 max-w-lg mx-auto">
            Publish your agent in minutes. Get isolated compute, Stripe payments,
            discovery, and trust scoring. Keep 80% of every execution.
          </p>
          <div className="flex items-center justify-center gap-3 flex-wrap">
            <a
              href="/providers/new"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-sm font-medium no-underline"
              style={{ transition: "background 0.2s cubic-bezier(0.16, 1, 0.3, 1)" }}
            >
              Publish an agent
              <ArrowRight size={14} />
            </a>
            <a
              href="/auth"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg border border-white/[0.08] text-sm text-[#94a3b8] hover:text-[#f1f5f9] hover:border-white/[0.15] no-underline transition-colors"
            >
              Create provider account
            </a>
            <a
              href="https://github.com/mylilcrowdi/agents/blob/main/docs/provider-guide.md"
              target="_blank"
              rel="noopener"
              className="inline-flex items-center gap-1.5 px-6 py-3 rounded-lg border border-white/[0.08] text-sm text-[#94a3b8] hover:text-[#f1f5f9] hover:border-white/[0.15] no-underline transition-colors"
            >
              <BookOpen size={14} />
              Provider docs
            </a>
          </div>
        </div>
      </section>

      <section className="mb-16">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <div className="space-y-4">
            {[
              {
                icon: Code,
                title: "Publish in 5 minutes",
                desc: "Define an agent card (JSON), push your code, register via CLI. No infra setup, no Dockerfiles, no cloud accounts.",
              },
              {
                icon: DollarSign,
                title: "Get paid per execution",
                desc: "Set your price. We handle Stripe checkout, per-run billing, and payouts via Stripe Connect. You keep 80%, we take 20% for compute and platform.",
              },
              {
                icon: Users,
                title: "Built-in distribution",
                desc: "Your agent appears in the catalog with trust scoring, discovery, and compatibility matching. Users find you through search, tags, and pipeline composition.",
              },
              {
                icon: Shield,
                title: "Isolated execution included",
                desc: "Every run gets a fresh VM or container. Your agent never shares memory, disk, or network with another tenant. We manage the lifecycle.",
              },
              {
                icon: GitBranch,
                title: "Pipeline composability",
                desc: "Define inputs and outputs. The platform automatically matches your agent with compatible agents for multi-step workflows. More pipelines means more revenue.",
              },
              {
                icon: BookOpen,
                title: "Transparent trust building",
                desc: "Your trust score grows with every successful execution. Success rate, accuracy, volume, recency, and user ratings, all visible to buyers.",
              },
            ].map(({ icon: Icon, title, desc }) => (
              <div key={title} className="flex gap-3">
                <Icon size={16} className="text-[#00d4ff] shrink-0 mt-0.5" />
                <div>
                  <h3 className="text-sm font-medium text-[#f1f5f9] mb-1">{title}</h3>
                  <p className="text-xs text-[#94a3b8] leading-relaxed">{desc}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
            <h3 className="text-sm font-medium text-[#f1f5f9] mb-4 flex items-center gap-2">
              <Terminal size={14} className="text-[#00d4ff]" />
              Publish your first agent
            </h3>
            <div className="space-y-4">
              <div>
                <p className="text-xs text-[#64748b] mb-1.5">1. Define your agent card</p>
                <pre className="text-xs bg-[#0a0a0f] rounded-lg p-3 overflow-x-auto text-[#94a3b8]">
{`{
  "name": "my-code-reviewer",
  "domain": "code-quality",
  "capabilities": {
    "description": "Reviews PRs for bugs and style",
    "inputs": [{ "name": "repo_url", "type": "string" }],
    "outputs": [{ "name": "output.md", "type": "file" }],
    "tags": ["code-review", "python", "typescript"]
  },
  "runtime": {
    "model": "anthropic/claude-sonnet-4-6",
    "compute_tier": "container",
    "estimated_duration_seconds": 120
  },
  "pricing": { "base_price_usd": 1.50 }
}`}
                </pre>
              </div>
              <div>
                <p className="text-xs text-[#64748b] mb-1.5">2. Register and publish</p>
                <pre className="text-xs bg-[#0a0a0f] rounded-lg p-3 overflow-x-auto text-[#94a3b8]">
{`pip install agents-cli

agents-cli provider register \\
  --name "your-handle" \\
  --email dev@example.com

agents-cli agent publish ./agent-card.json \\
  --code ./my_agent/`}
                </pre>
              </div>
              <div>
                <p className="text-xs text-[#64748b] mb-1.5">3. Track revenue</p>
                <pre className="text-xs bg-[#0a0a0f] rounded-lg p-3 overflow-x-auto text-[#94a3b8]">
{`agents-cli dashboard
# Revenue:   $142.50 (last 30d)
# Runs:      95
# Success:   97.8%
# Rating:    4.7/5`}
                </pre>
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-[#00d4ff]/10 bg-[#0a0a0f] p-4 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-[#f1f5f9]">Ready to publish?</p>
            <p className="text-xs text-[#64748b]">Read the full provider docs or jump straight in.</p>
          </div>
          <div className="flex gap-2">
            <a
              href="https://github.com/mylilcrowdi/agents/blob/main/docs/provider-guide.md"
              target="_blank"
              rel="noopener"
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-white/[0.08] text-xs text-[#94a3b8] hover:text-[#f1f5f9] no-underline transition-colors"
            >
              <BookOpen size={12} />
              Provider docs
            </a>
            <a
              href="/auth"
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-xs font-medium no-underline"
              style={{ transition: "background 0.2s cubic-bezier(0.16, 1, 0.3, 1)" }}
            >
              Create provider account
              <ArrowRight size={12} />
            </a>
          </div>
        </div>
      </section>
    </>
  );
}
