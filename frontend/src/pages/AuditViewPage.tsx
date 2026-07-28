import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  ClipboardList,
  FileText,
  History,
  Loader2,
  ShieldCheck,
  Users,
  Zap,
} from "lucide-react";

interface AgentSummary {
  id: string;
  name: string;
  version: number;
  risk_class: string;
  status: string;
}

interface ProfileResponse {
  share: {
    label: string;
    auditor_name: string | null;
    auditor_organisation: string | null;
    expires_at: string;
    org_role: string;
    scope_agent_id: string | null;
    access_count: number;
  };
  agents: AgentSummary[];
}

interface DocRow {
  id: string;
  doc_type: string;
  title: string;
  agent_id: string | null;
  agent_version: number | null;
  status: string;
  created_at: string;
  updated_at: string;
  approved_at: string | null;
}

interface DocDetail extends DocRow {
  payload: Record<string, unknown>;
}

interface EventRow {
  id: string;
  event_type: string;
  actor_role: string | null;
  resource_type: string | null;
  resource_id: string | null;
  payload: Record<string, unknown> | null;
  created_at: string;
}

interface ModificationRow {
  id: string;
  modification_type: string;
  classification: string;
  version_from: number | null;
  version_to: number | null;
  summary: string;
  rationale: string | null;
  triggered_reassessment: boolean;
  reassessment_at: string | null;
  created_at: string;
}

interface RosterMember {
  name: string;
  email: string;
  role_title: string | null;
  authority_level: string;
  training_certificates: Array<Record<string, unknown>>;
  competence_notes: string | null;
  authority_source: string | null;
}

interface Roster {
  agent: { id: string; name: string; risk_class: string };
  total_assigned_persons: number;
  required_roles: string[];
  coverage_gaps: string[];
  compliant: boolean;
  roster: Array<{ role: string; members: RosterMember[] }>;
}

interface IncidentRow {
  id: string;
  agent_id: string | null;
  severity: string;
  status: string;
  title: string;
  summary: string;
  detected_at: string | null;
  reported_to_authority_at: string | null;
  authority_name: string | null;
}

type Tab = "overview" | "documents" | "events" | "modifications" | "oversight" | "incidents";

const TABS: { key: Tab; label: string; icon: typeof FileText }[] = [
  { key: "overview", label: "Overview", icon: ShieldCheck },
  { key: "documents", label: "Documents", icon: FileText },
  { key: "events", label: "Event log", icon: Zap },
  { key: "modifications", label: "Modifications", icon: History },
  { key: "oversight", label: "Oversight", icon: Users },
  { key: "incidents", label: "Incidents", icon: AlertTriangle },
];

export function AuditViewPage() {
  const { token } = useParams<{ token: string }>();
  const [profile, setProfile] = useState<ProfileResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<Tab>("overview");

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    fetch(`/v1/audit/${token}/profile`)
      .then(async (r) => {
        if (!r.ok) throw new Error(await r.text());
        return r.json();
      })
      .then((data: ProfileResponse) => {
        setProfile(data);
        setError(null);
      })
      .catch(() => setError("Share not found, expired, or revoked."))
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-xs text-[#64748b] p-12 justify-center">
        <Loader2 size={14} className="animate-spin" />
        Loading auditor view…
      </div>
    );
  }

  if (error || !profile || !token) {
    return (
      <div className="max-w-lg mx-auto pt-20">
        <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-6 text-center">
          <AlertCircle size={24} className="text-red-400 mx-auto mb-3" />
          <h2 className="text-lg font-semibold text-[#f1f5f9] mb-1">
            Share unavailable
          </h2>
          <p className="text-sm text-[#94a3b8]">
            {error || "This auditor link is no longer active."}
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      <section className="relative mb-8 pt-4">
        <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-5">
          <div className="flex items-start gap-3">
            <ShieldCheck size={18} className="text-emerald-300 shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-[10px] text-emerald-300/80 uppercase tracking-widest mb-1">
                Read-only auditor access
              </p>
              <h1 className="text-xl font-semibold text-[#f1f5f9] mb-1">
                {profile.share.label}
              </h1>
              <p className="text-xs text-[#94a3b8]">
                {profile.share.auditor_name || "Unnamed auditor"}
                {profile.share.auditor_organisation
                  ? ` · ${profile.share.auditor_organisation}`
                  : ""}
              </p>
              <p className="text-xs text-[#64748b] mt-1">
                Expires {new Date(profile.share.expires_at).toLocaleString()} ·{" "}
                Scope:{" "}
                {profile.share.scope_agent_id
                  ? `single agent (${profile.share.scope_agent_id})`
                  : "all agents"}{" "}
                · Visit #{profile.share.access_count}
              </p>
            </div>
          </div>
        </div>
      </section>

      <div className="flex flex-wrap gap-2 mb-6 border-b border-white/[0.06] pb-2">
        {TABS.map((t) => {
          const Icon = t.icon;
          return (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-colors ${
                tab === t.key
                  ? "bg-white/[0.08] text-[#f1f5f9]"
                  : "text-[#64748b] hover:text-[#94a3b8]"
              }`}
            >
              <Icon size={12} />
              {t.label}
            </button>
          );
        })}
      </div>

      {tab === "overview" && <OverviewTab profile={profile} />}
      {tab === "documents" && <DocumentsTab token={token} />}
      {tab === "events" && <EventsTab token={token} />}
      {tab === "modifications" && (
        <PerAgentTab
          agents={profile.agents}
          token={token}
          endpoint="modifications"
          render={(data: ModificationRow[]) => <ModificationsList rows={data} />}
        />
      )}
      {tab === "oversight" && (
        <PerAgentTab
          agents={profile.agents}
          token={token}
          endpoint="oversight"
          render={(roster: Roster) => <OversightView roster={roster} />}
        />
      )}
      {tab === "incidents" && <IncidentsTab token={token} />}
    </>
  );
}

function OverviewTab({ profile }: { profile: ProfileResponse }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {profile.agents.map((a) => (
        <div
          key={a.id}
          className="rounded-xl border border-white/[0.06] bg-[#111118] p-4"
        >
          <div className="flex items-start justify-between gap-2">
            <div>
              <h3 className="text-sm font-medium text-[#f1f5f9]">{a.name}</h3>
              <p className="text-xs text-[#64748b] font-mono">{a.id}</p>
            </div>
            <span
              className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded border ${
                a.risk_class === "high"
                  ? "bg-red-500/10 text-red-300 border-red-500/20"
                  : "bg-white/5 text-[#94a3b8] border-white/[0.08]"
              }`}
            >
              {a.risk_class}
            </span>
          </div>
          <p className="text-xs text-[#94a3b8] mt-2">
            v{a.version} · {a.status}
          </p>
        </div>
      ))}
      {profile.agents.length === 0 && (
        <p className="text-xs text-[#64748b] col-span-2 p-6 text-center">
          No agents in scope for this share.
        </p>
      )}
    </div>
  );
}

function DocumentsTab({ token }: { token: string }) {
  const [docs, setDocs] = useState<DocRow[]>([]);
  const [busy, setBusy] = useState(true);
  const [detail, setDetail] = useState<DocDetail | null>(null);

  useEffect(() => {
    setBusy(true);
    fetch(`/v1/audit/${token}/documents`)
      .then((r) => r.json())
      .then((data) => setDocs(Array.isArray(data) ? data : []))
      .finally(() => setBusy(false));
  }, [token]);

  const openDetail = async (id: string) => {
    const res = await fetch(`/v1/audit/${token}/documents/${id}`);
    if (!res.ok) return;
    setDetail(await res.json());
  };

  if (busy) {
    return <Spinner />;
  }
  if (docs.length === 0) {
    return <Empty icon={FileText} text="No compliance documents yet." />;
  }

  return (
    <>
      <div className="space-y-2">
        {docs.map((d) => (
          <button
            key={d.id}
            onClick={() => openDetail(d.id)}
            className="w-full text-left rounded-xl border border-white/[0.06] bg-[#111118] p-4 hover:border-white/[0.12] transition-colors"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-white/5 text-[#94a3b8] border border-white/[0.08]">
                    {d.doc_type.replace("_", " ")}
                  </span>
                  <StatusBadge status={d.status} />
                </div>
                <p className="text-sm text-[#f1f5f9]">{d.title}</p>
                <p className="text-xs text-[#64748b] mt-0.5">
                  {d.agent_id ? `${d.agent_id} · v${d.agent_version}` : "org-level"} ·
                  updated {new Date(d.updated_at).toLocaleString()}
                </p>
              </div>
            </div>
          </button>
        ))}
      </div>
      {detail && <DocumentDetailModal doc={detail} onClose={() => setDetail(null)} />}
    </>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    draft: "bg-white/5 text-[#94a3b8] border-white/[0.08]",
    submitted: "bg-amber-500/10 text-amber-300 border-amber-500/20",
    approved: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20",
    archived: "bg-white/5 text-[#64748b] border-white/[0.04]",
  };
  return (
    <span
      className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded border ${styles[status] || styles.draft}`}
    >
      {status}
    </span>
  );
}

function DocumentDetailModal({
  doc,
  onClose,
}: {
  doc: DocDetail;
  onClose: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-3xl max-h-[85vh] overflow-y-auto rounded-xl border border-white/[0.08] bg-[#0a0a0f] p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 mb-4">
          <div>
            <p className="text-xs text-[#64748b] uppercase tracking-wider mb-1">
              {doc.doc_type.replace("_", " ")}
            </p>
            <h2 className="text-xl font-semibold text-[#f1f5f9]">{doc.title}</h2>
          </div>
          <button
            onClick={onClose}
            className="text-[#64748b] hover:text-[#f1f5f9] text-xs"
          >
            Close
          </button>
        </div>
        <pre className="text-xs text-[#94a3b8] p-4 rounded-lg bg-[#111118] border border-white/[0.06] overflow-x-auto whitespace-pre-wrap break-words">
          {JSON.stringify(doc.payload, null, 2)}
        </pre>
      </div>
    </div>
  );
}

function EventsTab({ token }: { token: string }) {
  const [events, setEvents] = useState<EventRow[]>([]);
  const [busy, setBusy] = useState(true);

  useEffect(() => {
    fetch(`/v1/audit/${token}/events?limit=500`)
      .then((r) => r.json())
      .then((data) => setEvents(Array.isArray(data) ? data : []))
      .finally(() => setBusy(false));
  }, [token]);

  if (busy) return <Spinner />;
  if (events.length === 0) {
    return <Empty icon={Zap} text="No events logged for this scope." />;
  }

  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#111118] overflow-hidden">
      <table className="w-full text-xs">
        <thead className="text-left text-[#64748b]">
          <tr>
            <th className="p-3 border-b border-white/[0.06]">When</th>
            <th className="p-3 border-b border-white/[0.06]">Event</th>
            <th className="p-3 border-b border-white/[0.06]">Actor</th>
            <th className="p-3 border-b border-white/[0.06]">Resource</th>
          </tr>
        </thead>
        <tbody>
          {events.map((e) => (
            <tr key={e.id} className="border-t border-white/[0.04]">
              <td className="p-3 text-[#94a3b8] whitespace-nowrap">
                {new Date(e.created_at).toLocaleString()}
              </td>
              <td className="p-3 text-[#e2e8f0] font-mono">{e.event_type}</td>
              <td className="p-3 text-[#94a3b8]">{e.actor_role || "-"}</td>
              <td className="p-3 text-[#94a3b8]">
                {e.resource_type || "-"}
                {e.resource_id ? ` · ${e.resource_id}` : ""}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PerAgentTab<T>({
  agents,
  token,
  endpoint,
  render,
}: {
  agents: AgentSummary[];
  token: string;
  endpoint: "modifications" | "oversight";
  render: (data: T) => React.ReactNode;
}) {
  const [selected, setSelected] = useState<string>(agents[0]?.id || "");
  const [data, setData] = useState<T | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!selected) return;
    setBusy(true);
    try {
      const res = await fetch(`/v1/audit/${token}/${endpoint}/${selected}`);
      if (res.ok) setData(await res.json());
      else setData(null);
    } finally {
      setBusy(false);
    }
  }, [token, endpoint, selected]);

  useEffect(() => {
    load();
  }, [load]);

  if (agents.length === 0) {
    return <Empty icon={ClipboardList} text="No agents in scope." />;
  }

  return (
    <>
      <div className="mb-4">
        <label className="inline-flex items-center gap-2">
          <span className="text-xs text-[#64748b]">Agent</span>
          <select
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            className="px-3 py-2 rounded-lg bg-[#0a0a0f] border border-white/[0.06] text-sm text-[#f1f5f9] focus:outline-none"
          >
            {agents.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      {busy ? <Spinner /> : data ? render(data) : <Empty icon={ClipboardList} text="No data." />}
    </>
  );
}

function ModificationsList({ rows }: { rows: ModificationRow[] }) {
  if (!rows || rows.length === 0) {
    return <Empty icon={History} text="No modifications recorded." />;
  }
  return (
    <div className="space-y-2">
      {rows.map((r) => (
        <div
          key={r.id}
          className="rounded-xl border border-white/[0.06] bg-[#111118] p-4"
        >
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span
              className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded border ${
                r.classification === "substantial"
                  ? "bg-red-500/10 text-red-300 border-red-500/20"
                  : r.classification === "non_substantial"
                  ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/20"
                  : "bg-amber-500/10 text-amber-300 border-amber-500/20"
              }`}
            >
              {r.classification}
            </span>
            <span className="text-[10px] text-[#64748b] uppercase tracking-wider">
              {r.modification_type.replace("_", " ")}
            </span>
            {r.version_from !== null && r.version_to !== null && (
              <span className="text-[10px] text-[#64748b]">
                v{r.version_from} → v{r.version_to}
              </span>
            )}
            {r.triggered_reassessment && (
              <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded border bg-indigo-500/10 text-indigo-300 border-indigo-500/20">
                reassessed
              </span>
            )}
          </div>
          <p className="text-sm text-[#e2e8f0] mb-0.5">{r.summary}</p>
          {r.rationale && (
            <p className="text-xs text-[#94a3b8] mt-1">{r.rationale}</p>
          )}
          <p className="text-xs text-[#64748b] mt-1">
            {new Date(r.created_at).toLocaleString()}
          </p>
        </div>
      ))}
    </div>
  );
}

function OversightView({ roster }: { roster: Roster }) {
  const coverage = roster.compliant ? (
    <div className="flex items-center gap-2 text-xs text-emerald-300 mb-4">
      <CheckCircle2 size={14} /> Fully covered ({roster.required_roles.join(", ")})
    </div>
  ) : (
    <div className="flex items-center gap-2 text-xs text-amber-300 mb-4">
      <AlertTriangle size={14} /> Missing: {roster.coverage_gaps.join(", ")}
    </div>
  );

  const rosterBlocks = useMemo(
    () => roster.roster || [],
    [roster.roster],
  );

  return (
    <div>
      {coverage}
      {rosterBlocks.length === 0 && (
        <Empty icon={Users} text="No assignments for this agent." />
      )}
      {rosterBlocks.map((block) => (
        <div key={block.role} className="mb-4">
          <h3 className="text-xs font-medium text-[#64748b] uppercase tracking-wider mb-2">
            {block.role.replace("_", " ")} ({block.members.length})
          </h3>
          <div className="space-y-2">
            {block.members.map((m) => (
              <div
                key={m.email + block.role}
                className="rounded-xl border border-white/[0.06] bg-[#111118] p-4"
              >
                <p className="text-sm text-[#f1f5f9]">
                  {m.name}{" "}
                  <span className="text-xs text-[#64748b]">&lt;{m.email}&gt;</span>
                </p>
                {m.role_title && (
                  <p className="text-xs text-[#94a3b8]">{m.role_title}</p>
                )}
                <p className="text-xs text-[#94a3b8] mt-1">
                  Authority:{" "}
                  <code className="text-[#f1f5f9]">
                    {m.authority_level.replace("_", " ")}
                  </code>{" "}
                  · Training: {m.training_certificates.length} cert(s)
                </p>
                {m.competence_notes && (
                  <p className="text-xs text-[#64748b] mt-1">{m.competence_notes}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function IncidentsTab({ token }: { token: string }) {
  const [rows, setRows] = useState<IncidentRow[]>([]);
  const [busy, setBusy] = useState(true);

  useEffect(() => {
    fetch(`/v1/audit/${token}/incidents`)
      .then((r) => r.json())
      .then((data) => setRows(Array.isArray(data) ? data : []))
      .finally(() => setBusy(false));
  }, [token]);

  if (busy) return <Spinner />;
  if (rows.length === 0) {
    return <Empty icon={AlertTriangle} text="No incidents logged." />;
  }

  return (
    <div className="space-y-2">
      {rows.map((r) => (
        <div
          key={r.id}
          className="rounded-xl border border-white/[0.06] bg-[#111118] p-4"
        >
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span
              className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded border ${
                r.severity === "critical"
                  ? "bg-red-500/10 text-red-300 border-red-500/20"
                  : "bg-amber-500/10 text-amber-300 border-amber-500/20"
              }`}
            >
              {r.severity}
            </span>
            <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded border bg-white/5 text-[#94a3b8] border-white/[0.08]">
              {r.status}
            </span>
          </div>
          <p className="text-sm text-[#f1f5f9]">{r.title}</p>
          <p className="text-xs text-[#94a3b8] mt-1">{r.summary}</p>
          {r.reported_to_authority_at && (
            <p className="text-[10px] text-emerald-300 mt-1">
              Reported to {r.authority_name || "authority"} on{" "}
              {new Date(r.reported_to_authority_at).toLocaleString()}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

function Spinner() {
  return (
    <div className="flex items-center gap-2 text-xs text-[#64748b] p-8 justify-center">
      <Loader2 size={14} className="animate-spin" />
      Loading…
    </div>
  );
}

function Empty({ icon: Icon, text }: { icon: typeof FileText; text: string }) {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-8 text-center">
      <Icon size={24} className="text-[#64748b] mx-auto mb-3" />
      <p className="text-sm text-[#94a3b8]">{text}</p>
    </div>
  );
}
