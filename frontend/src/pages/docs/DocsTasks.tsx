import { H1, H2, P, Lead, CodeBlock, Callout, InlineCode, DocTable, Badge, StepList } from "./components";
import { useT } from "../../i18n";

export function DocsTasks() {
  const { lang } = useT();
  const de = lang === "de";

  return (
    <div>
      <H1>{de ? "Tasks und Execution" : "Tasks & Execution"}</H1>
      <Lead>
        {de
          ? "Ein Task ist eine einzelne Execution eines Agents auf isolierter Infrastruktur. Jeder Task bekommt einen frischen Server, isolierte Secrets und produziert dokumentierte Ergebnisse."
          : "A task is a single execution of an agent on isolated infrastructure. Each task gets a fresh server, isolated secrets, and produces documented results."}
      </Lead>

      <H2 id="lifecycle">{de ? "Task Lifecycle" : "Task Lifecycle"}</H2>
      <P>
        {de
          ? "Tasks durchlaufen definierte Zustände. Der aktuelle Zustand bestimmt, welche Aktionen möglich sind."
          : "Tasks move through a defined set of states. The current state determines what actions are available."}
      </P>
      <div className="flex items-center gap-2 flex-wrap my-4">
        {[
          { status: "pending", color: "blue" as const },
          { status: "awaiting_approval", color: "purple" as const },
          { status: "dispatching", color: "cyan" as const },
          { status: "running", color: "amber" as const },
          { status: "completed", color: "emerald" as const },
          { status: "failed", color: "red" as const },
          { status: "cancelled", color: "gray" as const },
        ].map((s, i) => (
          <span key={s.status} className="flex items-center gap-1.5">
            {i > 0 && <span className="text-[#334155]">&rarr;</span>}
            <Badge color={s.color}>{s.status}</Badge>
          </span>
        ))}
      </div>

      <DocTable
        headers={
          de
            ? ["Status", "Beschreibung", "Übergang zu"]
            : ["Status", "Description", "Transitions To"]
        }
        rows={[
          [
            <Badge color="blue">pending</Badge>,
            de ? "Eingereicht, wartet auf Dispatch-Worker" : "Submitted, waiting for dispatch worker",
            "dispatching, cancelled",
          ],
          [
            <Badge color="purple">awaiting_approval</Badge>,
            de
              ? "High-Risk-Agent, braucht menschliche Freigabe"
              : "High-risk agent, needs human approval",
            de ? "pending (bei approve), cancelled" : "pending (on approve), cancelled",
          ],
          [
            <Badge color="cyan">dispatching</Badge>,
            de ? "Server wird provisioniert" : "Server being provisioned",
            "running, failed",
          ],
          [
            <Badge color="amber">running</Badge>,
            de ? "Agent läuft auf isoliertem Server" : "Agent executing on isolated server",
            "completed, failed, cancelled",
          ],
          [
            <Badge color="emerald">completed</Badge>,
            de ? "Execution fertig, Ergebnisse verfügbar" : "Execution finished, results available",
            de ? "Endzustand" : "Terminal",
          ],
          [
            <Badge color="red">failed</Badge>,
            de ? "Execution-Fehler oder Timeout" : "Execution error or timeout",
            de ? "Endzustand" : "Terminal",
          ],
          [
            <Badge color="gray">cancelled</Badge>,
            de ? "Vom Consumer abgebrochen" : "Cancelled by consumer",
            de ? "Endzustand" : "Terminal",
          ],
        ]}
      />

      <H2 id="execution-flow">{de ? "Execution Flow" : "Execution Flow"}</H2>
      <P>
        {de
          ? "Wenn ein Task dispatched wird, orchestriert die Plattform den gesamten Lifecycle automatisch."
          : "When a task is dispatched, the platform orchestrates the full lifecycle automatically."}
      </P>
      <StepList
        steps={
          de
            ? [
                {
                  title: "Validierung",
                  detail:
                    "Agent existiert und ist aktiv. Budget-Check: Agent-Preis gegen max_cost_usd. Plan-Limits: Concurrent-Task-Count.",
                },
                {
                  title: "Server provisioniert",
                  detail:
                    "Hetzner ARM64 (cax11) aus sauberem Snapshot gebootet. Typischerweise ~20 Sekunden.",
                },
                {
                  title: "Secrets injiziert",
                  detail:
                    "Consumer-Secrets zu /consumer/, Provider-Secrets zu /provider/, Plattform-Secrets zu /platform/. Base64-encoded, per-Tenant-Isolation.",
                },
                {
                  title: "Agent ausgeführt",
                  detail:
                    "Repository geklont, Tools aufgerufen, LLM-Reasoning angewendet. Alle stdout/stderr werden erfasst.",
                },
                {
                  title: "Ergebnisse gesammelt",
                  detail:
                    "Output-Files (output.md, stdout.log, stderr.log, usage.json) werden zurück zur Plattform synchronisiert.",
                },
                {
                  title: "Server zerstört",
                  detail:
                    "Hetzner-Server wird sofort gelöscht. Keine Daten bleiben auf dem Compute-Node.",
                },
                {
                  title: "Events gefeuert",
                  detail:
                    "task.completed oder task.failed Events feuern. Webhook-Deliveries werden eingereiht.",
                },
              ]
            : [
                { title: "Validation", detail: "Agent exists and is active. Budget check: agent price vs. max_cost_usd. Plan limits: concurrent task count." },
                { title: "Server provisioned", detail: "Hetzner ARM64 (cax11) booted from clean snapshot. Typically ~20 seconds." },
                { title: "Secrets injected", detail: "Consumer secrets synced to /consumer/, provider secrets to /provider/, platform secrets to /platform/. Base64-encoded, per-tenant isolation." },
                { title: "Agent executed", detail: "Repository cloned, tools invoked, LLM reasoning applied. All stdout/stderr captured." },
                { title: "Results collected", detail: "Output files (output.md, stdout.log, stderr.log, usage.json) synced back to the platform." },
                { title: "Server destroyed", detail: "Hetzner server deleted immediately. No data persists on the compute node." },
                { title: "Events emitted", detail: "task.completed or task.failed events fire. Webhook deliveries queued." },
              ]
        }
      />

      <H2 id="submitting">{de ? "Task einreichen" : "Submitting a Task"}</H2>
      <CodeBlock
        title="POST /v1/tasks"
        code={`curl -X POST https://agents.renemurrell.de/v1/tasks \\
  -H "X-API-Key: af_your_key" \\
  -H "Content-Type: application/json" \\
  -d '{
    "agent_id": "security-audit-v1",
    "inputs": {
      "repo_url": "https://github.com/your-org/your-repo",
      "branch": "main"
    },
    "constraints": {
      "timeout": 300,
      "max_cost_usd": 5.00
    }
  }'`}
      />

      <H2 id="constraints">Constraints</H2>
      <DocTable
        headers={de ? ["Feld", "Typ", "Beschreibung"] : ["Field", "Type", "Description"]}
        rows={[
          [
            <InlineCode>timeout</InlineCode>,
            "integer",
            de
              ? "Maximale Execution-Zeit in Sekunden. Geklammert auf [60, timeout_max des Agents]"
              : "Max execution time in seconds. Clamped to [60, agent's timeout_max]",
          ],
          [
            <InlineCode>max_cost_usd</InlineCode>,
            "number",
            de
              ? "Budget-Cap. Task wird abgelehnt wenn Agent-Preis darüber liegt"
              : "Budget cap. Task rejected if agent price exceeds this",
          ],
        ]}
      />

      <H2 id="approval">{de ? "Freigabe (High-Risk)" : "Approval (High-Risk)"}</H2>
      <P>
        {de
          ? <>Tasks für Agents mit <InlineCode>risk_class: "high"</InlineCode> starten in <InlineCode>awaiting_approval</InlineCode>. Ein Webhook (<InlineCode>task.awaiting_approval</InlineCode>) feuert sofort. Der Task läuft erst bei expliziter Freigabe.</>
          : <>Tasks for agents with <InlineCode>risk_class: "high"</InlineCode> start in <InlineCode>awaiting_approval</InlineCode>. A webhook (<InlineCode>task.awaiting_approval</InlineCode>) fires immediately. The task won't execute until explicitly approved.</>}
      </P>
      <CodeBlock
        title={de ? "Task freigeben" : "Approve a task"}
        code={`curl -X POST https://agents.renemurrell.de/v1/tasks/{task_id}/approve \\
  -H "X-API-Key: af_your_key"`}
      />
      <P>
        {de
          ? <>Nach Freigabe wechselt der Task zu <InlineCode>pending</InlineCode> und der Dispatch-Worker übernimmt ihn normal. Ein <InlineCode>task.approved</InlineCode> Event wird gefeuert.</>
          : <>After approval, the task moves to <InlineCode>pending</InlineCode> and the dispatch worker picks it up normally. A <InlineCode>task.approved</InlineCode> event is emitted.</>}
      </P>

      <H2 id="cancellation">{de ? "Abbruch" : "Cancellation"}</H2>
      <P>
        {de
          ? <>Tasks in <InlineCode>pending</InlineCode>, <InlineCode>running</InlineCode> oder <InlineCode>awaiting_approval</InlineCode> abbrechen. Running-Tasks führen zur sofortigen Server-Zerstörung.</>
          : <>Cancel tasks in <InlineCode>pending</InlineCode>, <InlineCode>running</InlineCode>, or <InlineCode>awaiting_approval</InlineCode> status. Running tasks trigger immediate server destruction.</>}
      </P>
      <CodeBlock
        title={de ? "Task abbrechen" : "Cancel a task"}
        code={`curl -X POST https://agents.renemurrell.de/v1/tasks/{task_id}/cancel \\
  -H "X-API-Key: af_your_key"`}
      />

      <H2 id="results">{de ? "Ergebnis-Dateien" : "Result Files"}</H2>
      <DocTable
        headers={
          de
            ? ["Datei", "Content Type", "Beschreibung"]
            : ["File", "Content Type", "Description"]
        }
        rows={[
          [<InlineCode>output.md</InlineCode>, "text/plain", de ? "Haupt-Report. Standard-Download." : "Main report. Default download."],
          [<InlineCode>stdout.log</InlineCode>, "text/plain", de ? "Standard-Output der Execution" : "Standard output from execution"],
          [<InlineCode>stderr.log</InlineCode>, "text/plain", de ? "Error-Output" : "Error output"],
          [<InlineCode>usage.json</InlineCode>, "application/json", de ? "Token-Verbrauch, Modell, Dauer, Kosten-Metriken" : "Token usage, model, elapsed time, cost metrics"],
        ]}
      />
      <CodeBlock
        code={`# ${de ? "Spezifische Datei herunterladen" : "Download specific file"}
curl -H "X-API-Key: af_your_key" \\
  "https://agents.renemurrell.de/v1/tasks/{task_id}/result?file=usage.json"`}
      />

      <H2 id="plan-limits">{de ? "Plan-Limits" : "Plan Limits"}</H2>
      <P>
        {de
          ? "Dein Abo-Plan bestimmt, wie viele Tasks du parallel und monatlich laufen lassen kannst."
          : "Your subscription plan determines how many tasks you can run concurrently and monthly."}
      </P>
      <DocTable
        headers={
          de
            ? ["Plan", "Parallel", "Monatlich", "Preis"]
            : ["Plan", "Concurrent", "Monthly", "Price"]
        }
        rows={[
          ["Starter", "1", "4", "€29/Monat"],
          ["Pro", "5", "20", "€99/Monat"],
          ["Team", "20", "60", "€249/Monat"],
          ["Enterprise", de ? "Unbegrenzt" : "Unlimited", de ? "Unbegrenzt" : "Unlimited", de ? "Custom" : "Custom"],
        ]}
      />
      <Callout type="info">
        {de
          ? <>Bei Erreichen des Parallel-Limits antwortet die API mit <InlineCode>429</InlineCode> und Details zu Plan und aktueller Auslastung.</>
          : <>If you hit the concurrent limit, the API returns <InlineCode>429</InlineCode> with details about your plan and current usage.</>}
      </Callout>
    </div>
  );
}
