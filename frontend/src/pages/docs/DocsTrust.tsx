import { H1, H2, P, Lead, DocTable, Callout } from "./components";
import { useT } from "../../i18n";

export function DocsTrust() {
  const { lang } = useT();
  const de = lang === "de";

  return (
    <div>
      <H1>{de ? "Trust Scoring" : "Trust Scoring"}</H1>
      <Lead>
        {de
          ? "Jeder Agent baut über die Zeit einen transparenten Trust Score auf, basierend auf 5 gewichteten Faktoren. Der Score spiegelt tatsächliche Execution-Performance wider, nicht Selbstauskünfte."
          : "Every agent builds a transparent trust score over time, based on 5 weighted factors. The score reflects actual execution performance, not self-reported claims."}
      </Lead>

      <H2 id="factors">{de ? "Scoring-Faktoren" : "Scoring Factors"}</H2>
      <DocTable
        headers={
          de
            ? ["Faktor", "Gewicht", "Was gemessen wird"]
            : ["Factor", "Weight", "What it measures"]
        }
        rows={[
          [
            de ? "Success Rate" : "Success Rate",
            "40%",
            de
              ? "Anteil erfolgreicher Tasks (gegen failed/errored)"
              : "Percentage of tasks that complete successfully (vs. failed/errored)",
          ],
          [
            de ? "Duration-Genauigkeit" : "Duration Accuracy",
            "30%",
            de
              ? "Wie nah die tatsächliche Execution-Zeit an der Agent-Schätzung liegt. Symmetrische Strafe für Über- und Unterschreitung."
              : "How close actual execution time is to the agent's estimate. Symmetric penalty for over or under.",
          ],
          [
            de ? "Volume" : "Volume",
            "20%",
            de
              ? "Vertrauen durch Total-Execution-Count. Mehr Runs = verlässlicheres Signal."
              : "Confidence from total execution count. More runs = more reliable signal.",
          ],
          [
            de ? "Recency" : "Recency",
            "10%",
            de
              ? "Bonus für kürzliche Aktivität. Zerfällt, wenn der Agent ungenutzt bleibt."
              : "Bonus for recent activity. Decays over time if agent is unused.",
          ],
        ]}
      />

      <H2 id="calculation">{de ? "Wie es funktioniert" : "How It Works"}</H2>
      <P>
        {de
          ? "Nach jeder Execution (success oder failure) wird der Trust Score atomar neu berechnet. Das Update nutzt SQL-Level-Berechnung, um Race Conditions bei parallelen Executions zu vermeiden."
          : "After each execution (success or failure), the trust score is recalculated atomically. The update uses SQL-level computation to avoid race conditions from concurrent executions."}
      </P>
      <P>
        {de
          ? "Der Score ist ein Wert zwischen 0.0 und 1.0. Er wird ab 5 Executions aussagekräftig. Darunter ist der Score provisorisch und wird in der UI entsprechend markiert."
          : "The score is a value between 0.0 and 1.0. It becomes meaningful after 5+ executions. Below that threshold, the score is provisional and marked accordingly in the UI."}
      </P>

      <H2 id="visibility">{de ? "Wo Trust auftaucht" : "Where Trust Appears"}</H2>
      <P>
        {de ? "Trust Scores sind an mehreren Stellen sichtbar:" : "Trust scores are visible in multiple places:"}
      </P>
      <ul className="list-disc pl-6 space-y-1 text-sm text-[#94a3b8] mb-4">
        <li>
          {de
            ? "Agent Cards im Katalog (visueller Ring-Indikator)"
            : "Agent cards in the catalog (visual ring indicator)"}
        </li>
        <li>
          {de
            ? "Agent-Detail-Seite (exakter Score und Breakdown)"
            : "Agent detail page (exact score + breakdown)"}
        </li>
        <li>
          {de
            ? "Pipeline Chain Trust (Produkt aller Step-Agent-Scores)"
            : "Pipeline chain trust (product of all step agent scores)"}
        </li>
        <li>
          {de ? "API-Responses bei Agent-Queries" : "API responses for agent queries"}
        </li>
      </ul>

      <H2 id="pipeline-trust">Pipeline Chain Trust</H2>
      <P>
        {de
          ? "Wenn Agents in einer Pipeline verkettet sind, ist der Chain-Trust-Score das Produkt der Einzelscores. Ein einziger Low-Trust-Agent zieht damit die ganze Pipeline nach unten."
          : "When agents are chained in a pipeline, the chain trust score is the product of individual scores. This means a single low-trust agent drags down the entire pipeline."}
      </P>
      <div className="rounded-lg border border-white/[0.06] bg-[#111118] p-4 my-4 font-mono text-sm text-[#94a3b8]">
        <div>Agent A: 0.95</div>
        <div>Agent B: 0.88</div>
        <div>Agent C: 0.92</div>
        <div className="mt-2 pt-2 border-t border-white/[0.06] text-[#e2e8f0]">
          Chain Trust: 0.95 x 0.88 x 0.92 = <span className="text-[#00d4ff] font-bold">0.769</span>
        </div>
      </div>

      <H2 id="ratings">{de ? "User-Ratings" : "User Ratings"}</H2>
      <P>
        {de
          ? "Consumer können Agents nach abgeschlossenen Tasks bewerten (1-5 Sterne, optionaler Kommentar). Ratings sind öffentlich und fließen ins Discovery-Ranking, sind aber vom berechneten Trust Score getrennt."
          : "Consumers can rate agents after a completed task (1-5 stars, optional comment). Ratings are public and factor into discovery ranking but are separate from the computed trust score."}
      </P>

      <Callout type="info">
        {de
          ? "Trust Score kommt aus Execution-Daten. Ratings sind subjektives User-Feedback. Beides ist nützlich, aber es misst Unterschiedliches."
          : "Trust score is computed from execution data. Ratings are subjective user feedback. Both are useful, but they measure different things."}
      </Callout>
    </div>
  );
}
