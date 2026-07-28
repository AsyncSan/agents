import { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Copy,
  Eye,
  Key,
  Link as LinkIcon,
  Loader2,
  Plus,
  Shield,
  Trash2,
  XCircle,
} from "lucide-react";
import { listAgents, type Agent } from "../api";

interface AuditShare {
  id: string;
  label: string;
  token_prefix: string;
  scope_agent_id: string | null;
  auditor_name: string | null;
  auditor_organisation: string | null;
  auditor_email: string | null;
  notes: string | null;
  expires_at: string;
  revoked_at: string | null;
  active: boolean;
  access_count: number;
  last_accessed_at: string | null;
  created_at: string;
}

interface CreateResponse extends AuditShare {
  token: string;
  url: string;
}

export function AuditSharesPage() {
  const apiKey = typeof window !== "undefined" ? localStorage.getItem("af_api_key") : null;

  const [shares, setShares] = useState<AuditShare[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newOpen, setNewOpen] = useState(false);
  const [fresh, setFresh] = useState<CreateResponse | null>(null);

  const refresh = useCallback(async () => {
    if (!apiKey) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/v1/audit-shares", {
        headers: { "X-API-Key": apiKey },
      });
      if (!res.ok) throw new Error(`Failed (${res.status})`);
      setShares(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Load failed");
    } finally {
      setLoading(false);
    }
  }, [apiKey]);

  useEffect(() => {
    refresh();
    listAgents().then((d) => setAgents(d.agents)).catch(() => setAgents([]));
  }, [refresh]);

  const revoke = async (id: string) => {
    if (!apiKey) return;
    const res = await fetch(`/v1/audit-shares/${id}/revoke`, {
      method: "POST",
      headers: { "X-API-Key": apiKey },
    });
    if (!res.ok) {
      setError("Revoke failed");
      return;
    }
    refresh();
  };

  const del = async (id: string) => {
    if (!apiKey) return;
    const res = await fetch(`/v1/audit-shares/${id}`, {
      method: "DELETE",
      headers: { "X-API-Key": apiKey },
    });
    if (!res.ok) {
      setError("Delete failed");
      return;
    }
    refresh();
  };

  return (
    <>
      <section className="relative mb-10 pt-8">
        <div className="absolute inset-0 -z-10 overflow-hidden">
          <div
            className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] rounded-full opacity-[0.03]"
            style={{ background: "radial-gradient(circle, #34d399 0%, transparent 60%)" }}
          />
        </div>
        <div className="text-center max-w-2xl mx-auto">
          <p className="text-xs text-[#64748b] mb-3 font-medium uppercase tracking-widest">
            Auditor access
          </p>
          <h1 className="text-3xl sm:text-4xl font-semibold text-[#f1f5f9] mb-4 leading-[1.15] tracking-tight">
            Read-only share<br />
            <span className="text-[#34d399]">for auditors.</span>
          </h1>
          <p className="text-[15px] text-[#94a3b8] leading-relaxed max-w-lg mx-auto">
            Hand an external auditor a scoped, time-limited URL. No account, no
            API key, no write access. Revoke anytime. Every visit is counted.
          </p>
        </div>
      </section>

      <div className="flex items-center justify-between mb-6">
        <h2 className="text-sm font-medium text-[#94a3b8]">Your shares</h2>
        <button
          onClick={() => setNewOpen(true)}
          className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-[#34d399] text-[#0a0a0f] text-xs font-medium hover:bg-[#34d399]/90 transition-colors"
        >
          <Plus size={12} />
          Create share
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 flex items-start gap-2 mb-4">
          <AlertCircle size={14} className="text-red-400 shrink-0 mt-0.5" />
          <p className="text-xs text-red-300">{error}</p>
        </div>
      )}

      {fresh && <FreshShareBanner share={fresh} onDismiss={() => setFresh(null)} />}

      {loading ? (
        <div className="flex items-center gap-2 text-xs text-[#64748b] p-6 justify-center">
          <Loader2 size={14} className="animate-spin" />
          Loading shares…
        </div>
      ) : shares.length === 0 ? (
        <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-8 text-center">
          <Shield size={24} className="text-[#64748b] mx-auto mb-3" />
          <p className="text-sm text-[#94a3b8] mb-1">No auditor shares yet.</p>
          <p className="text-xs text-[#64748b]">
            Create one to let an external auditor browse your compliance
            workspace without handing over credentials.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {shares.map((s) => (
            <div
              key={s.id}
              className="rounded-xl border border-white/[0.06] bg-[#111118] p-4"
            >
              <div className="flex items-start gap-3">
                {s.active ? (
                  <CheckCircle2 size={14} className="text-emerald-300 shrink-0 mt-0.5" />
                ) : s.revoked_at ? (
                  <XCircle size={14} className="text-red-300 shrink-0 mt-0.5" />
                ) : (
                  <Clock size={14} className="text-amber-300 shrink-0 mt-0.5" />
                )}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <span className="text-sm font-medium text-[#f1f5f9]">{s.label}</span>
                    <code className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-[#64748b] font-mono">
                      {s.token_prefix}…
                    </code>
                    {s.scope_agent_id && (
                      <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded border bg-cyan-500/10 text-cyan-300 border-cyan-500/20">
                        scoped: {s.scope_agent_id}
                      </span>
                    )}
                    {!s.scope_agent_id && (
                      <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded border bg-white/5 text-[#94a3b8] border-white/[0.08]">
                        org-wide
                      </span>
                    )}
                  </div>
                  {s.auditor_name && (
                    <p className="text-xs text-[#94a3b8]">
                      {s.auditor_name}
                      {s.auditor_organisation ? ` · ${s.auditor_organisation}` : ""}
                      {s.auditor_email ? ` · ${s.auditor_email}` : ""}
                    </p>
                  )}
                  <p className="text-xs text-[#64748b] mt-1">
                    Expires {new Date(s.expires_at).toLocaleString()} ·{" "}
                    {s.access_count} view{s.access_count === 1 ? "" : "s"}
                    {s.last_accessed_at
                      ? ` · last ${new Date(s.last_accessed_at).toLocaleString()}`
                      : ""}
                    {s.revoked_at ? ` · revoked ${new Date(s.revoked_at).toLocaleString()}` : ""}
                  </p>
                </div>
                <div className="flex gap-1">
                  {s.active && (
                    <button
                      onClick={() => revoke(s.id)}
                      className="text-[#64748b] hover:text-amber-400 transition-colors p-1"
                      title="Revoke"
                    >
                      <Key size={14} />
                    </button>
                  )}
                  <button
                    onClick={() => del(s.id)}
                    className="text-[#64748b] hover:text-red-400 transition-colors p-1"
                    title="Delete permanently"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {newOpen && (
        <NewShareModal
          agents={agents}
          apiKey={apiKey}
          onClose={() => setNewOpen(false)}
          onCreated={(result) => {
            setNewOpen(false);
            setFresh(result);
            refresh();
          }}
        />
      )}
    </>
  );
}

function FreshShareBanner({
  share,
  onDismiss,
}: {
  share: CreateResponse;
  onDismiss: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const fullUrl = `${window.location.origin}/audit/${share.token}`;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(fullUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* ignore */
    }
  };

  return (
    <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-5 mb-5">
      <div className="flex items-start gap-3">
        <LinkIcon size={16} className="text-emerald-300 shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-emerald-100 mb-2">
            Share URL (copy now, it won't be shown again)
          </h3>
          <div className="flex items-center gap-2 mb-2">
            <code className="flex-1 px-2.5 py-1.5 rounded bg-[#0a0a0f] border border-white/[0.08] text-xs text-[#f1f5f9] font-mono break-all">
              {fullUrl}
            </code>
            <button
              onClick={copy}
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-emerald-200 text-xs hover:bg-emerald-500/20 transition-colors shrink-0"
            >
              <Copy size={12} />
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
          <p className="text-xs text-emerald-200/80">
            Send this URL to {share.auditor_name || "the auditor"}. It expires on{" "}
            {new Date(share.expires_at).toLocaleString()}.
          </p>
        </div>
        <button
          onClick={onDismiss}
          className="text-[#64748b] hover:text-[#f1f5f9] transition-colors"
        >
          <XCircle size={14} />
        </button>
      </div>
    </div>
  );
}

function NewShareModal({
  agents,
  apiKey,
  onClose,
  onCreated,
}: {
  agents: Agent[];
  apiKey: string | null;
  onClose: () => void;
  onCreated: (result: CreateResponse) => void;
}) {
  const [label, setLabel] = useState("");
  const [scope, setScope] = useState<"org" | "agent">("org");
  const [scopeAgentId, setScopeAgentId] = useState("");
  const [auditorName, setAuditorName] = useState("");
  const [auditorOrganisation, setAuditorOrganisation] = useState("");
  const [auditorEmail, setAuditorEmail] = useState("");
  const [notes, setNotes] = useState("");
  const [ttlDays, setTtlDays] = useState(30);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const submit = async () => {
    if (!apiKey) return;
    if (!label.trim()) {
      setErr("Label is required.");
      return;
    }
    setBusy(true);
    setErr(null);
    try {
      const res = await fetch("/v1/audit-shares", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
        body: JSON.stringify({
          label,
          scope_agent_id: scope === "agent" ? scopeAgentId || undefined : undefined,
          auditor_name: auditorName || undefined,
          auditor_organisation: auditorOrganisation || undefined,
          auditor_email: auditorEmail || undefined,
          notes: notes || undefined,
          ttl_days: ttlDays,
        }),
      });
      if (!res.ok) {
        const body = await res.text();
        throw new Error(`Create failed (${res.status}) ${body.slice(0, 120)}`);
      }
      onCreated(await res.json());
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Create failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-xl border border-white/[0.08] bg-[#0a0a0f] p-6 space-y-4 max-h-[85vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold text-[#f1f5f9]">Create auditor share</h2>

        <Field label="Label (internal, shown only to you)">
          <input
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="e.g. BNetzA sandbox audit Q2 2026"
            className={inputClass}
          />
        </Field>

        <Field label="Scope">
          <div className="flex gap-4 text-xs text-[#94a3b8]">
            <label className="flex items-center gap-2">
              <input
                type="radio"
                checked={scope === "org"}
                onChange={() => setScope("org")}
              />
              All agents
            </label>
            <label className="flex items-center gap-2">
              <input
                type="radio"
                checked={scope === "agent"}
                onChange={() => setScope("agent")}
              />
              Single agent
            </label>
          </div>
        </Field>

        {scope === "agent" && (
          <Field label="Agent">
            <select
              value={scopeAgentId}
              onChange={(e) => setScopeAgentId(e.target.value)}
              className={inputClass}
            >
              <option value="">— choose agent —</option>
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
          </Field>
        )}

        <div className="grid grid-cols-2 gap-3">
          <Field label="Auditor name">
            <input
              value={auditorName}
              onChange={(e) => setAuditorName(e.target.value)}
              placeholder="Contact person"
              className={inputClass}
            />
          </Field>
          <Field label="Auditor organisation">
            <input
              value={auditorOrganisation}
              onChange={(e) => setAuditorOrganisation(e.target.value)}
              placeholder="Firm / authority"
              className={inputClass}
            />
          </Field>
        </div>
        <Field label="Auditor email">
          <input
            value={auditorEmail}
            onChange={(e) => setAuditorEmail(e.target.value)}
            placeholder="contact@example.com"
            type="email"
            className={inputClass}
          />
        </Field>

        <Field label="Expires in (days)">
          <input
            type="number"
            value={ttlDays}
            onChange={(e) => setTtlDays(Number(e.target.value))}
            min={1}
            max={180}
            className={inputClass}
          />
          <p className="text-[10px] text-[#64748b] mt-1">
            1–180 days. Default 30. Revoke anytime from the list.
          </p>
        </Field>

        <Field label="Notes">
          <textarea
            rows={2}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Purpose, engagement reference, internal ticket"
            className={inputClass}
          />
        </Field>

        {err && (
          <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 flex items-start gap-2">
            <AlertCircle size={14} className="text-red-400 shrink-0 mt-0.5" />
            <p className="text-xs text-red-300">{err}</p>
          </div>
        )}

        <div className="flex gap-2 justify-end pt-1">
          <button
            onClick={onClose}
            className="px-3 py-2 rounded-lg border border-white/[0.08] text-xs text-[#64748b] hover:text-[#f1f5f9] transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={busy}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-[#34d399] text-[#0a0a0f] text-xs font-medium disabled:opacity-40"
          >
            {busy ? <Loader2 size={12} className="animate-spin" /> : <Eye size={12} />}
            Generate URL
          </button>
        </div>
      </div>
    </div>
  );
}

const inputClass =
  "w-full px-3 py-2 rounded-lg bg-[#111118] border border-white/[0.06] text-sm text-[#f1f5f9] placeholder-[#64748b] focus:outline-none focus:border-[#34d399]/30";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="block text-xs text-[#64748b] mb-1.5">{label}</span>
      {children}
    </label>
  );
}
