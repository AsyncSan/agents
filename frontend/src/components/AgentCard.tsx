import { Link } from "react-router-dom";
import { ArrowRight, Clock, DollarSign, Shield } from "lucide-react";
import type { Agent } from "../api";

const domainColors: Record<string, string> = {
  research: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  content: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  benchmark: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  "code-quality": "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
};

export function AgentCard({ agent }: { agent: Agent }) {
  const domain = agent.card.capabilities.domain;
  const pricing = agent.card.pricing;
  const runtime = agent.card.runtime;
  const colorClass = domainColors[domain] || "bg-white/5 text-[#94a3b8] border-white/10";

  return (
    <Link
      to={`/agents/${agent.id}`}
      className="group block rounded-xl border border-white/[0.06] bg-[#111118] p-5 no-underline transition-all hover:border-[#00d4ff]/20 hover:bg-[#16161f]"
    >
      <div className="flex items-start justify-between mb-3">
        <span className={`text-xs px-2 py-0.5 rounded-full border ${colorClass}`}>
          {domain}
        </span>
        {agent.trust_score !== null && (
          <span className="flex items-center gap-1 text-xs text-emerald-400">
            <Shield size={12} />
            {agent.trust_score}
          </span>
        )}
      </div>

      <h3 className="text-[15px] font-medium text-[#f1f5f9] mb-1.5 group-hover:text-[#00d4ff] transition-colors">
        {agent.name}
      </h3>
      <p className="text-xs text-[#94a3b8] mb-4 line-clamp-2 leading-relaxed">
        {agent.description || agent.card.capabilities.description}
      </p>

      <div className="flex items-center gap-4 text-xs text-[#64748b]">
        <span className="flex items-center gap-1">
          <DollarSign size={12} />
          ${pricing.base_price_usd.toFixed(2)}/run
        </span>
        <span className="flex items-center gap-1">
          <Clock size={12} />
          ~{Math.round(runtime.estimated_duration_seconds / 60)}min
        </span>
        <span className="ml-auto text-[#00d4ff]/0 group-hover:text-[#00d4ff]/60 transition-colors">
          <ArrowRight size={14} />
        </span>
      </div>
    </Link>
  );
}
