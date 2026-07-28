import { H1, H2, P, Lead, CodeBlock, Callout, InlineCode, DocTable } from "./components";
import { useT } from "../../i18n";

export function DocsScheduling() {
  const { lang } = useT();
  const de = lang === "de";

  return (
    <div>
      <H1>{de ? "Scheduling" : "Scheduling"}</H1>
      <Lead>
        {de
          ? "Lasse Agents nach Cron-Expressions wiederkehrend laufen. Einmal einrichten, automatisch Ergebnisse in deiner Kadenz bekommen."
          : "Run agents on a recurring schedule using cron expressions. Set it once, get automated results on your cadence."}
      </Lead>

      <H2 id="how-it-works">{de ? "Wie es funktioniert" : "How It Works"}</H2>
      <P>
        {de
          ? "Der Scheduler läuft als Background-Worker und pollt alle 60 Sekunden. Wenn ein Schedule fällig ist (basierend auf Cron-Expression und Timezone), erzeugt der Worker automatisch einen Task mit den konfigurierten Inputs und Constraints."
          : "The scheduler runs a background worker that polls every 60 seconds. When a schedule is due (based on its cron expression and timezone), the worker automatically creates a task with the configured inputs and constraints."}
      </P>

      <H2 id="creating">{de ? "Schedule erstellen" : "Creating a Schedule"}</H2>
      <CodeBlock
        title={de ? "Wöchentlicher Security-Audit Montag 8 Uhr" : "Weekly Monday 8am security audit"}
        code={`curl -X POST https://agents.renemurrell.de/v1/schedules \\
  -H "X-API-Key: af_your_key" \\
  -H "Content-Type: application/json" \\
  -d '{
    "agent_id": "security-audit-v1",
    "name": "Weekly Repo Audit",
    "cron_expression": "0 8 * * 1",
    "timezone": "Europe/Berlin",
    "inputs": {
      "repo_url": "https://github.com/your-org/repo"
    },
    "constraints": {
      "timeout": 600,
      "max_cost_usd": 5.00
    }
  }'`}
      />

      <H2 id="cron">{de ? "Cron-Expression Format" : "Cron Expression Format"}</H2>
      <P>
        {de
          ? <>Standard 5-Feld-Cron: <InlineCode>minute stunde tag-des-monats monat wochentag</InlineCode></>
          : <>Standard 5-field cron: <InlineCode>minute hour day-of-month month day-of-week</InlineCode></>}
      </P>
      <DocTable
        headers={de ? ["Expression", "Zeitplan"] : ["Expression", "Schedule"]}
        rows={[
          [<InlineCode>0 8 * * 1</InlineCode>, de ? "Jeden Montag um 8:00 Uhr" : "Every Monday at 8:00 AM"],
          [<InlineCode>0 9 * * 1-5</InlineCode>, de ? "Jeden Wochentag um 9:00 Uhr" : "Every weekday at 9:00 AM"],
          [<InlineCode>0 0 1 * *</InlineCode>, de ? "Erster Tag jedes Monats um Mitternacht" : "First day of every month at midnight"],
          [<InlineCode>0 */6 * * *</InlineCode>, de ? "Alle 6 Stunden" : "Every 6 hours"],
          [<InlineCode>30 14 * * 5</InlineCode>, de ? "Jeden Freitag um 14:30 Uhr" : "Every Friday at 2:30 PM"],
        ]}
      />

      <Callout type="info" title={de ? "Timezone-Support" : "Timezone support"}>
        {de
          ? <>Immer eine Timezone angeben (z.B. <InlineCode>Europe/Berlin</InlineCode>, <InlineCode>America/New_York</InlineCode>). Der Scheduler berücksichtigt Sommerzeit-Wechsel.</>
          : <>Always specify a timezone (e.g. <InlineCode>Europe/Berlin</InlineCode>, <InlineCode>America/New_York</InlineCode>). The scheduler respects DST transitions.</>}
      </Callout>

      <H2 id="management">{de ? "Schedules verwalten" : "Managing Schedules"}</H2>

      <CodeBlock
        title={de ? "Schedules auflisten" : "List schedules"}
        code={`curl -H "X-API-Key: af_your_key" \\
  https://agents.renemurrell.de/v1/schedules`}
      />

      <CodeBlock
        title={de ? "Schedule pausieren" : "Pause a schedule"}
        code={`curl -X PATCH https://agents.renemurrell.de/v1/schedules/{id}/pause \\
  -H "X-API-Key: af_your_key"`}
      />

      <CodeBlock
        title={de ? "Pausierten Schedule fortsetzen" : "Resume a paused schedule"}
        code={`curl -X PATCH https://agents.renemurrell.de/v1/schedules/{id}/resume \\
  -H "X-API-Key: af_your_key"`}
      />

      <CodeBlock
        title={de ? "Schedule löschen" : "Delete a schedule"}
        code={`curl -X DELETE https://agents.renemurrell.de/v1/schedules/{id} \\
  -H "X-API-Key: af_your_key"`}
      />

      <H2 id="tracking">{de ? "Execution-Tracking" : "Execution Tracking"}</H2>
      <P>{de ? "Jeder Schedule trackt:" : "Each schedule tracks:"}</P>
      <DocTable
        headers={de ? ["Feld", "Beschreibung"] : ["Field", "Description"]}
        rows={[
          [<InlineCode>total_runs</InlineCode>, de ? "Anzahl der bisherigen Auslösungen" : "Total number of times this schedule has fired"],
          [<InlineCode>last_run_at</InlineCode>, de ? "Zeitstempel der letzten Execution" : "Timestamp of the most recent execution"],
          [<InlineCode>next_run_at</InlineCode>, de ? "Berechneter nächster Auslösezeitpunkt" : "Calculated next fire time"],
          [<InlineCode>active</InlineCode>, de ? "Ob der Schedule aktiv oder pausiert ist" : "Whether the schedule is currently active or paused"],
        ]}
      />

      <Callout type="success" title={de ? "Use Case: Wöchentliche Security-Audits" : "Use case: Weekly security audits"}>
        {de
          ? <>Plane deinen Security-Audit-Agent jeden Montag um 8 Uhr. Füge einen Slack-Webhook für <InlineCode>task.completed</InlineCode> Events hinzu. Dein Team bekommt jede Woche automatisch einen Security-Report in Slack, ohne manuelle Eingriffe.</>
          : <>Schedule your security audit agent to run every Monday at 8am. Add a Slack webhook for <InlineCode>task.completed</InlineCode> events. Your team gets an automated security report in Slack every week, no manual intervention needed.</>}
      </Callout>
    </div>
  );
}
