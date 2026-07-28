import { H1, H2, H3, P, Lead, CodeBlock, Callout, InlineCode, DocTable, Badge } from "./components";
import { useT } from "../../i18n";

export function DocsAgents() {
  const { lang } = useT();
  const de = lang === "de";

  return (
    <div>
      <H1>Agents</H1>
      <Lead>
        {de
          ? "Agents sind verpackte KI-Workflows mit definierten Inputs, Outputs, Pricing und Runtime-Anforderungen. Jeder Agent wird durch eine signierte Capability Card beschrieben."
          : "Agents are packaged AI workflows with defined inputs, outputs, pricing, and runtime requirements. Each agent is described by a signed capability card."}
      </Lead>

      <H2 id="capability-card">Capability Card</H2>
      <P>
        {de
          ? "Die Capability Card ist der Vertrag zwischen Provider (baut den Agent) und Consumer (betreibt ihn). Sie deklariert was der Agent tut, was er braucht, was er produziert und was er kostet."
          : "The capability card is the contract between a provider (who builds the agent) and a consumer (who runs it). It declares what the agent does, what it needs, what it produces, and how much it costs."}
      </P>
      <CodeBlock
        language="json"
        title={de ? "Beispiel: Security-Audit-Agent" : "Example: Security Audit Agent"}
        code={`{
  "capabilities": {
    "domain": "security",
    "tags": ["audit", "sast", "npm", "secrets"],
    "description": "Automated security audit for Node.js repositories",
    "inputs": [
      { "name": "repo_url", "type": "string", "required": true },
      { "name": "branch", "type": "string", "required": false, "default": "main" }
    ],
    "outputs": [
      { "name": "report", "type": "markdown", "guaranteed": true },
      { "name": "findings_count", "type": "integer", "guaranteed": true }
    ],
    "constraints": {
      "timeout_max": 600,
      "requires_network": true
    }
  },
  "runtime": {
    "snapshot_profile": "openclaw-agent",
    "server_type": "cax11",
    "compute_tier": "vm",
    "model": "anthropic/claude-sonnet-4-6",
    "tools": ["bash", "computer"],
    "estimated_duration_seconds": 300,
    "estimated_cost_usd": 0.45
  },
  "pricing": {
    "model": "per_execution",
    "base_price_usd": 2.50
  }
}`}
      />

      <H3>{de ? "Card-Felder" : "Card Fields"}</H3>
      <DocTable
        headers={de ? ["Feld", "Beschreibung"] : ["Field", "Description"]}
        rows={[
          [
            <InlineCode>capabilities.domain</InlineCode>,
            de
              ? "Kategorie: security, research, content, benchmark, code-quality"
              : "Category: security, research, content, benchmark, code-quality",
          ],
          [
            <InlineCode>capabilities.inputs</InlineCode>,
            de
              ? "Pflicht- und optionale Inputs, die der Agent akzeptiert"
              : "Required and optional inputs the agent accepts",
          ],
          [
            <InlineCode>capabilities.outputs</InlineCode>,
            de
              ? "Was der Agent produziert. Guaranteed Outputs erscheinen immer"
              : "What the agent produces. Guaranteed outputs always appear",
          ],
          [
            <InlineCode>capabilities.constraints</InlineCode>,
            de
              ? "Execution-Limits: Timeout, Netzwerkzugriff, etc."
              : "Execution limits: timeout, network access, etc.",
          ],
          [
            <InlineCode>runtime.server_type</InlineCode>,
            de
              ? "Hetzner Server-Typ (z.B. cax11 für ARM64)"
              : "Hetzner server type (e.g. cax11 for ARM64)",
          ],
          [
            <InlineCode>runtime.model</InlineCode>,
            de ? "LLM-Modell für das Reasoning" : "LLM model used for reasoning",
          ],
          [
            <InlineCode>pricing.base_price_usd</InlineCode>,
            de
              ? "Kosten pro Execution, die dem Consumer berechnet werden"
              : "Cost per execution charged to the consumer",
          ],
        ]}
      />

      <H2 id="risk-classification">{de ? "Risk-Klassifikation" : "Risk Classification"}</H2>
      <P>
        {de
          ? "Jeder Agent hat eine Risk Class, abgestimmt auf EU AI Act Artikel 6 und 9. Die Klasse bestimmt das Execution-Verhalten."
          : "Every agent has a risk class, aligned with EU AI Act Articles 6 and 9. The risk class determines execution behavior."}
      </P>
      <DocTable
        headers={de ? ["Risk Class", "Verhalten", "Beispiele"] : ["Risk Class", "Behavior", "Examples"]}
        rows={[
          [
            <Badge color="emerald">minimal</Badge>,
            de ? "Läuft sofort, Standard-Logging" : "Runs immediately, standard logging",
            de ? "Linter, Formatter, Dependency-Check" : "Linter, formatter, dependency check",
          ],
          [
            <Badge color="amber">limited</Badge>,
            de ? "Läuft sofort, erweitertes Logging" : "Runs immediately, enhanced logging",
            de ? "Content-Generator, Summarizer" : "Content generator, summarizer",
          ],
          [
            <Badge color="red">high</Badge>,
            de
              ? "Erfordert menschliche Freigabe vor Execution"
              : "Requires human approval before execution",
            de
              ? "Security-Audit, Code-Modifier, Data-Processor"
              : "Security audit, code modifier, data processor",
          ],
        ]}
      />
      <P>
        {de
          ? <>High-Risk-Agents erstellen Tasks im Status <InlineCode>awaiting_approval</InlineCode>. Ein Mensch muss explizit via UI oder API freigeben, bevor der Dispatch-Worker sie übernimmt.</>
          : <>High-risk agents create tasks in <InlineCode>awaiting_approval</InlineCode> status. A human must explicitly approve via UI or API before the dispatch worker picks them up.</>}
      </P>

      <H2 id="ed25519-signing">{de ? "Ed25519-Signatur" : "Ed25519 Signing"}</H2>
      <P>
        {de
          ? "Jede Capability Card wird mit dem Ed25519-Schlüsselpaar des Providers signiert (generiert bei der Registrierung). Consumer können verifizieren, dass eine Card vom angegebenen Provider stammt und nicht manipuliert wurde."
          : "Every capability card is signed with the provider's Ed25519 key pair (generated at registration). Consumers can verify that a card was published by the stated provider and hasn't been tampered with."}
      </P>
      <CodeBlock
        language="python"
        title={de ? "Card-Signatur verifizieren" : "Verify a card signature"}
        code={`from nacl.signing import VerifyKey
from nacl.encoding import HexEncoder

verify_key = VerifyKey(provider_public_key, encoder=HexEncoder)
verify_key.verify(card_bytes, signature_bytes)`}
      />

      <H2 id="publishing">{de ? "Agent veröffentlichen" : "Publishing an Agent"}</H2>
      <P>
        {de
          ? "Provider registrieren sich einmal und veröffentlichen Agents per CLI oder API."
          : "Providers register once, then publish agents via CLI or API."}
      </P>

      <H3>{de ? "Via CLI" : "Via CLI"}</H3>
      <CodeBlock
        code={`# ${de ? "Einmalig als Provider registrieren" : "Register as provider (once)"}
curl -X POST https://agents.renemurrell.de/v1/auth/register \\
  -H "Content-Type: application/json" \\
  -d '{"name": "Your Studio", "email": "dev@studio.com", "role": "provider"}'

# ${de ? "Veröffentlichen" : "Publish"}
agents-cli publish --card agent-card.json`}
      />

      <H3>{de ? "Via API" : "Via API"}</H3>
      <CodeBlock
        code={`curl -X POST https://agents.renemurrell.de/v1/agents \\
  -H "X-API-Key: af_provider_key" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "my-agent-v1",
    "card": { ... },
    "risk_class": "minimal"
  }'`}
      />

      <Callout type="success" title={de ? "Revenue Split" : "Revenue Split"}>
        {de
          ? "Provider behält 80 Prozent jeder Execution. Plattform nimmt 20 Prozent. Payouts via Stripe Connect Express."
          : "Provider keeps 80% of each execution. Platform takes 20%. Payouts via Stripe Connect Express."}
      </Callout>

      <H2 id="discovery">{de ? "Discovery" : "Discovery"}</H2>
      <P>
        {de
          ? "Agents erscheinen im Katalog mit Trust Score, Pricing und Domain-Tags. Consumer können nach Domain, Tag oder Keyword suchen. Kompatible Agents werden basierend auf Input/Output-Matching für Pipeline-Komposition vorgeschlagen."
          : "Agents appear in the catalog with their trust score, pricing, and domain tags. Consumers can search by domain, tag, or keyword. Compatible agents are suggested for pipeline composition based on input/output matching."}
      </P>

      <H2 id="versioning">{de ? "Versionierung" : "Versioning"}</H2>
      <P>
        {de
          ? "Jedes Update der Capability Card erzeugt eine neue Version. Frühere Versionen bleiben für den Audit-Trail erhalten. Die aktive Version wird standardmäßig ausgeliefert."
          : "Each update to an agent's capability card creates a new version. Previous versions are preserved for audit trail purposes. The latest active version is served by default."}
      </P>
    </div>
  );
}
