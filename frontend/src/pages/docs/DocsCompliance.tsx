import { H1, H2, H3, P, Lead, CodeBlock, Callout, InlineCode, DocTable, Badge } from "./components";
import { useT } from "../../i18n";

export function DocsCompliance() {
  const { lang } = useT();
  const de = lang === "de";

  return (
    <div>
      <H1>{de ? "EU AI Act Compliance" : "EU AI Act Compliance"}</H1>
      <Lead>
        {de
          ? "Die Plattform setzt technische Maßnahmen für 7 Artikel des EU AI Act (Verordnung 2024/1689) um. Die High-Risk-Pflichten gelten ab dem 2. August 2026, weitere Anforderungen folgen 2027. Die Bußgelder reichen bis 35 Millionen Euro oder 7 Prozent des globalen Umsatzes. KMU sind nach Art. 99 Abs. 6 auf den jeweils niedrigeren der beiden Werte gedeckelt."
          : "The platform implements technical measures covering 7 articles of the EU AI Act (Regulation 2024/1689). High-risk obligations apply from 2 August 2026, with additional requirements following in 2027. Non-compliance penalties reach up to 35M EUR or 7% of global turnover; SMEs are capped at the lower of the two under Art. 99(6)."}
      </Lead>

      <Callout type="warning" title={de ? "Regulatorische Timeline" : "Regulatory Timeline"}>
        {de
          ? "Der Act trat am 1. August 2024 in Kraft und gilt in Phasen. Verbotene Praktiken (Art. 5) und KI-Kompetenz (Art. 4) sind seit Februar 2025 scharf. GPAI-Pflichten und Strafenrahmen folgten im August 2025. High-Risk-Pflichten (Annex III), Deployer-Pflichten (Art. 26, 27) und Transparenz-Regeln (Art. 50) werden nach aktueller Timeline am 2. August 2026 anwendbar. Der vorgeschlagene Digital Omnibus kann den High-Risk-Termin auf Ende 2027 verschieben. Diese Plattform ist nach dem Original-Zeitplan audit-ready gebaut."
          : "The Act entered into force on 1 August 2024 and applies in phases. Prohibited practices (Art. 5) and AI literacy (Art. 4) have been in force since February 2025. GPAI obligations and the penalty framework followed in August 2025. High-risk system obligations (Annex III), deployer duties (Art. 26, 27), and transparency rules (Art. 50) become applicable on 2 August 2026 under the current timeline. The proposed Digital Omnibus may shift the high-risk application date to late 2027; this platform is built to be audit-ready under the original schedule."}
      </Callout>

      <Callout type="info" title={de ? "Für KMU gebaut" : "Built for SMEs"}>
        {de
          ? "Kleine und mittlere Unternehmen (nach Empfehlung 2003/361/EC) qualifizieren sich für reduzierte Konformitätsbewertungs-Gebühren (Art. 62), vereinfachtes QMS für Kleinstunternehmen (Art. 63), prioritären Sandbox-Zugang (Art. 57) und ein niedrigeres Bußgeld-Limit (Art. 99.6). Diese Plattform liefert das technische Scaffolding, damit sich dein Team auf die Teile konzentrieren kann, die nur ihr beantworten könnt."
          : "Small and medium enterprises (under Recommendation 2003/361/EC) qualify for reduced conformity assessment fees (Art. 62), simplified QMS for microenterprises (Art. 63), priority sandbox access (Art. 57), and a lower fine ceiling (Art. 99.6). This platform scaffolds the technical evidence so your team can focus on the parts only you can answer."}
      </Callout>

      <H2 id="article-12">{de ? "Artikel 12: Automatisches Logging" : "Article 12: Automatic Logging"}</H2>
      <P>
        {de
          ? "Die Verordnung verlangt, dass KI-Systeme ihre Aktivitäten zur Nachvollziehbarkeit loggen. Jede Execution auf der Plattform erzeugt einen unveränderlichen Audit-Trail."
          : "The regulation requires AI systems to log their activities for traceability. Every execution on the platform creates an immutable audit trail."}
      </P>
      <H3>{de ? "Was geloggt wird" : "What is logged"}</H3>
      <DocTable
        headers={de ? ["Datenpunkt", "Quelle"] : ["Data Point", "Source"]}
        rows={[
          [de ? "Gelieferte Inputs" : "Inputs provided", de ? "Task-Einreichung" : "Task submission"],
          [de ? "Produzierte Outputs" : "Outputs produced", de ? "Result-Collection" : "Result collection"],
          [de ? "Dauer und Timing" : "Duration and timing", de ? "Execution-Lifecycle" : "Execution lifecycle"],
          [de ? "Genutzte Compute-Ressourcen" : "Compute resources used", de ? "Server-Provisionierung" : "Server provisioning"],
          [de ? "Entstandene Kosten" : "Cost incurred", de ? "Billing-System" : "Billing system"],
          [de ? "Identität des Akteurs" : "Actor identity", de ? "Authentifizierung" : "Authentication"],
          [de ? "Agent-Version und Card" : "Agent version and card", de ? "Agent-Registry" : "Agent registry"],
        ]}
      />
      <H3>Export</H3>
      <P>
        {de
          ? "Exportiere den kompletten Audit-Trail als CSV oder JSON via Compliance-Endpoint."
          : "Export the full audit trail as CSV or JSON via the compliance endpoint."}
      </P>
      <CodeBlock
        code={`# JSON export
curl -H "X-API-Key: af_your_key" \\
  "https://agents.renemurrell.de/v1/dashboard/compliance/export?format=json"

# CSV export
curl -H "X-API-Key: af_your_key" \\
  "https://agents.renemurrell.de/v1/dashboard/compliance/export?format=csv"`}
      />

      <H3 id="article-19">{de ? "Aufbewahrung (Art. 19)" : "Retention (Art. 19)"}</H3>
      <P>
        {de
          ? "Art. 19 verpflichtet Provider von High-Risk-KI-Systemen, automatische Logs mindestens 6 Monate aufzubewahren, es sei denn Unions- oder nationales Recht verlangt längere Zeiträume. Die Plattform erzwingt diesen Floor, er kann nicht unterschritten werden."
          : "Art. 19 requires providers of high-risk AI systems to keep automatic logs for at least 6 months, unless longer periods are mandated by Union or national law. The platform enforces this as a floor that cannot be configured below."}
      </P>
      <DocTable
        headers={
          de
            ? ["Artefakt", "Standard-Retention", "Floor"]
            : ["Artefact", "Default retention", "Floor"]
        }
        rows={[
          [
            de ? "Event-Log (Art. 12 / 19)" : "Event log (Art. 12 / 19)",
            de ? "180 Tage" : "180 days",
            de ? "180 Tage, im Code erzwungen" : "180 days, enforced in code",
          ],
          [
            de ? "Result-Dateien (Payload)" : "Result files (payload)",
            de ? "180 Tage" : "180 days",
            de ? "Konfigurierbar, nicht von Art. 19 geregelt" : "Configurable, not regulated by Art. 19",
          ],
          [
            de
              ? "Technische Docs, QMS, Declarations (Art. 18)"
              : "Technical docs, QMS, declarations (Art. 18)",
            de ? "10 Jahre" : "10 years",
            de ? "10 Jahre" : "10 years",
          ],
          [
            de ? "Evidence Packs (pro-Task-Export)" : "Evidence packs (per-task export)",
            de ? "10 Jahre" : "10 years",
            de ? "10 Jahre" : "10 years",
          ],
        ]}
      />
      <Callout type="info">
        <InlineCode>event_log_retention_days</InlineCode>{" "}
        {de ? "wird durch" : "is clamped to 180 by"}{" "}
        <InlineCode>enforce_ai_act_retention_floor()</InlineCode>{" "}
        {de ? "in" : "in"}{" "}
        <InlineCode>agentforge/cleanup.py</InlineCode>{" "}
        {de
          ? "auf 180 geklammert. Ein kleinerer Wert produziert eine Warnung und wird zur Laufzeit ignoriert."
          : ". Configuring a smaller value produces a warning and is ignored at runtime."}
      </Callout>

      <H2 id="article-13">{de ? "Artikel 13: Transparenz" : "Article 13: Transparency"}</H2>
      <P>
        {de
          ? "KI-Systeme müssen transparent über Capabilities, Limits und Verhalten sein. Jeder Agent auf der Plattform hat eine Capability Card, die als Transparenz-Dokument dient."
          : "AI systems must be transparent about their capabilities, limitations, and behavior. Every agent on the platform has a capability card that serves as the transparency document."}
      </P>
      <H3>{de ? "Capability-Card-Inhalte" : "Capability Card contents"}</H3>
      <ul className="list-disc pl-6 space-y-1 text-sm text-[#94a3b8] mb-4">
        <li>{de ? "Was der Agent tut (Beschreibung, Domain, Tags)" : "What the agent does (description, domain, tags)"}</li>
        <li>{de ? "Welche Inputs er braucht und welche Outputs er produziert" : "What inputs it requires and what outputs it produces"}</li>
        <li>{de ? "Welches LLM-Modell für das Reasoning genutzt wird" : "Which LLM model is used for reasoning"}</li>
        <li>{de ? "Auf welche Daten der Agent zugreift" : "What data the agent accesses"}</li>
        <li>{de ? "Seiteneffekte (Netzwerkzugriff, File-Writes)" : "Side effects (network access, file writes)"}</li>
        <li>{de ? "Geschätzte Dauer und Kosten" : "Estimated duration and cost"}</li>
      </ul>
      <P>
        {de
          ? "Cards sind maschinenlesbar (JSON) und mit dem Ed25519-Key des Providers signiert. Das garantiert Authentizität und Manipulationserkennung."
          : "Cards are machine-readable (JSON) and signed with the provider's Ed25519 key. This ensures authenticity and tamper-detection."}
      </P>

      <H2 id="article-6-9">{de ? "Artikel 6 und 9: Risk-Klassifikation" : "Articles 6 & 9: Risk Classification"}</H2>
      <P>
        {de
          ? "Die Verordnung verlangt eine risikobasierte Kategorisierung von KI-Systemen. Jeder Agent trägt eine Risk Class, die sein Execution-Verhalten bestimmt."
          : "The regulation requires risk-based categorization of AI systems. Every agent is tagged with a risk class that determines its execution behavior."}
      </P>
      <DocTable
        headers={
          de
            ? ["Risk Class", "Anforderungen", "Plattform-Umsetzung"]
            : ["Risk Class", "Requirements", "Platform Implementation"]
        }
        rows={[
          [
            <Badge color="emerald">minimal</Badge>,
            de ? "Basis-Transparenz" : "Basic transparency",
            de ? "Standard-Logging, Capability Card" : "Standard logging, capability card",
          ],
          [
            <Badge color="amber">limited</Badge>,
            de ? "Erweiterte Transparenz" : "Enhanced transparency",
            de
              ? "Erweitertes Logging, detaillierte Metriken, längere Log-Retention"
              : "Extended logging, detailed metrics, longer log retention",
          ],
          [
            <Badge color="red">high</Badge>,
            de ? "Menschliche Oversight, Risikomanagement" : "Human oversight, risk management",
            de
              ? "Pflicht-Approval-Gate vor Execution, erweitertes Logging, Pre-Execution-Webhooks"
              : "Mandatory approval gate before execution, enhanced logging, pre-execution webhooks",
          ],
        ]}
      />

      <Callout type="info">
        {de
          ? "Die Risk Class wird vom Agent-Provider bei der Registrierung gesetzt und von der Plattform validiert. Consumer sehen die Risk Class, bevor sie einen Task einreichen."
          : "The risk class is set by the agent provider at registration time and validated by the platform. Consumers can see the risk class before submitting a task."}
      </Callout>

      <H2 id="article-2">{de ? "Artikel 2: EU-Data-Residency" : "Article 2: EU Data Residency"}</H2>
      <P>
        {de
          ? "Alle Compute läuft auf Hetzner-Infrastruktur in Nürnberg, Deutschland. Während der Execution verlassen keine Daten die EU."
          : "All compute runs on Hetzner infrastructure in Nuremberg, Germany. No data leaves the European Union during execution."}
      </P>
      <DocTable
        headers={de ? ["Aspekt", "Umsetzung"] : ["Aspect", "Implementation"]}
        rows={[
          [de ? "Compute-Standort" : "Compute location", "Hetzner Cloud, Nürnberg (Deutschland)"],
          [de ? "Datenspeicherung" : "Data storage", "PostgreSQL auf EU-Server (178.104.92.181)"],
          [
            de ? "Execution-Artefakte" : "Execution artifacts",
            de ? "Auf EU-Infrastruktur gespeichert, mit Server zerstört" : "Stored on EU infrastructure, destroyed with server",
          ],
          [
            de ? "CLOUD-Act-Exposure" : "CLOUD Act exposure",
            de ? "Keine. Kein US-ansässiger Infrastruktur-Provider" : "None. No US-headquartered infrastructure provider",
          ],
        ]}
      />

      <H2 id="article-11">{de ? "Artikel 11 und Annex IV: Technische Dokumentation" : "Article 11 & Annex IV: Technical Documentation"}</H2>
      <P>
        {de
          ? "Provider von High-Risk-Systemen müssen die in Annex IV gelistete technische Dokumentation vorbereiten und pflegen, bevor sie das System in Verkehr bringen. Die Plattform erzeugt einen Entwurf, der alle neun Sektionen aus der Capability Card, den beobachteten Runtime-Metriken und den Provider-Inputs abdeckt."
          : "Providers of high-risk systems must prepare and maintain the technical documentation listed in Annex IV before placing the system on the market. The platform generates a draft covering all nine sections from the agent capability card, observed runtime metrics, and provider inputs."}
      </P>
      <H3>{de ? "Neun Sektionen, ein Dokument" : "Nine sections, one document"}</H3>
      <DocTable
        headers={de ? ["Sektion", "Quelle"] : ["Section", "Source"]}
        rows={[
          [
            de ? "1. Allgemeine Beschreibung" : "1. General description",
            de ? "Agent-Card plus Provider-Kontakt" : "Agent card + provider contact",
          ],
          [
            de ? "2. Detaillierte Beschreibung" : "2. Detailed description",
            de ? "Agent-Card plus Entwicklungs-Methodik des Providers" : "Agent card + provider dev methodology",
          ],
          [
            de ? "3. Monitoring-Informationen" : "3. Monitoring information",
            de ? "Plattform-Runtime-Metriken plus Provider-Limits" : "Platform runtime metrics + provider limits",
          ],
          [
            de ? "4. Performance-Metriken" : "4. Performance metrics",
            de ? "Plattform-Metriken plus Provider-Rationale" : "Platform metrics + provider rationale",
          ],
          [
            de ? "5. Risk-Management-System" : "5. Risk management system",
            de ? "Agent-Risk-Class plus Provider-RMS" : "Agent risk class + provider RMS",
          ],
          [
            de ? "6. Änderungen" : "6. Changes",
            de ? "Plattform-Version-History plus Provider-Policy" : "Platform version history + provider policy",
          ],
          [
            de ? "7. Angewandte Standards" : "7. Applied standards",
            de ? "Provider-Input" : "Provider input",
          ],
          [
            de ? "8. Konformitätserklärung" : "8. Declaration of conformity",
            de ? "Provider-Input" : "Provider input",
          ],
          [
            de ? "9. Post-Market-Monitoring" : "9. Post-market monitoring",
            de ? "Plattform-Incident-Pipeline plus Provider-Plan" : "Platform incident pipeline + provider plan",
          ],
        ]}
      />
      <H3>{de ? "SME vereinfachtes Formular" : "SME simplified form"}</H3>
      <P>
        {de
          ? <>Art. 11 Abs. 1 Unterabs. 3 erlaubt KMU die Abgabe eines vereinfachten Formulars. Der Wizard bietet eine <InlineCode>simplified</InlineCode> Variante, die die Sektionen 2, 4 und 6 für Kleinstunternehmen und kleine Teams verdichtet.</>
          : <>Art. 11(1) sub-paragraph 3 permits SMEs to supply a simplified form. The wizard offers a <InlineCode>simplified</InlineCode> variant that condenses sections 2, 4, and 6 for microenterprises and small teams.</>}
      </P>
      <CodeBlock
        code={`# ${de ? "Volle Annex IV (JSON)" : "Full Annex IV (JSON)"}
curl -X POST https://agents.renemurrell.de/v1/annex-iv/template \\
  -H "X-API-Key: af_your_key" -H "Content-Type: application/json" \\
  -d '{"agent_id": "credit-scorer-v1", "variant": "full"}'

# ${de ? "Vereinfachtes Markdown für KMU" : "Simplified Markdown for SMEs"}
curl -X POST https://agents.renemurrell.de/v1/annex-iv/template/markdown \\
  -H "X-API-Key: af_your_key" -H "Content-Type: application/json" \\
  -d '{"agent_id": "credit-scorer-v1", "variant": "simplified"}' \\
  > annex-iv.md`}
      />
      <Callout type="info">
        {de
          ? <>Retention: Technische Dokumentation muss nach Art. 18 für 10 Jahre ab Inverkehrbringen aufbewahrt werden. Der Wizard-Entwurf unter <InlineCode>/annex-iv</InlineCode> lebt im Browser des Providers. Nach Finalisierung das Dokument im eigenen Dokumentenmanagement ablegen.</>
          : <>Retention: technical documentation must be kept for 10 years from placing the system on the market under Art. 18. The wizard draft at <InlineCode>/annex-iv</InlineCode> lives in the provider's browser. Once finalised, store the document in your document management system.</>}
      </Callout>

      <H2 id="article-4">{de ? "Artikel 4: KI-Kompetenz" : "Article 4: AI Literacy"}</H2>
      <P>
        {de
          ? "Seit dem 2. Februar 2025 in Kraft. Art. 4 verlangt von Providern und Deployern, dass Mitarbeitende eine ausreichende KI-Kompetenz relativ zu ihrer Rolle haben. Die Plattform liefert drei kurze Module plus einen Zertifikat-Generator, damit die Evidenz bereitliegt, wenn Auditoren fragen."
          : "In force since 2 February 2025, Art. 4 requires providers and deployers to ensure their staff have a sufficient level of AI literacy relative to their role. The platform ships three short modules plus a certificate generator so the evidence is ready when auditors ask."}
      </P>
      <DocTable
        headers={de ? ["Modul", "Dauer", "Fokus"] : ["Module", "Duration", "Focus"]}
        rows={[
          [
            de ? "M1: KI-Agents, Capabilities und Limits" : "M1: AI agents, capabilities and limits",
            "5 min",
            de
              ? "Was Agents tun, typische Failure-Modes, wo Menschen das Ruder behalten"
              : "What agents do, common failure modes, where humans stay in charge",
          ],
          [
            de
              ? "M2: Der EU AI Act für Deployer in 5 Minuten"
              : "M2: The EU AI Act for deployers in 5 minutes",
            "6 min",
            de
              ? "Risk-Klassen, Timeline, Art. 26/27, Bußgelder und das KMU-Limit"
              : "Risk classes, timeline, Art. 26/27, fines and the SME cap",
          ],
          [
            de ? "M3: Menschliche Oversight in der Praxis" : "M3: Human oversight in practice",
            "5 min",
            de
              ? "Automation-Bias, Stop-Kriterien, Serious-Incident-Reporting"
              : "Automation bias, stop criteria, serious incident reporting",
          ],
        ]}
      />
      <P>
        {de
          ? "Jedes Modul endet mit einem kurzen Quiz. Bestehen erzeugt ein herunterladbares JSON- und Markdown-Zertifikat mit deterministischem Fingerprint, Lernendenname, Organisation, Modul-ID, Score und Zeitstempel. Die einsetzende Organisation sammelt diese Zertifikate als Art.-4-Nachweis."
          : "Each module ends with a short quiz. Passing yields a downloadable JSON and Markdown certificate carrying a deterministic fingerprint, the learner's name, their organisation, module identifier, score, and timestamp. The deploying organisation collects these certificates as its Art. 4 evidence."}
      </P>
      <Callout type="info">
        {de
          ? <>Der Wizard unter <InlineCode>/literacy</InlineCode> speichert Fortschritt im Browser der Lernenden. Zertifikate werden serverseitig aus den eingereichten Antworten berechnet, aber nie persistiert. Der Deployer behält den Record.</>
          : <>The wizard at <InlineCode>/literacy</InlineCode> stores progress in the learner's browser. Certificates are computed server-side from the submitted answers but never persisted; the deployer retains the record.</>}
      </Callout>

      <H2 id="article-27">{de ? "Artikel 27: Grundrechte-Folgenabschätzung (FRIA)" : "Article 27: Fundamental Rights Impact Assessment"}</H2>
      <P>
        {de
          ? "Art. 27 verlangt von Deployern bestimmter High-Risk-Systeme eine FRIA vor der ersten Nutzung. Die Plattform erzeugt einen vorausgefüllten Entwurf aus der Capability Card und lässt nur die Sektionen offen, die deine Organisation beantworten muss."
          : "Art. 27 requires deployers of specific high-risk systems to complete a FRIA before first use. The platform generates a pre-filled draft from the agent capability card, leaving only the sections your organisation must answer."}
      </P>
      <H3>{de ? "Wer eine FRIA machen muss" : "Who must perform a FRIA"}</H3>
      <ul className="list-disc pl-6 space-y-1 text-sm text-[#94a3b8] mb-4">
        <li>
          {de
            ? "Öffentliche Stellen oder private Entitäten, die öffentliche Dienste erbringen"
            : "Public bodies, or private entities delivering public services"}
        </li>
        <li>
          {de
            ? "Deployer von Credit-Scoring-Systemen (Annex III § 5(b))"
            : "Deployers of credit scoring systems (Annex III §5(b))"}
        </li>
        <li>
          {de
            ? "Deployer von Risk-Assessment oder Preisbildung in Lebens- oder Krankenversicherung (Annex III § 5(c))"
            : "Deployers of risk assessment or pricing in life or health insurance (Annex III §5(c))"}
        </li>
      </ul>
      <H3>{de ? "Wie das Scaffold funktioniert" : "How the scaffold works"}</H3>
      <DocTable
        headers={de ? ["Sektion", "Quelle"] : ["Section", "Source"]}
        rows={[
          [
            de ? "1. Prozessbeschreibung" : "1. Process description",
            de ? "Agent-Card plus Deployer-Input" : "Agent card + deployer input",
          ],
          [
            de ? "2. Dauer und Frequenz" : "2. Duration and frequency",
            de ? "Deployer-Input" : "Deployer input",
          ],
          [
            de ? "3. Betroffene Personen und vulnerable Gruppen" : "3. Affected persons and vulnerable groups",
            de ? "Deployer-Input" : "Deployer input",
          ],
          [
            de ? "4. Spezifische Schadensrisiken" : "4. Specific risks of harm",
            de ? "Deployer-Input, aufgrund der Plattform-Risk-Class vorgeschlagen" : "Deployer input, prompted by platform risk class",
          ],
          [
            de ? "5. Maßnahmen zur menschlichen Oversight" : "5. Human oversight measures",
            de ? "Plattform (Art. 12-15) plus Deployer-Maßnahmen" : "Platform (Art. 12-15) + deployer measures",
          ],
          [
            de ? "6. Governance, Beschwerde, Behörden-Reporting" : "6. Governance, complaint, authority reporting",
            de ? "Deployer-Input, DPIA-Bridge (Art. 27 Abs. 4)" : "Deployer input, DPIA bridge (Art. 27.4)",
          ],
        ]}
      />
      <CodeBlock
        code={`# ${de ? "FRIA-Entwurf aus der CLI generieren" : "Generate a FRIA draft from the CLI"}
curl -X POST https://agents.renemurrell.de/v1/fria/template \\
  -H "X-API-Key: af_your_key" -H "Content-Type: application/json" \\
  -d '{"agent_id": "credit-scorer-v1", "use_case_key": "credit_scoring"}'

# ${de ? "Markdown-Export" : "Markdown export"}
curl -X POST https://agents.renemurrell.de/v1/fria/template/markdown \\
  -H "X-API-Key: af_your_key" -H "Content-Type: application/json" \\
  -d '{"agent_id": "credit-scorer-v1"}' > fria.md`}
      />
      <Callout type="info">
        {de
          ? <>Der Wizard unter <InlineCode>/fria</InlineCode> speichert deinen Entwurf nur im Browser, nie auf der Plattform. Deployer behalten volle Kontrolle über den regulatorischen Record.</>
          : <>The wizard at <InlineCode>/fria</InlineCode> stores your draft in the browser only, never on the platform. Deployers retain full control of the regulatory record.</>}
      </Callout>

      <H2 id="article-14">{de ? "Artikel 14: Menschliche Oversight" : "Article 14: Human Oversight"}</H2>
      <P>
        {de
          ? "High-Risk-KI-Systeme müssen menschliches Eingreifen erlauben. Die Plattform setzt das über Approval Gates und Cancellation um."
          : "High-risk AI systems must allow human intervention. The platform implements this through approval gates and cancellation."}
      </P>
      <H3>{de ? "Approval Gates" : "Approval Gates"}</H3>
      <P>
        {de
          ? <>Tasks für High-Risk-Agents (<InlineCode>risk_class: "high"</InlineCode>) starten im Status <InlineCode>awaiting_approval</InlineCode>. Der Consumer muss explizit freigeben, bevor die Execution startet.</>
          : <>Tasks for high-risk agents (<InlineCode>risk_class: "high"</InlineCode>) start in <InlineCode>awaiting_approval</InlineCode> status. The consumer must explicitly approve before execution begins.</>}
      </P>
      <ul className="list-disc pl-6 space-y-1 text-sm text-[#94a3b8] mb-4">
        <li>
          {de
            ? <>Pre-Execution-Webhook (<InlineCode>task.awaiting_approval</InlineCode>) feuert sofort</>
            : <>Pre-execution webhook (<InlineCode>task.awaiting_approval</InlineCode>) fires immediately</>}
        </li>
        <li>{de ? "Freigabe via API oder UI" : "Approve via API or UI"}</li>
        <li>
          {de
            ? <>Post-Approval-Webhook (<InlineCode>task.approved</InlineCode>) bestätigt die Entscheidung</>
            : <>Post-approval webhook (<InlineCode>task.approved</InlineCode>) confirms the decision</>}
        </li>
        <li>
          {de
            ? "Cancel statt Approve, wenn der Task nicht laufen soll"
            : "Cancel instead of approve if the task should not proceed"}
        </li>
      </ul>

      <H3>{de ? "Cancellation" : "Cancellation"}</H3>
      <P>
        {de
          ? "Jeder laufende Task kann abgebrochen werden. Cancellation führt zur sofortigen Server-Zerstörung und stoppt den Agent mitten in der Execution."
          : "Any running task can be cancelled. Cancellation triggers immediate server destruction, stopping the AI agent mid-execution."}
      </P>

      <H3>{de ? "Oversight-Roster (Art. 14 und 26 Abs. 2)" : "Oversight roster (Art. 14 + 26(2))"}</H3>
      <P>
        {de
          ? <>Ein Task-Approval-Flow erfüllt den Mechanismus, aber nicht die Nachweispflicht. Art. 26 Abs. 2 verlangt zusätzlich namentlich benannte natürliche Personen mit dokumentierter Kompetenz, Schulung und Befugnis. Das Oversight-Roster unter <InlineCode>/oversight</InlineCode> trackt das pro Agent.</>
          : <>Assigning a task-approval flow satisfies the mechanism but not the paperwork. Art. 26(2) additionally requires named natural persons with documented competence, training and authority. The oversight roster lives at <InlineCode>/oversight</InlineCode> and tracks that per agent.</>}
      </P>
      <ul className="list-disc pl-6 space-y-1 text-sm text-[#94a3b8] mb-4">
        <li>
          {de
            ? "Fünf Oversight-Rollen: approver, reviewer, operator, overseer, incident_owner (Art. 73)"
            : "Five oversight roles: approver, reviewer, operator, overseer, incident_owner (Art. 73)"}
        </li>
        <li>
          {de
            ? "Fünf Authority-Level: read_only, review, approve, override, deputy_provider"
            : "Five authority levels: read_only, review, approve, override, deputy_provider"}
        </li>
        <li>
          {de
            ? "Per-Agent-Coverage-Check: High-Risk-Systeme brauchen mindestens approver, overseer und incident_owner"
            : "Per-agent coverage check: high-risk systems need approver, overseer and incident_owner at minimum"}
        </li>
        <li>
          {de
            ? "Trainings-Zertifikate aus dem Art.-4-Literacy-Modul können als Evidenz an jede Assignment gepinnt werden"
            : "Training certificates from the Art. 4 literacy module can be pinned to each assignment as evidence"}
        </li>
        <li>
          {de
            ? <>PDF-Roster-Export pro Agent, einsatzbereit für die Annex-IV-Sektion &quot;Human oversight measures&quot;</>
            : <>PDF roster export for each agent; ready for the Annex IV &quot;Human oversight measures&quot; section</>}
        </li>
      </ul>
      <CodeBlock
        code={`# ${de ? "Per-Agent-Roster mit Coverage-Check" : "Per-agent roster with coverage check"}
curl -H "X-API-Key: af_your_key" \\
  "https://agents.renemurrell.de/v1/oversight/roster/credit-scorer-v1"

# ${de ? "Als PDF für die Auditor-Übergabe exportieren" : "Export as PDF for auditor handover"}
curl -H "X-API-Key: af_your_key" \\
  "https://agents.renemurrell.de/v1/oversight/roster/credit-scorer-v1/pdf" \\
  -o oversight.pdf`}
      />

      <H2 id="article-50">{de ? "Artikel 50: Transparenz bei KI-generierten Inhalten" : "Article 50: Transparency for AI-Generated Content"}</H2>
      <P>
        {de
          ? "Jedes Task-Ergebnis trägt einen maschinenlesbaren Provenance-Record, der es als KI-generiert ausweist. Das erfüllt die Art.-50-Markierungspflicht für synthetische Inhalte."
          : "Every task result carries a machine-readable provenance record identifying it as AI-generated. This satisfies the Art. 50 marking requirement for synthetic content."}
      </P>
      <H3>{de ? "Wie es funktioniert" : "How it works"}</H3>
      <ul className="list-disc pl-6 space-y-1 text-sm text-[#94a3b8] mb-4">
        <li>
          <InlineCode>X-AI-Generated: true</InlineCode>{" "}
          {de ? "Header auf jeder Result-Response" : "header on every result response"}
        </li>
        <li>
          <InlineCode>X-AI-Provenance</InlineCode>{" "}
          {de ? "Header trägt einen kompakten JSON-Record" : "header carrying a compact JSON record"}
        </li>
        <li>
          {de
            ? "Markdown-Outputs bekommen einen Disclosure-Block angehängt"
            : "Markdown outputs receive an appended disclosure block"}
        </li>
        <li>
          {de
            ? <>JSON-Outputs bekommen ein eingebettetes <InlineCode>_ai_provenance</InlineCode> Feld</>
            : <>JSON outputs receive an embedded <InlineCode>_ai_provenance</InlineCode> field</>}
        </li>
        <li>
          {de
            ? <>Dedizierter <InlineCode>/v1/tasks/&#123;id&#125;/provenance</InlineCode> Endpoint liefert den vollen Record als JSON</>
            : <>Dedicated <InlineCode>/v1/tasks/&#123;id&#125;/provenance</InlineCode> endpoint returns the full record as JSON</>}
        </li>
      </ul>
      <H3>{de ? "Provenance-Felder" : "Provenance fields"}</H3>
      <DocTable
        headers={de ? ["Feld", "Zweck"] : ["Field", "Purpose"]}
        rows={[
          ["ai_generated", de ? "Boolean-Flag für Detection-Systeme" : "Boolean flag for detection systems"],
          ["platform", de ? "Ursprungs-Plattform-Kennung" : "Originating platform identifier"],
          ["regulation", de ? "Regulatorische Referenz (EU 2024/1689 Art. 50)" : "Regulatory reference (EU 2024/1689 Art. 50)"],
          ["agent", de ? "ID, Name, Version, Risk Class" : "ID, name, version, risk class"],
          ["task_id / execution_id", de ? "Rückverfolgbar zum Event-Log und Evidence Pack" : "Traceable back to event log and evidence pack"],
          ["generated_at", de ? "ISO-8601-Zeitstempel der Execution-Vollendung" : "ISO-8601 timestamp of execution completion"],
          ["disclosure", de ? "Für Menschen lesbare Disclosure-Statement" : "Human-readable disclosure statement"],
        ]}
      />
      <CodeBlock
        code={`# ${de ? "Provenance für einen Task abrufen" : "Fetch provenance for a task"}
curl -H "X-API-Key: af_your_key" \\
  "https://agents.renemurrell.de/v1/tasks/tc-20260421-abc123/provenance"`}
      />

      <H2 id="article-47">{de ? "Artikel 47 und Annex V: Konformitätserklärung" : "Article 47 and Annex V: Declaration of Conformity"}</H2>
      <P>
        {de
          ? "Provider von High-Risk-Systemen müssen eine EU-Konformitätserklärung ausstellen, bevor das System in Verkehr gebracht oder in Betrieb genommen wird, und sie 10 Jahre für die zuständigen Behörden bereithalten."
          : "Providers of high-risk systems must issue an EU Declaration of Conformity before placing the system on the market or putting it into service, and retain it for 10 years at the disposal of competent authorities."}
      </P>
      <H3>{de ? "Was du bekommst" : "What you get"}</H3>
      <ul className="list-disc pl-6 space-y-1 text-sm text-[#94a3b8] mb-4">
        <li>
          {de
            ? "Alle 9 Annex-V-Datenpunkte vorausgefüllt aus der Capability Card"
            : "All 9 Annex V data points pre-filled from the capability card"}
        </li>
        <li>
          {de
            ? "DSGVO-Statement (§ 5) automatisch aktiviert bei Domains mit Personendaten"
            : "GDPR statement (§ 5) auto-enabled for domains that process personal data"}
        </li>
        <li>
          {de
            ? "Notified-Body-Sektion (§ 7) nur gerendert wenn erforderlich (biometrische Annex III)"
            : "Notified body section (§ 7) only rendered when required (biometric Annex III)"}
        </li>
        <li>
          {de
            ? "CE-Marking-Block nach Art. 48, mit digital-only Anbringung nach Art. 48 Abs. 4"
            : "CE marking block per Art. 48, with digital-only affixing per Art. 48(4)"}
        </li>
        <li>
          {de
            ? "Retention-Hinweis eingebacken in jeden Export-Footer"
            : "Retention reminder baked into the footer of every export"}
        </li>
        <li>
          {de
            ? "JSON/Markdown/PDF-Exports, im Workspace gespeichert mit Approval-Workflow"
            : "JSON / Markdown / PDF exports; saved to workspace with approval workflow"}
        </li>
      </ul>
      <CodeBlock
        code={`# ${de ? "Declaration anonym preview" : "Preview a declaration anonymously"}
curl https://agents.renemurrell.de/v1/declaration/template/public/agent-id

# ${de ? "Authentifizierter Entwurf mit Provider-Inputs" : "Authenticated draft with provider inputs"}
curl -X POST -H "X-API-Key: af_your_key" -H "Content-Type: application/json" \\
  -d '{"agent_id":"credit-scorer-v1","provider_name":"Acme Bank GmbH"}' \\
  https://agents.renemurrell.de/v1/declaration/template`}
      />
      <P>
        {de
          ? <>Fülle die verbleibenden <InlineCode>[PROVIDER: …]</InlineCode> Platzhalter aus, signiere (physisch oder eIDAS-qualifiziert elektronisch), archiviere. Die Plattform behält den Entwurf im Compliance-Workspace und markiert ihn als veraltet, wenn sich die Agent-Version ändert, sodass jede materielle Revision eine frische Signatur auslöst.</>
          : <>Fill the remaining <InlineCode>[PROVIDER: …]</InlineCode> placeholders, sign (physical or eIDAS-qualified electronic), and archive. The platform will keep the draft in the compliance workspace and flag it stale when the agent version changes, so each material revision triggers a fresh signature.</>}
      </P>

      <H2 id="article-43">{de ? "Artikel 43: Tracking wesentlicher Änderungen" : "Article 43: Substantial Modification Tracking"}</H2>
      <P>
        {de
          ? "Art. 43 Abs. 4 verlangt eine neue Konformitätsbewertung, wann immer ein High-Risk-System wesentlich modifiziert wird, also über das hinaus geändert wird, was in der ursprünglichen Bewertung vorgesehen war, und zwar in einer Weise, die die Kapitel-III-Abschnitt-2-Anforderungen oder den Intended Purpose betrifft."
          : "Art. 43(4) requires a new conformity assessment whenever a high-risk system is substantially modified, i.e. changed beyond what was foreseen in the initial assessment in a way that affects Chapter III Section 2 requirements or the intended purpose."}
      </P>
      <H3>{de ? "Wie es funktioniert" : "How it works"}</H3>
      <ul className="list-disc pl-6 space-y-1 text-sm text-[#94a3b8] mb-4">
        <li>
          {de
            ? <>Jedes <InlineCode>PUT /v1/agents/:id</InlineCode> schreibt automatisch einen Modification-Record mit Feld-Level-Diff</>
            : <>Every <InlineCode>PUT /v1/agents/:id</InlineCode> automatically writes a modification record with a field-level diff</>}
        </li>
        <li>
          {de
            ? <>Der Auto-Klassifikator schlägt <InlineCode>substantial</InlineCode> vor, wenn sich Risk Class, Foundation-Modell, Tools, Compute-Tier, Inputs, Outputs oder Intended Purpose ändern</>
            : <>The auto-classifier suggests <InlineCode>substantial</InlineCode> when risk class, foundation model, tools, compute tier, inputs, outputs or intended purpose change</>}
        </li>
        <li>
          {de
            ? <>Kosmetische Änderungen (Tags, Pricing, Name) werden als <InlineCode>non_substantial</InlineCode> markiert</>
            : <>Cosmetic changes (tags, pricing, name) are flagged as <InlineCode>non_substantial</InlineCode></>}
        </li>
        <li>
          {de
            ? "Der Provider kann den Vorschlag übersteuern und den Record als reassessed markieren, sobald eine frische Konformitätsbewertung erfolgt ist"
            : "The provider can override the suggestion and mark the record reassessed once a fresh conformity check is done"}
        </li>
        <li>
          {de
            ? "Manuelle Einträge unterstützen Training-Data-Swaps, Intended-Purpose-Updates und Oversight-Maßnahmen, die nicht über das Card-PUT laufen"
            : "Manual entries support training-data swaps, intended-purpose updates and oversight-measure changes that don't go through the card PUT"}
        </li>
      </ul>
      <CodeBlock
        code={`# ${de ? "Modifikationen für einen Agent auflisten" : "List modifications for an agent"}
curl -H "X-API-Key: af_your_key" \\
  "https://agents.renemurrell.de/v1/modifications?agent_id=credit-scorer-v1"

# ${de ? "Annex-IV-Addendum als PDF exportieren" : "Export Annex IV addendum PDF"}
curl -H "X-API-Key: af_your_key" \\
  "https://agents.renemurrell.de/v1/modifications/export/pdf/credit-scorer-v1" \\
  -o modifications.pdf`}
      />

      <H2 id="article-15">{de ? "Artikel 15: Genauigkeit und Sicherheit" : "Article 15: Accuracy & Security"}</H2>
      <P>
        {de
          ? "KI-Systeme müssen genau, robust und cybersicher sein."
          : "AI systems must be accurate, robust, and cybersecure."}
      </P>
      <DocTable
        headers={de ? ["Anforderung", "Umsetzung"] : ["Requirement", "Implementation"]}
        rows={[
          [
            de ? "Accuracy-Tracking" : "Accuracy tracking",
            de
              ? "5-Faktor-Trust-Score misst Zuverlässigkeit über die Zeit"
              : "5-factor trust score measures reliability over time",
          ],
          [
            de ? "Isolation" : "Isolation",
            de
              ? "Frische VM pro Execution, kein geteilter State zwischen Tenants"
              : "Fresh VM per execution, no shared state between tenants",
          ],
          [
            de ? "Secret-Sicherheit" : "Secret security",
            de
              ? "Drei-Pfad-Tenant-Isolation, base64-encoded, ephemeral"
              : "Three-path tenant isolation, base64-encoded, ephemeral",
          ],
          [
            de ? "Verhinderung von Datenleckage" : "Data leakage prevention",
            de
              ? "Server wird nach Execution zerstört, kein persistenter Speicher"
              : "Server destroyed after execution, no persistent storage",
          ],
          [
            de ? "Manipulations-Erkennung" : "Tamper detection",
            de ? "Ed25519-signierte Capability Cards" : "Ed25519 signed capability cards",
          ],
        ]}
      />

      <H2 id="your-obligations">{de ? "Deine Compliance-Pflichten" : "Your Compliance Obligations"}</H2>
      <P>
        {de
          ? "Die Plattform liefert die technische Infrastruktur. Als Deployer von KI-Agents hast du je nach Use Case ggf. zusätzliche Pflichten:"
          : "The platform provides the technical infrastructure. As a deployer of AI agents, you may have additional obligations depending on your use case:"}
      </P>
      <ul className="list-disc pl-6 space-y-1 text-sm text-[#94a3b8] mb-4">
        <li>
          {de
            ? "Bewerten, ob dein Use Case die High-Risk-Klassifikation auslöst"
            : "Assess whether your use case triggers high-risk classification"}
        </li>
        <li>
          {de
            ? "Records der KI-System-Nutzung pflegen (der Compliance-Export hilft dabei)"
            : "Maintain records of AI system usage (compliance export helps here)"}
        </li>
        <li>
          {de
            ? "End-User informieren, wenn sie mit KI-generierten Inhalten interagieren"
            : "Inform end users when they interact with AI-generated content"}
        </li>
        <li>
          {de
            ? "Schwere Vorfälle an die nationale KI-Behörde melden"
            : "Report serious incidents to your national AI authority"}
        </li>
      </ul>

      <Callout type="info" title={de ? "Keine Rechtsberatung" : "Not legal advice"}>
        {de
          ? "Diese Dokumentation beschreibt die technischen Compliance-Maßnahmen der Plattform. Für deine konkreten regulatorischen Pflichten solltest du juristischen Rat einholen."
          : "This documentation describes the platform's technical compliance measures. Consult legal counsel for your specific regulatory obligations."}
      </Callout>
    </div>
  );
}
