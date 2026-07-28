"""EU AI Act Art. 47 + Annex V — EU Declaration of Conformity.

Art. 47 requires providers of high-risk systems to draw up a written,
machine-readable, physical or electronically signed EU declaration of
conformity for each AI system before placing it on the market or putting
it into service. The declaration must be kept at the disposal of the
national competent authorities for 10 years after the system has been
placed on the market or put into service.

Annex V enumerates the 9 mandatory data points. This module builds the
declaration from the agent capability card and provider inputs, then
lets the caller download it as JSON / Markdown / PDF for signature and
retention.

CE-marking (Art. 48) is embedded as a checkbox block in the declaration
since for digital-only systems the marking is affixed electronically in
accompanying documentation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agentforge.models.agent import Agent

SCHEMA_VERSION = "1"
REGULATION_REF = "EU 2024/1689 Art. 47, Annex V"

DEFAULT_HARMONISED_STANDARDS = [
    "ISO/IEC 42001:2023 (AI Management Systems)",
    "ISO/IEC 23894:2023 (AI Risk Management)",
    "ISO/IEC 5259 (Data Quality for Analytics and ML)",
]


def _processes_personal_data(agent: Agent, inputs: dict[str, Any]) -> bool:
    if "processes_personal_data" in inputs:
        return bool(inputs["processes_personal_data"])
    card = agent.card or {}
    capabilities = card.get("capabilities", {}) if isinstance(card, dict) else {}
    domain = (capabilities.get("domain") or "").lower()
    return domain in {"fintech", "hr", "hr-tech", "healthtech", "legaltech", "insurtech"}


def build_declaration(
    agent: Agent,
    provider_inputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compose the Annex V declaration of conformity for one agent."""
    inputs = provider_inputs or {}
    card = agent.card or {}
    capabilities = card.get("capabilities", {}) if isinstance(card, dict) else {}

    processes_pii = _processes_personal_data(agent, inputs)
    standards = inputs.get("harmonised_standards") or list(DEFAULT_HARMONISED_STANDARDS)
    notified_body_required = (
        agent.risk_class == "high" and bool(inputs.get("notified_body_required", False))
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "regulation": REGULATION_REF,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agent": {
            "id": agent.id,
            "name": agent.name,
            "version": agent.version,
            "risk_class": agent.risk_class,
        },
        # Annex V fields (numbering follows the regulation)
        "annex_v_1_system_identification": {
            "name": agent.name,
            "type": capabilities.get("domain") or "AI agent",
            "unique_reference": agent.id,
            "traceability_id": f"capability-card@v{agent.version}",
            "version": f"v{agent.version}",
            "additional_references": inputs.get("additional_references") or [],
        },
        "annex_v_2_provider": {
            "name": inputs.get("provider_name")
            or "[PROVIDER: legal name of the provider]",
            "address": inputs.get("provider_address")
            or "[PROVIDER: registered address]",
            "authorised_representative": {
                "applicable": bool(inputs.get("auth_rep_required", False)),
                "name": inputs.get("auth_rep_name")
                or (
                    "[PROVIDER: EU authorised representative per Art. 22]"
                    if inputs.get("auth_rep_required")
                    else "Not applicable (EU-established provider)"
                ),
                "address": inputs.get("auth_rep_address"),
            },
        },
        "annex_v_3_sole_responsibility_statement": (
            "This EU declaration of conformity is issued under the sole "
            "responsibility of the provider named in section 2."
        ),
        "annex_v_4_conformity_statement": (
            "The AI system described in section 1 is in conformity with "
            "Regulation (EU) 2024/1689 (EU AI Act)"
            + (
                ", with Regulation (EU) 2016/679 (GDPR), and with any other Union law "
                "providing for the issuing of this declaration that is applicable to "
                "the intended purpose."
                if processes_pii
                else ", and with any other Union law providing for the issuing of "
                "this declaration that is applicable to the intended purpose."
            )
        ),
        "annex_v_5_data_protection_statement": (
            {
                "applicable": True,
                "text": (
                    "The AI system processes personal data and complies with "
                    "Regulation (EU) 2016/679 (GDPR), Regulation (EU) 2018/1725, and "
                    "Directive (EU) 2016/680 where applicable."
                ),
                "dpo_contact": inputs.get("dpo_contact")
                or "[PROVIDER: DPO contact, required where Art. 37 GDPR applies]",
            }
            if processes_pii
            else {
                "applicable": False,
                "text": (
                    "The AI system does not process personal data within the meaning "
                    "of Regulation (EU) 2016/679."
                ),
            }
        ),
        "annex_v_6_harmonised_standards": {
            "standards_applied": standards,
            "common_specifications": inputs.get("common_specifications") or [],
            "notes": inputs.get("standards_notes")
            or "Where harmonised standards under Art. 40 are not yet published, "
            "the closest applicable ISO/IEC baseline standards are listed.",
        },
        "annex_v_7_notified_body": (
            {
                "applicable": True,
                "name": inputs.get("notified_body_name")
                or "[PROVIDER: notified body name]",
                "identification_number": inputs.get("notified_body_id")
                or "[PROVIDER: NB 4-digit number]",
                "assessment_procedure": inputs.get("assessment_procedure")
                or "Annex VII (conformity assessment based on assessment of the "
                "quality management system and assessment of the technical "
                "documentation).",
                "certificate_reference": inputs.get("certificate_reference")
                or "[PROVIDER: certificate number and issue date]",
            }
            if notified_body_required
            else {
                "applicable": False,
                "rationale": (
                    "Self-assessment under Annex VI (internal control) is permitted "
                    "for this system. No notified body involvement required."
                ),
            }
        ),
        "annex_v_8_signature": {
            "place": inputs.get("signature_place")
            or "[PROVIDER: place of issue, e.g. Berlin]",
            "date": inputs.get("signature_date")
            or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "signatory_name": inputs.get("signatory_name")
            or "[PROVIDER: full name of signing person]",
            "signatory_function": inputs.get("signatory_function")
            or "[PROVIDER: role, e.g. Managing Director]",
            "signed_on_behalf_of": inputs.get("signed_on_behalf_of")
            or inputs.get("provider_name")
            or "[PROVIDER: provider organisation]",
            "signature": inputs.get("signature")
            or "[PROVIDER: physical or electronic signature]",
        },
        "annex_v_9_language": {
            "drawn_up_in": inputs.get("language") or "en",
            "translations_available": inputs.get("translations_available")
            or ["de"],
            "notice": (
                "Art. 47(2): the declaration must be translated into a language "
                "easily understood by the competent authorities of each Member State "
                "where the system is placed on the market."
            ),
        },
        # Art. 48 CE-marking evidence block
        "ce_marking": {
            "affixed": bool(inputs.get("ce_marking_affixed", False)),
            "affixed_electronically": bool(
                inputs.get("ce_marking_affixed_electronically", True)
            ),
            "notified_body_number_alongside": notified_body_required,
            "visibility_statement": (
                "CE marking is affixed in machine-readable form in the Annex IV "
                "technical documentation bundle, on the agent card displayed in the "
                "runtime catalogue, and in this declaration. It is legible in the "
                "electronic form in which the system is placed on the market per "
                "Art. 48(4)."
            ),
        },
        "retention_notice": (
            "Retain this declaration at the disposal of the national competent "
            "authorities for 10 years after the AI system has been placed on the "
            "market or put into service (Art. 47(1))."
        ),
        "status": "draft",
    }


def declaration_to_markdown(record: dict[str, Any]) -> str:
    a = record["agent"]
    ident = record["annex_v_1_system_identification"]
    provider = record["annex_v_2_provider"]
    auth_rep = provider["authorised_representative"]
    pii = record["annex_v_5_data_protection_statement"]
    standards = record["annex_v_6_harmonised_standards"]
    nb = record["annex_v_7_notified_body"]
    sig = record["annex_v_8_signature"]
    lang = record["annex_v_9_language"]
    ce = record["ce_marking"]

    def _bullets(items: Any, empty: str = "- (none)") -> str:
        if isinstance(items, list):
            if not items:
                return empty
            return "\n".join(f"- {item}" for item in items)
        return f"- {items}"

    nb_block = (
        f"""

## 7. Notified body

- **Applicable:** Yes
- **Name:** {nb["name"]}
- **Identification number:** {nb["identification_number"]}
- **Assessment procedure:** {nb["assessment_procedure"]}
- **Certificate reference:** {nb["certificate_reference"]}
"""
        if nb["applicable"]
        else f"""

## 7. Notified body

- **Applicable:** No
- **Rationale:** {nb["rationale"]}
"""
    )

    pii_block = (
        f"""

## 5. Data protection statement

{pii["text"]}

**DPO contact:** {pii.get("dpo_contact") or "-"}
"""
        if pii["applicable"]
        else f"""

## 5. Data protection statement

{pii["text"]}
"""
    )

    return f"""# EU Declaration of Conformity (Annex V)

**Regulation:** {record["regulation"]}
**Generated:** {record["generated_at"]}
**Status:** {record["status"]}

**System:** `{a["id"]}` · {a["name"]} · v{a["version"]} · risk class `{a["risk_class"]}`

---

## 1. System identification

- **Name:** {ident["name"]}
- **Type:** {ident["type"]}
- **Unique reference:** `{ident["unique_reference"]}`
- **Traceability ID:** `{ident["traceability_id"]}`
- **Version:** {ident["version"]}
- **Additional references:** {", ".join(ident["additional_references"] or []) or "-"}

## 2. Provider

- **Name:** {provider["name"]}
- **Address:** {provider["address"]}

**Authorised representative:**
- **Applicable:** {"Yes" if auth_rep["applicable"] else "No"}
- **Name:** {auth_rep["name"]}
- **Address:** {auth_rep.get("address") or "-"}

## 3. Sole responsibility

{record["annex_v_3_sole_responsibility_statement"]}

## 4. Conformity statement

{record["annex_v_4_conformity_statement"]}
{pii_block}

## 6. Harmonised standards and common specifications

**Harmonised standards applied:**
{_bullets(standards["standards_applied"])}

**Common specifications:**
{_bullets(standards["common_specifications"])}

**Notes:** {standards["notes"]}
{nb_block}

## 8. Signature

- **Place:** {sig["place"]}
- **Date:** {sig["date"]}
- **Signatory name:** {sig["signatory_name"]}
- **Signatory function:** {sig["signatory_function"]}
- **Signed on behalf of:** {sig["signed_on_behalf_of"]}
- **Signature:** {sig["signature"]}

## 9. Language

- **Drawn up in:** `{lang["drawn_up_in"]}`
- **Translations available:** {", ".join(lang["translations_available"] or []) or "-"}

*{lang["notice"]}*

---

## CE marking (Art. 48)

- **Affixed:** {"Yes" if ce["affixed"] else "No"}
- **Affixed electronically:** {"Yes" if ce["affixed_electronically"] else "No"}
- **Notified body number alongside CE:** {"Yes" if ce["notified_body_number_alongside"] else "No"}

{ce["visibility_statement"]}

---

*{record["retention_notice"]} Generated by the agents.renemurrell.de
declaration scaffolding engine. Sections marked `[PROVIDER: …]` must be
completed by the provider before signature.*
"""
