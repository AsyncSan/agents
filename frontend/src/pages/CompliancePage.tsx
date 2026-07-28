import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertCircle,
  Archive,
  CheckCircle,
  Clock,
  FileCheck,
  FileText,
  GraduationCap,
  Building2,
  LayoutDashboard,
  Loader2,
  RefreshCw,
  ShieldAlert,
  Siren,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import {
  archiveComplianceDocument,
  approveComplianceDocument,
  deleteComplianceDocument,
  getComplianceDocument,
  getComplianceSummary,
  listComplianceDocuments,
  type ComplianceDocument,
  type ComplianceDocumentDetail,
  type ComplianceSummary,
} from "../compliance-api";
import { useT } from "../i18n";
import { loadOrgProfile } from "../org-profile";

const DOC_TYPE_LABEL: Record<string, string> = {
  fria: "FRIA",
  annex_iv: "Annex IV",
  literacy_completion: "Literacy",
  pmm_plan: "PMM plan",
  qms_manual: "QMS",
  eu_db_registration: "EU DB",
  declaration_of_conformity: "Declaration",
};

const DOC_TYPE_ICON: Record<string, typeof Sparkles> = {
  fria: Sparkles,
  annex_iv: FileCheck,
  literacy_completion: GraduationCap,
  pmm_plan: FileCheck,
  qms_manual: FileCheck,
  eu_db_registration: FileCheck,
  declaration_of_conformity: FileCheck,
};

const STATUS_STYLE: Record<string, string> = {
  draft: "bg-white/5 text-[#94a3b8] border-white/[0.08]",
  submitted: "bg-amber-500/10 text-amber-300 border-amber-500/20",
  approved: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20",
  archived: "bg-white/5 text-[#64748b] border-white/[0.04]",
};

export function CompliancePage() {
  const { t, lang } = useT();
  const apiKey = typeof window !== "undefined" ? localStorage.getItem("af_api_key") : null;

  const statusLabel = (key: string) => {
    if (lang !== "de") return key.charAt(0).toUpperCase() + key.slice(1);
    return {
      all: "Alle",
      draft: "Entwurf",
      approved: "Freigegeben",
      archived: "Archiviert",
    }[key] || key;
  };
  const [docs, setDocs] = useState<ComplianceDocument[]>([]);
  const [summary, setSummary] = useState<ComplianceSummary | null>(null);
  const [staleCount, setStaleCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<string>("all");
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [detail, setDetail] = useState<ComplianceDocumentDetail | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    if (!apiKey) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const [list, sum] = await Promise.all([
        listComplianceDocuments(apiKey, {
          doc_type: filterType !== "all" ? filterType : undefined,
          status: filterStatus !== "all" ? filterStatus : undefined,
        }),
        getComplianceSummary(apiKey),
      ]);
      setDocs(list.documents);
      setStaleCount(list.stale_count);
      setSummary(sum);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load workspace");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterType, filterStatus, apiKey]);

  const totalStale = staleCount;

  const handleOpen = async (id: string) => {
    if (!apiKey) return;
    try {
      setDetail(await getComplianceDocument(apiKey, id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to open document");
    }
  };

  const handleApprove = async (id: string) => {
    if (!apiKey) return;
    setBusy(true);
    try {
      await approveComplianceDocument(apiKey, id);
      await refresh();
      if (detail?.id === id) setDetail(await getComplianceDocument(apiKey, id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Approve failed");
    } finally {
      setBusy(false);
    }
  };

  const handleArchive = async (id: string) => {
    if (!apiKey) return;
    setBusy(true);
    try {
      await archiveComplianceDocument(apiKey, id);
      await refresh();
      if (detail?.id === id) setDetail(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Archive failed");
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!apiKey) return;
    if (!confirm("Delete this document permanently? Downloads already made are unaffected.")) return;
    setBusy(true);
    try {
      await deleteComplianceDocument(apiKey, id);
      await refresh();
      if (detail?.id === id) setDetail(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  };

  const stats = useMemo(() => {
    const byType = summary?.by_doc_type || {};
    const byStatus = summary?.by_status || {};
    const total = Object.values(byType).reduce((s, n) => s + n, 0);
    return {
      total,
      fria: byType.fria || 0,
      annex_iv: byType.annex_iv || 0,
      literacy: byType.literacy_completion || 0,
      draft: byStatus.draft || 0,
      approved: byStatus.approved || 0,
      archived: byStatus.archived || 0,
    };
  }, [summary]);

  if (!apiKey) {
    return (
      <div className="max-w-xl mx-auto py-16 text-center">
        <LayoutDashboard size={40} className="text-[#00d4ff] mx-auto mb-4" />
        <h1 className="text-2xl font-semibold text-[#f1f5f9] mb-2">{t("compliance.login.title")}</h1>
        <p className="text-sm text-[#94a3b8] mb-6">{t("compliance.login.desc")}</p>
        <Link
          to="/auth"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-sm font-medium no-underline"
        >
          {t("compliance.login.cta")}
        </Link>
      </div>
    );
  }

  return (
    <>
      <section className="mb-8 pt-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <p className="text-xs text-[#64748b] mb-1 font-medium uppercase tracking-widest">
              {t("compliance.page.eyebrow")}
            </p>
            <h1 className="text-2xl font-semibold text-[#f1f5f9]">{t("compliance.page.title")}</h1>
          </div>
          <button
            onClick={refresh}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-white/[0.08] text-xs text-[#94a3b8] hover:text-[#f1f5f9] disabled:opacity-40 transition-colors"
          >
            {loading ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
            {t("compliance.refresh")}
          </button>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
          <Stat label="Total" value={stats.total} icon={FileText} />
          <Stat label="FRIA" value={stats.fria} icon={Sparkles} />
          <Stat label="Annex IV" value={stats.annex_iv} icon={FileCheck} />
          <Stat label="Literacy" value={stats.literacy} icon={GraduationCap} />
        </div>

        <div className="rounded-xl border border-[#00d4ff]/20 bg-gradient-to-r from-[#00d4ff]/[0.05] to-[#111118] p-4 mb-4 flex items-center gap-3">
          <Sparkles size={18} className="text-[#00d4ff] shrink-0" />
          <div className="flex-1">
            <p className="text-sm text-[#f1f5f9] font-medium">
              New: one-shot compliance bundle
            </p>
            <p className="text-xs text-[#94a3b8] mt-0.5">
              Pick a use-case, describe your system, get every required document
              (FRIA, Annex IV, PMM, data sheet, EU-DB) in one ZIP.
            </p>
          </div>
          <Link
            to="/compliance/setup"
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-xs font-medium no-underline"
          >
            Run setup
          </Link>
        </div>

        {!loadOrgProfile().organisation && (
          <div className="rounded-xl border border-[#00d4ff]/15 bg-[#00d4ff]/[0.03] p-3 mb-4 flex items-start gap-2">
            <Building2 size={14} className="text-[#00d4ff] shrink-0 mt-0.5" />
            <div className="flex-1 text-xs text-[#94a3b8]">
              <strong className="text-[#f1f5f9]">Set up your organisation profile once.</strong>{" "}
              Your legal name, address, accountable contact, and size category flow into every
              FRIA, Annex IV, PMM, QMS, and EU-DB draft.{" "}
              <Link to="/settings/org" className="text-[#00d4ff] hover:underline">
                Configure now (60s)
              </Link>
            </div>
          </div>
        )}

        <div className="mb-6">
          <Link
            to="/incidents"
            className="flex items-center gap-2 px-4 py-3 rounded-xl border border-amber-500/10 bg-amber-500/5 text-xs text-[#94a3b8] hover:border-amber-500/20 no-underline transition-colors"
          >
            <Siren size={14} className="text-amber-400" />
            <span className="flex-1">
              <span className="text-[#f1f5f9] font-medium">Serious incident reporting (Art. 73)</span>
              <span className="text-[#64748b] ml-2">
                Draft the report, track the 2/10/15-day deadline, file with the MSA.
              </span>
            </span>
            <span className="text-[#00d4ff]">Open →</span>
          </Link>
        </div>

        {totalStale > 0 && (
          <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 mb-4 flex items-start gap-2">
            <ShieldAlert size={14} className="text-amber-400 shrink-0 mt-0.5" />
            <p className="text-xs text-amber-200/90">
              <strong>{totalStale}</strong> document{totalStale === 1 ? "" : "s"} reference{totalStale === 1 ? "s" : ""} an agent
              version that has since been superseded. Review and re-approve.
            </p>
          </div>
        )}

        <div className="flex flex-wrap gap-2 mb-4">
          <FilterPills
            label={t("compliance.filter.type")}
            options={[
              { key: "all", label: `${statusLabel("all")} (${stats.total})` },
              { key: "fria", label: `FRIA (${stats.fria})` },
              { key: "annex_iv", label: `Annex IV (${stats.annex_iv})` },
              { key: "literacy_completion", label: `Literacy (${stats.literacy})` },
            ]}
            value={filterType}
            onChange={setFilterType}
          />
          <FilterPills
            label={t("compliance.filter.status")}
            options={[
              { key: "all", label: statusLabel("all") },
              { key: "draft", label: `${statusLabel("draft")} (${stats.draft})` },
              { key: "approved", label: `${statusLabel("approved")} (${stats.approved})` },
              { key: "archived", label: `${statusLabel("archived")} (${stats.archived})` },
            ]}
            value={filterStatus}
            onChange={setFilterStatus}
          />
        </div>

        {error && (
          <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 flex items-start gap-2 mb-4">
            <AlertCircle size={14} className="text-red-400 shrink-0 mt-0.5" />
            <p className="text-xs text-red-300">{error}</p>
          </div>
        )}

        {loading && docs.length === 0 ? (
          <p className="text-center text-sm text-[#64748b] py-10">Loading…</p>
        ) : docs.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="rounded-xl border border-white/[0.06] bg-[#111118] overflow-hidden">
            <table className="w-full text-sm">
              <thead className="border-b border-white/[0.06] bg-[#0a0a0f]">
                <tr className="text-xs text-[#64748b]">
                  <th className="text-left py-2.5 px-4 font-medium">Type</th>
                  <th className="text-left py-2.5 px-4 font-medium">Title</th>
                  <th className="text-left py-2.5 px-4 font-medium">Agent</th>
                  <th className="text-left py-2.5 px-4 font-medium">Status</th>
                  <th className="text-left py-2.5 px-4 font-medium">Updated</th>
                  <th className="text-right py-2.5 px-4 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {docs.map((doc) => {
                  const Icon = DOC_TYPE_ICON[doc.doc_type] || FileText;
                  return (
                    <tr
                      key={doc.id}
                      className="border-b border-white/[0.04] hover:bg-white/[0.02] cursor-pointer"
                      onClick={() => handleOpen(doc.id)}
                    >
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <Icon size={14} className="text-[#00d4ff]" />
                          <span className="text-xs text-[#94a3b8]">
                            {DOC_TYPE_LABEL[doc.doc_type] || doc.doc_type}
                          </span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-[#f1f5f9]">
                        <div className="flex items-center gap-2">
                          <span className="truncate max-w-xs">{doc.title}</span>
                          {doc.is_stale && (
                            <span
                              title="Agent version changed since this document was last reviewed"
                              className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium border border-amber-500/20 bg-amber-500/10 text-amber-300"
                            >
                              <ShieldAlert size={10} />
                              stale
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4 text-xs text-[#94a3b8]">
                        {doc.agent_id ? (
                          <span className="font-mono">
                            {doc.agent_id}
                            {doc.agent_version != null && ` · v${doc.agent_version}`}
                          </span>
                        ) : (
                          <span className="text-[#64748b]">-</span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-[10px] font-medium border ${
                            STATUS_STYLE[doc.status] || STATUS_STYLE.draft
                          }`}
                        >
                          {doc.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-xs text-[#64748b]">
                        {new Date(doc.updated_at).toLocaleDateString()}
                      </td>
                      <td className="py-3 px-4" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center justify-end gap-1">
                          {doc.status !== "approved" && doc.status !== "archived" && (
                            <IconButton
                              title="Approve"
                              disabled={busy}
                              onClick={() => handleApprove(doc.id)}
                            >
                              <CheckCircle size={14} className="text-emerald-400" />
                            </IconButton>
                          )}
                          {doc.status !== "archived" && (
                            <IconButton
                              title="Archive"
                              disabled={busy}
                              onClick={() => handleArchive(doc.id)}
                            >
                              <Archive size={14} />
                            </IconButton>
                          )}
                          <IconButton
                            title="Delete"
                            disabled={busy}
                            onClick={() => handleDelete(doc.id)}
                          >
                            <Trash2 size={14} className="text-red-400" />
                          </IconButton>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {detail && (
        <div
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm p-4 flex items-center justify-center"
          onClick={() => setDetail(null)}
        >
          <div
            className="rounded-xl border border-white/[0.08] bg-[#111118] w-full max-w-3xl max-h-[85vh] overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between p-5 border-b border-white/[0.06]">
              <div>
                <p className="text-xs text-[#64748b] mb-1 font-medium uppercase tracking-widest">
                  {DOC_TYPE_LABEL[detail.doc_type]} · {detail.status}
                </p>
                <h2 className="text-base font-semibold text-[#f1f5f9]">{detail.title}</h2>
                <div className="flex items-center gap-3 mt-2 text-xs text-[#64748b]">
                  {detail.agent_id && (
                    <span>
                      <span className="font-mono">{detail.agent_id}</span>
                      {detail.agent_version != null && ` · v${detail.agent_version}`}
                      {detail.is_stale && detail.current_agent_version != null && (
                        <span className="ml-2 text-amber-300">
                          (current v{detail.current_agent_version})
                        </span>
                      )}
                    </span>
                  )}
                  <span className="flex items-center gap-1">
                    <Clock size={10} />
                    {new Date(detail.updated_at).toLocaleString()}
                  </span>
                </div>
              </div>
              <button
                onClick={() => setDetail(null)}
                className="p-1.5 rounded-lg text-[#64748b] hover:text-[#f1f5f9] transition-colors"
              >
                <X size={16} />
              </button>
            </div>
            <div className="p-5 overflow-y-auto flex-1">
              <pre className="text-xs text-[#94a3b8] whitespace-pre-wrap break-words">
                {JSON.stringify(detail.payload, null, 2)}
              </pre>
            </div>
          </div>
        </div>
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
  icon: typeof Sparkles;
}) {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-4">
      <div className="flex items-center gap-2 text-xs text-[#64748b] mb-2">
        <Icon size={12} />
        {label}
      </div>
      <div className="text-2xl font-semibold text-[#f1f5f9]">{value}</div>
    </div>
  );
}

function FilterPills({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { key: string; label: string }[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex items-center gap-1 flex-wrap">
      <span className="text-xs text-[#64748b] mr-1">{label}:</span>
      {options.map((o) => (
        <button
          key={o.key}
          onClick={() => onChange(o.key)}
          className={`px-2.5 py-1 rounded-lg text-xs transition-colors ${
            value === o.key
              ? "bg-[#00d4ff]/10 text-[#00d4ff] border border-[#00d4ff]/20"
              : "text-[#94a3b8] hover:text-[#f1f5f9] border border-white/[0.06]"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

function IconButton({
  children,
  title,
  onClick,
  disabled,
}: {
  children: React.ReactNode;
  title: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className="p-1.5 rounded-lg text-[#64748b] hover:text-[#f1f5f9] hover:bg-white/[0.04] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
    >
      {children}
    </button>
  );
}

function EmptyState() {
  const { t } = useT();
  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-10 text-center">
      <LayoutDashboard size={32} className="text-[#64748b] mx-auto mb-3" />
      <h3 className="text-sm font-medium text-[#f1f5f9] mb-2">{t("compliance.empty.title")}</h3>
      <p className="text-xs text-[#94a3b8] mb-6 max-w-sm mx-auto">{t("compliance.empty.desc")}</p>
      <div className="flex flex-wrap gap-2 justify-center">
        <Link
          to="/fria"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-white/[0.08] text-xs text-[#94a3b8] hover:text-[#f1f5f9] no-underline transition-colors"
        >
          <Sparkles size={12} />
          Start a FRIA
        </Link>
        <Link
          to="/annex-iv"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-white/[0.08] text-xs text-[#94a3b8] hover:text-[#f1f5f9] no-underline transition-colors"
        >
          <FileCheck size={12} />
          Annex IV draft
        </Link>
        <Link
          to="/literacy"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-white/[0.08] text-xs text-[#94a3b8] hover:text-[#f1f5f9] no-underline transition-colors"
        >
          <GraduationCap size={12} />
          AI Literacy
        </Link>
      </div>
    </div>
  );
}
