"""EU AI Act Art. 49 — EU database registration (Annex VIII).

Art. 49 requires providers of high-risk systems to register themselves and
each system in the EU database before placing it on the market. Art. 6(3)
exemptions (non-high-risk declaration) must also be registered. The
database goes live with the high-risk application date on 2 August 2026.

Annex VIII Section B enumerates the 11 data points a provider must supply
for each system. This module builds the registration record from the
agent capability card, runtime data, and provider inputs, then lets the
caller download it as JSON / Markdown / PDF for submission once the
portal opens.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agentforge.models.agent import Agent

SCHEMA_VERSION = "1"
REGULATION_REF = "EU 2024/1689 Art. 49, Annex VIII Section B"

STATUSES = ("on_market", "no_longer_placed", "recalled", "withdrawn")


def _system_description(agent: Agent) -> dict[str, Any]:
    card = agent.card or {}
    capabilities = card.get("capabilities", {}) if isinstance(card, dict) else {}
    runtime = card.get("runtime", {}) if isinstance(card, dict) else {}
    ai_components = [
        f"Foundation model: {runtime.get('model')}" if runtime.get("model") else None,
        "Agent runtime: agents.renemurrell.de managed runtime",
        "Event log: platform-native (Art. 12)",
    ]
    return {
        "intended_purpose": capabilities.get("description") or agent.description,
        "domain": capabilities.get("domain"),
        "ai_components": [c for c in ai_components if c],
    }


def build_eu_db_registration(
    agent: Agent,
    provider_inputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compose the Annex VIII Section B record for one agent."""
    inputs = provider_inputs or {}

    status = inputs.get("status", "on_market")
    if status not in STATUSES:
        status = "on_market"

    sys_desc = _system_description(agent)

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
        # Annex VIII Section B fields
        "section_b_1_provider": {
            "name": inputs.get("provider_name")
            or "[PROVIDER: legal name of the provider]",
            "address": inputs.get("provider_address")
            or "[PROVIDER: registered address]",
            "contact": inputs.get("provider_contact")
            or "[PROVIDER: accountable contact, email, phone]",
        },
        "section_b_2_submitter": {
            "name": inputs.get("submitter_name")
            or "(Same as provider)",
            "relationship": inputs.get("submitter_relationship") or "provider",
        },
        "section_b_3_authorised_representative": {
            "required": inputs.get("auth_rep_required", False),
            "name": inputs.get("auth_rep_name")
            or (
                "[PROVIDER: EU-established authorised representative, mandatory for"
                " non-EU providers under Art. 22]"
                if inputs.get("auth_rep_required")
                else "Not required (EU-established provider)"
            ),
            "mandate_reference": inputs.get("auth_rep_mandate_reference"),
        },
        "section_b_4_system_identification": {
            "trade_name": inputs.get("trade_name") or agent.name,
            "unique_reference": agent.id,
            "traceability_id": f"capability-card@v{agent.version}",
            "additional_identifiers": inputs.get("additional_identifiers") or [],
        },
        "section_b_5_description": {
            "intended_purpose": sys_desc["intended_purpose"],
            "domain": sys_desc["domain"],
            "ai_components": sys_desc["ai_components"],
        },
        "section_b_6_status": {
            "current_status": status,
            "placed_on_market_date": inputs.get("placed_on_market_date")
            or "[PROVIDER: date placed on market]",
            "withdrawal_date": inputs.get("withdrawal_date"),
            "withdrawal_reason": inputs.get("withdrawal_reason"),
        },
        "section_b_7_software": {
            "type": inputs.get("software_type") or "Managed web service / API",
            "version_or_serial": f"v{agent.version}",
        },
        "section_b_8_member_states": inputs.get("member_states")
        or ["[PROVIDER: list EU Member States where the system is placed on market]"],
        "section_b_9_declaration_of_conformity": {
            "reference": inputs.get("doc_reference")
            or f"[PROVIDER: attach EU Declaration of Conformity for {agent.id} v{agent.version} per Annex V]",
            "ce_marking_affixed": inputs.get("ce_marking_affixed", False),
        },
        "section_b_10_instructions_for_use": {
            "ifu_reference": f"capability-card@v{agent.version}",
            "electronic_url": inputs.get("ifu_url")
            or f"https://agents.renemurrell.de/agents/{agent.id}",
        },
        "section_b_11_additional_info_url": inputs.get("additional_info_url")
        or f"https://agents.renemurrell.de/agents/{agent.id}",
        "non_high_risk_declaration": _non_high_risk_declaration(agent, inputs),
        "submission_note": (
            "The EU database opens with the high-risk application date (2 August 2026)."
            " This record is the submission draft; retain for 10 years under Art. 18."
        ),
        "status": "draft",
    }


def _non_high_risk_declaration(agent: Agent, inputs: dict[str, Any]) -> dict[str, Any] | None:
    """Art. 6(3) permits declaring non-high-risk with justification."""
    if agent.risk_class != "minimal" and agent.risk_class != "limited":
        return None
    if not inputs.get("non_high_risk_justification"):
        return None
    return {
        "applicable": True,
        "justification": inputs["non_high_risk_justification"],
        "notice": (
            "Art. 6(3) declaration: the system does not pose a significant risk of harm."
            " Must still be registered per Art. 49(2)."
        ),
    }


def eu_db_to_markdown(record: dict[str, Any]) -> str:
    a = record["agent"]
    provider = record["section_b_1_provider"]
    submitter = record["section_b_2_submitter"]
    auth_rep = record["section_b_3_authorised_representative"]
    ident = record["section_b_4_system_identification"]
    desc = record["section_b_5_description"]
    status = record["section_b_6_status"]
    software = record["section_b_7_software"]
    ms = record["section_b_8_member_states"]
    doc = record["section_b_9_declaration_of_conformity"]
    ifu = record["section_b_10_instructions_for_use"]

    def _bullets(items: Any) -> str:
        if isinstance(items, list):
            if not items:
                return "- (none)"
            return "\n".join(f"- {item}" for item in items)
        return f"- {items}"

    non_hr_block = ""
    nhr = record.get("non_high_risk_declaration")
    if nhr:
        non_hr_block = f"""

## Non-high-risk declaration (Art. 6(3))

{nhr["notice"]}

**Justification:** {nhr["justification"]}
"""

    return f"""# EU Database Registration (Annex VIII Section B)

**Regulation:** {record["regulation"]}
**Generated:** {record["generated_at"]}
**Status:** {record["status"]}

**System:** `{a["id"]}` · {a["name"]} · v{a["version"]} · risk class `{a["risk_class"]}`

---

## 1. Provider

- **Name:** {provider["name"]}
- **Address:** {provider["address"]}
- **Contact:** {provider["contact"]}

## 2. Submitter

- **Name:** {submitter["name"]}
- **Relationship:** {submitter["relationship"]}

## 3. Authorised representative

- **Required:** {"Yes" if auth_rep["required"] else "No"}
- **Name:** {auth_rep["name"]}
- **Mandate reference:** {auth_rep.get("mandate_reference") or "-"}

## 4. System identification

- **Trade name:** {ident["trade_name"]}
- **Unique reference:** `{ident["unique_reference"]}`
- **Traceability ID:** `{ident["traceability_id"]}`
- **Additional identifiers:** {", ".join(ident["additional_identifiers"] or []) or "-"}

## 5. Description

- **Intended purpose:** {desc["intended_purpose"]}
- **Domain:** {desc["domain"]}

**AI components:**
{_bullets(desc["ai_components"])}

## 6. Status

- **Current status:** `{status["current_status"]}`
- **Placed on market:** {status["placed_on_market_date"]}
- **Withdrawal date:** {status.get("withdrawal_date") or "-"}
- **Withdrawal reason:** {status.get("withdrawal_reason") or "-"}

## 7. Software

- **Type:** {software["type"]}
- **Version/Serial:** {software["version_or_serial"]}

## 8. Member States on market

{_bullets(ms)}

## 9. Declaration of conformity

- **Reference:** {doc["reference"]}
- **CE marking affixed:** {doc["ce_marking_affixed"]}

## 10. Instructions for use

- **IFU reference:** `{ifu["ifu_reference"]}`
- **Electronic URL:** {ifu["electronic_url"]}

## 11. Additional info URL

{record["section_b_11_additional_info_url"]}
{non_hr_block}

---

*{record["submission_note"]} Generated by the agents.renemurrell.de EU
database scaffolding engine. Sections marked `[PROVIDER: …]` require
completion by the placing-on-market organisation.*
"""
