import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle,
  Clock,
  Download,
  FileCheck,
  Loader2,
  Plus,
  Send,
  ShieldAlert,
  Trash2,
  X,
} from "lucide-react";
import { listAgents, type Agent } from "../api";
import {
  createIncident,
  deleteIncident,
  fetchReportMarkdown,
  fetchReportPDF,
  getIncident,
  listIncidents,
  listSeverities,
  markReported,
  type Incident,
  type Severity,
  type SeverityCatalogEntry,
} from "../incidents-api";

const SEVERITY_STYLE: Record<Severity, string> = {
  death_or_serious_health: "border-red-500/30 bg-red-500/10 text-red-300",
  critical_infrastructure: "border-red-500/30 bg-red-500/10 text-red-300",
  fundamental_rights: "border-amber-500/30 bg-amber-500/10 text-amber-300",
  widespread_infringement: "border-red-500/30 bg-red-500/10 text-red-300",
  serious_property_harm: "border-amber-500/20 bg-amber-500/5 text-amber-300",
  environmental_harm: "border-amber-500/20 bg-amber-500/5 text-amber-300",
};

const STATUS_STYLE: Record<string, string> = {
  draft: "bg-white/5 text-[#94a3b8] border-white/[0.08]",
  confirmed: "bg-amber-500/10 text-amber-300 border-amber-500/20",
  under_investigation: "bg-amber-500/10 text-amber-300 border-amber-500/20",
  reported: "bg-[#00d4ff]/10 text-[#00d4ff] border-[#00d4ff]/20",
  resolved: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20",
  withdrawn: "bg-white/5 text-[#64748b] border-white/[0.04]",
};

function formatCountdown(seconds: number): { label: string; overdue: boolean } {
  const abs = Math.abs(seconds);
  const days = Math.floor(abs / 86400);
  const hours = Math.floor((abs % 86400) / 3600);
  const mins = Math.floor((abs % 3600) / 60);
  const parts = [];
  if (days) parts.push(`${days}d`);
  if (hours) parts.push(`${hours}h`);
  if (mins && !days) parts.push(`${mins}m`);
  const label = parts.join(" ") || "<1m";
  return { label, overdue: seconds < 0 };
}

export function IncidentsPage() {
  const apiKey = typeof window !== "undefined" ? localStorage.getItem("af_api_key") : null;

  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [overdueCount, setOverdueCount] = useState(0);
  const [openCount, setOpenCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>("open");
  const [showNew, setShowNew] = useState(false);
  const [detail, setDetail] = useState<Incident | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    if (!apiKey) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const statusFilter =
        filterStatus === "open"
          ? undefined // we'll slice client-side for "open" aggregate
          : filterStatus !== "all"
          ? filterStatus
          : undefined;
      const data = await listIncidents(apiKey, { status: statusFilter });
      const filtered =
        filterStatus === "open"
          ? data.incidents.filter((i) =>
              ["draft", "confirmed", "under_investigation"].includes(i.status),
            )
          : data.incidents;
      setIncidents(filtered);
      setOverdueCount(data.overdue_count);
      setOpenCount(data.open_count);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load incidents");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterStatus, apiKey]);

  if (!apiKey) {
    return (
      <div className="max-w-xl mx-auto py-16 text-center">
        <ShieldAlert size={40} className="text-[#00d4ff] mx-auto mb-4" />
        <h1 className="text-2xl font-semibold text-[#f1f5f9] mb-2">Incident reporting</h1>
        <p className="text-sm text-[#94a3b8] mb-6">
          Log in to file and track serious incidents under EU AI Act Art. 73.
        </p>
        <Link
          to="/auth"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-sm font-medium no-underline"
        >
          Log in
        </Link>
      </div>
    );
  }

  return (
    <>
      <section className="mb-8 pt-6">
        <div className="flex items-start justify-between mb-6 gap-4">
          <div>
            <p className="text-xs text-[#64748b] mb-1 font-medium uppercase tracking-widest">
              EU AI Act Art. 73
            </p>
            <h1 className="text-2xl font-semibold text-[#f1f5f9]">Serious incident reporting</h1>
            <p className="text-xs text-[#94a3b8] mt-1 max-w-xl">
              Draft the report, track the deadline, download the document the MSA expects.
              Deadlines: 2 days for critical infrastructure or widespread infringement, 10 days
              for fundamental-rights and health incidents, 15 days otherwise.
            </p>
          </div>
          <button
            onClick={() => setShowNew(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-sm font-medium"
            style={{ transition: "background 0.2s cubic-bezier(0.16, 1, 0.3, 1)" }}
          >
            <Plus size={14} />
            New incident
          </button>
        </div>

        <div className="grid grid-cols-3 gap-3 mb-6">
          <Stat label="Overdue" value={overdueCount} tone="red" />
          <Stat label="Open" value={openCount} tone="amber" />
          <Stat label="Total" value={incidents.length} tone="neutral" />
        </div>

        <div className="flex gap-1 flex-wrap mb-4">
          {[
            { key: "open", label: "Open" },
            { key: "reported", label: "Reported" },
            { key: "resolved", label: "Resolved" },
            { key: "all", label: "All" },
          ].map((o) => (
            <button
              key={o.key}
              onClick={() => setFilterStatus(o.key)}
              className={`px-3 py-1.5 rounded-lg text-xs transition-colors border ${
                filterStatus === o.key
                  ? "bg-[#00d4ff]/10 text-[#00d4ff] border-[#00d4ff]/20"
                  : "text-[#94a3b8] hover:text-[#f1f5f9] border-white/[0.06]"
              }`}
            >
              {o.label}
            </button>
          ))}
        </div>

        {error && (
          <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 flex items-start gap-2 mb-4">
            <AlertCircle size={14} className="text-red-400 shrink-0 mt-0.5" />
            <p className="text-xs text-red-300">{error}</p>
          </div>
        )}

        {loading && incidents.length === 0 ? (
          <p className="text-center text-sm text-[#64748b] py-10">Loading…</p>
        ) : incidents.length === 0 ? (
          <EmptyState onNew={() => setShowNew(true)} />
        ) : (
          <div className="rounded-xl border border-white/[0.06] bg-[#111118] overflow-hidden">
            <table className="w-full text-sm">
              <thead className="border-b border-white/[0.06] bg-[#0a0a0f]">
                <tr className="text-xs text-[#64748b]">
                  <th className="text-left py-2.5 px-4 font-medium">Severity</th>
                  <th className="text-left py-2.5 px-4 font-medium">Title</th>
                  <th className="text-left py-2.5 px-4 font-medium">Status</th>
                  <th className="text-left py-2.5 px-4 font-medium">Deadline</th>
                  <th className="text-left py-2.5 px-4 font-medium">Agent</th>
                </tr>
              </thead>
              <tbody>
                {incidents.map((inc) => {
                  const { label, overdue } = formatCountdown(inc.time_remaining_seconds);
                  return (
                    <tr
                      key={inc.id}
                      className="border-b border-white/[0.04] hover:bg-white/[0.02] cursor-pointer"
                      onClick={() => setDetail(inc)}
                    >
                      <td className="py-3 px-4">
                        <span
                          className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-medium border ${SEVERITY_STYLE[inc.severity]}`}
                        >
                          {inc.severity.replace(/_/g, " ")}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-[#f1f5f9] max-w-sm truncate">{inc.title}</td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-[10px] font-medium border ${STATUS_STYLE[inc.status]}`}
                        >
                          {inc.status.replace(/_/g, " ")}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        {inc.status === "reported" ? (
                          <span className="text-xs text-emerald-400 flex items-center gap-1">
                            <CheckCircle size={12} /> filed
                          </span>
                        ) : overdue ? (
                          <span className="text-xs text-red-400 font-medium flex items-center gap-1">
                            <AlertTriangle size={12} /> overdue {label}
                          </span>
                        ) : (
                          <span className="text-xs text-amber-300 flex items-center gap-1">
                            <Clock size={12} /> {label} left
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-xs text-[#94a3b8] font-mono">
                        {inc.agent_id ? (
                          <>
                            {inc.agent_id}
                            {inc.agent_version != null && ` · v${inc.agent_version}`}
                          </>
                        ) : (
                          "-"
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {showNew && apiKey && (
        <NewIncidentModal
          apiKey={apiKey}
          onClose={() => setShowNew(false)}
          onCreated={async () => {
            setShowNew(false);
            await refresh();
          }}
        />
      )}

      {detail && apiKey && (
        <IncidentDetailModal
          apiKey={apiKey}
          incident={detail}
          busy={busy}
          onChange={async () => {
            if (!detail) return;
            try {
              setDetail(await getIncident(apiKey, detail.id));
            } catch {
              // ignore
            }
            await refresh();
          }}
          setBusy={setBusy}
          onClose={() => setDetail(null)}
        />
      )}
    </>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "red" | "amber" | "neutral";
}) {
  const toneClass =
    tone === "red"
      ? "text-red-400"
      : tone === "amber"
      ? "text-amber-300"
      : "text-[#f1f5f9]";
  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-4">
      <div className="text-xs text-[#64748b] mb-2">{label}</div>
      <div className={`text-2xl font-semibold ${toneClass}`}>{value}</div>
    </div>
  );
}

function EmptyState({ onNew }: { onNew: () => void }) {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-10 text-center">
      <ShieldAlert size={32} className="text-[#64748b] mx-auto mb-3" />
      <h3 className="text-sm font-medium text-[#f1f5f9] mb-2">No incidents recorded</h3>
      <p className="text-xs text-[#94a3b8] mb-6 max-w-sm mx-auto">
        Good. File a new incident here the moment you become aware of a serious issue.
        We track the deadline and prepare the MSA-ready report for you.
      </p>
      <button
        onClick={onNew}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-sm font-medium"
      >
        <Plus size={14} />
        File an incident
      </button>
    </div>
  );
}

function NewIncidentModal({
  apiKey,
  onClose,
  onCreated,
}: {
  apiKey: string;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [severities, setSeverities] = useState<SeverityCatalogEntry[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [severity, setSeverity] = useState<Severity>("serious_property_harm");
  const [detectedAt, setDetectedAt] = useState<string>(new Date().toISOString().slice(0, 16));
  const [awarenessAt, setAwarenessAt] = useState<string>(new Date().toISOString().slice(0, 16));
  const [agentId, setAgentId] = useState<string>("");
  const [affected, setAffected] = useState<string>("");
  const [mitigation, setMitigation] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listSeverities(apiKey).then(setSeverities).catch(() => setSeverities([]));
    listAgents()
      .then((d) => setAgents(d.agents))
      .catch(() => setAgents([]));
  }, [apiKey]);

  const selectedAgent = agents.find((a) => a.id === agentId) || null;
  const selectedSeverity = severities.find((s) => s.key === severity);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await createIncident(apiKey, {
        title,
        summary,
        severity,
        detected_at: new Date(detectedAt).toISOString(),
        awareness_at: new Date(awarenessAt).toISOString(),
        agent_id: agentId || undefined,
        agent_version: selectedAgent
          ? (selectedAgent as unknown as { version?: number }).version
          : undefined,
        affected_persons_estimate: affected ? parseInt(affected, 10) : undefined,
        mitigation_taken: mitigation || undefined,
      });
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create incident");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm p-4 flex items-center justify-center"
      onClick={onClose}
    >
      <form
        onSubmit={handleSubmit}
        onClick={(e) => e.stopPropagation()}
        className="rounded-xl border border-white/[0.08] bg-[#111118] w-full max-w-2xl max-h-[90vh] overflow-y-auto"
      >
        <div className="flex items-start justify-between p-5 border-b border-white/[0.06]">
          <div>
            <h2 className="text-base font-semibold text-[#f1f5f9]">File a serious incident</h2>
            <p className="text-xs text-[#94a3b8] mt-1">
              The deadline starts the moment your organisation became aware.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#64748b] hover:text-[#f1f5f9] transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <Field label="Title">
            <input
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Short descriptive title"
              className={inputClass}
            />
          </Field>

          <Field label="Severity (Art. 3(49) category)">
            <select
              value={severity}
              onChange={(e) => setSeverity(e.target.value as Severity)}
              className={inputClass}
            >
              {severities.map((s) => (
                <option key={s.key} value={s.key}>
                  {s.description} ({s.deadline_days}d deadline)
                </option>
              ))}
            </select>
            {selectedSeverity && (
              <p className="text-xs text-amber-300 mt-1">
                Deadline: {selectedSeverity.deadline_days} days from awareness.
              </p>
            )}
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Detected at">
              <input
                type="datetime-local"
                required
                value={detectedAt}
                onChange={(e) => setDetectedAt(e.target.value)}
                className={inputClass}
              />
            </Field>
            <Field label="Awareness at (deadline starts here)">
              <input
                type="datetime-local"
                required
                value={awarenessAt}
                onChange={(e) => setAwarenessAt(e.target.value)}
                className={inputClass}
              />
            </Field>
          </div>

          <Field label="Agent (optional)">
            <select
              value={agentId}
              onChange={(e) => setAgentId(e.target.value)}
              className={inputClass}
            >
              <option value="">Not tied to a specific agent</option>
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} ({a.id})
                </option>
              ))}
            </select>
          </Field>

          <Field label="Affected persons estimate (optional)">
            <input
              type="number"
              min="0"
              value={affected}
              onChange={(e) => setAffected(e.target.value)}
              placeholder="e.g., 120"
              className={inputClass}
            />
          </Field>

          <Field label="Summary">
            <textarea
              required
              rows={4}
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              placeholder="What happened? Factual summary, one or two paragraphs."
              className={inputClass}
            />
          </Field>

          <Field label="Immediate mitigation taken (optional)">
            <textarea
              rows={3}
              value={mitigation}
              onChange={(e) => setMitigation(e.target.value)}
              placeholder="What was done right away to stop or contain the issue?"
              className={inputClass}
            />
          </Field>

          {error && (
            <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 flex items-start gap-2">
              <AlertCircle size={14} className="text-red-400 shrink-0 mt-0.5" />
              <p className="text-xs text-red-300">{error}</p>
            </div>
          )}
        </div>

        <div className="p-5 border-t border-white/[0.06] flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg border border-white/[0.08] text-sm text-[#94a3b8] hover:text-[#f1f5f9] transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={busy}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {busy ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
            Record incident
          </button>
        </div>
      </form>
    </div>
  );
}

function IncidentDetailModal({
  apiKey,
  incident,
  busy,
  setBusy,
  onChange,
  onClose,
}: {
  apiKey: string;
  incident: Incident;
  busy: boolean;
  setBusy: (b: boolean) => void;
  onChange: () => Promise<void>;
  onClose: () => void;
}) {
  const [authorityName, setAuthorityName] = useState("BNetzA");
  const [authorityRef, setAuthorityRef] = useState("");
  const [organisation, setOrganisation] = useState("");
  const [contact, setContact] = useState("");
  const [error, setError] = useState<string | null>(null);
  const { label, overdue } = useMemo(
    () => formatCountdown(incident.time_remaining_seconds),
    [incident.time_remaining_seconds],
  );

  const handleDownloadMarkdown = async () => {
    setBusy(true);
    setError(null);
    try {
      const md = await fetchReportMarkdown(apiKey, incident.id, { organisation, contact });
      const blob = new Blob([md], { type: "text/markdown" });
      triggerDownload(blob, `incident-${incident.id}.md`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Markdown export failed");
    } finally {
      setBusy(false);
    }
  };

  const handleDownloadPDF = async () => {
    setBusy(true);
    setError(null);
    try {
      const blob = await fetchReportPDF(apiKey, incident.id, { organisation, contact });
      triggerDownload(blob, `incident-${incident.id}.pdf`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "PDF export failed");
    } finally {
      setBusy(false);
    }
  };

  const handleMarkReported = async () => {
    setBusy(true);
    setError(null);
    try {
      await markReported(apiKey, incident.id, {
        authority_name: authorityName || undefined,
        authority_reference: authorityRef || undefined,
      });
      await onChange();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to mark reported");
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm("Delete this incident permanently?")) return;
    setBusy(true);
    try {
      await deleteIncident(apiKey, incident.id);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm p-4 flex items-center justify-center"
      onClick={onClose}
    >
      <div
        className="rounded-xl border border-white/[0.08] bg-[#111118] w-full max-w-3xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between p-5 border-b border-white/[0.06]">
          <div>
            <p className="text-xs text-[#64748b] mb-1 font-medium uppercase tracking-widest">
              {incident.severity.replace(/_/g, " ")}
            </p>
            <h2 className="text-base font-semibold text-[#f1f5f9]">{incident.title}</h2>
            <div className="flex items-center gap-3 mt-2 text-xs text-[#64748b]">
              <span>Status: {incident.status.replace(/_/g, " ")}</span>
              {incident.status !== "reported" &&
                (overdue ? (
                  <span className="text-red-400 flex items-center gap-1">
                    <AlertTriangle size={10} /> overdue by {label}
                  </span>
                ) : (
                  <span className="text-amber-300 flex items-center gap-1">
                    <Clock size={10} /> {label} remaining
                  </span>
                ))}
              {incident.status === "reported" && (
                <span className="text-emerald-400 flex items-center gap-1">
                  <CheckCircle size={10} /> filed with authority
                </span>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#64748b] hover:text-[#f1f5f9] transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        <div className="p-5 space-y-5">
          <section>
            <h3 className="text-xs font-medium text-[#64748b] uppercase tracking-widest mb-2">
              Summary
            </h3>
            <p className="text-sm text-[#94a3b8] whitespace-pre-wrap">{incident.summary}</p>
          </section>

          <section className="grid grid-cols-2 gap-3 text-xs">
            <Info label="Detected at" value={new Date(incident.detected_at).toLocaleString()} />
            <Info
              label="Awareness at"
              value={new Date(incident.awareness_at).toLocaleString()}
            />
            <Info
              label="Deadline"
              value={new Date(incident.deadline_at).toLocaleString()}
            />
            <Info
              label="Agent"
              value={
                incident.agent_id
                  ? `${incident.agent_id}${incident.agent_version != null ? ` · v${incident.agent_version}` : ""}`
                  : "-"
              }
            />
            <Info
              label="Affected persons"
              value={
                incident.affected_persons_estimate != null
                  ? String(incident.affected_persons_estimate)
                  : "-"
              }
            />
            <Info
              label="Reported at"
              value={
                incident.reported_to_authority_at
                  ? new Date(incident.reported_to_authority_at).toLocaleString()
                  : "not yet"
              }
            />
          </section>

          {incident.status !== "reported" && (
            <section className="rounded-xl border border-[#00d4ff]/10 bg-[#00d4ff]/5 p-4 space-y-3">
              <h3 className="text-sm font-medium text-[#f1f5f9]">File with authority</h3>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Provider organisation">
                  <input
                    value={organisation}
                    onChange={(e) => setOrganisation(e.target.value)}
                    placeholder="Legal name"
                    className={inputClass}
                  />
                </Field>
                <Field label="Accountable contact">
                  <input
                    value={contact}
                    onChange={(e) => setContact(e.target.value)}
                    placeholder="Name, role, email"
                    className={inputClass}
                  />
                </Field>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={handleDownloadMarkdown}
                  disabled={busy}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-white/[0.08] text-xs text-[#94a3b8] hover:text-[#f1f5f9] disabled:opacity-40 transition-colors"
                >
                  <FileCheck size={12} />
                  Download Markdown
                </button>
                <button
                  onClick={handleDownloadPDF}
                  disabled={busy}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-white/[0.08] text-xs text-[#94a3b8] hover:text-[#f1f5f9] disabled:opacity-40 transition-colors"
                >
                  <Download size={12} />
                  Download PDF
                </button>
              </div>
              <div className="border-t border-[#00d4ff]/10 pt-3">
                <div className="grid grid-cols-2 gap-3 mb-3">
                  <Field label="Authority">
                    <input
                      value={authorityName}
                      onChange={(e) => setAuthorityName(e.target.value)}
                      className={inputClass}
                    />
                  </Field>
                  <Field label="Authority reference (once filed)">
                    <input
                      value={authorityRef}
                      onChange={(e) => setAuthorityRef(e.target.value)}
                      placeholder="Case number, ticket ID"
                      className={inputClass}
                    />
                  </Field>
                </div>
                <button
                  onClick={handleMarkReported}
                  disabled={busy}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-sm font-medium disabled:opacity-40 transition-colors"
                >
                  <Send size={12} />
                  Mark as filed with authority
                </button>
              </div>
            </section>
          )}

          {error && (
            <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 flex items-start gap-2">
              <AlertCircle size={14} className="text-red-400 shrink-0 mt-0.5" />
              <p className="text-xs text-red-300">{error}</p>
            </div>
          )}
        </div>

        <div className="p-5 border-t border-white/[0.06] flex items-center justify-between">
          <button
            onClick={handleDelete}
            disabled={busy}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-[#64748b] hover:text-red-400 transition-colors"
          >
            <Trash2 size={12} />
            Delete incident
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg border border-white/[0.08] text-sm text-[#94a3b8] hover:text-[#f1f5f9] transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

const inputClass =
  "w-full px-3 py-2 rounded-lg bg-[#0a0a0f] border border-white/[0.06] text-sm text-[#f1f5f9] placeholder-[#64748b] focus:outline-none focus:border-[#00d4ff]/30";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="block text-xs text-[#64748b] mb-1.5">{label}</span>
      {children}
    </label>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] text-[#64748b] uppercase tracking-widest mb-0.5">{label}</div>
      <div className="text-xs text-[#f1f5f9]">{value}</div>
    </div>
  );
}
