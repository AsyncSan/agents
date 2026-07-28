import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AlertCircle, Building2, CheckCircle, Save, Trash2 } from "lucide-react";
import {
  clearOrgProfile,
  EMPTY_PROFILE,
  loadOrgProfile,
  saveOrgProfile,
  type OrgProfile,
  type SizeCategory,
} from "../org-profile";

const SIZE_OPTIONS: { key: SizeCategory; label: string; hint: string }[] = [
  {
    key: "microenterprise",
    label: "Microenterprise",
    hint: "< 10 employees, < €2M turnover. Qualifies for Art. 63 simplified QMS.",
  },
  {
    key: "sme",
    label: "SME",
    hint: "< 250 employees, < €50M turnover. Art. 62 + Art. 99(6) benefits apply.",
  },
  { key: "large", label: "Large enterprise", hint: "250+ employees." },
  {
    key: "public_body",
    label: "Public body / public service",
    hint: "Triggers Art. 27 FRIA obligations for Annex III systems.",
  },
];

export function OrgProfilePage() {
  const navigate = useNavigate();
  const [profile, setProfile] = useState<OrgProfile>(EMPTY_PROFILE);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setProfile(loadOrgProfile());
  }, []);

  const setField = <K extends keyof OrgProfile>(k: K, v: OrgProfile[K]) => {
    setProfile((p) => ({ ...p, [k]: v }));
    setSaved(false);
  };

  const handleSave = () => {
    if (!profile.organisation.trim()) {
      setError("Organisation name is required.");
      return;
    }
    setError(null);
    saveOrgProfile(profile);
    setSaved(true);
  };

  const handleClear = () => {
    if (!confirm("Clear the organisation profile? Wizards will fall back to placeholders.")) return;
    clearOrgProfile();
    setProfile(EMPTY_PROFILE);
    setSaved(false);
  };

  return (
    <div className="max-w-2xl mx-auto py-8">
      <div className="mb-6">
        <p className="text-xs text-[#64748b] mb-1 font-medium uppercase tracking-widest">Settings</p>
        <h1 className="text-2xl font-semibold text-[#f1f5f9]">Organisation profile</h1>
        <p className="text-xs text-[#94a3b8] mt-1">
          Enter your organisation once. Every compliance wizard picks it up, so you stop
          retyping the same legal name, address, and accountable contact into each document.
          Stored in your browser; never sent to us.
        </p>
      </div>

      <Card>
        <Field label="Legal name *">
          <input
            value={profile.organisation}
            onChange={(e) => setField("organisation", e.target.value)}
            placeholder="Company or public body legal name"
            className={inputClass}
          />
        </Field>
        <Field label="Registered address">
          <input
            value={profile.address}
            onChange={(e) => setField("address", e.target.value)}
            placeholder="Street, ZIP, City, Country"
            className={inputClass}
          />
        </Field>
        <Field label="Accountable contact">
          <input
            value={profile.contact}
            onChange={(e) => setField("contact", e.target.value)}
            placeholder="Name, role, email, phone"
            className={inputClass}
          />
        </Field>
      </Card>

      <Card title="Size category">
        <p className="text-xs text-[#64748b] mb-3">
          Drives simplified-form availability and fine-cap assumptions. Pick what matches your entity today.
        </p>
        <div className="space-y-2">
          {SIZE_OPTIONS.map((opt) => (
            <label
              key={opt.key}
              className={`flex items-start gap-2 p-3 rounded-lg border cursor-pointer transition-colors ${
                profile.size_category === opt.key
                  ? "border-[#00d4ff]/30 bg-[#00d4ff]/5"
                  : "border-white/[0.06] hover:border-white/[0.12]"
              }`}
            >
              <input
                type="radio"
                name="size_category"
                checked={profile.size_category === opt.key}
                onChange={() => setField("size_category", opt.key)}
                className="mt-0.5"
              />
              <div>
                <div className="text-sm text-[#f1f5f9]">{opt.label}</div>
                <div className="text-xs text-[#64748b]">{opt.hint}</div>
              </div>
            </label>
          ))}
        </div>
      </Card>

      <Card title="Governance roles">
        <Field label="Accountability owner (QMS, Art. 17(1)(m))">
          <input
            value={profile.accountability_owner}
            onChange={(e) => setField("accountability_owner", e.target.value)}
            placeholder="Role or named person responsible for the QMS"
            className={inputClass}
          />
        </Field>
        <Field label="PMM owner (Art. 72)">
          <input
            value={profile.pmm_owner}
            onChange={(e) => setField("pmm_owner", e.target.value)}
            placeholder="Role accountable for post-market monitoring"
            className={inputClass}
          />
        </Field>
        <Field label="Authority liaison (Art. 17(1)(j))">
          <input
            value={profile.authority_contact}
            onChange={(e) => setField("authority_contact", e.target.value)}
            placeholder="Who the MSA (e.g., BNetzA) contacts"
            className={inputClass}
          />
        </Field>
      </Card>

      <Card title="Market placement">
        <Field label="Member States where you place systems on market (one per line)">
          <textarea
            rows={3}
            value={profile.member_states}
            onChange={(e) => setField("member_states", e.target.value)}
            placeholder={"Germany\nAustria\nFrance"}
            className={inputClass}
          />
        </Field>
        <label className="flex items-center gap-2 text-sm text-[#94a3b8]">
          <input
            type="checkbox"
            checked={profile.ce_marking_affixed}
            onChange={(e) => setField("ce_marking_affixed", e.target.checked)}
          />
          CE marking affixed on placed systems (Art. 48)
        </label>
      </Card>

      {error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 flex items-start gap-2 mb-4">
          <AlertCircle size={14} className="text-red-400 shrink-0 mt-0.5" />
          <p className="text-xs text-red-300">{error}</p>
        </div>
      )}

      {saved && (
        <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3 flex items-start gap-2 mb-4">
          <CheckCircle size={14} className="text-emerald-400 shrink-0 mt-0.5" />
          <p className="text-xs text-emerald-200/90">
            Saved. Your next FRIA, Annex IV, QMS, PMM and EU-DB draft will pull these values.
          </p>
        </div>
      )}

      <div className="flex items-center justify-between pt-2">
        <button
          onClick={handleClear}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-[#64748b] hover:text-red-400 transition-colors"
        >
          <Trash2 size={12} />
          Clear profile
        </button>
        <div className="flex gap-2">
          <Link
            to="/compliance"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-white/[0.08] text-sm text-[#94a3b8] hover:text-[#f1f5f9] no-underline transition-colors"
          >
            Back to workspace
          </Link>
          <button
            onClick={handleSave}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-sm font-medium"
            style={{ transition: "background 0.2s cubic-bezier(0.16, 1, 0.3, 1)" }}
          >
            <Save size={14} />
            Save profile
          </button>
        </div>
      </div>
    </div>
  );
}

const inputClass =
  "w-full px-3 py-2 rounded-lg bg-[#0a0a0f] border border-white/[0.06] text-sm text-[#f1f5f9] placeholder-[#64748b] focus:outline-none focus:border-[#00d4ff]/30";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block mb-3">
      <span className="block text-xs text-[#64748b] mb-1.5">{label}</span>
      {children}
    </label>
  );
}

function Card({ title, children }: { title?: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5 mb-4">
      {title && (
        <h2 className="text-sm font-medium text-[#f1f5f9] mb-3 flex items-center gap-2">
          <Building2 size={14} className="text-[#00d4ff]" />
          {title}
        </h2>
      )}
      {children}
    </div>
  );
}
