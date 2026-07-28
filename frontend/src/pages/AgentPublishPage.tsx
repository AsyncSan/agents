import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle,
  Code2,
  Loader2,
  Plus,
  Trash2,
} from "lucide-react";

type InputField = { name: string; type: string; required: boolean };
type OutputField = { name: string; type: string; guaranteed: boolean };

interface Draft {
  id: string;
  name: string;
  description: string;
  domain: string;
  tags: string;
  risk_class: "minimal" | "limited" | "high";
  instructions: string;
  inputs: InputField[];
  outputs: OutputField[];
  runtime_model: string;
  runtime_compute_tier: "container" | "vm";
  runtime_server_type: string;
  runtime_tools: string;
  runtime_estimated_duration_seconds: number;
  pricing_base_price_usd: number;
  constraints_timeout_max: number;
}

const EMPTY: Draft = {
  id: "",
  name: "",
  description: "",
  domain: "",
  tags: "",
  risk_class: "minimal",
  instructions: "",
  inputs: [{ name: "input", type: "string", required: true }],
  outputs: [{ name: "output.md", type: "markdown", guaranteed: true }],
  runtime_model: "anthropic/claude-sonnet-4-6",
  runtime_compute_tier: "container",
  runtime_server_type: "cax11",
  runtime_tools: "shell",
  runtime_estimated_duration_seconds: 300,
  pricing_base_price_usd: 1.0,
  constraints_timeout_max: 3600,
};

const DRAFT_KEY = "af_agent_publish_draft_v1";

function loadDraft(): Draft {
  if (typeof window === "undefined") return EMPTY;
  try {
    const raw = localStorage.getItem(DRAFT_KEY);
    return raw ? { ...EMPTY, ...JSON.parse(raw) } : EMPTY;
  } catch {
    return EMPTY;
  }
}

export function AgentPublishPage() {
  const navigate = useNavigate();
  const apiKey = typeof window !== "undefined" ? localStorage.getItem("af_api_key") : null;
  const role = typeof window !== "undefined" ? localStorage.getItem("af_role") : null;

  const [draft, setDraft] = useState<Draft>(loadDraft);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [published, setPublished] = useState<{ id: string; name: string } | null>(null);

  const setField = <K extends keyof Draft>(k: K, v: Draft[K]) => {
    setDraft((prev) => {
      const next = { ...prev, [k]: v };
      try {
        localStorage.setItem(DRAFT_KEY, JSON.stringify(next));
      } catch {
        // ignore storage errors
      }
      return next;
    });
  };

  const handleSubmit = async () => {
    if (!apiKey) {
      setError("Log in as a provider to publish.");
      return;
    }
    if (role !== "provider") {
      setError("Agent publishing requires a provider account. Register again with the Provider role.");
      return;
    }
    const payload = {
      id: draft.id.trim(),
      name: draft.name.trim(),
      description: draft.description.trim() || null,
      domain: draft.domain.trim(),
      tags: draft.tags.split(",").map((s) => s.trim()).filter(Boolean),
      risk_class: draft.risk_class,
      instructions: draft.instructions,
      inputs: draft.inputs.filter((i) => i.name.trim() !== ""),
      outputs: draft.outputs.filter((o) => o.name.trim() !== ""),
      runtime: {
        model: draft.runtime_model,
        compute_tier: draft.runtime_compute_tier,
        server_type: draft.runtime_server_type,
        tools: draft.runtime_tools.split(",").map((s) => s.trim()).filter(Boolean),
        estimated_duration_seconds: draft.runtime_estimated_duration_seconds,
      },
      pricing: {
        model: "per_execution",
        base_price_usd: draft.pricing_base_price_usd,
      },
      constraints: {
        timeout_max: draft.constraints_timeout_max,
      },
    };

    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/v1/agents", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.error?.message || "Publish failed");
      }
      const data = await res.json();
      setPublished({ id: data.id, name: data.name });
      localStorage.removeItem(DRAFT_KEY);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Publish failed");
    } finally {
      setBusy(false);
    }
  };

  if (!apiKey) {
    return (
      <div className="max-w-xl mx-auto py-16 text-center">
        <Code2 size={40} className="text-[#00d4ff] mx-auto mb-4" />
        <h1 className="text-2xl font-semibold text-[#f1f5f9] mb-2">Publish an agent</h1>
        <p className="text-sm text-[#94a3b8] mb-6">Log in as a provider to publish an agent.</p>
        <Link
          to="/auth"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-sm font-medium no-underline"
        >
          Log in
        </Link>
      </div>
    );
  }

  if (published) {
    return (
      <div className="max-w-xl mx-auto py-16 text-center">
        <CheckCircle size={40} className="text-emerald-400 mx-auto mb-4" />
        <h1 className="text-2xl font-semibold text-[#f1f5f9] mb-2">Agent published</h1>
        <p className="text-sm text-[#94a3b8] mb-6">
          <span className="text-[#f1f5f9]">{published.name}</span> is now in the catalog as{" "}
          <code className="text-[#00d4ff]">{published.id}</code>.
        </p>
        <div className="flex items-center justify-center gap-2">
          <Link
            to={`/agents/${published.id}`}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-sm font-medium no-underline"
          >
            View agent page
          </Link>
          <button
            onClick={() => {
              setPublished(null);
              setDraft(EMPTY);
            }}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg border border-white/[0.08] text-sm text-[#94a3b8] hover:text-[#f1f5f9] transition-colors"
          >
            Publish another
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto py-8">
      <Link
        to="/providers"
        className="inline-flex items-center gap-1.5 text-xs text-[#64748b] hover:text-[#f1f5f9] mb-4 no-underline transition-colors"
      >
        <ArrowLeft size={12} />
        Back to providers
      </Link>
      <div className="mb-6">
        <p className="text-xs text-[#64748b] mb-1 font-medium uppercase tracking-widest">
          Provider · Publish agent
        </p>
        <h1 className="text-2xl font-semibold text-[#f1f5f9]">Publish an agent</h1>
        <p className="text-xs text-[#94a3b8] mt-1 max-w-xl">
          Define your capability card in the form below. On submit we POST to{" "}
          <code>/v1/agents</code> and the agent appears in the catalog.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 flex items-start gap-2 mb-4">
          <AlertCircle size={14} className="text-red-400 shrink-0 mt-0.5" />
          <p className="text-xs text-red-300">{error}</p>
        </div>
      )}

      <Card title="Identity">
        <Field label="Agent ID (slug, lowercase + hyphens)">
          <input
            value={draft.id}
            onChange={(e) => setField("id", e.target.value)}
            placeholder="my-agent-v1"
            className={inputClass}
          />
        </Field>
        <Field label="Name">
          <input
            value={draft.name}
            onChange={(e) => setField("name", e.target.value)}
            placeholder="My Agent"
            className={inputClass}
          />
        </Field>
        <Field label="Description">
          <textarea
            rows={2}
            value={draft.description}
            onChange={(e) => setField("description", e.target.value)}
            placeholder="One-paragraph description of what the agent does"
            className={inputClass}
          />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Domain">
            <input
              value={draft.domain}
              onChange={(e) => setField("domain", e.target.value)}
              placeholder="security, research, content, …"
              className={inputClass}
            />
          </Field>
          <Field label="Risk class (Art. 6/9)">
            <select
              value={draft.risk_class}
              onChange={(e) =>
                setField("risk_class", e.target.value as Draft["risk_class"])
              }
              className={inputClass}
            >
              <option value="minimal">minimal</option>
              <option value="limited">limited</option>
              <option value="high">high</option>
            </select>
          </Field>
        </div>
        <Field label="Tags (comma-separated)">
          <input
            value={draft.tags}
            onChange={(e) => setField("tags", e.target.value)}
            placeholder="security, audit, compliance"
            className={inputClass}
          />
        </Field>
      </Card>

      <Card title="Inputs">
        {draft.inputs.map((inp, idx) => (
          <div key={idx} className="grid grid-cols-[1fr_1fr_auto_auto] gap-2 items-end">
            <Field label="Name">
              <input
                value={inp.name}
                onChange={(e) => {
                  const next = [...draft.inputs];
                  next[idx] = { ...inp, name: e.target.value };
                  setField("inputs", next);
                }}
                className={inputClass}
              />
            </Field>
            <Field label="Type">
              <input
                value={inp.type}
                onChange={(e) => {
                  const next = [...draft.inputs];
                  next[idx] = { ...inp, type: e.target.value };
                  setField("inputs", next);
                }}
                className={inputClass}
              />
            </Field>
            <label className="flex items-center gap-1.5 text-xs text-[#94a3b8] pb-2">
              <input
                type="checkbox"
                checked={inp.required}
                onChange={(e) => {
                  const next = [...draft.inputs];
                  next[idx] = { ...inp, required: e.target.checked };
                  setField("inputs", next);
                }}
              />
              required
            </label>
            <button
              onClick={() => {
                const next = draft.inputs.filter((_, i) => i !== idx);
                setField("inputs", next);
              }}
              className="p-2 rounded text-[#64748b] hover:text-red-400 mb-0.5"
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
        <button
          onClick={() =>
            setField("inputs", [...draft.inputs, { name: "", type: "string", required: true }])
          }
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-white/[0.08] text-xs text-[#94a3b8] hover:text-[#f1f5f9] transition-colors"
        >
          <Plus size={12} />
          Add input
        </button>
      </Card>

      <Card title="Outputs">
        {draft.outputs.map((out, idx) => (
          <div key={idx} className="grid grid-cols-[1fr_1fr_auto_auto] gap-2 items-end">
            <Field label="Filename">
              <input
                value={out.name}
                onChange={(e) => {
                  const next = [...draft.outputs];
                  next[idx] = { ...out, name: e.target.value };
                  setField("outputs", next);
                }}
                className={inputClass}
              />
            </Field>
            <Field label="Type">
              <input
                value={out.type}
                onChange={(e) => {
                  const next = [...draft.outputs];
                  next[idx] = { ...out, type: e.target.value };
                  setField("outputs", next);
                }}
                className={inputClass}
              />
            </Field>
            <label className="flex items-center gap-1.5 text-xs text-[#94a3b8] pb-2">
              <input
                type="checkbox"
                checked={out.guaranteed}
                onChange={(e) => {
                  const next = [...draft.outputs];
                  next[idx] = { ...out, guaranteed: e.target.checked };
                  setField("outputs", next);
                }}
              />
              guaranteed
            </label>
            <button
              onClick={() => {
                const next = draft.outputs.filter((_, i) => i !== idx);
                setField("outputs", next);
              }}
              className="p-2 rounded text-[#64748b] hover:text-red-400 mb-0.5"
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
        <button
          onClick={() =>
            setField("outputs", [...draft.outputs, { name: "", type: "markdown", guaranteed: true }])
          }
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-white/[0.08] text-xs text-[#94a3b8] hover:text-[#f1f5f9] transition-colors"
        >
          <Plus size={12} />
          Add output
        </button>
      </Card>

      <Card title="Runtime">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Model">
            <input
              value={draft.runtime_model}
              onChange={(e) => setField("runtime_model", e.target.value)}
              className={inputClass}
            />
          </Field>
          <Field label="Compute tier">
            <select
              value={draft.runtime_compute_tier}
              onChange={(e) =>
                setField("runtime_compute_tier", e.target.value as "container" | "vm")
              }
              className={inputClass}
            >
              <option value="container">container (~100ms boot)</option>
              <option value="vm">vm (~20s boot, full isolation)</option>
            </select>
          </Field>
          <Field label="Server type">
            <input
              value={draft.runtime_server_type}
              onChange={(e) => setField("runtime_server_type", e.target.value)}
              placeholder="cax11, cax21, cx22, …"
              className={inputClass}
            />
          </Field>
          <Field label="Tools (comma-separated)">
            <input
              value={draft.runtime_tools}
              onChange={(e) => setField("runtime_tools", e.target.value)}
              placeholder="shell, browser, sql"
              className={inputClass}
            />
          </Field>
          <Field label="Estimated duration (sec)">
            <input
              type="number"
              min="10"
              max="3600"
              value={draft.runtime_estimated_duration_seconds}
              onChange={(e) =>
                setField(
                  "runtime_estimated_duration_seconds",
                  parseInt(e.target.value, 10) || 300,
                )
              }
              className={inputClass}
            />
          </Field>
          <Field label="Timeout max (sec)">
            <input
              type="number"
              min="60"
              max="3600"
              value={draft.constraints_timeout_max}
              onChange={(e) =>
                setField("constraints_timeout_max", parseInt(e.target.value, 10) || 3600)
              }
              className={inputClass}
            />
          </Field>
        </div>
      </Card>

      <Card title="Pricing">
        <Field label="Base price (USD per execution)">
          <input
            type="number"
            min="0"
            step="0.1"
            value={draft.pricing_base_price_usd}
            onChange={(e) =>
              setField("pricing_base_price_usd", parseFloat(e.target.value) || 0)
            }
            className={inputClass}
          />
        </Field>
        <p className="text-[10px] text-[#64748b]">
          You receive 80 % per execution (via Stripe Connect), 20 % covers platform + compute.
        </p>
      </Card>

      <Card title="Instructions">
        <Field label="Agent prompt (system instructions)">
          <textarea
            rows={10}
            value={draft.instructions}
            onChange={(e) => setField("instructions", e.target.value)}
            placeholder="You are a security audit agent. Given a repo URL, run …"
            className={`${inputClass} font-mono text-[12px]`}
          />
        </Field>
      </Card>

      <div className="flex items-center justify-end gap-2 pt-2">
        <Link
          to="/providers"
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-white/[0.08] text-sm text-[#94a3b8] hover:text-[#f1f5f9] no-underline transition-colors"
        >
          Cancel
        </Link>
        <button
          onClick={handleSubmit}
          disabled={busy || !draft.id || !draft.name || !draft.domain || !draft.instructions}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {busy ? <Loader2 size={14} className="animate-spin" /> : <Code2 size={14} />}
          Publish agent
        </button>
      </div>
    </div>
  );
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

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5 space-y-3 mb-4">
      <h2 className="text-sm font-medium text-[#f1f5f9]">{title}</h2>
      {children}
    </div>
  );
}
