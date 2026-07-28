import { useEffect, useState } from "react";
import {
  Search,
  Shield,
  FileCheck,
  ArrowRight,
  ExternalLink,
  CheckCircle,
  Terminal,
  Calendar,
  Download,
  Globe,
  Scale,
  Eye,
  AlertTriangle,
  Stamp,
  Sparkles,
  TrendingDown,
  Briefcase,
  Lock,
  GraduationCap,
} from "lucide-react";
import { listAgents, type Agent } from "../api";
import { AgentCard } from "../components/AgentCard";
import { ReportViewer } from "../components/ReportViewer";
import { useT } from "../i18n";

const DOMAINS = ["all", "security", "research", "content", "benchmark", "code-quality"];

const SAMPLE_REPORT = `# Security Audit Report: OWASP Juice Shop v19.2.1

**Date:** 2026-04-15
**Repository:** https://github.com/juice-shop/juice-shop
**License:** MIT

---

## Executive Summary

OWASP Juice Shop is an **intentionally vulnerable** web application designed for security training and CTF challenges. The vulnerabilities found below are by design. This report documents them as if auditing a production application.

**Risk Rating: CRITICAL** — Multiple high-severity vulnerabilities including code injection via eval(), SQL injection, path traversal, open redirects, and hardcoded credentials throughout the codebase.

---

## Findings by Severity

### CRITICAL

#### C1: Remote Code Execution via eval() (CWE-94)
- **File:** \`routes/captcha.ts:22\`, \`routes/userProfile.ts:62\`
- **Detail:** eval(expression) on user-influenced captcha expressions and eval(code) on user profile template input.
- **Impact:** Full server-side code execution. An attacker can execute arbitrary Node.js code on the server.
- **Evidence:**
\`\`\`typescript
// routes/captcha.ts:22
const answer = eval(expression).toString()
// routes/userProfile.ts:62
username = eval(code)
\`\`\`

#### C2: SQL Injection (CWE-89)
- **File:** \`routes/search.ts:47\`
- **Detail:** Raw SQL query with string interpolation in sequelize.query() calls (login, search).
- **Impact:** Full database read/write access, authentication bypass, data exfiltration.

### HIGH

#### H1: Hardcoded Credentials (CWE-798)
- **File:** 40+ instances across \`test/api/\` files
- **Detail:** Passwords found: demo, ncc-1701, kunigunde, admin123, 123456, Mr. N00dles, testtesttest
- **Impact:** Default credentials enable trivial account takeover.

#### H2: Path Traversal via res.sendFile() (CWE-22)
- **File:** \`routes/fileServer.ts:33\`, \`routes/quarantineServer.ts:14\`, \`routes/keyServer.ts:14\`
- **Detail:** Potential arbitrary file read if the file parameter is not properly sanitized.
- **Impact:** Arbitrary file read on the server.

#### H3: JWT Key Material Exposure (CWE-321)
- **File:** \`lib/insecurity.ts:22\`, \`routes/keyServer.ts\`
- **Detail:** JWT public key served via API enables JWT forgery attacks (algorithm confusion RS256 to HS256).
- **Impact:** Authentication bypass via token forgery.

#### H4: Open Redirect (CWE-601)
- **File:** \`routes/redirect.ts:19\`
- **Detail:** res.redirect(toUrl) with bypassable allowlist.
- **Impact:** Phishing attacks via trusted domain redirect.

### MEDIUM

#### M1: Server-Side Request Forgery (CWE-918)
- **File:** \`routes/profileImageUrlUpload.ts:19\`
- **Detail:** Accepts arbitrary imageUrl from request body.
- **Impact:** Internal network scanning, access to cloud metadata endpoints.

#### M2: Dependency Vulnerabilities
- **Detail:** npm audit could not complete (no node_modules installed). Given 1400+ dependencies, vulnerabilities are statistically certain.
- **Impact:** Potential supply chain risk.

### LOW

#### L1: Sensitive Data in Test Fixtures
- **File:** Base64-encoded passwords in test files
- **Detail:** Information disclosure if test files are deployed to production.
- **Impact:** Low risk, test-only data exposure.

#### L2: Encryption Key Files in Repository
- **File:** \`encryptionkeys/\` directory committed to source
- **Detail:** Private keys in version control enable token forgery.
- **Impact:** Key compromise if repo is public.

---

## Recommendations

1. **Eliminate eval()** — Replace with safe expression parsers (e.g., mathjs) for captcha; use template engines for profiles.
2. **Parameterize all SQL** — Use Sequelize ORM methods or parameterized queries exclusively.
3. **Remove hardcoded credentials** — Use environment variables or a secrets manager.
4. **Sanitize file paths** — Validate and whitelist file parameters before path.resolve(). Reject ../ sequences.
5. **Protect JWT keys** — Remove encryptionkeys/ from the repository. Use environment-injected secrets.
6. **Restrict redirects** — Use a strict allowlist with exact URL matching.
7. **Validate URLs server-side** — For SSRF: restrict to allowlisted domains, block private IP ranges.
8. **Run npm audit fix** — Address known dependency vulnerabilities.
9. **Add CI security gates** — Integrate SAST (CodeQL/Semgrep) and SCA into the CI pipeline.
10. **Separate test data** — Ensure test fixtures with credentials are never included in production builds.

---

*Report generated by automated security audit on an isolated ARM64 VM. Server destroyed after execution.*
`;

export function CatalogPage() {
  const { t } = useT();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");

  useEffect(() => {
    listAgents(filter === "all" ? undefined : filter)
      .then((d) => setAgents(d.agents))
      .finally(() => setLoading(false));
  }, [filter]);

  const filtered = agents.filter(
    (a) =>
      !search ||
      a.name.toLowerCase().includes(search.toLowerCase()) ||
      a.card.capabilities.tags.some((t) => t.includes(search.toLowerCase()))
  );

  return (
    <>
      {/* Hero: Outcome-first for SME decision makers */}
      <section className="relative mb-20 pt-12">
        <div className="absolute inset-0 -z-10 overflow-hidden">
          <div
            className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] rounded-full opacity-[0.03]"
            style={{ background: "radial-gradient(circle, #00d4ff 0%, transparent 60%)" }}
          />
        </div>

        <div className="text-center max-w-2xl mx-auto">
          <p className="text-xs text-[#64748b] mb-4 font-medium uppercase tracking-widest">
            {t("home.hero.eyebrow")}
          </p>
          <h1 className="text-3xl sm:text-5xl font-semibold text-[#f1f5f9] mb-5 leading-[1.15] tracking-tight">
            {t("home.hero.title1")}<br />
            <span className="text-[#00d4ff]">{t("home.hero.title2")}</span>
          </h1>

          <p className="text-[16px] text-[#94a3b8] leading-relaxed mb-8 max-w-lg mx-auto">
            {t("home.hero.sub")}
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-8 max-w-xl mx-auto text-left">
            <div className="flex items-start gap-2 rounded-lg border border-white/[0.06] bg-[#111118] p-3">
              <CheckCircle size={14} className="text-emerald-400 shrink-0 mt-0.5" />
              <p className="text-xs text-[#94a3b8] leading-snug">
                <span className="text-[#f1f5f9] font-medium">{t("home.hero.bullet1.strong")}</span>
                {t("home.hero.bullet1.rest")}
              </p>
            </div>
            <div className="flex items-start gap-2 rounded-lg border border-white/[0.06] bg-[#111118] p-3">
              <CheckCircle size={14} className="text-emerald-400 shrink-0 mt-0.5" />
              <p className="text-xs text-[#94a3b8] leading-snug">
                <span className="text-[#f1f5f9] font-medium">{t("home.hero.bullet2.strong")}</span>
                {t("home.hero.bullet2.rest")}
              </p>
            </div>
            <div className="flex items-start gap-2 rounded-lg border border-white/[0.06] bg-[#111118] p-3">
              <CheckCircle size={14} className="text-emerald-400 shrink-0 mt-0.5" />
              <p className="text-xs text-[#94a3b8] leading-snug">
                <span className="text-[#f1f5f9] font-medium">{t("home.hero.bullet3.strong")}</span>
                {t("home.hero.bullet3.rest")}
              </p>
            </div>
          </div>

          <div className="flex items-center justify-center gap-3 mb-6 flex-wrap">
            <a
              href="/sample-evidence-pack.zip"
              download
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-sm font-medium no-underline"
              style={{ transition: "background 0.2s cubic-bezier(0.16, 1, 0.3, 1)" }}
            >
              <Download size={14} />
              {t("home.hero.cta.primary")}
            </a>
            <a
              href="/auth"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg border border-white/[0.08] text-sm text-[#94a3b8] hover:text-[#f1f5f9] hover:border-white/[0.15] no-underline transition-colors"
            >
              {t("home.hero.cta.trial")}
            </a>
            <a
              href="mailto:hello@renemurrell.de?subject=Agent%20Platform%20Inquiry"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg border border-white/[0.08] text-sm text-[#94a3b8] hover:text-[#f1f5f9] hover:border-white/[0.15] no-underline transition-colors"
            >
              {t("home.hero.cta.talk")}
            </a>
          </div>

          <div className="flex items-center justify-center gap-3 text-xs text-[#64748b] flex-wrap">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
              {t("home.hero.trust.hosted")}
            </span>
            <span>{t("home.hero.trust.articles")}</span>
            <span>{t("home.hero.trust.gdpr")}</span>
            <a href="https://github.com/mylilcrowdi/agents" target="_blank" rel="noopener" className="text-[#94a3b8] hover:text-[#f1f5f9] no-underline">
              {t("home.hero.trust.oss")} <ExternalLink size={10} className="inline" />
            </a>
          </div>
        </div>
      </section>

      {/* The Problem: concrete, short */}
      <section className="mb-20">
        <h2 className="text-xs font-medium text-[#64748b] uppercase tracking-widest mb-6 text-center">
          {t("home.problem.title")}
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            {
              icon: Calendar,
              title: t("home.problem.card1.title"),
              desc: t("home.problem.card1.desc"),
            },
            {
              icon: TrendingDown,
              title: t("home.problem.card2.title"),
              desc: t("home.problem.card2.desc"),
            },
            {
              icon: Briefcase,
              title: t("home.problem.card3.title"),
              desc: t("home.problem.card3.desc"),
            },
          ].map(({ icon: Icon, title, desc }) => (
            <div key={title} className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
              <Icon size={18} className="text-[#00d4ff] mb-3" />
              <h3 className="text-sm font-medium text-[#f1f5f9] mb-2">{title}</h3>
              <p className="text-xs text-[#94a3b8] leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* What you get: outcomes, not features */}
      <section className="mb-20">
        <h2 className="text-xs font-medium text-[#64748b] uppercase tracking-widest mb-2 text-center">
          {t("home.wyg.title")}
        </h2>
        <p className="text-xs text-[#64748b] text-center mb-6 max-w-lg mx-auto">
          {t("home.wyg.sub")}
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            {
              icon: FileCheck,
              title: t("home.wyg.card1.title"),
              desc: t("home.wyg.card1.desc"),
              href: undefined,
              hrefLabel: undefined,
            },
            {
              icon: Sparkles,
              title: t("home.wyg.card2.title"),
              desc: t("home.wyg.card2.desc"),
              href: "/fria",
              hrefLabel: t("home.wyg.card2.cta"),
            },
            {
              icon: Stamp,
              title: t("home.wyg.card3.title"),
              desc: t("home.wyg.card3.desc"),
              href: undefined,
              hrefLabel: undefined,
            },
          ].map(({ icon: Icon, title, desc, href, hrefLabel }) => (
            <div key={title} className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
              <Icon size={18} className="text-[#00d4ff] mb-3" />
              <h3 className="text-sm font-medium text-[#f1f5f9] mb-2">{title}</h3>
              <p className="text-xs text-[#94a3b8] leading-relaxed">{desc}</p>
              {href && (
                <a
                  href={href}
                  className="mt-3 inline-flex items-center gap-1.5 text-xs text-[#00d4ff] no-underline hover:underline"
                >
                  {hrefLabel}
                  <ArrowRight size={12} />
                </a>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Sample Evidence Pack */}
      <section id="evidence-pack" className="mb-20 scroll-mt-20">
        <h2 className="text-xs font-medium text-[#64748b] uppercase tracking-widest mb-2 text-center">
          {t("home.evidence.title")}
        </h2>
        <p className="text-xs text-[#64748b] text-center mb-6 max-w-lg mx-auto">
          {t("home.evidence.sub")}
        </p>
        <div className="flex items-center justify-center mb-6">
          <a
            href="/sample-evidence-pack.zip"
            download
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg border border-[#00d4ff]/20 bg-[#00d4ff]/5 text-[#00d4ff] text-xs font-medium no-underline hover:bg-[#00d4ff]/10 transition-colors"
          >
            <Download size={14} />
            {t("home.evidence.download")}
          </a>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-4">
            <FileCheck size={16} className="text-[#00d4ff] mb-2" />
            <h3 className="text-sm font-medium text-[#f1f5f9] mb-1">{t("home.evidence.output.title")}</h3>
            <p className="text-xs text-[#94a3b8] leading-relaxed">{t("home.evidence.output.desc")}</p>
          </div>
          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-4">
            <Eye size={16} className="text-[#00d4ff] mb-2" />
            <h3 className="text-sm font-medium text-[#f1f5f9] mb-1">{t("home.evidence.log.title")}</h3>
            <p className="text-xs text-[#94a3b8] leading-relaxed">{t("home.evidence.log.desc")}</p>
          </div>
          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-4">
            <Stamp size={16} className="text-[#00d4ff] mb-2" />
            <h3 className="text-sm font-medium text-[#f1f5f9] mb-1">{t("home.evidence.prov.title")}</h3>
            <p className="text-xs text-[#94a3b8] leading-relaxed">{t("home.evidence.prov.desc")}</p>
          </div>
        </div>
        <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
          <ReportViewer
            markdown={SAMPLE_REPORT}
            execution={{
              elapsed_seconds: 284,
              server_id: "127039826",
              exit_code: 0,
              metrics: {
                model: "anthropic/claude-sonnet-4-6",
                output_bytes: 5809,
                output_tokens_est: 1452,
                elapsed_seconds: 150,
                gateway_mode: "false",
              },
              started_at: "2026-04-15T11:16:26Z",
              completed_at: "2026-04-15T11:21:26Z",
            }}
            onShowRaw={() => {}}
          />
        </div>
      </section>

      {/* EU AI Act Coverage */}
      <section id="compliance" className="mb-20 scroll-mt-20">
        <h2 className="text-xs font-medium text-[#64748b] uppercase tracking-widest mb-2 text-center">
          {t("home.coverage.title")}
        </h2>
        <p className="text-xs text-[#64748b] text-center mb-6 max-w-lg mx-auto">
          {t("home.coverage.sub")}
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[
            {
              icon: Eye,
              article: "Art. 12",
              title: "Automatic logging",
              desc: "Immutable event log per execution: inputs, outputs, duration, compute, cost, actor. Exportable as CSV or JSON for regulatory review.",
            },
            {
              icon: FileCheck,
              article: "Art. 13",
              title: "Transparency",
              desc: "Agent capability cards describe exactly what each agent does, what data it accesses, and what side effects it has. Machine-readable, signed with Ed25519.",
            },
            {
              icon: AlertTriangle,
              article: "Art. 6 / 9",
              title: "Risk classification",
              desc: "Every agent tagged minimal, limited, or high. High-risk agents gate on approval, get stricter isolation and extended log retention.",
            },
            {
              icon: Scale,
              article: "Art. 14",
              title: "Human oversight",
              desc: "Built-in approval gates for high-risk tasks. Webhooks fire before execution. Cancel any running task via API or UI.",
            },
            {
              icon: Shield,
              article: "Art. 15",
              title: "Accuracy and security",
              desc: "5-factor trust score tracks reliability over time. Ephemeral compute with 3-path secret isolation prevents cross-tenant leakage.",
            },
            {
              icon: Stamp,
              article: "Art. 50",
              title: "Content provenance",
              desc: "Every output carries machine-readable X-AI-Generated and X-AI-Provenance headers. Markdown outputs get an inline disclosure block.",
            },
            {
              icon: Globe,
              article: "Residency",
              desc: "All compute runs in Hetzner Nuremberg. No data leaves the EU. No CLOUD Act exposure through US-based providers.",
              title: "EU data residency",
            },
          ].map(({ icon: Icon, article, title, desc }) => (
            <div key={title} className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
              <div className="flex items-center gap-2 mb-3">
                <Icon size={16} className="text-[#00d4ff]" />
                <span className="text-[10px] font-mono text-[#64748b] px-1.5 py-0.5 rounded bg-white/5">{article}</span>
              </div>
              <h3 className="text-sm font-medium text-[#f1f5f9] mb-2">{title}</h3>
              <p className="text-xs text-[#94a3b8] leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
        <div className="mt-6 text-center">
          <a
            href="/docs/eu-ai-act"
            className="inline-flex items-center gap-1.5 text-xs text-[#00d4ff] no-underline hover:underline"
          >
            {t("home.coverage.readMore")}
            <ArrowRight size={12} />
          </a>
        </div>
      </section>

      {/* Built for SMEs */}
      <section id="for-smes" className="mb-20 scroll-mt-20">
        <h2 className="text-xs font-medium text-[#64748b] uppercase tracking-widest mb-2 text-center">
          {t("home.sme.title")}
        </h2>
        <p className="text-xs text-[#64748b] text-center mb-6 max-w-lg mx-auto">
          {t("home.sme.sub")}
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
            <div className="flex items-center gap-2 mb-3">
              <TrendingDown size={16} className="text-emerald-400" />
              <span className="text-[10px] font-mono text-[#64748b] px-1.5 py-0.5 rounded bg-white/5">Art. 99(6)</span>
            </div>
            <h3 className="text-sm font-medium text-[#f1f5f9] mb-2">{t("home.sme.card1.title")}</h3>
            <p className="text-xs text-[#94a3b8] leading-relaxed">{t("home.sme.card1.desc")}</p>
          </div>
          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
            <div className="flex items-center gap-2 mb-3">
              <Briefcase size={16} className="text-emerald-400" />
              <span className="text-[10px] font-mono text-[#64748b] px-1.5 py-0.5 rounded bg-white/5">Art. 62</span>
            </div>
            <h3 className="text-sm font-medium text-[#f1f5f9] mb-2">{t("home.sme.card2.title")}</h3>
            <p className="text-xs text-[#94a3b8] leading-relaxed">{t("home.sme.card2.desc")}</p>
          </div>
          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles size={16} className="text-emerald-400" />
              <span className="text-[10px] font-mono text-[#64748b] px-1.5 py-0.5 rounded bg-white/5">Art. 63</span>
            </div>
            <h3 className="text-sm font-medium text-[#f1f5f9] mb-2">{t("home.sme.card3.title")}</h3>
            <p className="text-xs text-[#94a3b8] leading-relaxed">{t("home.sme.card3.desc")}</p>
          </div>
          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
            <div className="flex items-center gap-2 mb-3">
              <Globe size={16} className="text-emerald-400" />
              <span className="text-[10px] font-mono text-[#64748b] px-1.5 py-0.5 rounded bg-white/5">Art. 57</span>
            </div>
            <h3 className="text-sm font-medium text-[#f1f5f9] mb-2">{t("home.sme.card4.title")}</h3>
            <p className="text-xs text-[#94a3b8] leading-relaxed">{t("home.sme.card4.desc")}</p>
          </div>
        </div>
        <div className="rounded-xl border border-emerald-500/10 bg-emerald-500/5 p-4 mb-4">
          <p className="text-xs text-emerald-200/80 leading-relaxed">
            <strong className="text-emerald-300">{t("home.sme.summary.bold")}</strong>
            {t("home.sme.summary.rest")}
          </p>
        </div>
        <div className="flex flex-wrap gap-2 justify-center">
          <a
            href="/compliance/setup"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#00d4ff] text-[#0a0a0f] text-xs font-medium no-underline"
            style={{ transition: "background 0.2s cubic-bezier(0.16, 1, 0.3, 1)" }}
          >
            <Sparkles size={12} />
            Run compliance setup (all docs at once)
          </a>
          <a
            href="/fria"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-white/[0.08] text-xs text-[#94a3b8] hover:text-[#f1f5f9] no-underline transition-colors"
          >
            <Sparkles size={12} />
            {t("home.sme.cta.fria")}
          </a>
          <a
            href="/literacy"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-white/[0.08] text-xs text-[#94a3b8] hover:text-[#f1f5f9] no-underline transition-colors"
          >
            <GraduationCap size={12} />
            {t("home.sme.cta.literacy")}
          </a>
          <a
            href="/annex-iv"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-white/[0.08] text-xs text-[#94a3b8] hover:text-[#f1f5f9] no-underline transition-colors"
          >
            <FileCheck size={12} />
            {t("home.sme.cta.annex")}
          </a>
          <a
            href="/pmm"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-white/[0.08] text-xs text-[#94a3b8] hover:text-[#f1f5f9] no-underline transition-colors"
          >
            <FileCheck size={12} />
            PMM plan (Art. 72)
          </a>
          <a
            href="/qms"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-white/[0.08] text-xs text-[#94a3b8] hover:text-[#f1f5f9] no-underline transition-colors"
          >
            <Briefcase size={12} />
            QMS manual (Art. 17)
          </a>
          <a
            href="/data-governance"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-white/[0.08] text-xs text-[#94a3b8] hover:text-[#f1f5f9] no-underline transition-colors"
          >
            <FileCheck size={12} />
            Data governance (Art. 10)
          </a>
          <a
            href="/eu-db"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-white/[0.08] text-xs text-[#94a3b8] hover:text-[#f1f5f9] no-underline transition-colors"
          >
            <FileCheck size={12} />
            EU DB registration (Art. 49)
          </a>
          <a
            href="/declaration"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-white/[0.08] text-xs text-[#94a3b8] hover:text-[#f1f5f9] no-underline transition-colors"
          >
            <FileCheck size={12} />
            Declaration of Conformity (Art. 47)
          </a>
          <a
            href="/modifications"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-white/[0.08] text-xs text-[#94a3b8] hover:text-[#f1f5f9] no-underline transition-colors"
          >
            <FileCheck size={12} />
            Modification log (Art. 43)
          </a>
          <a
            href="/oversight"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-white/[0.08] text-xs text-[#94a3b8] hover:text-[#f1f5f9] no-underline transition-colors"
          >
            <FileCheck size={12} />
            Oversight roster (Art. 14)
          </a>
          <a
            href="/audit-shares"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-white/[0.08] text-xs text-[#94a3b8] hover:text-[#f1f5f9] no-underline transition-colors"
          >
            <FileCheck size={12} />
            Auditor share (read-only URL)
          </a>
          <a
            href="/sample-docs"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-white/[0.08] text-xs text-[#94a3b8] hover:text-[#f1f5f9] no-underline transition-colors"
          >
            <FileCheck size={12} />
            Sample PDFs (4 domains)
          </a>
          <a
            href="/sample-evidence-pack.zip"
            download
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-white/[0.08] text-xs text-[#94a3b8] hover:text-[#f1f5f9] no-underline transition-colors"
          >
            <Download size={12} />
            {t("home.sme.cta.sample")}
          </a>
        </div>
      </section>

      {/* Pricing */}
      <section className="mb-20">
        <h2 className="text-xs font-medium text-[#64748b] uppercase tracking-widest mb-6 text-center">
          {t("home.pricing.title")}
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 max-w-4xl mx-auto">
          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
            <h3 className="text-sm font-medium text-[#f1f5f9] mb-1">Starter</h3>
            <div className="text-2xl font-bold text-[#f1f5f9] mb-1">€29<span className="text-sm font-normal text-[#64748b]">/mo</span></div>
            <p className="text-xs text-[#64748b] mb-4">{t("home.pricing.starter.tag")}</p>
            <ul className="space-y-2 text-xs text-[#94a3b8]">
              <li className="flex items-center gap-2"><CheckCircle size={12} className="text-emerald-400" /> 4 runs/month</li>
              <li className="flex items-center gap-2"><CheckCircle size={12} className="text-emerald-400" /> 1 scheduled agent</li>
              <li className="flex items-center gap-2"><CheckCircle size={12} className="text-emerald-400" /> Slack/webhook delivery</li>
              <li className="flex items-center gap-2"><CheckCircle size={12} className="text-emerald-400" /> EU-hosted execution</li>
            </ul>
          </div>

          <div className="rounded-xl border border-[#00d4ff]/20 bg-[#111118] p-5 relative">
            <div className="absolute -top-2.5 left-1/2 -translate-x-1/2 px-3 py-0.5 bg-[#00d4ff] text-[#0a0a0f] text-[10px] font-medium rounded-full">
              {t("home.pricing.pro.popular")}
            </div>
            <h3 className="text-sm font-medium text-[#f1f5f9] mb-1">Pro</h3>
            <div className="text-2xl font-bold text-[#f1f5f9] mb-1">€99<span className="text-sm font-normal text-[#64748b]">/mo</span></div>
            <p className="text-xs text-[#64748b] mb-4">{t("home.pricing.pro.tag")}</p>
            <ul className="space-y-2 text-xs text-[#94a3b8]">
              <li className="flex items-center gap-2"><CheckCircle size={12} className="text-emerald-400" /> 20 runs/month</li>
              <li className="flex items-center gap-2"><CheckCircle size={12} className="text-emerald-400" /> 5 scheduled agents</li>
              <li className="flex items-center gap-2"><CheckCircle size={12} className="text-emerald-400" /> FRIA scaffolding</li>
              <li className="flex items-center gap-2"><CheckCircle size={12} className="text-emerald-400" /> Compliance export (CSV/JSON)</li>
            </ul>
          </div>

          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
            <h3 className="text-sm font-medium text-[#f1f5f9] mb-1">Team</h3>
            <div className="text-2xl font-bold text-[#f1f5f9] mb-1">€249<span className="text-sm font-normal text-[#64748b]">/mo</span></div>
            <p className="text-xs text-[#64748b] mb-4">{t("home.pricing.team.tag")}</p>
            <ul className="space-y-2 text-xs text-[#94a3b8]">
              <li className="flex items-center gap-2"><CheckCircle size={12} className="text-emerald-400" /> 60 runs/month</li>
              <li className="flex items-center gap-2"><CheckCircle size={12} className="text-emerald-400" /> 20 scheduled agents</li>
              <li className="flex items-center gap-2"><CheckCircle size={12} className="text-emerald-400" /> Webhook event subscriptions</li>
              <li className="flex items-center gap-2"><CheckCircle size={12} className="text-emerald-400" /> SOC 2 ready audit trail</li>
            </ul>
          </div>

          <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
            <h3 className="text-sm font-medium text-[#f1f5f9] mb-1">Enterprise</h3>
            <div className="text-2xl font-bold text-[#f1f5f9] mb-1">Custom</div>
            <p className="text-xs text-[#64748b] mb-4">{t("home.pricing.enterprise.tag")}</p>
            <ul className="space-y-2 text-xs text-[#94a3b8]">
              <li className="flex items-center gap-2"><CheckCircle size={12} className="text-emerald-400" /> Unlimited runs</li>
              <li className="flex items-center gap-2"><CheckCircle size={12} className="text-emerald-400" /> Custom agents</li>
              <li className="flex items-center gap-2"><CheckCircle size={12} className="text-emerald-400" /> SSO + RBAC</li>
              <li className="flex items-center gap-2"><CheckCircle size={12} className="text-emerald-400" /> Dedicated support</li>
            </ul>
          </div>
        </div>
        <p className="text-center text-xs text-[#64748b] mt-4">
          {t("home.pricing.footnote")}
        </p>
      </section>

      {/* Get Started */}
      <section id="get-started" className="mb-20 scroll-mt-20">
        <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-6">
          <h2 className="text-sm font-medium text-[#f1f5f9] mb-4 flex items-center gap-2">
            <Terminal size={14} className="text-[#00d4ff]" />
            Get started in 60 seconds
          </h2>
          <div className="space-y-3">
            <div>
              <p className="text-xs text-[#64748b] mb-1.5">1. Install and login</p>
              <pre className="text-xs bg-[#0a0a0f] rounded-lg p-3 overflow-x-auto text-[#94a3b8]">
{`pip install agents-cli
agents-cli login --api-key af_your_key`}
              </pre>
            </div>
            <div>
              <p className="text-xs text-[#64748b] mb-1.5">2. Run your first task</p>
              <pre className="text-xs bg-[#0a0a0f] rounded-lg p-3 overflow-x-auto text-[#94a3b8]">
{`agents-cli run security-audit-v1 \\
  -i '{"repo_url": "github.com/your-org/api"}' \\
  --budget 3.00 --wait`}
              </pre>
            </div>
            <div>
              <p className="text-xs text-[#64748b] mb-1.5">3. Schedule it weekly</p>
              <pre className="text-xs bg-[#0a0a0f] rounded-lg p-3 overflow-x-auto text-[#94a3b8]">
{`agents-cli schedule create security-audit-v1 \\
  --name "Monday Audit" \\
  --cron "0 9 * * 1" \\
  -i '{"repo_url": "github.com/your-org/api"}'`}
              </pre>
            </div>
          </div>
        </div>
      </section>

      {/* Secondary entry points for other audiences */}
      <section className="mb-20">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-3xl mx-auto">
          <a
            href="/enterprise"
            className="group rounded-xl border border-white/[0.06] bg-[#111118] p-5 no-underline hover:border-white/[0.12] transition-colors"
          >
            <Lock size={18} className="text-[#00d4ff] mb-3" />
            <h3 className="text-sm font-medium text-[#f1f5f9] mb-1">
              For engineering teams
              <ArrowRight size={12} className="inline ml-1 text-[#64748b] group-hover:translate-x-0.5 transition-transform" />
            </h3>
            <p className="text-xs text-[#94a3b8] leading-relaxed">
              DIY comparison, governance, SOC 2 alignment, scheduled workflows.
            </p>
          </a>
          <a
            href="/providers"
            className="group rounded-xl border border-white/[0.06] bg-[#111118] p-5 no-underline hover:border-white/[0.12] transition-colors"
          >
            <Download size={18} className="text-[#00d4ff] mb-3" />
            <h3 className="text-sm font-medium text-[#f1f5f9] mb-1">
              For agent developers
              <ArrowRight size={12} className="inline ml-1 text-[#64748b] group-hover:translate-x-0.5 transition-transform" />
            </h3>
            <p className="text-xs text-[#94a3b8] leading-relaxed">
              Publish an agent, keep 80% per execution, get distribution built in.
            </p>
          </a>
        </div>
      </section>

      {/* Agent Catalog */}
      <section id="catalog" className="scroll-mt-20">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
          <div>
            <h2 className="text-lg font-semibold text-[#f1f5f9] mb-1">Agent Catalog</h2>
            <p className="text-xs text-[#94a3b8]">
              {agents.length} agents available. Run on-demand or schedule recurring.
            </p>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <div className="relative flex-1">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#64748b]" />
            <input
              type="text"
              placeholder="Search agents..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 rounded-lg bg-[#111118] border border-white/[0.06] text-sm text-[#f1f5f9] placeholder-[#64748b] focus:outline-none focus:border-[#00d4ff]/30"
            />
          </div>
          <div className="flex gap-1 flex-wrap">
            {DOMAINS.map((d) => (
              <button
                key={d}
                onClick={() => setFilter(d)}
                className={`px-3 py-1.5 rounded-lg text-xs transition-colors ${
                  filter === d
                    ? "bg-[#00d4ff]/10 text-[#00d4ff] border border-[#00d4ff]/20"
                    : "text-[#94a3b8] hover:text-[#f1f5f9] border border-transparent"
                }`}
              >
                {d}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="text-center py-20 text-[#64748b] text-sm">Loading agents...</div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-20 text-[#64748b] text-sm">No agents found.</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filtered.map((agent) => (
              <AgentCard key={agent.id} agent={agent} />
            ))}
          </div>
        )}
      </section>
    </>
  );
}
