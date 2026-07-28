import { Edit3 } from "lucide-react";
import type { Agent } from "../api";
import { useT } from "../i18n";

export type ManualAgentState = {
  name: string;
  version: number;
  risk_class: "minimal" | "limited" | "high";
  description: string;
  domain: string;
  model: string;
};

export const EMPTY_MANUAL: ManualAgentState = {
  name: "",
  version: 1,
  risk_class: "minimal",
  description: "",
  domain: "",
  model: "",
};

export function manualAgentPayload(m: ManualAgentState) {
  return {
    name: m.name.trim(),
    version: m.version || 1,
    risk_class: m.risk_class,
    description: m.description.trim() || undefined,
    domain: m.domain.trim() || undefined,
    model: m.model.trim() || undefined,
  };
}

export const MANUAL_MARKER = "__manual__";

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

/**
 * AgentOrManualSelector — a combined dropdown that lets the user either pick a
 * platform-registered agent or describe an external system manually. The
 * manual fields are shown inline when the special marker is selected.
 *
 * Use ``mode === "manual"`` (or ``agent_id === ""`` when ``mode === "agent"``)
 * to decide which payload field to send.
 */
export function AgentOrManualSelector({
  agents,
  agentId,
  mode,
  manual,
  onAgentIdChange,
  onModeChange,
  onManualChange,
  requireManualName = true,
  label,
}: {
  agents: Agent[];
  agentId: string;
  mode: "agent" | "manual";
  manual: ManualAgentState;
  onAgentIdChange: (id: string) => void;
  onModeChange: (mode: "agent" | "manual") => void;
  onManualChange: (m: ManualAgentState) => void;
  requireManualName?: boolean;
  label?: string;
}) {
  const { lang } = useT();
  const de = lang === "de";
  const t = de
    ? {
        label: "Agent",
        select: "Agent auswählen…",
        manual: "Externes System manuell beschreiben…",
        hint: "Beschreibt das zu bewertende KI-System. Muss nicht auf der Plattform registriert sein.",
        systemName: "Systemname",
        version: "Version",
        riskClass: "Risikoklasse",
        description: "Verwendungszweck / Kurzbeschreibung",
        descriptionPh: "Was das System macht, für wen es eingesetzt wird",
        domain: "Domäne",
        domainPh: "Fintech, HR, Gesundheit…",
        model: "Zugrundeliegendes Modell",
      }
    : {
        label: "Agent",
        select: "Select an agent…",
        manual: "Describe an external system manually…",
        hint:
          "Describe the AI system you want to assess. It does not need to be registered here.",
        systemName: "System name",
        version: "Version",
        riskClass: "Risk class",
        description: "Intended purpose / short description",
        descriptionPh: "What this system does, who it is used for",
        domain: "Domain",
        domainPh: "fintech, hr, healthcare…",
        model: "Underlying model",
      };
  const dropdownValue = mode === "manual" ? MANUAL_MARKER : agentId;
  const activeLabel = label ?? t.label;

  return (
    <div className="space-y-3">
      <Field label={activeLabel}>
        <select
          value={dropdownValue}
          onChange={(e) => {
            const val = e.target.value;
            if (val === MANUAL_MARKER) {
              onModeChange("manual");
            } else {
              onModeChange("agent");
              onAgentIdChange(val);
            }
          }}
          className={inputClass}
        >
          <option value="">{t.select}</option>
          {agents.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name} ({a.id})
            </option>
          ))}
          <option value={MANUAL_MARKER}>{t.manual}</option>
        </select>
      </Field>

      {mode === "manual" && (
        <div className="rounded-lg border border-[#00d4ff]/15 bg-[#00d4ff]/[0.03] p-3 space-y-3">
          <div className="flex items-center gap-2 text-xs text-[#94a3b8]">
            <Edit3 size={12} className="text-[#00d4ff]" />
            <span>{t.hint}</span>
          </div>
          <Field label={`${t.systemName}${requireManualName ? " *" : ""}`}>
            <input
              value={manual.name}
              onChange={(e) => onManualChange({ ...manual, name: e.target.value })}
              placeholder={de ? "z. B. Interner Credit Scorer" : "e.g., Internal Credit Scorer"}
              className={inputClass}
            />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label={t.version}>
              <input
                type="number"
                min="1"
                value={manual.version}
                onChange={(e) =>
                  onManualChange({
                    ...manual,
                    version: parseInt(e.target.value, 10) || 1,
                  })
                }
                className={inputClass}
              />
            </Field>
            <Field label={t.riskClass}>
              <select
                value={manual.risk_class}
                onChange={(e) =>
                  onManualChange({
                    ...manual,
                    risk_class: e.target.value as ManualAgentState["risk_class"],
                  })
                }
                className={inputClass}
              >
                <option value="minimal">minimal</option>
                <option value="limited">limited</option>
                <option value="high">high</option>
              </select>
            </Field>
          </div>
          <Field label={t.description}>
            <textarea
              rows={2}
              value={manual.description}
              onChange={(e) =>
                onManualChange({ ...manual, description: e.target.value })
              }
              placeholder={t.descriptionPh}
              className={inputClass}
            />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label={t.domain}>
              <input
                value={manual.domain}
                onChange={(e) =>
                  onManualChange({ ...manual, domain: e.target.value })
                }
                placeholder={t.domainPh}
                className={inputClass}
              />
            </Field>
            <Field label={t.model}>
              <input
                value={manual.model}
                onChange={(e) =>
                  onManualChange({ ...manual, model: e.target.value })
                }
                placeholder={de ? "z. B. gpt-4o, claude-sonnet" : "e.g., gpt-4o, claude-sonnet"}
                className={inputClass}
              />
            </Field>
          </div>
        </div>
      )}
    </div>
  );
}
