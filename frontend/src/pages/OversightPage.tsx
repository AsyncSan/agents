import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Download,
  FileCheck,
  GraduationCap,
  Loader2,
  Plus,
  ShieldCheck,
  Trash2,
  UserCheck,
  Users,
} from "lucide-react";
import { listAgents, type Agent } from "../api";

const OVERSIGHT_ROLES = [
  "approver",
  "reviewer",
  "operator",
  "overseer",
  "incident_owner",
] as const;
const AUTHORITY_LEVELS = [
  "read_only",
  "review",
  "approve",
  "override",
  "deputy_provider",
] as const;

type OversightRole = (typeof OVERSIGHT_ROLES)[number];
type AuthorityLevel = (typeof AUTHORITY_LEVELS)[number];

interface TrainingCert {
  certificate_id?: string;
  module_id?: string;
  module_title?: string;
  issued_at?: string;
  score_pct?: number;
}

interface Assignment {
  id: string;
  staff_name: string;
  staff_email: string;
  staff_role_title: string | null;
  oversight_role: OversightRole;
  authority_level: AuthorityLevel;
  assigned_agent_ids: string[] | null;
  training_certificates: TrainingCert[] | null;
  competence_notes: string | null;
  authority_source: string | null;
  active: boolean;
  created_at: string;
}

interface RosterBlock {
  role: OversightRole;
  members: Array<{
    name: string;
    email: string;
    role_title: string | null;
    authority_level: AuthorityLevel;
    training_certificates: TrainingCert[];
    competence_notes: string | null;
    authority_source: string | null;
  }>;
}

interface Roster {
  regulation: string;
  agent: { id: string; name: string; risk_class: string };
  required_roles: string[];
  coverage_gaps: string[];
  compliant: boolean;
  total_assigned_persons: number;
  roster: RosterBlock[];
}

const ROLE_ICON: Record<OversightRole, typeof UserCheck> = {
  approver: CheckCircle2,
  reviewer: FileCheck,
  operator: Users,
  overseer: ShieldCheck,
  incident_owner: AlertTriangle,
};

const ROLE_LABEL: Record<OversightRole, string> = {
  approver: "Approver",
  reviewer: "Reviewer",
  operator: "Operator",
  overseer: "Overseer (Art. 14)",
  incident_owner: "Incident owner",
};

function downloadBlob(filename: string, content: string | Blob, mime?: string) {
  const blob = typeof content === "string" ? new Blob([content], { type: mime }) : content;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function OversightPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const apiKey = typeof window !== "undefined" ? localStorage.getItem("af_api_key") : null;

  const [agents, setAgents] = useState<Agent[]>([]);
  const [agentId, setAgentId] = useState<string>(searchParams.get("agent_id") || "");
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [roster, setRoster] = useState<Roster | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newOpen, setNewOpen] = useState(false);

  useEffect(() => {
    listAgents().then((d) => setAgents(d.agents)).catch(() => setAgents([]));
  }, []);

  const refresh = useCallback(async () => {
    if (!apiKey) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const allRes = await fetch("/v1/oversight/assignments", {
        headers: { "X-API-Key": apiKey },
      });
      if (!allRes.ok) throw new Error(`Failed to load assignments (${allRes.status})`);
      setAssignments(await allRes.json());

      if (agentId) {
        const rosterRes = await fetch(
          `/v1/oversight/roster/${encodeURIComponent(agentId)}`,
          { headers: { "X-API-Key": apiKey } },
        );
        if (rosterRes.ok) {
          setRoster(await rosterRes.json());
        } else {
          setRoster(null);
        }
      } else {
        setRoster(null);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Load failed");
    } finally {
      setLoading(false);
    }
  }, [apiKey, agentId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const selectAgent = (id: string) => {
    setAgentId(id);
    const next = new URLSearchParams(searchParams);
    if (id) next.set("agent_id", id); else next.delete("agent_id");
    setSearchParams(next, { replace: true });
  };

  const stats = useMemo(() => {
    const distinct = new Set(assignments.map((a) => a.staff_email));
    const byRole: Record<string, number> = {};
    for (const a of assignments) byRole[a.oversight_role] = (byRole[a.oversight_role] || 0) + 1;
    return { total: assignments.length, distinct: distinct.size, byRole };
  }, [assignments]);

  const deleteAssignment = async (id: string) => {
    if (!apiKey) return;
    const res = await fetch(`/v1/oversight/assignments/${id}`, {
      method: "DELETE",
      headers: { "X-API-Key": apiKey },
    });
    if (!res.ok) {
      setError("Delete failed");
      return;
    }
    refresh();
  };

  const downloadMarkdown = async () => {
    if (!apiKey || !agentId) return;
    const res = await fetch(`/v1/oversight/roster/${agentId}/markdown`, {
      headers: { "X-API-Key": apiKey },
    });
    if (!res.ok) {
      setError("Markdown export failed");
      return;
    }
    downloadBlob(`oversight-${agentId}.md`, await res.text(), "text/markdown");
  };

  const downloadPDF = async () => {
    if (!apiKey || !agentId) return;
    const res = await fetch(`/v1/oversight/roster/${agentId}/pdf`, {
      headers: { "X-API-Key": apiKey },
    });
    if (!res.ok) {
      setError("PDF export failed");
      return;
    }
    downloadBlob(`oversight-${agentId}.pdf`, await res.blob());
  };

  return (
    <>
      <section className="relative mb-10 pt-8">
        <div className="absolute inset-0 -z-10 overflow-hidden">
          <div
            className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] rounded-full opacity-[0.03]"
            style={{ background: "radial-gradient(circle, #a78bfa 0%, transparent 60%)" }}
          />
        </div>
        <div className="text-center max-w-2xl mx-auto">
          <p className="text-xs text-[#64748b] mb-3 font-medium uppercase tracking-widest">
            EU AI Act Art. 14 · Art. 26(2) · Art. 4
          </p>
          <h1 className="text-3xl sm:text-4xl font-semibold text-[#f1f5f9] mb-4 leading-[1.15] tracking-tight">
            Human oversight<br />
            <span className="text-[#a78bfa]">roster.</span>
          </h1>
          <p className="text-[15px] text-[#94a3b8] leading-relaxed max-w-lg mx-auto">
            Named persons, assigned roles, training evidence. Coverage checks run
            per agent so you know before an auditor does whether the required
            oversight roles are filled.
          </p>
        </div>
      </section>

      <div className="grid grid-cols-3 gap-3 mb-6">
        <Stat label="Assignments" value={stats.total} icon={Users} />
        <Stat label="Distinct staff" value={stats.distinct} icon={UserCheck} />
        <Stat
          label="Overseers"
          value={stats.byRole.overseer || 0}
          icon={ShieldCheck}
        />
      </div>

      <div className="flex flex-wrap items-center gap-3 mb-6">
        <label className="flex items-center gap-2">
          <span className="text-xs text-[#64748b]">Coverage check for agent</span>
          <select
            value={agentId}
            onChange={(e) => selectAgent(e.target.value)}
            className="px-3 py-2 rounded-lg bg-[#0a0a0f] border border-white/[0.06] text-sm text-[#f1f5f9] focus:outline-none focus:border-[#a78bfa]/30"
          >
            <option value="">— any agent —</option>
            {agents.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
                {(a as unknown as { risk_class?: string }).risk_class === "high"
                  ? " (high-risk)"
                  : ""}
              </option>
            ))}
          </select>
        </label>
        {agentId && (
          <>
            <button
              onClick={downloadMarkdown}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-white/[0.08] text-xs text-[#94a3b8] hover:text-[#f1f5f9] transition-colors"
            >
              <FileCheck size={12} />
              Markdown
            </button>
            <button
              onClick={downloadPDF}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-white/[0.08] text-xs text-[#94a3b8] hover:text-[#f1f5f9] transition-colors"
            >
              <Download size={12} />
              PDF roster
            </button>
          </>
        )}
        <button
          onClick={() => setNewOpen(true)}
          className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-[#a78bfa] text-[#0a0a0f] text-xs font-medium hover:bg-[#a78bfa]/90 transition-colors ml-auto"
        >
          <Plus size={12} />
          Assign staff
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 flex items-start gap-2 mb-4">
          <AlertCircle size={14} className="text-red-400 shrink-0 mt-0.5" />
          <p className="text-xs text-red-300">{error}</p>
        </div>
      )}

      {roster && (
        <div
          className={`rounded-xl border p-5 mb-6 ${
            roster.compliant
              ? "border-emerald-500/20 bg-emerald-500/5"
              : "border-amber-500/20 bg-amber-500/5"
          }`}
        >
          <div className="flex items-start gap-3">
            {roster.compliant ? (
              <CheckCircle2 size={18} className="text-emerald-300 shrink-0 mt-0.5" />
            ) : (
              <AlertTriangle size={18} className="text-amber-300 shrink-0 mt-0.5" />
            )}
            <div className="flex-1">
              <h3 className="text-sm font-medium text-[#f1f5f9] mb-1">
                {roster.agent.name}
                <span className="text-xs text-[#64748b] ml-2">
                  risk class: {roster.agent.risk_class}
                </span>
              </h3>
              {roster.compliant ? (
                <p className="text-xs text-emerald-200/90">
                  All required roles covered ({roster.required_roles.join(", ")}).
                  {roster.total_assigned_persons} distinct person(s) assigned.
                </p>
              ) : (
                <p className="text-xs text-amber-200/90">
                  Missing required roles:{" "}
                  <strong>{roster.coverage_gaps.join(", ")}</strong>. Assign staff
                  before production use or an auditor will flag this.
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex items-center gap-2 text-xs text-[#64748b] p-6 justify-center">
          <Loader2 size={14} className="animate-spin" />
          Loading assignments…
        </div>
      ) : assignments.length === 0 ? (
        <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-8 text-center">
          <Users size={24} className="text-[#64748b] mx-auto mb-3" />
          <p className="text-sm text-[#94a3b8] mb-1">No staff assigned yet.</p>
          <p className="text-xs text-[#64748b]">
            Art. 14 requires named human oversight. Click "Assign staff" above to
            add the first approver.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {assignments.map((a) => {
            const Icon = ROLE_ICON[a.oversight_role] || UserCheck;
            const isOrgWide = !a.assigned_agent_ids || a.assigned_agent_ids.length === 0;
            const certs = a.training_certificates || [];
            return (
              <div
                key={a.id}
                className="rounded-xl border border-white/[0.06] bg-[#111118] p-4"
              >
                <div className="flex items-start gap-3">
                  <Icon size={14} className="text-[#a78bfa] shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <span className="text-sm font-medium text-[#f1f5f9]">
                        {a.staff_name}
                      </span>
                      <span className="text-xs text-[#64748b]">
                        &lt;{a.staff_email}&gt;
                      </span>
                      {a.staff_role_title && (
                        <span className="text-xs text-[#64748b]">
                          · {a.staff_role_title}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 flex-wrap mb-2 text-[10px] uppercase tracking-wider">
                      <span className="px-2 py-0.5 rounded border bg-violet-500/10 text-violet-300 border-violet-500/20">
                        {ROLE_LABEL[a.oversight_role]}
                      </span>
                      <span className="px-2 py-0.5 rounded border bg-white/5 text-[#94a3b8] border-white/[0.08]">
                        authority: {a.authority_level.replace("_", " ")}
                      </span>
                      <span className="text-[#64748b] normal-case">
                        Scope: {isOrgWide ? "org-wide" : `${a.assigned_agent_ids!.length} agent(s)`}
                      </span>
                    </div>
                    {certs.length > 0 && (
                      <div className="flex items-center gap-1.5 text-xs text-[#94a3b8] mb-1">
                        <GraduationCap size={12} className="text-emerald-400" />
                        {certs.length} training certificate(s):{" "}
                        {certs
                          .map((c) => c.module_title || c.certificate_id || "unnamed")
                          .join(", ")}
                      </div>
                    )}
                    {a.competence_notes && (
                      <p className="text-xs text-[#94a3b8] mb-1">
                        <span className="text-[#64748b]">Competence:</span>{" "}
                        {a.competence_notes}
                      </p>
                    )}
                    {a.authority_source && (
                      <p className="text-xs text-[#94a3b8]">
                        <span className="text-[#64748b]">Authority source:</span>{" "}
                        {a.authority_source}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={() => deleteAssignment(a.id)}
                    className="text-[#64748b] hover:text-red-400 transition-colors p-1"
                    title="Remove assignment"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {newOpen && (
        <NewAssignmentModal
          agents={agents}
          apiKey={apiKey}
          defaultAgentId={agentId}
          onClose={() => setNewOpen(false)}
          onCreated={() => {
            setNewOpen(false);
            refresh();
          }}
        />
      )}
    </>
  );
}

function Stat({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: number;
  icon: typeof Users;
}) {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-4 flex items-center gap-3">
      <Icon size={20} className="text-[#a78bfa]" />
      <div>
        <p className="text-xs text-[#64748b] uppercase tracking-wider">{label}</p>
        <p className="text-2xl font-semibold text-[#f1f5f9]">{value}</p>
      </div>
    </div>
  );
}

function NewAssignmentModal({
  agents,
  apiKey,
  defaultAgentId,
  onClose,
  onCreated,
}: {
  agents: Agent[];
  apiKey: string | null;
  defaultAgentId: string;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [staffName, setStaffName] = useState("");
  const [staffEmail, setStaffEmail] = useState("");
  const [staffRoleTitle, setStaffRoleTitle] = useState("");
  const [oversightRole, setOversightRole] = useState<OversightRole>("approver");
  const [authorityLevel, setAuthorityLevel] = useState<AuthorityLevel>("approve");
  const [scopeMode, setScopeMode] = useState<"org_wide" | "specific">(
    defaultAgentId ? "specific" : "org_wide",
  );
  const [assignedAgentIds, setAssignedAgentIds] = useState<string[]>(
    defaultAgentId ? [defaultAgentId] : [],
  );
  const [competenceNotes, setCompetenceNotes] = useState("");
  const [authoritySource, setAuthoritySource] = useState("");
  const [certModuleTitle, setCertModuleTitle] = useState("");
  const [certId, setCertId] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const toggleAgent = (id: string) => {
    setAssignedAgentIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  };

  const submit = async () => {
    if (!apiKey) return;
    if (!staffName.trim() || !staffEmail.trim()) {
      setErr("Name and email are required.");
      return;
    }
    setBusy(true);
    setErr(null);
    try {
      const training_certificates = certId.trim() || certModuleTitle.trim()
        ? [
            {
              certificate_id: certId.trim() || undefined,
              module_title: certModuleTitle.trim() || undefined,
            },
          ]
        : undefined;
      const res = await fetch("/v1/oversight/assignments", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
        body: JSON.stringify({
          staff_name: staffName,
          staff_email: staffEmail,
          staff_role_title: staffRoleTitle || undefined,
          oversight_role: oversightRole,
          authority_level: authorityLevel,
          assigned_agent_ids:
            scopeMode === "org_wide" ? undefined : assignedAgentIds,
          training_certificates,
          competence_notes: competenceNotes || undefined,
          authority_source: authoritySource || undefined,
        }),
      });
      if (!res.ok) {
        const body = await res.text();
        throw new Error(`Create failed (${res.status}) ${body.slice(0, 120)}`);
      }
      onCreated();
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
        className="w-full max-w-xl max-h-[85vh] overflow-y-auto rounded-xl border border-white/[0.08] bg-[#0a0a0f] p-6 space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold text-[#f1f5f9]">Assign oversight role</h2>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Staff name">
            <input
              value={staffName}
              onChange={(e) => setStaffName(e.target.value)}
              placeholder="Full name"
              className={inputClass}
            />
          </Field>
          <Field label="Email">
            <input
              value={staffEmail}
              onChange={(e) => setStaffEmail(e.target.value)}
              placeholder="work@example.com"
              type="email"
              className={inputClass}
            />
          </Field>
        </div>

        <Field label="Role title (optional)">
          <input
            value={staffRoleTitle}
            onChange={(e) => setStaffRoleTitle(e.target.value)}
            placeholder="e.g. Senior Risk Analyst"
            className={inputClass}
          />
        </Field>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Oversight role">
            <select
              value={oversightRole}
              onChange={(e) => setOversightRole(e.target.value as OversightRole)}
              className={inputClass}
            >
              {OVERSIGHT_ROLES.map((r) => (
                <option key={r} value={r}>
                  {ROLE_LABEL[r]}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Authority level">
            <select
              value={authorityLevel}
              onChange={(e) => setAuthorityLevel(e.target.value as AuthorityLevel)}
              className={inputClass}
            >
              {AUTHORITY_LEVELS.map((a) => (
                <option key={a} value={a}>
                  {a.replace("_", " ")}
                </option>
              ))}
            </select>
          </Field>
        </div>

        <Field label="Scope">
          <div className="flex gap-4 text-xs text-[#94a3b8]">
            <label className="flex items-center gap-2">
              <input
                type="radio"
                checked={scopeMode === "org_wide"}
                onChange={() => setScopeMode("org_wide")}
              />
              Org-wide (all current and future agents)
            </label>
            <label className="flex items-center gap-2">
              <input
                type="radio"
                checked={scopeMode === "specific"}
                onChange={() => setScopeMode("specific")}
              />
              Specific agents
            </label>
          </div>
        </Field>

        {scopeMode === "specific" && (
          <div className="max-h-40 overflow-y-auto rounded-lg border border-white/[0.06] bg-[#111118] p-2 space-y-1">
            {agents.length === 0 && (
              <p className="text-xs text-[#64748b] p-2">No agents available.</p>
            )}
            {agents.map((a) => (
              <label
                key={a.id}
                className="flex items-center gap-2 p-1.5 rounded text-xs text-[#94a3b8] hover:text-[#f1f5f9] cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={assignedAgentIds.includes(a.id)}
                  onChange={() => toggleAgent(a.id)}
                />
                {a.name}
                <span className="text-[#64748b]">({a.id})</span>
              </label>
            ))}
          </div>
        )}

        <div className="pt-2 border-t border-white/[0.06]">
          <p className="text-xs text-[#64748b] uppercase tracking-wider mb-2">
            Training evidence (Art. 4)
          </p>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Module title">
              <input
                value={certModuleTitle}
                onChange={(e) => setCertModuleTitle(e.target.value)}
                placeholder="e.g. AI Act Essentials"
                className={inputClass}
              />
            </Field>
            <Field label="Certificate ID">
              <input
                value={certId}
                onChange={(e) => setCertId(e.target.value)}
                placeholder="From /literacy"
                className={inputClass}
              />
            </Field>
          </div>
          <p className="text-[10px] text-[#64748b] mt-1">
            Additional certificates can be added after creation.
          </p>
        </div>

        <Field label="Competence notes">
          <textarea
            rows={2}
            value={competenceNotes}
            onChange={(e) => setCompetenceNotes(e.target.value)}
            placeholder="Prior experience, role-relevant training, domain knowledge"
            className={inputClass}
          />
        </Field>

        <Field label="Authority source">
          <input
            value={authoritySource}
            onChange={(e) => setAuthoritySource(e.target.value)}
            placeholder="e.g. delegation memo, job description reference"
            className={inputClass}
          />
        </Field>

        {err && (
          <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 flex items-start gap-2">
            <AlertCircle size={14} className="text-red-400 shrink-0 mt-0.5" />
            <p className="text-xs text-red-300">{err}</p>
          </div>
        )}

        <div className="flex gap-2 justify-end pt-2">
          <button
            onClick={onClose}
            className="px-3 py-2 rounded-lg border border-white/[0.08] text-xs text-[#64748b] hover:text-[#f1f5f9] transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={busy}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-[#a78bfa] text-[#0a0a0f] text-xs font-medium disabled:opacity-40"
          >
            {busy ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />}
            Create assignment
          </button>
        </div>
      </div>
    </div>
  );
}

const inputClass =
  "w-full px-3 py-2 rounded-lg bg-[#111118] border border-white/[0.06] text-sm text-[#f1f5f9] placeholder-[#64748b] focus:outline-none focus:border-[#a78bfa]/30";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="block text-xs text-[#64748b] mb-1.5">{label}</span>
      {children}
    </label>
  );
}
