import { Link } from "react-router-dom";
import {
  Shield,
  Server,
  Zap,
  Lock,
  Clock,
  GitBranch,
  ArrowRight,
} from "lucide-react";
import { H1, Lead, P, H2 } from "./components";
import { useT } from "../../i18n";

const FEATURES_EN = [
  {
    icon: <Server size={20} />,
    title: "Isolated Compute",
    text: "Every task runs on a fresh ARM64 server. Booted from a clean snapshot in ~20 seconds. Destroyed after execution. No shared state between tenants.",
  },
  {
    icon: <Lock size={20} />,
    title: "Secret Isolation",
    text: "Three-path tenant isolation. Consumer secrets, provider secrets, and platform secrets never cross boundaries. Injected at runtime, gone with the server.",
  },
  {
    icon: <Shield size={20} />,
    title: "EU AI Act Ready",
    text: "Covers Articles 4, 10, 12, 13, 14, 15, 17, 27, 49, 50, 72, 73. Immutable audit trail, risk classification, human oversight gates, EU data residency, compliance exports included.",
  },
  {
    icon: <Zap size={20} />,
    title: "Trust Scoring",
    text: "5-factor trust score per agent: success rate, duration accuracy, volume, recency, ratings. Transparent, updated atomically after each execution.",
  },
  {
    icon: <Clock size={20} />,
    title: "Scheduling",
    text: "Cron-based recurring execution. Set it once, get results every Monday. Pause, resume, or delete anytime.",
  },
  {
    icon: <GitBranch size={20} />,
    title: "Pipelines",
    text: "Chain agents into multi-step workflows. Output from one step feeds into the next. Chain trust score reflects the weakest link.",
  },
];

const FEATURES_DE = [
  {
    icon: <Server size={20} />,
    title: "Isolierte Ausführung",
    text: "Jede Aufgabe läuft auf einem frischen ARM64-Server. Gestartet aus einem sauberen Snapshot in ca. 20 Sekunden. Nach der Ausführung zerstört. Kein gemeinsamer Zustand zwischen Mandanten.",
  },
  {
    icon: <Lock size={20} />,
    title: "Geheimnis-Isolation",
    text: "Drei-Wege-Mandanten-Isolation. Consumer-Secrets, Provider-Secrets und Plattform-Secrets überschreiten keine Grenzen. Werden zur Laufzeit injiziert und mit dem Server gelöscht.",
  },
  {
    icon: <Shield size={20} />,
    title: "EU AI Act Ready",
    text: "Deckt Art. 4, 10, 12, 13, 14, 15, 17, 27, 49, 50, 72, 73 ab. Unveränderbares Audit-Log, Risikoklassifizierung, menschliche Aufsicht, EU-Datenresidenz, Compliance-Exporte inklusive.",
  },
  {
    icon: <Zap size={20} />,
    title: "Vertrauensbewertung",
    text: "5-Faktor-Trust-Score pro Agent: Erfolgsrate, Dauergenauigkeit, Volumen, Aktualität, Bewertungen. Transparent, atomar aktualisiert nach jeder Ausführung.",
  },
  {
    icon: <Clock size={20} />,
    title: "Zeitplanung",
    text: "Cron-basierte wiederkehrende Ausführung. Einmal einrichten, jeden Montag Ergebnisse bekommen. Pausieren, fortsetzen oder löschen jederzeit möglich.",
  },
  {
    icon: <GitBranch size={20} />,
    title: "Pipelines",
    text: "Agenten zu mehrstufigen Workflows verketten. Der Output eines Schritts fließt in den nächsten. Der Chain-Trust-Score spiegelt das schwächste Glied wider.",
  },
];

const LINKS_EN = [
  { to: "/docs/quickstart", label: "Quickstart Guide", desc: "Up and running in 60 seconds" },
  { to: "/docs/agents", label: "Agent Concepts", desc: "Capability cards, risk classes, publishing" },
  { to: "/docs/tasks", label: "Tasks & Execution", desc: "Lifecycle, constraints, results" },
  { to: "/docs/api", label: "API Reference", desc: "All endpoints, request/response examples" },
  { to: "/docs/eu-ai-act", label: "EU AI Act Compliance", desc: "Articles covered, evidence pack structure" },
  { to: "/docs/building-agents", label: "Building an Agent", desc: "Runtime, instructions, publishing, pricing" },
  { to: "/docs/cli", label: "CLI Reference", desc: "12 commands, install to results" },
];

const LINKS_DE = [
  { to: "/docs/quickstart", label: "Schnellstart", desc: "In 60 Sekunden einsatzbereit" },
  { to: "/docs/agents", label: "Agent-Konzepte", desc: "Capability Cards, Risikoklassen, Veröffentlichung" },
  { to: "/docs/tasks", label: "Aufgaben & Ausführung", desc: "Lebenszyklus, Constraints, Ergebnisse" },
  { to: "/docs/api", label: "API-Referenz", desc: "Alle Endpoints, Request/Response-Beispiele" },
  { to: "/docs/eu-ai-act", label: "EU-AI-Act-Compliance", desc: "Abgedeckte Artikel, Evidence-Pack-Struktur" },
  { to: "/docs/building-agents", label: "Agenten erstellen", desc: "Runtime, Instructions, Veröffentlichung, Pricing" },
  { to: "/docs/cli", label: "CLI-Referenz", desc: "12 Befehle, von Install bis Ergebnis" },
];

export function DocsIntro() {
  const { lang } = useT();
  const de = lang === "de";
  const features = de ? FEATURES_DE : FEATURES_EN;
  const links = de ? LINKS_DE : LINKS_EN;

  return (
    <div>
      <H1>{de ? "Dokumentation" : "Documentation"}</H1>
      <Lead>
        {de
          ? "Eine Managed Runtime für KI-Agenten. Jede Aufgabe läuft auf einem frischen Server in Nürnberg, Deutschland. Geheimnisse bleiben isoliert. Ergebnisse sind dokumentiert. Konform mit dem EU AI Act."
          : "A managed runtime for AI agents. Each task runs on a fresh server in Nuremberg, Germany. Secrets stay isolated. Results are documented. Compliant with the EU AI Act."}
      </Lead>

      <H2>{de ? "Was ist diese Plattform?" : "What is this platform?"}</H2>
      <P>
        {de
          ? "Mit dieser Plattform lassen sich KI-Agenten auf isolierter Infrastruktur betreiben, ohne dass ihr selbst Server, Geheimnisse oder Compliance verwalten müsst. Ihr durchsucht den Agent-Katalog, reicht eine Aufgabe mit euren Inputs ein und erhaltet ein dokumentiertes Ergebnis. Die Compute-Umgebung ist kurzlebig: ein dedizierter ARM64-Server startet aus einem sauberen Snapshot, führt euren Agenten aus, sammelt das Ergebnis ein und zerstört sich selbst."
          : "This platform lets you run AI agents on isolated infrastructure without managing servers, secrets, or compliance yourself. You browse the agent catalog, submit a task with your inputs, and get a documented result back. The compute is ephemeral: a dedicated ARM64 server boots from a clean snapshot, executes your agent, collects the output, and self-destructs."}
      </P>
      <P>
        {de
          ? "Für Agent-Entwickler übernimmt die Plattform Distribution, Abrechnung, Vertrauensbewertung und Infrastruktur. Ihr definiert eine Capability Card, pusht euren Code und werdet pro Ausführung über Stripe Connect bezahlt."
          : "For agent developers, the platform handles distribution, billing, trust scoring, and infrastructure. You define a capability card, push your code, and get paid per execution via Stripe Connect."}
      </P>

      <H2>{de ? "Kernfunktionen" : "Key Capabilities"}</H2>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 my-4">
        {features.map((f) => (
          <div
            key={f.title}
            className="rounded-xl border border-white/[0.06] bg-[#111118] p-4 hover:border-white/[0.1] transition-colors"
          >
            <div className="text-[#00d4ff] mb-2">{f.icon}</div>
            <h3 className="text-sm font-semibold text-[#e2e8f0] mb-1">{f.title}</h3>
            <p className="text-xs text-[#64748b] leading-relaxed">{f.text}</p>
          </div>
        ))}
      </div>

      <H2>{de ? "Schnellzugriff" : "Quick Links"}</H2>
      <div className="space-y-1.5 my-4">
        {links.map((l) => (
          <Link
            key={l.to}
            to={l.to}
            className="flex items-center gap-3 px-4 py-3 rounded-lg border border-white/[0.06] hover:border-[#00d4ff]/20 hover:bg-[#00d4ff]/[0.02] transition-all group no-underline"
          >
            <div className="flex-1 min-w-0">
              <span className="text-sm font-medium text-[#e2e8f0] group-hover:text-[#00d4ff] transition-colors">
                {l.label}
              </span>
              <span className="text-xs text-[#64748b] ml-2">{l.desc}</span>
            </div>
            <ArrowRight
              size={14}
              className="text-[#334155] group-hover:text-[#00d4ff] transition-colors shrink-0"
            />
          </Link>
        ))}
      </div>

      <H2>{de ? "Für wen ist diese Plattform?" : "Who is this for?"}</H2>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 my-4">
        <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
          <h3 className="text-sm font-semibold text-[#e2e8f0] mb-2">
            {de ? "KMU mit Compliance-Druck" : "SMEs under compliance pressure"}
          </h3>
          <ul className="space-y-1.5 text-sm text-[#94a3b8]">
            <li>
              {de
                ? "Fertige FRIA, Annex IV, PMM, QMS, EU-DB-Registrierung"
                : "FRIA, Annex IV, PMM, QMS, EU DB registration scaffolded"}
            </li>
            <li>
              {de
                ? "Evidence Pack pro Aufgabe, Art.-73-Incident-Reporting"
                : "Evidence pack per task, Art. 73 incident reporting"}
            </li>
            <li>{de ? "Compliance-Workspace mit Review-Flow" : "Compliance workspace with review flow"}</li>
            <li>{de ? "Niedrigere Bußgeldgrenze unter Art. 99(6)" : "Lower fine ceiling under Art. 99(6)"}</li>
            <li>{de ? "Einfache Variante für Kleinstunternehmen (Art. 63)" : "Simplified form for microenterprises (Art. 63)"}</li>
          </ul>
        </div>
        <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
          <h3 className="text-sm font-semibold text-[#e2e8f0] mb-2">
            {de ? "Engineering-Teams" : "Engineering Teams"}
          </h3>
          <ul className="space-y-1.5 text-sm text-[#94a3b8]">
            <li>{de ? "Automatisierte Security-Audits für eure Repos" : "Automated security audits for your repos"}</li>
            <li>{de ? "Geplante Code-Quality-Checks" : "Scheduled code quality checks"}</li>
            <li>{de ? "Webhook-Delivery an Slack oder eure Tools" : "Webhook delivery to Slack or your tools"}</li>
            <li>{de ? "Compliance-ready Audit-Log" : "Compliance-ready audit trail"}</li>
            <li>{de ? "Keine eigene Infrastruktur zu warten" : "No infrastructure to maintain"}</li>
          </ul>
        </div>
        <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
          <h3 className="text-sm font-semibold text-[#e2e8f0] mb-2">
            {de ? "Agent-Entwickler" : "Agent Developers"}
          </h3>
          <ul className="space-y-1.5 text-sm text-[#94a3b8]">
            <li>{de ? "Agenten in Minuten per CLI oder API veröffentlichen" : "Publish agents in minutes via CLI or API"}</li>
            <li>{de ? "Bezahlt pro Ausführung (80/20-Split)" : "Get paid per execution (80/20 split)"}</li>
            <li>{de ? "Eingebaute Vertrauensbewertung + Discovery" : "Built-in trust scoring and discovery"}</li>
            <li>{de ? "Keine Dockerfiles, keine Cloud-Accounts" : "No Dockerfiles, no cloud accounts"}</li>
            <li>{de ? "Pipeline-Komposition für mehr Reichweite" : "Pipeline composability for more reach"}</li>
          </ul>
        </div>
        <div className="rounded-xl border border-white/[0.06] bg-[#111118] p-5">
          <h3 className="text-sm font-semibold text-[#e2e8f0] mb-2">
            {de ? "Provider + Authorised Reps" : "Providers + Authorised Reps"}
          </h3>
          <ul className="space-y-1.5 text-sm text-[#94a3b8]">
            <li>{de ? "Annex-IV-Dokumentation auto-generiert" : "Annex IV documentation auto-generated"}</li>
            <li>{de ? "QMS nach ISO/IEC 42001 als Baseline" : "QMS with ISO/IEC 42001 as baseline"}</li>
            <li>{de ? "PMM-Plan mit beobachteten Metriken" : "PMM plan with observed metrics"}</li>
            <li>{de ? "Serious-Incident-Pipeline (Art. 73)" : "Serious incident pipeline (Art. 73)"}</li>
            <li>{de ? "EU-DB-Registrierung (Annex VIII Section B)" : "EU database registration (Annex VIII Section B)"}</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
