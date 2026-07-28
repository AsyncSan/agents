import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Key, UserPlus, Copy, Check, AlertTriangle, LogIn } from "lucide-react";
import { login, register } from "../api";

export function AuthPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"register" | "login">("register");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
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
      const result = await register(name, email, role, password || undefined);
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

  const handleLogin = async () => {
    if (!email || !password) return;
    setLoading(true);
    setError("");
    try {
      const result = await login(email, password);
      const key = result.api_key;
      localStorage.setItem("af_api_key", key);
      localStorage.setItem("af_role", result.role);
      localStorage.setItem("af_name", result.name);
      navigate(landingFor(result.role));
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Login failed";
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

  const landingFor = (r: "consumer" | "provider") =>
    r === "provider" ? "/providers" : "/compliance";

  const handleSetKey = (key: string) => {
    localStorage.setItem("af_api_key", key);
    const storedRole =
      (localStorage.getItem("af_role") as "consumer" | "provider" | null) || "consumer";
    navigate(landingFor(storedRole));
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
            onClick={() => navigate(landingFor(role))}
            className="w-full py-2.5 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-sm font-medium hover:bg-[#00bfea]"
            style={{
              transition:
                "background 0.2s cubic-bezier(0.16, 1, 0.3, 1)",
            }}
          >
            {role === "provider" ? "Go to provider dashboard" : "Open compliance workspace"}
          </button>

          {role === "consumer" && (
            <button
              onClick={() => navigate("/settings/org")}
              className="w-full mt-2 py-2 rounded-lg border border-white/[0.08] text-xs text-[#94a3b8] hover:text-[#f1f5f9] transition-colors"
            >
              Set up organisation profile first (recommended, 60s)
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-md mx-auto mt-12">
      <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-6">
        <div className="flex items-center gap-1 mb-6 p-1 rounded-lg bg-[#0a0a0f] border border-white/[0.04]">
          <button
            onClick={() => {
              setMode("register");
              setError("");
            }}
            className={`flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              mode === "register"
                ? "bg-[#111118] text-[#00d4ff]"
                : "text-[#64748b] hover:text-[#94a3b8]"
            }`}
          >
            <UserPlus size={12} />
            Create account
          </button>
          <button
            onClick={() => {
              setMode("login");
              setError("");
            }}
            className={`flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              mode === "login"
                ? "bg-[#111118] text-[#00d4ff]"
                : "text-[#64748b] hover:text-[#94a3b8]"
            }`}
          >
            <LogIn size={12} />
            Log in
          </button>
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
              onClick={() => {
                const storedRole =
                  (localStorage.getItem("af_role") as "consumer" | "provider" | null) ||
                  "consumer";
                navigate(landingFor(storedRole));
              }}
              className="block mt-2 text-xs text-[#00d4ff] hover:underline"
            >
              Continue with this key
            </button>
          </div>
        ) : null}

        {/* Register or Login form */}
        <div className="space-y-3 mb-4">
          {mode === "register" && (
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
          )}
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
            <label className="block text-xs text-[#64748b] mb-1">
              Password {mode === "register" && <span className="text-[#475569]">(optional, ≥ 8 chars)</span>}
            </label>
            <input
              type="password"
              placeholder={mode === "login" ? "Your password" : "Set a password for future logins"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && mode === "login") handleLogin();
              }}
              className="w-full px-3 py-2 rounded-lg bg-[#0a0a0f] border border-white/[0.06] text-sm text-[#f1f5f9] placeholder-[#64748b] focus:outline-none focus:border-[#00d4ff]/30"
            />
          </div>
          {mode === "register" && (
            <div>
              <label className="block text-xs text-[#64748b] mb-1">Role</label>
              <div className="grid grid-cols-2 gap-2">
                {(["consumer", "provider"] as const).map((r) => (
                  <button
                    key={r}
                    onClick={() => setRole(r)}
                    className={`py-2.5 px-2 rounded-lg text-sm transition-colors border text-left ${
                      role === r
                        ? "border-[#00d4ff]/30 bg-[#00d4ff]/5 text-[#00d4ff]"
                        : "border-white/[0.06] text-[#94a3b8] hover:border-white/[0.12]"
                    }`}
                  >
                    <span className="block font-medium">
                      {r === "consumer" ? "Consumer / Deployer" : "Provider"}
                    </span>
                    <span className="block text-[10px] text-[#64748b] mt-0.5 leading-tight">
                      {r === "consumer"
                        ? "Run agents, generate compliance docs (FRIA, Annex IV, QMS, PMM, EU-DB). EU AI Act Deployer."
                        : "Publish agents, earn revenue share. EU AI Act Provider."}
                    </span>
                  </button>
                ))}
              </div>
              <p className="text-[10px] text-[#64748b] mt-2 leading-relaxed">
                Not sure? Pick <span className="text-[#94a3b8]">Consumer / Deployer</span> if you want
                to use AI systems in your business and need compliance documents. Pick{" "}
                <span className="text-[#94a3b8]">Provider</span> if you build and sell agents.
              </p>
            </div>
          )}
        </div>

        <button
          onClick={mode === "register" ? handleRegister : handleLogin}
          disabled={
            loading ||
            !email ||
            (mode === "register" ? !name : !password)
          }
          className="w-full py-2.5 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-sm font-medium hover:bg-[#00bfea] disabled:opacity-40 disabled:cursor-not-allowed"
          style={{
            transition:
              "background 0.2s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.2s",
          }}
        >
          {loading
            ? (mode === "register" ? "Creating account..." : "Logging in...")
            : (mode === "register" ? "Create Account" : "Log in")}
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
