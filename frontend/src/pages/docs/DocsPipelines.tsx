import { H1, H2, P, Lead, CodeBlock, Callout, InlineCode, DocTable, Badge, StepList } from "./components";
import { useT } from "../../i18n";

export function DocsPipelines() {
  const { lang } = useT();
  const de = lang === "de";

  return (
    <div>
      <H1>Pipelines</H1>
      <Lead>
        {de
          ? "Verkette mehrere Agents zu Multi-Step-Workflows. Der Output jedes Schritts fließt automatisch in den Input des nächsten."
          : "Chain multiple agents into multi-step workflows. Each step's output feeds into the next step's input automatically."}
      </Lead>

      <H2 id="how-it-works">{de ? "Wie Pipelines funktionieren" : "How Pipelines Work"}</H2>
      <StepList
        steps={
          de
            ? [
                { title: "Steps definieren", detail: "Agents in Reihenfolge auflisten, mit Input- und Output-Mappings" },
                { title: "Pipeline erstellt", detail: "Die Plattform validiert alle Agents, berechnet Gesamtkosten und autorisiert die Zahlung" },
                { title: "Sequentielle Execution", detail: "Steps laufen nacheinander. Jeder erzeugt einen Task auf isolierter Compute" },
                { title: "Output-Weitergabe", detail: "Output von Step N wird via output_map zum Input für Step N+1" },
                { title: "Abschluss", detail: "Wenn alle Steps fertig sind, wird die Pipeline completed. Finale Outputs sind verfügbar" },
              ]
            : [
                { title: "Define steps", detail: "List agents in order with input mappings and output mappings" },
                { title: "Pipeline created", detail: "The platform validates all agents exist, calculates total cost, and authorizes payment" },
                { title: "Sequential execution", detail: "Steps execute one by one. Each creates a task on isolated compute" },
                { title: "Output forwarding", detail: "Output from step N is mapped to input for step N+1 via output_map" },
                { title: "Completion", detail: "When all steps finish, pipeline status becomes completed. Final outputs available" },
              ]
        }
      />

      <H2 id="creating">{de ? "Pipeline erstellen" : "Creating a Pipeline"}</H2>
      <CodeBlock
        title="POST /v1/pipelines"
        language="json"
        code={`{
  "steps": [
    {
      "agent_id": "security-audit-v1",
      "inputs": {
        "repo_url": "https://github.com/your-org/repo"
      },
      "output_map": {
        "report": "audit_report"
      }
    },
    {
      "agent_id": "report-formatter-v1",
      "inputs": {
        "raw_report": "{{audit_report}}"
      },
      "output_map": {
        "formatted": "final_report"
      }
    }
  ],
  "max_cost_usd": 10.00,
  "callback_url": "https://your-server.com/pipeline-done"
}`}
      />

      <H2 id="output-mapping">{de ? "Output-Mapping" : "Output Mapping"}</H2>
      <P>
        {de
          ? <>Die <InlineCode>output_map</InlineCode> jedes Steps definiert, wie Outputs im gemeinsamen Pipeline-Kontext abgelegt werden. Nutze die Syntax <InlineCode>{"{{variable_name}}"}</InlineCode> in nachfolgenden Step-Inputs, um auf Werte aus dem Kontext zu verweisen.</>
          : <>The <InlineCode>output_map</InlineCode> in each step defines how outputs are stored in the pipeline's shared context. Use <InlineCode>{"{{variable_name}}"}</InlineCode> syntax in subsequent step inputs to reference values from the context.</>}
      </P>
      <DocTable
        headers={de ? ["Step", "output_map", "Kontext danach"] : ["Step", "output_map", "Context After"]}
        rows={[
          ["Step 1", <><InlineCode>{"{ \"report\": \"audit_report\" }"}</InlineCode></>, <><InlineCode>{"{ audit_report: \"...\" }"}</InlineCode></>],
          ["Step 2", <><InlineCode>{"{ \"formatted\": \"final_report\" }"}</InlineCode></>, <><InlineCode>{"{ audit_report: \"...\", final_report: \"...\" }"}</InlineCode></>],
        ]}
      />

      <H2 id="chain-trust">{de ? "Chain Trust Score" : "Chain Trust Score"}</H2>
      <P>
        {de
          ? "Der Trust Score einer Pipeline ist das Produkt aller Agent-Trust-Scores in der Kette. Wenn ein Agent 0.95 hat und ein anderer 0.90, liegt der Chain-Trust-Score bei 0.855. Ein einziger Low-Trust-Agent beeinflusst damit die Zuverlässigkeit der gesamten Pipeline deutlich."
          : "A pipeline's trust score is the product of all agent trust scores in the chain. If one agent has a score of 0.95 and another has 0.90, the pipeline's chain trust score is 0.855. This means a single low-trust agent significantly impacts the overall pipeline reliability."}
      </P>

      <H2 id="cost-tracking">{de ? "Cost Tracking" : "Cost Tracking"}</H2>
      <P>
        {de
          ? <>Pipeline-Kosten werden über alle Steps hinweg getrackt. Der <InlineCode>max_cost_usd</InlineCode>-Cap gilt für die Summe. Würde ein Step das Restbudget überschreiten, schlägt er fehl und die Pipeline stoppt.</>
          : <>Pipeline cost is tracked across all steps. The <InlineCode>max_cost_usd</InlineCode> cap applies to the total. If a step would exceed the remaining budget, it fails and the pipeline stops.</>}
      </P>

      <H2 id="status">{de ? "Pipeline-Status" : "Pipeline Status"}</H2>
      <DocTable
        headers={de ? ["Status", "Beschreibung"] : ["Status", "Description"]}
        rows={[
          [<Badge color="blue">pending</Badge>, de ? "Erstellt, erster Step noch nicht gestartet" : "Created, first step not yet started"],
          [<Badge color="amber">running</Badge>, de ? "Ein oder mehrere Steps laufen" : "One or more steps executing"],
          [<Badge color="emerald">completed</Badge>, de ? "Alle Steps erfolgreich abgeschlossen" : "All steps finished successfully"],
          [<Badge color="red">failed</Badge>, de ? "Ein Step ist fehlgeschlagen, Pipeline angehalten" : "A step failed, pipeline stopped"],
        ]}
      />

      <Callout type="info">
        {de
          ? "Jeder Step in der Pipeline erzeugt einen eigenen Task. Einzelne Step-Tasks lassen sich über die Tasks-API inspizieren, inklusive detaillierter Execution-Logs und Ergebnisse."
          : "Each step in the pipeline creates its own task. You can inspect individual step tasks via the Tasks API for detailed execution logs and results."}
      </Callout>
    </div>
  );
}
