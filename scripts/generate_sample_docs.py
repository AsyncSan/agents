"""Generate filled sample compliance documents per use-case domain.

Writes PDFs to ``frontend/public/samples/`` so that an anonymous evaluator
can download a polished artefact before signing up. These samples use
realistic inputs so they read like finished work, not scaffolds.

Run from the repo root:

    python scripts/generate_sample_docs.py
"""

from __future__ import annotations

from pathlib import Path

from agentforge.annex_iv import annex_iv_to_markdown, build_annex_iv_template
from agentforge.fria import build_fria_template, fria_to_markdown
from agentforge.manual_agent import ManualAgentInput, build_manual_agent
from agentforge.pdf import markdown_to_pdf

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLES_DIR = REPO_ROOT / "frontend" / "public" / "samples"

SCENARIOS = [
    {
        "slug": "credit-scoring",
        "title": "Credit scoring (fintech KMU)",
        "spec": ManualAgentInput(
            name="Retail Credit Risk Scorer",
            version=3,
            risk_class="high",
            description=(
                "Evaluates consumer credit applications for a German retail bank."
                " Inputs an application JSON (demographics, employment, income,"
                " existing obligations) and returns a PD score plus recommendation."
            ),
            domain="fintech",
            model="anthropic/claude-sonnet-4-6",
            tools=["sql"],
            inputs=[
                {"name": "application", "type": "object", "required": True},
            ],
            outputs=[
                {"name": "score.json", "type": "json", "guaranteed": True},
            ],
        ),
        "fria_inputs": {
            "use_case_key": "credit_scoring",
            "deployer_organisation": "Acme Bank GmbH",
            "deployer_contact": "Head of Compliance, compliance@acme.example",
            "deployer_process_summary": (
                "Loan officers receive an automated risk score for each incoming"
                " consumer credit application. Scores under 0.3 are auto-rejected"
                " after a mandatory human review; scores above 0.7 are auto-approved"
                " with a human spot-check on 10% of cases."
            ),
            "intended_duration": "Ongoing from 2026-09-01",
            "frequency": "Every incoming credit application (c. 12,000/month)",
            "estimated_volume_per_month": "~12,000 affected applicants",
            "affected_categories": [
                "Consumer credit applicants in Germany",
                "Existing card holders under portfolio review",
            ],
            "vulnerable_groups": [
                "Applicants over 65",
                "Applicants with limited credit history (new residents, young adults)",
                "Applicants with language-barrier markers",
            ],
            "potential_harms": [
                "Disparate impact on protected characteristics via correlated features",
                "Erroneous credit rejection leading to economic harm",
                "Opacity reducing applicants' right to contest adverse decisions",
            ],
            "severity_assessment": "Medium for individual harm, high in aggregate if a subgroup is systematically under-served.",
            "likelihood_assessment": "Low for any single decision, medium for systemic drift over time without monitoring.",
            "deployer_oversight_measures": [
                "Named oversight officer reviews 10% of outcomes daily",
                "All 'decline' decisions require human sign-off before communication",
                "Monthly bias audit across age, gender, and residency buckets",
            ],
            "internal_governance": [
                "Monthly review with Chief Compliance Officer + Head of Risk",
                "Stop-deployment authority: Head of Risk",
                "Quarterly review with Management Board",
            ],
            "complaint_mechanism": (
                "In-branch form + online portal; written response within 14 days;"
                " right to human review referenced in decision letters."
            ),
            "authority_reporting": (
                "Serious incidents escalated via Art. 73 pipeline at agents.renemurrell.de;"
                " MSA of record is BNetzA."
            ),
            "dpia_reference": "DPIA-2026-001 (internal reference)",
        },
        "annex_inputs": {
            "provider_name": "Acme Bank GmbH",
            "provider_contact": "ai-governance@acme.example",
            "development_methodology": (
                "Shadow deployment on 3 months of historical applications before"
                " live cutover. Weekly ML-ops review. Change-control board approves"
                " every card-version increment."
            ),
            "training_data_summary": (
                "Foundation model used without fine-tuning. Prompts parameterised with"
                " application fields only; no historical outcome data sent to the LLM."
            ),
            "known_limitations": [
                "Degraded performance on applications with missing income data",
                "Not validated for non-retail (SME) lending",
            ],
            "metric_rationale": (
                "Approval/denial accuracy vs. a held-out human-reviewed benchmark,"
                " alongside demographic parity checks, are the most load-bearing metrics"
                " for our fairness-first framing."
            ),
            "rms_owner": "Head of AI Governance",
            "identified_risks": [
                "Disparate impact",
                "Prompt injection via free-text application notes",
                "Model drift after retraining of underlying LLM",
            ],
            "mitigation_measures": [
                "Input sanitisation before prompt construction",
                "Fortnightly fairness dashboard review",
                "Immediate rollback if trust score drops >0.15",
            ],
            "review_cadence": "monthly",
            "harmonised_standards_applied": [
                "ISO/IEC 42001 as baseline",
                "EN ISO 9001 for engineering quality",
            ],
        },
    },
    {
        "slug": "hr-hiring",
        "title": "HR CV screening (HR-Tech KMU)",
        "spec": ManualAgentInput(
            name="Role-match CV Screener",
            version=2,
            risk_class="high",
            description=(
                "Ranks incoming CVs against a job specification, producing a match"
                " score and explanatory snippets. Used to triage large applicant"
                " pools before human recruiters review shortlisted candidates."
            ),
            domain="hr",
            model="anthropic/claude-sonnet-4-6",
            tools=["shell"],
            inputs=[
                {"name": "cv_text", "type": "string", "required": True},
                {"name": "job_spec", "type": "string", "required": True},
            ],
            outputs=[
                {"name": "score.json", "type": "json", "guaranteed": True},
                {"name": "rationale.md", "type": "markdown", "guaranteed": False},
            ],
        ),
        "fria_inputs": {
            "use_case_key": "other_high_risk",
            "deployer_organisation": "Nordlicht HR GmbH",
            "deployer_contact": "DPO, dpo@nordlicht.example",
            "deployer_process_summary": (
                "Recruiters bulk-upload CV PDFs against a job posting. The system"
                " returns a ranked list; recruiters shortlist manually from the top"
                " 30%. No candidate is rejected without human review."
            ),
            "frequency": "Daily during active hiring cycles",
            "estimated_volume_per_month": "~800 candidates across 8 open roles",
            "affected_categories": ["Job applicants in the DACH region"],
            "vulnerable_groups": [
                "Applicants with non-native German language CVs",
                "Applicants with career gaps (parental leave, caregiving, illness)",
                "Applicants over 50",
            ],
            "potential_harms": [
                "Discriminatory ranking on age, gender, ethnicity correlates",
                "Reinforcement of historical hiring bias in the training data",
                "Loss of qualified candidates who do not fit the model's expected CV format",
            ],
            "deployer_oversight_measures": [
                "Mandatory human review of top 30% of ranked candidates",
                "Quarterly shortlist audit comparing model ranking to final hires by demographic",
                "Candidate right to request human-only review on demand",
            ],
            "internal_governance": [
                "Bi-weekly review with works council representative",
                "Quarterly bias audit presented to management",
                "Stop-deployment authority: DPO",
            ],
            "complaint_mechanism": (
                "Candidates can request full human review via email; 10-day response."
            ),
            "dpia_reference": "DPIA-HIRE-2026-04",
        },
        "annex_inputs": {
            "provider_name": "Nordlicht HR GmbH",
            "provider_contact": "ai-governance@nordlicht.example",
            "known_limitations": [
                "Optimised for tech and administrative roles; less reliable for trades",
                "Sensitive to CV formatting; non-standard layouts may score lower",
            ],
            "identified_risks": [
                "Disparate impact across demographic groups",
                "Prompt injection via CV content",
            ],
            "mitigation_measures": [
                "Monthly audit against synthesised CVs matched on skill but varied on demographics",
                "Input sanitisation and token-cap on CV excerpts sent to the LLM",
            ],
        },
    },
    {
        "slug": "insurance-pricing",
        "title": "Health insurance pricing (InsurTech KMU)",
        "spec": ManualAgentInput(
            name="Premium Tier Recommender",
            version=1,
            risk_class="high",
            description=(
                "Suggests premium tiers for health-insurance policy renewals based"
                " on anonymised claims history and declared lifestyle factors."
                " A human underwriter approves the final tier."
            ),
            domain="insurtech",
            model="anthropic/claude-sonnet-4-6",
            tools=["sql"],
            inputs=[
                {"name": "policy_id", "type": "string", "required": True},
                {"name": "renewal_context", "type": "object", "required": True},
            ],
            outputs=[{"name": "tier_recommendation.json", "type": "json", "guaranteed": True}],
        ),
        "fria_inputs": {
            "use_case_key": "insurance_pricing",
            "deployer_organisation": "Alpenversicherung AG",
            "deployer_process_summary": (
                "At renewal, the system suggests a premium tier band. An underwriter"
                " must approve before the tier communicates to the policyholder."
            ),
            "frequency": "Per policy renewal (~4,000/month)",
            "estimated_volume_per_month": "~4,000 policyholders",
            "affected_categories": ["Health insurance policyholders"],
            "vulnerable_groups": [
                "Policyholders with chronic conditions",
                "Elderly policyholders",
                "Pregnant or post-partum policyholders",
            ],
            "potential_harms": [
                "Disparate pricing on health-adjacent features",
                "Loss of coverage if upward tier moves are unaffordable",
                "Chilling effect on claims behaviour",
            ],
            "deployer_oversight_measures": [
                "All upward tier moves require human underwriter approval",
                "Monthly bias check on approvals across age + condition buckets",
                "Annual review with external actuarial board",
            ],
        },
        "annex_inputs": {
            "provider_name": "Alpenversicherung AG",
        },
    },
    {
        "slug": "security-audit",
        "title": "Automated codebase security audit (engineering team)",
        "spec": ManualAgentInput(
            name="Codebase Security Audit",
            version=2,
            risk_class="limited",
            description=(
                "Runs automated SAST, dependency, and secret-leak scans on a"
                " codebase and summarises findings in a structured report."
            ),
            domain="security",
            model="anthropic/claude-sonnet-4-6",
            tools=["shell"],
            inputs=[{"name": "repo_url", "type": "string", "required": True}],
            outputs=[{"name": "output.md", "type": "markdown", "guaranteed": True}],
        ),
        "fria_inputs": {
            "use_case_key": "other_high_risk",
            "deployer_organisation": "Example Engineering GmbH",
            "deployer_process_summary": (
                "Weekly scheduled scan of all active repositories; findings are"
                " routed to the owning team via Slack."
            ),
            "frequency": "Weekly per repository",
            "affected_categories": [
                "No direct personal-data processing; engineering data only",
            ],
            "potential_harms": [
                "Missed vulnerability (false negative)",
                "Exposure of sensitive scan content if report is mis-routed",
            ],
            "deployer_oversight_measures": [
                "Security lead reviews critical findings before dissemination",
                "Scan reports never leave internal infrastructure",
            ],
        },
        "annex_inputs": {
            "provider_name": "SecureAudit UG (haftungsbeschränkt)",
        },
    },
]


def _write_pdf(path: Path, md_text: str, title: str) -> None:
    pdf_bytes = markdown_to_pdf(md_text, title=title)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pdf_bytes)
    print(f"  {path.name}: {len(pdf_bytes):,} bytes")


def main() -> None:
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    index: list[dict[str, str]] = []

    for scenario in SCENARIOS:
        print(f"== {scenario['title']}")
        agent = build_manual_agent(scenario["spec"])
        slug = scenario["slug"]

        fria_doc = build_fria_template(agent, scenario["fria_inputs"])
        fria_md = fria_to_markdown(fria_doc)
        _write_pdf(
            SAMPLES_DIR / f"fria-{slug}.pdf",
            fria_md,
            f"FRIA sample · {scenario['title']}",
        )

        annex_doc = build_annex_iv_template(
            agent, scenario["annex_inputs"], variant="full"
        )
        annex_md = annex_iv_to_markdown(annex_doc)
        _write_pdf(
            SAMPLES_DIR / f"annex-iv-{slug}.pdf",
            annex_md,
            f"Annex IV sample · {scenario['title']}",
        )

        index.append(
            {
                "slug": slug,
                "title": scenario["title"],
                "fria": f"fria-{slug}.pdf",
                "annex_iv": f"annex-iv-{slug}.pdf",
            }
        )

    import json

    (SAMPLES_DIR / "index.json").write_text(json.dumps(index, indent=2))
    print(f"\nWrote index.json with {len(index)} scenarios.")


if __name__ == "__main__":
    main()
