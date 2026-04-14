import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Key, UserPlus, Copy, Check, AlertTriangle } from "lucide-react";
import { register } from "../api";

export function AuthPage() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<"consumer" | "provider">("consumer");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [copied, setCopied] = useState(false);

  // Check if already authenticated
  const existingKey = localStorage.getItem("af_api_key");

  const handleRegister = async () => {
    if (!name || !email) return;
    setLoading(true);
    setError("");
    try {
      const result = await register(name, email, role);
      const key = result.api_key;
      setApiKey(key);
      localStorage.setItem("af_api_key", key);
      localStorage.setItem("af_role", role);
      localStorage.setItem("af_name", name);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Registration failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(apiKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSetKey = (key: string) => {
    localStorage.setItem("af_api_key", key);
    navigate("/tasks");
  };

  // Success state: show the API key
  if (apiKey) {
    return (
      <div className="max-w-md mx-auto mt-12">
        <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Check size={18} className="text-emerald-400" />
            <h2 className="text-lg font-semibold text-[#f1f5f9]">
              Account created
            </h2>
          </div>

          <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 mb-4">
            <div className="flex items-center gap-1.5 text-xs text-amber-400 mb-2">
              <AlertTriangle size={12} />
              Save this API key now. It won't be shown again.
            </div>
            <div className="flex items-center gap-2">
              <code className="flex-1 text-sm text-[#f1f5f9] font-mono bg-[#0a0a0f] rounded px-3 py-2 break-all">
                {apiKey}
              </code>
              <button
                onClick={handleCopy}
                className="shrink-0 p-2 rounded-lg bg-[#111118] border border-white/[0.06] text-[#94a3b8] hover:text-[#00d4ff] transition-colors"
              >
                {copied ? <Check size={14} /> : <Copy size={14} />}
              </button>
            </div>
          </div>

          <button
            onClick={() => navigate("/tasks")}
            className="w-full py-2.5 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-sm font-medium hover:bg-[#00bfea]"
            style={{
              transition:
                "background 0.2s cubic-bezier(0.16, 1, 0.3, 1)",
            }}
          >
            Go to Tasks
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-md mx-auto mt-12">
      <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-6">
        <div className="flex items-center gap-2 mb-6">
          <UserPlus size={18} className="text-[#00d4ff]" />
          <h2 className="text-lg font-semibold text-[#f1f5f9]">
            Get Started
          </h2>
        </div>

        {/* Existing key shortcut */}
        {existingKey ? (
          <div className="rounded-lg border border-white/[0.04] bg-[#0a0a0f] p-3 mb-6">
            <p className="text-xs text-[#64748b] mb-2">
              Already have a key stored:
            </p>
            <code className="text-xs text-[#94a3b8] font-mono">
              {existingKey.slice(0, 12)}...
            </code>
            <button
              onClick={() => navigate("/tasks")}
              className="block mt-2 text-xs text-[#00d4ff] hover:underline"
            >
              Continue with this key
            </button>
          </div>
        ) : null}

        {/* Register form */}
        <div className="space-y-3 mb-4">
          <div>
            <label className="block text-xs text-[#64748b] mb-1">Name</label>
            <input
              type="text"
              placeholder="Your name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-[#0a0a0f] border border-white/[0.06] text-sm text-[#f1f5f9] placeholder-[#64748b] focus:outline-none focus:border-[#00d4ff]/30"
            />
          </div>
          <div>
            <label className="block text-xs text-[#64748b] mb-1">Email</label>
            <input
              type="email"
              placeholder="you@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-[#0a0a0f] border border-white/[0.06] text-sm text-[#f1f5f9] placeholder-[#64748b] focus:outline-none focus:border-[#00d4ff]/30"
            />
          </div>
          <div>
            <label className="block text-xs text-[#64748b] mb-1">Role</label>
            <div className="grid grid-cols-2 gap-2">
              {(["consumer", "provider"] as const).map((r) => (
                <button
                  key={r}
                  onClick={() => setRole(r)}
                  className={`py-2 rounded-lg text-sm transition-colors border ${
                    role === r
                      ? "border-[#00d4ff]/30 bg-[#00d4ff]/5 text-[#00d4ff]"
                      : "border-white/[0.06] text-[#94a3b8] hover:border-white/[0.12]"
                  }`}
                >
                  {r === "consumer" ? "Consumer" : "Provider"}
                  <span className="block text-[10px] text-[#64748b] mt-0.5">
                    {r === "consumer"
                      ? "Run agents"
                      : "Publish agents"}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>

        <button
          onClick={handleRegister}
          disabled={loading || !name || !email}
          className="w-full py-2.5 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-sm font-medium hover:bg-[#00bfea] disabled:opacity-40 disabled:cursor-not-allowed"
          style={{
            transition:
              "background 0.2s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.2s",
          }}
        >
          {loading ? "Creating account..." : "Create Account"}
        </button>

        {error && (
          <p className="mt-3 text-xs text-red-400 text-center">{error}</p>
        )}

        {/* Manual key entry */}
        <div className="mt-6 pt-4 border-t border-white/[0.04]">
          <p className="text-xs text-[#64748b] mb-2">
            Already have an API key?
          </p>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Key
                size={12}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-[#64748b]"
              />
              <input
                type="password"
                placeholder="af_..."
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    handleSetKey((e.target as HTMLInputElement).value);
                  }
                }}
                className="w-full pl-8 pr-3 py-2 rounded-lg bg-[#0a0a0f] border border-white/[0.06] text-xs text-[#f1f5f9] placeholder-[#64748b] focus:outline-none focus:border-[#00d4ff]/30"
              />
            </div>
            <button
              onClick={(e) => {
                const input = (e.target as HTMLElement)
                  .closest(".flex")
                  ?.querySelector("input") as HTMLInputElement;
                if (input?.value) handleSetKey(input.value);
              }}
              className="px-3 py-2 rounded-lg bg-[#111118] border border-white/[0.06] text-xs text-[#94a3b8] hover:text-[#00d4ff] transition-colors"
            >
              Use Key
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
