import {
  ArrowRight,
  Building2,
  Calendar,
  FileCheck,
  Lock,
  Plug,
  Shield,
  Terminal,
  Workflow,
} from "lucide-react";

export function EnterprisePage() {
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
            For Engineering Teams
          </p>
          <h1 className="text-3xl sm:text-5xl font-semibold text-[#f1f5f9] mb-5 leading-[1.15] tracking-tight">
            You could run this yourself.<br />
            <span className="text-[#00d4ff]">Here is why teams don't.</span>
          </h1>
          <p className="text-[16px] text-[#94a3b8] leading-relaxed mb-8 max-w-lg mx-auto">
            Scheduled agents, isolated compute, immutable audit trails, scoped
            API keys, and governance that maps to SOC 2 and the EU AI Act.
            One CLI command, not a month of plumbing.
          </p>
          <div className="flex items-center justify-center gap-3">
            <a
              href="mailto:hello@renemurrell.de?subject=Agent%20Platform%20Enterprise%20Inquiry"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-sm font-medium no-underline"
              style={{ transition: "background 0.2s cubic-bezier(0.16, 1, 0.3, 1)" }}
            >
              Talk to us
              <ArrowRight size={14} />
            </a>
            <a
              href="/docs"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg border border-white/[0.08] text-sm text-[#94a3b8] hover:text-[#f1f5f9] hover:border-white/[0.15] no-underline transition-colors"
            >
              Browse docs
            </a>
          </div>
        </div>
      </section>

      <section className="mb-16">
        <h2 className="text-xs font-medium text-[#64748b] uppercase tracking-widest mb-6 text-center">
          What you get
        </h2>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
            <Workflow size={18} className="text-[#00d4ff] mb-3" />
            <h3 className="text-sm font-medium text-[#f1f5f9] mb-2">No infra to maintain</h3>
            <p className="text-xs text-[#94a3b8] leading-relaxed">
              No CI runners to scale, no Docker images to maintain, no secret rotation scripts.
              Each agent task gets a fresh server from a clean snapshot. Provisioned in 20 seconds,
              destroyed after. Your ops team does not need to touch it.
            </p>
          </div>
          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
            <Plug size={18} className="text-[#00d4ff] mb-3" />
            <h3 className="text-sm font-medium text-[#f1f5f9] mb-2">Integrates where you work</h3>
            <p className="text-xs text-[#94a3b8] leading-relaxed">
              Webhook delivery to Slack, Teams, PagerDuty, or any endpoint. Trigger agents from
              CI/CD pipelines via API. Schedule recurring workflows with cron expressions. Export
              results as JSON or CSV for your existing dashboards.
            </p>
          </div>
          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
            <Building2 size={18} className="text-[#00d4ff] mb-3" />
            <h3 className="text-sm font-medium text-[#f1f5f9] mb-2">Governance built in</h3>
            <p className="text-xs text-[#94a3b8] leading-relaxed">
              Every execution logged with immutable audit trail. Per-team API keys with scoped
              permissions. Cost dashboards show spend per agent, per repo, per team. Compliance
              exports map directly to SOC 2 Type II and EU AI Act requirements.
            </p>
          </div>
        </div>
      </section>

      <section className="mb-16">
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

      <section className="mb-16">
        <h2 className="text-xs font-medium text-[#64748b] uppercase tracking-widest mb-6 text-center">
          Why not just run tools yourself?
        </h2>
        <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-6">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-[#64748b] border-b border-white/[0.06]">
                  <th className="text-left py-2 pr-4 font-medium w-1/3"></th>
                  <th className="text-left py-2 pr-4 font-medium">DIY (Semgrep, CI scripts)</th>
                  <th className="text-left py-2 font-medium text-[#00d4ff]">Managed Agents</th>
                </tr>
              </thead>
              <tbody className="text-[#94a3b8]">
                {[
                  ["Setup time", "Days to weeks per tool", "60 seconds, one CLI command"],
                  ["Infra cost", "CI minutes + storage + maintenance", "Pay per run, nothing idle"],
                  ["Secret management", "Your responsibility", "Tenant-isolated, never shared"],
                  ["Multi-repo governance", "Custom scripting per repo", "One schedule, all repos"],
                  ["Audit trail", "Grep through CI logs", "Structured, exportable, immutable"],
                  ["EU data residency", "Depends on your CI provider", "Germany by default"],
                  ["New capabilities", "Evaluate, install, configure", "Browse catalog, run"],
                ].map(([capability, diy, managed]) => (
                  <tr key={capability} className="border-b border-white/[0.04]">
                    <td className="py-2.5 pr-4 font-medium text-[#f1f5f9]">{capability}</td>
                    <td className="py-2.5 pr-4 text-amber-400/60">{diy}</td>
                    <td className="py-2.5 text-emerald-400">{managed}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section className="mb-16">
        <h2 className="text-xs font-medium text-[#64748b] uppercase tracking-widest mb-6 text-center">
          The gap nobody fills
        </h2>
        <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-6">
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

      <section className="text-center">
        <a
          href="mailto:hello@renemurrell.de?subject=Agent%20Platform%20Enterprise%20Inquiry"
          className="inline-flex items-center gap-2 px-6 py-3 rounded-lg border border-white/[0.08] text-sm text-[#94a3b8] hover:text-[#f1f5f9] hover:border-white/[0.15] no-underline transition-colors"
        >
          Talk to us about Enterprise
          <ArrowRight size={14} />
        </a>
      </section>
    </>
  );
}
