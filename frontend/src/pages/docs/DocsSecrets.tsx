import { H1, H2, P, Lead, CodeBlock, Callout, InlineCode, DocTable } from "./components";
import { useT } from "../../i18n";

export function DocsSecrets() {
  const { lang } = useT();
  const de = lang === "de";

  return (
    <div>
      <H1>Secrets</H1>
      <Lead>
        {de
          ? "Speichere API-Keys, Tokens und Credentials, die in die Execution-Umgebung des Agents injiziert werden. Strikte Tenant-Isolation verhindert, dass Secrets Grenzen überschreiten."
          : "Store API keys, tokens, and credentials that get injected into the agent's execution environment. Strict tenant isolation ensures no secret crosses boundaries."}
      </Lead>

      <H2 id="isolation">{de ? "Drei-Pfad-Isolation" : "Three-Path Isolation"}</H2>
      <P>
        {de
          ? "Während der Execution werden Secrets in drei isolierte Verzeichnisse auf die VM synchronisiert. Kein Pfad kann auf einen anderen zugreifen."
          : "During execution, secrets are synced to the VM in three isolated directories. No path can access another."}
      </P>
      <DocTable
        headers={de ? ["Pfad", "Inhaber", "Enthält"] : ["Path", "Owner", "Contains"]}
        rows={[
          [
            <InlineCode>/consumer/</InlineCode>,
            de ? "Consumer (du)" : "Consumer (you)",
            de ? "Deine API-Keys, Tokens, Credentials" : "Your API keys, tokens, credentials",
          ],
          [
            <InlineCode>/provider/</InlineCode>,
            de ? "Agent-Provider" : "Agent provider",
            de ? "Interne Keys und Configs des Providers" : "Provider's internal keys and configs",
          ],
          [
            <InlineCode>/platform/</InlineCode>,
            de ? "Plattform" : "Platform",
            de ? "Plattform-weite Konfiguration" : "Platform-level configuration",
          ],
        ]}
      />
      <P>
        {de
          ? "Der Agent-Code hat Lesezugriff auf alle drei Pfade, aber nur Plattform und jeweilige Inhaber können schreiben. Consumer-Secrets eines Users sind niemals in den Tasks eines anderen sichtbar."
          : "The agent code has access to all three paths but only the platform and respective owners can write to them. Consumer secrets from one user are never visible to another user's tasks."}
      </P>

      <H2 id="managing">{de ? "Secrets verwalten" : "Managing Secrets"}</H2>

      <CodeBlock
        title={de ? "Secret speichern" : "Store a secret"}
        code={`curl -X PUT https://agents.renemurrell.de/v1/secrets \\
  -H "X-API-Key: af_your_key" \\
  -H "Content-Type: application/json" \\
  -d '{"key": "GITHUB_TOKEN", "value": "ghp_xxx..."}'`}
      />

      <CodeBlock
        title={de ? "Secrets auflisten (Werte versteckt)" : "List secrets (values are hidden)"}
        code={`curl -H "X-API-Key: af_your_key" \\
  https://agents.renemurrell.de/v1/secrets`}
      />

      <CodeBlock
        title={de ? "Secret löschen" : "Delete a secret"}
        code={`curl -X DELETE \\
  -H "X-API-Key: af_your_key" \\
  https://agents.renemurrell.de/v1/secrets/GITHUB_TOKEN`}
      />

      <Callout type="warning" title={de ? "Ephemeral by Design" : "Ephemeral by design"}>
        {de
          ? "Secrets werden base64-encoded und zur Laufzeit auf die Execution-VM synchronisiert. Wenn der Server nach der Execution zerstört wird, sind auch die Secrets weg. Sie werden niemals über die Task-Lebensdauer hinaus auf der Compute-Node-Disk persistiert."
          : "Secrets are base64-encoded and synced to the execution VM at runtime. When the server is destroyed after execution, secrets are gone. They are never persisted on the compute node's disk beyond the task lifetime."}
      </Callout>

      <H2 id="use-cases">{de ? "Typische Use Cases" : "Common Use Cases"}</H2>
      <DocTable
        headers={de ? ["Secret-Key", "Zweck"] : ["Secret Key", "Purpose"]}
        rows={[
          [
            <InlineCode>GITHUB_TOKEN</InlineCode>,
            de ? "Private Repositories für Security-Audits klonen" : "Clone private repositories for security audits",
          ],
          [
            <InlineCode>SLACK_WEBHOOK_URL</InlineCode>,
            de ? "Agent-spezifische Slack-Benachrichtigungen" : "Agent-level Slack notifications",
          ],
          [
            <InlineCode>NPM_TOKEN</InlineCode>,
            de ? "Zugriff auf private npm-Pakete" : "Access private npm packages",
          ],
          [
            <InlineCode>OPENAI_API_KEY</InlineCode>,
            de ? "Agent nutzt externes LLM als Tool" : "Agent uses external LLM as tool",
          ],
        ]}
      />
    </div>
  );
}
