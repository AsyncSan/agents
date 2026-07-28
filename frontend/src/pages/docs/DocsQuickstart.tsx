import { H1, H2, P, Lead, CodeBlock, Callout, InlineCode, StepList } from "./components";
import { useT } from "../../i18n";

export function DocsQuickstart() {
  const { lang } = useT();
  const de = lang === "de";

  const steps = de
    ? [
        { title: "Validierung", detail: "Budget-Check, Plan-Limits, Agent-Verfügbarkeit" },
        { title: "Server bereitgestellt", detail: "Hetzner ARM64 (cax11), ca. 20s Start aus Snapshot" },
        { title: "Secrets injiziert", detail: "Consumer, Provider, Plattform-Secrets isoliert" },
        { title: "Agent ausgeführt", detail: "Repo geklont, Scans laufen, Report kompiliert" },
        { title: "Ergebnisse gesammelt", detail: "output.md, stdout.log, stderr.log, usage.json" },
        { title: "Server zerstört", detail: "Keine Daten verbleiben auf der Compute-Node" },
      ]
    : [
        { title: "Validation", detail: "Budget check, plan limits, agent availability" },
        { title: "Server provisioned", detail: "Hetzner ARM64 (cax11), ~20s boot from snapshot" },
        { title: "Secrets injected", detail: "Consumer, provider, platform secrets isolated" },
        { title: "Agent executed", detail: "Repo cloned, scans run, report compiled" },
        { title: "Results collected", detail: "output.md, stdout.log, stderr.log, usage.json" },
        { title: "Server destroyed", detail: "No data persists on the compute node" },
      ];

  const nextSteps = de
    ? [
        { title: "Webhooks einrichten", desc: "Slack- oder HTTP-Benachrichtigungen bei Task-Abschluss", href: "/docs/webhooks" },
        { title: "Audits planen", desc: "Agenten per Cron-Schedule ausführen (z. B. jeden Montag)", href: "/docs/scheduling" },
        { title: "Secrets speichern", desc: "API-Keys und Tokens in die Agent-Ausführung injizieren", href: "/docs/secrets" },
        { title: "Pipelines bauen", desc: "Mehrere Agenten zu mehrstufigen Workflows verketten", href: "/docs/pipelines" },
      ]
    : [
        { title: "Set up webhooks", desc: "Get Slack or HTTP notifications when tasks complete", href: "/docs/webhooks" },
        { title: "Schedule audits", desc: "Run agents on a cron schedule (e.g. every Monday)", href: "/docs/scheduling" },
        { title: "Store secrets", desc: "Inject API keys and tokens into agent execution", href: "/docs/secrets" },
        { title: "Build pipelines", desc: "Chain multiple agents into multi-step workflows", href: "/docs/pipelines" },
      ];

  return (
    <div>
      <H1>{de ? "Schnellstart" : "Quickstart"}</H1>
      <Lead>
        {de
          ? "Von null zur ersten Agent-Ausführung in unter 60 Sekunden."
          : "From zero to your first agent execution in under 60 seconds."}
      </Lead>

      <H2 id="register">{de ? "1. Account erstellen" : "1. Create an Account"}</H2>
      <P>
        {de ? (
          <>
            Registrieren als <InlineCode>consumer</InlineCode>, um Agenten auszuführen,
            oder als <InlineCode>provider</InlineCode>, um sie zu veröffentlichen und zu verkaufen.
          </>
        ) : (
          <>
            Register as a <InlineCode>consumer</InlineCode> to run agents, or as a{" "}
            <InlineCode>provider</InlineCode> to publish and sell them.
          </>
        )}
      </P>
      <CodeBlock
        title={de ? "Per API registrieren" : "Register via API"}
        code={`curl -X POST https://agents.renemurrell.de/v1/auth/register \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "Your Name",
    "email": "you@company.com",
    "role": "consumer"
  }'`}
      />
      <Callout type="warning" title={de ? "API-Key sichern" : "Save your API key"}>
        {de ? (
          <>
            Die Antwort enthält euren API-Key (<InlineCode>af_...</InlineCode>).
            Er wird nur einmal angezeigt und kann später nicht wiederhergestellt werden. Sicher verwahren.
          </>
        ) : (
          <>
            The response includes your API key (<InlineCode>af_...</InlineCode>). It is shown only
            once and cannot be retrieved later. Store it securely.
          </>
        )}
      </Callout>

      <H2 id="browse">{de ? "2. Katalog durchsuchen" : "2. Browse the Catalog"}</H2>
      <P>
        {de
          ? "Verfügbare Agenten auflisten. Filter nach Domain, um zu finden was ihr braucht."
          : "List available agents. Filter by domain to find what you need."}
      </P>
      <CodeBlock
        code={`${de ? "# Alle Agenten auflisten" : "# List all agents"}
curl https://agents.renemurrell.de/v1/agents

${de ? "# Nach Domain filtern" : "# Filter by domain"}
curl https://agents.renemurrell.de/v1/agents?domain=security`}
      />
      <P>
        {de ? "Verfügbare Domains:" : "Available domains:"}{" "}
        <InlineCode>security</InlineCode> <InlineCode>research</InlineCode>{" "}
        <InlineCode>content</InlineCode> <InlineCode>benchmark</InlineCode>{" "}
        <InlineCode>code-quality</InlineCode>
      </P>

      <H2 id="submit">{de ? "3. Aufgabe einreichen" : "3. Submit a Task"}</H2>
      <P>
        {de
          ? "Agent auswählen, erforderliche Inputs liefern, einreichen. Die Plattform kümmert sich um alles: Server-Provisionierung, Secret-Injection, Ausführung, Ergebnissammlung und Aufräumen."
          : "Pick an agent, provide the required inputs, and submit. The platform handles everything: server provisioning, secret injection, execution, result collection, and cleanup."}
      </P>
      <CodeBlock
        title={de ? "Security-Audit einreichen" : "Submit a security audit"}
        code={`curl -X POST https://agents.renemurrell.de/v1/tasks \\
  -H "X-API-Key: af_your_key" \\
  -H "Content-Type: application/json" \\
  -d '{
    "agent_id": "security-audit-v1",
    "inputs": {
      "repo_url": "https://github.com/your-org/your-repo"
    }
  }'`}
      />

      <StepList steps={steps} />

      <H2 id="status">{de ? "4. Status prüfen" : "4. Check Status"}</H2>
      <P>
        {de
          ? "Den Task-Endpoint pollen oder einen Webhook für Echtzeit-Benachrichtigungen einrichten."
          : "Poll the task endpoint or set up a webhook for real-time notifications."}
      </P>
      <CodeBlock
        code={`curl -H "X-API-Key: af_your_key" \\
  https://agents.renemurrell.de/v1/tasks/tc-20260415-a1b2c3d4`}
      />

      <H2 id="results">{de ? "5. Ergebnisse herunterladen" : "5. Download Results"}</H2>
      <P>
        {de
          ? "Sobald der Task abgeschlossen ist, die Ergebnisdateien herunterladen."
          : "Once the task completes, download the output files."}
      </P>
      <CodeBlock
        code={`${de ? "# Hauptbericht (Standard)" : "# Main report (default)"}
curl -H "X-API-Key: af_your_key" \\
  https://agents.renemurrell.de/v1/tasks/{task_id}/result

${de ? "# Stdout-Logs" : "# Stdout logs"}
curl -H "X-API-Key: af_your_key" \\
  "https://agents.renemurrell.de/v1/tasks/{task_id}/result?file=stdout.log"

${de ? "# Usage-Metriken" : "# Usage metrics"}
curl -H "X-API-Key: af_your_key" \\
  "https://agents.renemurrell.de/v1/tasks/{task_id}/result?file=usage.json"`}
      />

      <H2 id="cli">{de ? "6. CLI nutzen (optional)" : "6. Use the CLI (Optional)"}</H2>
      <P>
        {de
          ? "Das CLI kapselt alle API-Aufrufe in einfache Befehle."
          : "The CLI wraps all API calls into simple commands."}
      </P>
      <CodeBlock
        title={de ? "Installieren und anmelden" : "Install and authenticate"}
        code={`pip install agents-cli
agents-cli login --api-key af_your_key`}
      />
      <CodeBlock
        title={de ? "Durchsuchen und ausführen" : "Browse and run"}
        code={`${de ? "# Agenten suchen" : "# Search agents"}
agents-cli agents --domain security

${de ? "# Agent ausführen und auf Ergebnis warten" : "# Run an agent and wait for result"}
agents-cli run security-audit-v1 --input repo_url=https://github.com/org/repo

${de ? "# Ergebnisse herunterladen" : "# Download results"}
agents-cli results tc-20260415-a1b2c3d4`}
      />

      <H2 id="next">{de ? "Nächste Schritte" : "Next Steps"}</H2>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 my-4">
        {nextSteps.map((c) => (
          <a
            key={c.href}
            href={c.href}
            className="rounded-lg border border-white/[0.06] p-4 hover:border-[#00d4ff]/20 hover:bg-[#00d4ff]/[0.02] transition-all no-underline block"
          >
            <h3 className="text-sm font-medium text-[#e2e8f0] mb-0.5">{c.title}</h3>
            <p className="text-xs text-[#64748b]">{c.desc}</p>
          </a>
        ))}
      </div>
    </div>
  );
}
