const statusStyles: Record<string, string> = {
  pending: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  dispatching: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  running: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
  completed: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  failed: "bg-red-500/10 text-red-400 border-red-500/20",
  provisioning: "bg-violet-500/10 text-violet-400 border-violet-500/20",
  active: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
};

export function StatusBadge({ status }: { status: string }) {
  const style = statusStyles[status] || "bg-white/5 text-[#94a3b8] border-white/10";
  return (
    <span className={`text-[11px] px-2 py-0.5 rounded-full border ${style}`}>
      {status}
    </span>
  );
}
