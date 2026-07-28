"""EU AI Act Art. 4 — AI Literacy modules and certificate generator.

Art. 4 has been in force since 2 February 2025 and requires providers and
deployers to ensure their staff have a sufficient level of AI literacy,
proportionate to their role and the AI systems they operate.

This module exposes three short training units (about 5 minutes each) and
a stateless certificate generator. Completion tracking lives in the
learner's browser; the certificate download serves as the evidence artefact
the deploying organisation hands to auditors.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

CERTIFICATE_SCHEMA_VERSION = "1"
REGULATION_REF = "EU 2024/1689 Art. 4"
PASS_THRESHOLD_PCT = 70

MODULES: list[dict[str, Any]] = [
    {
        "id": "m1-fundamentals",
        "title": "AI Agents: capabilities and limits",
        "summary": "What an AI agent is, what it can and cannot do, and where the boundaries of automation should sit.",
        "duration_minutes": 5,
        "slides": [
            {
                "title": "What is an AI agent?",
                "body": "An AI agent is a system that takes goals or tasks as input, plans a sequence of actions, and executes them autonomously using tools, models, and data. On this platform, every agent runs on a fresh isolated server, uses specified tools, and produces a documented output.",
            },
            {
                "title": "Capabilities vs. appearance",
                "body": "Agents can search, analyse, summarise, generate, and call APIs. They do not understand intent the way a human does. A fluent answer is not a correct answer. Always separate how confident the output sounds from how confident you are in the underlying process.",
            },
            {
                "title": "Common failure modes",
                "body": "Hallucinated facts, prompt injection via untrusted input, silent drift as models are updated, automation bias in the reviewer, and degraded performance on under-represented groups. Each of these is a known category, not an edge case.",
            },
            {
                "title": "Where humans stay in charge",
                "body": "Decisions that affect rights, money, employment, health, safety, or eligibility for services require a human in the loop with the authority to override. Art. 14 (human oversight) is not optional for high-risk systems.",
            },
        ],
        "questions": [
            {
                "id": "q1",
                "prompt": "A fluent, confident output from an AI agent is:",
                "options": [
                    "Evidence the answer is correct",
                    "A separate property from correctness; both must be checked",
                    "Always untrusted, regardless of the process",
                    "Required before an output can be used",
                ],
                "correct": 1,
            },
            {
                "id": "q2",
                "prompt": "Which is NOT a known failure mode of AI agents?",
                "options": [
                    "Hallucinating facts",
                    "Prompt injection via untrusted input",
                    "Deterministic deadlock between identical prompts",
                    "Automation bias in the reviewer",
                ],
                "correct": 2,
            },
            {
                "id": "q3",
                "prompt": "Under Art. 14, human oversight for high-risk systems is:",
                "options": [
                    "Recommended where practical",
                    "Required, with authority to override",
                    "Only required during initial deployment",
                    "Optional if the vendor provides a trust score",
                ],
                "correct": 1,
            },
        ],
    },
    {
        "id": "m2-eu-ai-act",
        "title": "The EU AI Act for deployers in 5 minutes",
        "summary": "Risk classes, deployer obligations, the August 2026 deadline, and how the platform maps to the regulation.",
        "duration_minutes": 6,
        "slides": [
            {
                "title": "The four risk classes",
                "body": "The Act classifies AI systems as prohibited (Art. 5), high-risk (Annex III), limited-risk (transparency only), and minimal-risk. High-risk covers HR, credit scoring, insurance pricing, hiring, education, and more. Provider obligations differ from deployer obligations: if you publish an agent, you are a provider; if you use one in your process, you are a deployer.",
            },
            {
                "title": "The timeline you need to know",
                "body": "Prohibited practices and AI literacy (Art. 4) apply since Feb 2025. GPAI obligations and the penalty framework since Aug 2025. High-risk obligations and deployer duties (Art. 26, 27) apply from 2 August 2026 under the current timeline. The proposed Digital Omnibus may shift that to late 2027, but conservative planning targets Aug 2026.",
            },
            {
                "title": "What deployers must do (Art. 26)",
                "body": "Use the system per the instructions for use, assign a competent human overseer, monitor outputs, keep automatic logs for at least 6 months, inform affected workers and customers, and cooperate with authorities on request.",
            },
            {
                "title": "FRIA (Art. 27)",
                "body": "A Fundamental Rights Impact Assessment is required before first use for public bodies, private actors delivering public services, credit scoring deployers, and life/health insurance pricing deployers. It documents the process, affected people, specific harm risks, oversight measures, and governance mechanisms. This platform scaffolds it for you.",
            },
            {
                "title": "Fines and the SME cap",
                "body": "Non-compliance penalties reach €35M or 7% of global turnover for prohibited practices, €15M or 3% for operator breaches, €7.5M or 1% for incorrect information. For SMEs, Art. 99(6) applies the lower of the two amounts, not the higher.",
            },
        ],
        "questions": [
            {
                "id": "q1",
                "prompt": "High-risk system obligations for deployers become applicable on:",
                "options": [
                    "2 February 2025",
                    "2 August 2025",
                    "2 August 2026",
                    "2 August 2028",
                ],
                "correct": 2,
            },
            {
                "id": "q2",
                "prompt": "Which use-case triggers a FRIA under Art. 27?",
                "options": [
                    "Generating marketing copy internally",
                    "Credit scoring of natural persons",
                    "Benchmarking open-source libraries",
                    "Summarising meeting transcripts",
                ],
                "correct": 1,
            },
            {
                "id": "q3",
                "prompt": "Minimum retention for automatic logs of high-risk systems under Art. 19 is:",
                "options": [
                    "30 days",
                    "90 days",
                    "6 months",
                    "2 years",
                ],
                "correct": 2,
            },
            {
                "id": "q4",
                "prompt": "An SME that deploys a high-risk AI system commits a serious operator breach. The fine ceiling under Art. 99(6) is:",
                "options": [
                    "Always €15M, regardless of turnover",
                    "Always 3% of global turnover",
                    "The higher of €15M or 3% of turnover",
                    "The lower of €15M or 3% of turnover",
                ],
                "correct": 3,
            },
        ],
    },
    {
        "id": "m3-oversight",
        "title": "Human oversight in practice",
        "summary": "Spot automation bias, set stop-criteria, handle incidents. A five-minute playbook for reviewers.",
        "duration_minutes": 5,
        "slides": [
            {
                "title": "Automation bias is the default",
                "body": "Reviewers confronted with confident automated output accept it more often than they should, even when they have the information to catch the error. The countermeasure is procedural: require reviewers to state a reason BEFORE seeing the agent's suggestion on a fraction of cases. That disrupts the confirmation loop.",
            },
            {
                "title": "Pre-defined stop criteria",
                "body": "Do not wait for a crisis to decide when to halt. Define in advance what triggers a stop: trust-score drop below X, error spike over Y%, affected-persons complaint volume over Z/week, or regulatory inquiry. Stop criteria must be written, named to a role, and testable.",
            },
            {
                "title": "Serious incident reporting (Art. 73)",
                "body": "Serious incidents must be reported to the national market surveillance authority within 15 days (standard), 10 days (critical infrastructure), or 2 days (widespread infringement). The clock starts when the provider becomes aware. Have a template ready; deciding the format during an incident is too late.",
            },
            {
                "title": "The reviewer's four-question check",
                "body": "Before acting on an agent output, the reviewer asks: (1) Is the input clean and the task in scope? (2) Does the output pattern match what I would expect? (3) Are the cited sources real and consistent? (4) Does the decision affect rights, money, or safety — and if so, is another reviewer required?",
            },
        ],
        "questions": [
            {
                "id": "q1",
                "prompt": "The most effective single counter to automation bias is:",
                "options": [
                    "Adding a bigger warning label to the UI",
                    "Having the reviewer state their own hypothesis before seeing the agent's output on a sample of cases",
                    "Training a second AI to review the first",
                    "Increasing the confidence threshold before showing output",
                ],
                "correct": 1,
            },
            {
                "id": "q2",
                "prompt": "The reporting deadline for a serious incident affecting critical infrastructure is:",
                "options": [
                    "2 days",
                    "10 days",
                    "15 days",
                    "30 days",
                ],
                "correct": 1,
            },
            {
                "id": "q3",
                "prompt": "Stop criteria should be:",
                "options": [
                    "Decided during the first incident to stay flexible",
                    "Set by the vendor, not the deployer",
                    "Written, named to a role, and testable in advance",
                    "Kept secret so the agent does not game them",
                ],
                "correct": 2,
            },
        ],
    },
]

_MODULES_BY_ID = {m["id"]: m for m in MODULES}


def list_modules() -> list[dict[str, Any]]:
    """Public module listing without answers."""
    return [
        {
            "id": m["id"],
            "title": m["title"],
            "summary": m["summary"],
            "duration_minutes": m["duration_minutes"],
            "slide_count": len(m["slides"]),
            "question_count": len(m["questions"]),
        }
        for m in MODULES
    ]


def get_module(module_id: str) -> dict[str, Any] | None:
    """Full module content including question options, but without correct answers."""
    module = _MODULES_BY_ID.get(module_id)
    if module is None:
        return None
    return {
        "id": module["id"],
        "title": module["title"],
        "summary": module["summary"],
        "duration_minutes": module["duration_minutes"],
        "slides": module["slides"],
        "questions": [
            {"id": q["id"], "prompt": q["prompt"], "options": q["options"]}
            for q in module["questions"]
        ],
    }


def score_answers(module_id: str, answers: dict[str, int]) -> dict[str, Any]:
    """Score a submitted set of answers. Returns score, pass flag, and per-question breakdown."""
    module = _MODULES_BY_ID.get(module_id)
    if module is None:
        raise ValueError(f"Unknown module: {module_id}")

    total = len(module["questions"])
    correct_count = 0
    breakdown = []
    for question in module["questions"]:
        qid = question["id"]
        submitted = answers.get(qid)
        is_correct = submitted == question["correct"]
        if is_correct:
            correct_count += 1
        breakdown.append(
            {
                "id": qid,
                "correct": question["correct"],
                "submitted": submitted,
                "is_correct": is_correct,
            }
        )

    score_pct = round((correct_count / total) * 100) if total else 0
    return {
        "module_id": module_id,
        "score_pct": score_pct,
        "correct_count": correct_count,
        "total": total,
        "pass_threshold_pct": PASS_THRESHOLD_PCT,
        "passed": score_pct >= PASS_THRESHOLD_PCT,
        "breakdown": breakdown,
    }


def _fingerprint(
    learner_name: str,
    learner_organisation: str,
    module_id: str,
    completed_at: str,
    score_pct: int,
) -> str:
    """Short deterministic id for the certificate, visible on the printout."""
    material = f"{learner_name}|{learner_organisation}|{module_id}|{completed_at}|{score_pct}"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return digest[:16]


def build_certificate(
    learner_name: str,
    learner_organisation: str,
    module_id: str,
    score: dict[str, Any],
    completed_at: datetime | None = None,
) -> dict[str, Any]:
    """Produce a machine-readable completion certificate."""
    module = _MODULES_BY_ID.get(module_id)
    if module is None:
        raise ValueError(f"Unknown module: {module_id}")
    ts = completed_at or datetime.now(timezone.utc)
    completed_iso = ts.isoformat()
    fingerprint = _fingerprint(
        learner_name, learner_organisation, module_id, completed_iso, score["score_pct"]
    )

    return {
        "schema_version": CERTIFICATE_SCHEMA_VERSION,
        "regulation": REGULATION_REF,
        "type": "ai_literacy_completion",
        "certificate_id": fingerprint,
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "learner": {
            "name": learner_name,
            "organisation": learner_organisation,
        },
        "module": {
            "id": module_id,
            "title": module["title"],
            "summary": module["summary"],
            "duration_minutes": module["duration_minutes"],
        },
        "result": {
            "completed_at": completed_iso,
            "score_pct": score["score_pct"],
            "correct_count": score["correct_count"],
            "total": score["total"],
            "pass_threshold_pct": score["pass_threshold_pct"],
            "passed": score["passed"],
        },
        "issuer": "agents.renemurrell.de",
    }


def certificate_to_markdown(cert: dict[str, Any]) -> str:
    learner = cert["learner"]
    module = cert["module"]
    result = cert["result"]
    passed = "PASSED" if result["passed"] else "NOT PASSED"

    return f"""# AI Literacy Completion Certificate

**Regulation:** {cert["regulation"]}
**Certificate ID:** `{cert["certificate_id"]}`
**Issued:** {cert["issued_at"]}
**Issuer:** {cert["issuer"]}

---

## Learner

- **Name:** {learner["name"]}
- **Organisation:** {learner["organisation"]}

## Module

- **Title:** {module["title"]}
- **Identifier:** `{module["id"]}`
- **Duration:** {module["duration_minutes"]} minutes
- **Summary:** {module["summary"]}

## Result

- **Completed at:** {result["completed_at"]}
- **Score:** {result["score_pct"]}% ({result["correct_count"]}/{result["total"]})
- **Pass threshold:** {result["pass_threshold_pct"]}%
- **Outcome:** {passed}

---

*This certificate evidences that the named learner completed the module and met
the platform's pass threshold. Under EU AI Act Art. 4, the deploying
organisation is responsible for ensuring its personnel have AI literacy
proportionate to their role. This document forms part of that evidence.*
"""
