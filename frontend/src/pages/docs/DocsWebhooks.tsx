import { H1, H2, H3, P, Lead, CodeBlock, Callout, InlineCode, DocTable, Badge } from "./components";
import { useT } from "../../i18n";

export function DocsWebhooks() {
  const { lang } = useT();
  const de = lang === "de";

  return (
    <div>
      <H1>Webhooks</H1>
      <Lead>
        {de
          ? "Lass dich in Echtzeit benachrichtigen, wenn Events auf der Plattform passieren. Abonniere bestimmte Event-Typen und empfange JSON-Payloads, Slack Block Kit Messages, Splunk HEC Events, Datadog Logs oder Jira/Linear Issues."
          : "Get notified in real-time when events happen on the platform. Subscribe to specific event types and receive JSON payloads, Slack Block Kit messages, Splunk HEC events, Datadog logs, or Jira/Linear issues."}
      </Lead>

      <H2 id="types">{de ? "Webhook-Typen" : "Webhook Types"}</H2>
      <DocTable
        headers={
          de
            ? ["Typ", "Format", "Verifikation / Credential"]
            : ["Type", "Format", "Verification / credential"]
        }
        rows={[
          [
            <Badge color="cyan">generic</Badge>,
            de ? "JSON-Payload mit vollem Event-Envelope" : "JSON payload with full event envelope",
            de
              ? "HMAC-SHA256-Signatur im X-Webhook-Signature Header"
              : "HMAC-SHA256 signature in X-Webhook-Signature header",
          ],
          [
            <Badge color="purple">slack</Badge>,
            de
              ? "Slack Block Kit Message mit farb-codierten Attachments"
              : "Slack Block Kit message with color-coded attachments",
            de
              ? "Slack Incoming-Webhook URL authentifiziert"
              : "Slack incoming-webhook URL authenticates",
          ],
          [
            <Badge color="cyan">splunk_hec</Badge>,
            de
              ? "Splunk HEC Single-Event-Payload, numerische Epoch-Zeit, sourcetype agentforge:event"
              : "Splunk HEC single-event payload, numeric epoch time, sourcetype agentforge:event",
            <>
              <InlineCode>secret_override</InlineCode> = HEC Token
            </>,
          ],
          [
            <Badge color="cyan">datadog_logs</Badge>,
            de
              ? "Datadog Logs v2 Intake-Array mit ddtags, status und service Feldern"
              : "Datadog Logs v2 intake array with ddtags, status and service fields",
            <>
              <InlineCode>secret_override</InlineCode> = Datadog API Key
            </>,
          ],
          [
            <Badge color="purple">jira</Badge>,
            de
              ? "Jira Cloud REST Issue-Create (labelled, typed Task) bei jedem Event"
              : "Jira Cloud REST issue-create (labelled, typed Task) on every event",
            <>
              <InlineCode>secret_override</InlineCode> ={" "}
              <InlineCode>PROJECT_KEY|email:api_token</InlineCode>
            </>,
          ],
          [
            <Badge color="purple">linear</Badge>,
            de ? "Linear GraphQL issueCreate-Mutation" : "Linear GraphQL issueCreate mutation",
            <>
              <InlineCode>secret_override</InlineCode> ={" "}
              <InlineCode>TEAM_ID|api_key</InlineCode>
            </>,
          ],
        ]}
      />

      <H2 id="setup">{de ? "Webhooks einrichten" : "Setting Up Webhooks"}</H2>
      <H3>{de ? "Generischer Webhook" : "Generic Webhook"}</H3>
      <CodeBlock
        code={`curl -X POST https://agents.renemurrell.de/v1/webhooks \\
  -H "X-API-Key: af_your_key" \\
  -H "Content-Type: application/json" \\
  -d '{
    "url": "https://your-server.com/webhook",
    "event_types": ["task.completed", "task.failed"],
    "webhook_type": "generic"
  }'`}
      />

      <H3>{de ? "Slack Webhook" : "Slack Webhook"}</H3>
      <CodeBlock
        code={`curl -X POST https://agents.renemurrell.de/v1/webhooks \\
  -H "X-API-Key: af_your_key" \\
  -H "Content-Type: application/json" \\
  -d '{
    "url": "https://hooks.slack.com/services/T.../B.../xxx",
    "event_types": ["task.completed", "task.failed", "task.awaiting_approval"],
    "webhook_type": "slack"
  }'`}
      />

      <H3>Splunk HTTP Event Collector</H3>
      <CodeBlock
        code={`curl -X POST https://agents.renemurrell.de/v1/me/webhooks \\
  -H "X-API-Key: af_your_key" \\
  -H "Content-Type: application/json" \\
  -d '{
    "url": "https://splunk.example.com:8088/services/collector/event",
    "event_types": ["task.failed", "incident.*", "agent.updated"],
    "webhook_type": "splunk_hec",
    "secret_override": "YOUR-HEC-TOKEN"
  }'`}
      />

      <H3>Datadog Logs</H3>
      <CodeBlock
        code={`curl -X POST https://agents.renemurrell.de/v1/me/webhooks \\
  -H "X-API-Key: af_your_key" \\
  -H "Content-Type: application/json" \\
  -d '{
    "url": "https://http-intake.logs.datadoghq.eu/api/v2/logs",
    "event_types": ["*"],
    "webhook_type": "datadog_logs",
    "secret_override": "YOUR_DATADOG_API_KEY"
  }'`}
      />

      <H3>{de ? "Jira (erzeugt Issue pro Event)" : "Jira (create issue on each event)"}</H3>
      <CodeBlock
        code={`curl -X POST https://agents.renemurrell.de/v1/me/webhooks \\
  -H "X-API-Key: af_your_key" \\
  -H "Content-Type: application/json" \\
  -d '{
    "url": "https://your-team.atlassian.net/rest/api/3/issue",
    "event_types": ["incident.created", "task.failed"],
    "webhook_type": "jira",
    "secret_override": "SEC|you@example.com:api_token"
  }'`}
      />

      <H3>{de ? "Linear (erzeugt Issue pro Event)" : "Linear (create issue on each event)"}</H3>
      <CodeBlock
        code={`curl -X POST https://agents.renemurrell.de/v1/me/webhooks \\
  -H "X-API-Key: af_your_key" \\
  -H "Content-Type: application/json" \\
  -d '{
    "url": "https://api.linear.app/graphql",
    "event_types": ["incident.created"],
    "webhook_type": "linear",
    "secret_override": "<TEAM_ID>|lin_api_xxx"
  }'`}
      />

      <H2 id="events">{de ? "Event-Typen" : "Event Types"}</H2>
      <P>
        {de
          ? "Abonniere die Events, die für dich wichtig sind. Jedes Event enthält ein typisiertes Payload mit relevanten Ressourcendaten."
          : "Subscribe to the events you care about. Each event includes a typed payload with relevant resource data."}
      </P>

      <H3>{de ? "Task Events" : "Task Events"}</H3>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5 my-3">
        {["task.created", "task.awaiting_approval", "task.approved", "task.dispatching", "task.completed", "task.failed"].map((e) => (
          <span key={e} className="text-[11px] font-mono text-[#94a3b8] bg-white/[0.03] rounded px-2 py-1.5 border border-white/[0.04]">{e}</span>
        ))}
      </div>

      <H3>{de ? "Execution Events" : "Execution Events"}</H3>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5 my-3">
        {["execution.started", "execution.completed", "execution.failed"].map((e) => (
          <span key={e} className="text-[11px] font-mono text-[#94a3b8] bg-white/[0.03] rounded px-2 py-1.5 border border-white/[0.04]">{e}</span>
        ))}
      </div>

      <H3>{de ? "Pipeline Events" : "Pipeline Events"}</H3>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5 my-3">
        {["pipeline.created", "pipeline.completed", "pipeline.failed"].map((e) => (
          <span key={e} className="text-[11px] font-mono text-[#94a3b8] bg-white/[0.03] rounded px-2 py-1.5 border border-white/[0.04]">{e}</span>
        ))}
      </div>

      <H3>{de ? "Weitere Events" : "Other Events"}</H3>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5 my-3">
        {["payment.authorized", "payment.captured", "payment.cancelled", "agent.created", "agent.updated", "agent.deleted", "schedule.created", "schedule.fired", "schedule.deleted", "rating.created", "webhook.test"].map((e) => (
          <span key={e} className="text-[11px] font-mono text-[#94a3b8] bg-white/[0.03] rounded px-2 py-1.5 border border-white/[0.04]">{e}</span>
        ))}
      </div>

      <H2 id="payload">{de ? "Payload-Format" : "Payload Format"}</H2>
      <CodeBlock
        language="json"
        title={de ? "Generischer Webhook-Payload" : "Generic webhook payload"}
        code={`{
  "event_type": "task.completed",
  "timestamp": "2026-04-15T11:21:10Z",
  "actor_id": "uuid",
  "actor_role": "consumer",
  "resource_type": "task",
  "resource_id": "tc-20260415-a1b2c3d4",
  "payload": {
    "agent_id": "security-audit-v1",
    "status": "completed",
    "elapsed_seconds": 284,
    "exit_code": 0
  }
}`}
      />

      <H2 id="verification">{de ? "HMAC-Verifikation" : "HMAC Verification"}</H2>
      <P>
        {de
          ? <>Generische Webhooks enthalten einen <InlineCode>X-Webhook-Signature</InlineCode> Header. Verifiziere, indem du HMAC-SHA256 über den rohen Request-Body mit deinem Webhook-Secret berechnest.</>
          : <>Generic webhooks include an <InlineCode>X-Webhook-Signature</InlineCode> header. Verify by computing HMAC-SHA256 of the raw request body with your webhook secret.</>}
      </P>
      <CodeBlock
        language="python"
        title={de ? "Verifikations-Beispiel" : "Verification example"}
        code={`import hmac, hashlib

def verify_webhook(body: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)`}
      />

      <Callout type="warning" title={de ? "Immer verifizieren" : "Always verify"}>
        {de
          ? "Vertraue Webhook-Payloads nie ohne Signatur-Verifikation. Das Webhook-Secret wird bei der Erstellung zurückgegeben und sollte sicher gespeichert werden."
          : "Never trust webhook payloads without signature verification. The webhook secret is returned when you create the webhook and should be stored securely."}
      </Callout>

      <H2 id="delivery">{de ? "Delivery und Retries" : "Delivery & Retries"}</H2>
      <P>
        {de
          ? "Webhook-Delivery ist asynchron und non-blocking. Fehlgeschlagene Deliveries werden bis zu 3-mal mit exponential backoff (2s Base Delay) retried."
          : "Webhook delivery is asynchronous and non-blocking. Failed deliveries are retried up to 3 times with exponential backoff (2s base delay)."}
      </P>
      <DocTable
        headers={de ? ["Versuch", "Verzögerung"] : ["Attempt", "Delay"]}
        rows={[
          [de ? "1. Retry" : "1st retry", de ? "2 Sekunden" : "2 seconds"],
          [de ? "2. Retry" : "2nd retry", de ? "4 Sekunden" : "4 seconds"],
          [de ? "3. Retry" : "3rd retry", de ? "8 Sekunden" : "8 seconds"],
        ]}
      />
      <P>
        {de
          ? <>Nach aufgebrauchten Retries wird die Delivery als failed markiert. Der <InlineCode>total_failures</InlineCode> Counter des Webhooks wird inkrementiert.</>
          : <>After all retries are exhausted, the delivery is marked as failed. The webhook's <InlineCode>total_failures</InlineCode> counter increments.</>}
      </P>

      <H2 id="management">{de ? "Management" : "Management"}</H2>
      <CodeBlock
        title={de ? "Webhooks auflisten" : "List webhooks"}
        code={`curl -H "X-API-Key: af_your_key" \\
  https://agents.renemurrell.de/v1/webhooks`}
      />
      <CodeBlock
        title={de ? "Webhook testen" : "Test a webhook"}
        code={`curl -X POST https://agents.renemurrell.de/v1/webhooks/{id}/test \\
  -H "X-API-Key: af_your_key"`}
      />
      <CodeBlock
        title={de ? "Webhook löschen" : "Delete a webhook"}
        code={`curl -X DELETE https://agents.renemurrell.de/v1/webhooks/{id} \\
  -H "X-API-Key: af_your_key"`}
      />
    </div>
  );
}
