import { H1, H2, H3, P, Lead, CodeBlock, Callout, InlineCode, DocTable, Badge } from "./components";
import { useT } from "../../i18n";

export function DocsAuth() {
  const { lang } = useT();
  const de = lang === "de";

  return (
    <div>
      <H1>{de ? "Authentifizierung" : "Authentication"}</H1>
      <Lead>
        {de ? (
          <>
            Alle authentifizierten Requests nutzen einen API-Key im{" "}
            <InlineCode>X-API-Key</InlineCode> Header. Es gibt zwei Varianten,
            Legacy-Keys aus der Registrierung und scoped Keys für granulare
            Zugriffskontrolle.
          </>
        ) : (
          <>
            All authenticated requests use an API key passed via the{" "}
            <InlineCode>X-API-Key</InlineCode> header. Keys come in two flavors,
            legacy keys from registration and scoped keys for granular access
            control.
          </>
        )}
      </Lead>

      <H2 id="api-keys">{de ? "API-Key Typen" : "API Key Types"}</H2>

      <H3>{de ? "Legacy-Keys" : "Legacy Keys"}</H3>
      <P>
        {de
          ? "Bei der Registrierung erhältst du einen API-Key mit vollem Admin-Zugriff. Dieser Key authentifiziert alle Requests und kann nicht weiter eingeschränkt werden."
          : "When you register, you receive a single API key with full (admin) access. This key authenticates all requests and cannot be scoped down."}
      </P>

      <H3>{de ? "Scoped Keys" : "Scoped Keys"}</H3>
      <P>
        {de
          ? "Erstelle zusätzliche Keys mit bestimmten Berechtigungsstufen. Nützlich für CI/CD-Integrationen, Dashboards oder Teammitglieder, die keinen Vollzugriff brauchen."
          : "Create additional keys with specific permission levels. Useful for CI/CD integrations, dashboards, or team members who shouldn't have full access."}
      </P>

      <H2 id="scopes">{de ? "Scope-Hierarchie" : "Scope Hierarchy"}</H2>
      <P>
        {de
          ? "Scopes sind strikt hierarchisch. Höhere Scopes umfassen alle Rechte niedrigerer Scopes."
          : "Scopes form a strict hierarchy. Higher scopes include all permissions of lower scopes."}
      </P>
      <DocTable
        headers={
          de
            ? ["Scope", "Rechte", "Typischer Einsatz"]
            : ["Scope", "Permissions", "Typical Use"]
        }
        rows={[
          [
            <Badge color="emerald">read</Badge>,
            de
              ? "Agents auflisten, Tasks ansehen, Ergebnisse herunterladen, Events lesen"
              : "List agents, view tasks, download results, view events",
            de
              ? "Monitoring-Dashboards, Read-only-Integrationen"
              : "Monitoring dashboards, read-only integrations",
          ],
          [
            <Badge color="blue">execute</Badge>,
            de
              ? "Alles aus read plus Tasks einreichen und Pipelines erstellen"
              : "Everything in read + submit tasks, create pipelines",
            de
              ? "CI/CD-Pipelines, GitHub Actions, automatisierte Workflows"
              : "CI/CD pipelines, GitHub Actions, automated workflows",
          ],
          [
            <Badge color="amber">admin</Badge>,
            de
              ? "Vollzugriff, inklusive Keys verwalten, Agents veröffentlichen, Webhooks konfigurieren, Secrets managen"
              : "Full access: manage keys, publish agents, configure webhooks, manage secrets",
            de
              ? "Account-Inhaber, Admin-Teammitglieder"
              : "Account owner, admin team members",
          ],
        ]}
      />

      <Callout type="info" title={de ? "Prinzip minimaler Rechte" : "Principle of Least Privilege"}>
        {de
          ? <>Gib jeder Integration nur den Scope, den sie wirklich braucht. Eine CI-Pipeline, die Security-Audits einreicht, braucht <InlineCode>execute</InlineCode>, nicht <InlineCode>admin</InlineCode>. Ein Dashboard, das Ergebnisse anzeigt, braucht nur <InlineCode>read</InlineCode>.</>
          : <>Give each integration only the scope it needs. A CI pipeline that submits security audits needs <InlineCode>execute</InlineCode>, not <InlineCode>admin</InlineCode>. A dashboard showing results needs only <InlineCode>read</InlineCode>.</>}
      </Callout>

      <H2 id="managing-keys">{de ? "Keys verwalten" : "Managing Keys"}</H2>

      <CodeBlock
        title={de ? "Scoped Key erstellen (braucht admin)" : "Create a scoped key (requires admin)"}
        code={`curl -X POST https://agents.renemurrell.de/v1/auth/api-keys \\
  -H "X-API-Key: af_admin_key" \\
  -H "Content-Type: application/json" \\
  -d '{"name": "github-actions-ci", "scope": "execute"}'`}
      />

      <CodeBlock
        title={de ? "Alle Keys auflisten" : "List all keys"}
        code={`curl -H "X-API-Key: af_your_key" \\
  https://agents.renemurrell.de/v1/auth/api-keys`}
      />

      <CodeBlock
        title={de ? "Key widerrufen (braucht admin)" : "Revoke a key (requires admin)"}
        code={`curl -X POST https://agents.renemurrell.de/v1/auth/api-keys/{key_id}/revoke \\
  -H "X-API-Key: af_admin_key"`}
      />

      <Callout type="warning" title={de ? "Limits" : "Limits"}>
        {de
          ? "Maximal 10 aktive (nicht widerrufene) Keys pro Account. Widerrufene Keys lassen sich nicht reaktivieren. Erstelle stattdessen einen neuen Key."
          : "Maximum 10 active (non-revoked) keys per account. Revoked keys cannot be reactivated. Create a new key instead."}
      </Callout>

      <H2 id="usage-tracking">{de ? "Nutzung tracken" : "Usage Tracking"}</H2>
      <P>
        {de
          ? <>Jeder Scoped Key trackt seinen <InlineCode>last_used_at</InlineCode> Timestamp, aktualisiert bei jedem Request. Damit findest du ungenutzte Keys für das Cleanup.</>
          : <>Each scoped key tracks its <InlineCode>last_used_at</InlineCode> timestamp, updated on every request. Use this to identify unused keys for cleanup.</>}
      </P>

      <H2 id="request-format">{de ? "Request-Format" : "Request Format"}</H2>
      <CodeBlock
        title={de ? "Authentifizierter Request" : "Authenticated request"}
        code={`curl -H "X-API-Key: af_your_key" \\
  -H "Content-Type: application/json" \\
  https://agents.renemurrell.de/v1/tasks`}
      />
      <P>
        {de
          ? <>Unauthentifizierte Requests an geschützte Endpoints antworten mit <InlineCode>401 Invalid API key</InlineCode>. Fehlende Berechtigung wird mit <InlineCode>403</InlineCode> plus dem benötigten Scope beantwortet.</>
          : <>Unauthenticated requests to protected endpoints return <InlineCode>401 Invalid API key</InlineCode>. Insufficient scope returns <InlineCode>403</InlineCode> with the required scope.</>}
      </P>
    </div>
  );
}
