"""One-shot compliance bundle for a given use-case.

Most deployers land on the platform with a single concrete question: "What
documents do I need for a credit-scoring agent by August 2026?". This
module takes one agent (platform-registered or manually described) plus a
use-case key and produces the full set of EU AI Act artefacts that apply:

  * FRIA when the use-case triggers Art. 27
  * Annex IV technical documentation (Art. 11)
  * Post-market monitoring plan (Art. 72)
  * Data governance sheet (Art. 10)
  * EU database registration draft (Art. 49)

The output is a ZIP of PDFs plus a manifest. No wizards to click through
one by one.
"""

from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone
from typing import Any

from agentforge.annex_iv import annex_iv_to_markdown, build_annex_iv_template
from agentforge.data_governance import (
    agent_data_sheet_to_markdown,
    build_agent_data_sheet,
)
from agentforge.eu_db import build_eu_db_registration, eu_db_to_markdown
from agentforge.fria import (
    TRIGGER_USE_CASES,
    build_fria_template,
    fria_to_markdown,
)
from agentforge.pdf import markdown_to_pdf
from agentforge.pmm_plan import build_pmm_plan_template, pmm_plan_to_markdown

SCHEMA_VERSION = "1"
REGULATION_REF = "EU 2024/1689 · multi-article bundle"

# Heuristic: when to include FRIA based on use-case trigger
FRIA_TRIGGERING = {"credit_scoring", "insurance_pricing", "public_service"}


def _pdf_or_blank(md: str, title: str) -> bytes:
    """Small helper that renders Markdown to PDF bytes."""
    return markdown_to_pdf(md, title=title)


def _bundle_manifest(
    agent: Any,
    use_case_key: str,
    included: list[str],
) -> dict[str, Any]:
    use_case_description = TRIGGER_USE_CASES.get(use_case_key)
    return {
        "schema_version": SCHEMA_VERSION,
        "regulation": REGULATION_REF,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "use_case": {
            "key": use_case_key,
            "description": use_case_description,
            "triggers_fria": use_case_key in FRIA_TRIGGERING,
        },
        "agent": {
            "id": agent.id,
            "name": agent.name,
            "version": agent.version,
            "risk_class": agent.risk_class,
        },
        "included_artefacts": included,
        "filing_notes": (
            "Retain FRIA + Annex IV + PMM + Data Sheet + EU DB draft for 10 "
            "years under Art. 18. Serious incidents route through Art. 73 at "
            "agents.renemurrell.de/incidents."
        ),
    }


def build_compliance_bundle(
    agent: Any,
    use_case_key: str,
    deployer_inputs: dict[str, Any] | None = None,
    provider_inputs: dict[str, Any] | None = None,
) -> tuple[bytes, dict[str, Any]]:
    """Generate the full artefact ZIP. Returns ``(zip_bytes, manifest)``."""
    deployer_inputs = deployer_inputs or {}
    provider_inputs = provider_inputs or {}

    include_fria = use_case_key in FRIA_TRIGGERING

    artefacts: dict[str, tuple[str, bytes, str]] = {}

    if include_fria:
        fria = build_fria_template(
            agent,
            {**deployer_inputs, "use_case_key": use_case_key},
        )
        fria_md = fria_to_markdown(fria)
        artefacts["fria"] = (
            f"fria-{agent.id.replace('/', '-')}.pdf",
            _pdf_or_blank(fria_md, f"FRIA · {agent.name}"),
            fria_md,
        )

    annex = build_annex_iv_template(agent, provider_inputs, variant="full")
    annex_md = annex_iv_to_markdown(annex)
    artefacts["annex_iv"] = (
        f"annex-iv-{agent.id.replace('/', '-')}.pdf",
        _pdf_or_blank(annex_md, f"Annex IV · {agent.name}"),
        annex_md,
    )

    pmm = build_pmm_plan_template(agent, provider_inputs)
    pmm_md = pmm_plan_to_markdown(pmm)
    artefacts["pmm_plan"] = (
        f"pmm-plan-{agent.id.replace('/', '-')}.pdf",
        _pdf_or_blank(pmm_md, f"PMM plan · {agent.name}"),
        pmm_md,
    )

    data_sheet = build_agent_data_sheet(agent, provider_inputs)
    ds_md = agent_data_sheet_to_markdown(data_sheet)
    artefacts["data_sheet"] = (
        f"data-sheet-{agent.id.replace('/', '-')}.pdf",
        _pdf_or_blank(ds_md, f"Data sheet · {agent.name}"),
        ds_md,
    )

    eu_db = build_eu_db_registration(agent, provider_inputs)
    eu_db_md = eu_db_to_markdown(eu_db)
    artefacts["eu_db"] = (
        f"eu-db-{agent.id.replace('/', '-')}.pdf",
        _pdf_or_blank(eu_db_md, f"EU DB registration · {agent.name}"),
        eu_db_md,
    )

    manifest = _bundle_manifest(agent, use_case_key, sorted(artefacts.keys()))

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2, sort_keys=True))
        zf.writestr("README.md", _readme(agent, use_case_key, include_fria))
        zf.writestr(
            "payloads/fria.json",
            json.dumps(fria if include_fria else {"skipped": "use-case does not trigger Art. 27"}, indent=2),
        )
        zf.writestr("payloads/annex-iv.json", json.dumps(annex, indent=2))
        zf.writestr("payloads/pmm-plan.json", json.dumps(pmm, indent=2))
        zf.writestr("payloads/data-sheet.json", json.dumps(data_sheet, indent=2))
        zf.writestr("payloads/eu-db.json", json.dumps(eu_db, indent=2))
        for key, (filename, pdf_bytes, md) in artefacts.items():
            zf.writestr(f"pdf/{filename}", pdf_bytes)
            zf.writestr(f"markdown/{filename.replace('.pdf', '.md')}", md)

    return buf.getvalue(), manifest


def _readme(agent: Any, use_case_key: str, include_fria: bool) -> str:
    use_case_description = TRIGGER_USE_CASES.get(use_case_key, use_case_key)
    fria_line = (
        "- `pdf/fria-*.pdf` — Fundamental Rights Impact Assessment (Art. 27)"
        if include_fria
        else "- **FRIA skipped**: selected use-case does not trigger Art. 27(1)."
    )
    return f"""# EU AI Act compliance bundle

**System:** {agent.name} · `{agent.id}` · v{agent.version} · risk class `{agent.risk_class}`
**Use-case:** {use_case_description}
**Generated:** {datetime.now(timezone.utc).isoformat()}

---

## What is in this ZIP

{fria_line}
- `pdf/annex-iv-*.pdf` — Annex IV technical documentation (Art. 11)
- `pdf/pmm-plan-*.pdf` — Post-market monitoring plan (Art. 72)
- `pdf/data-sheet-*.pdf` — Data governance sheet (Art. 10)
- `pdf/eu-db-*.pdf` — EU database registration draft (Art. 49, Annex VIII)
- `markdown/*` — Markdown source of every PDF, editable
- `payloads/*.json` — Machine-readable source payloads per artefact
- `manifest.json` — Index

## How to use

1. Review each PDF. Sections marked `[DEPLOYER: …]` or `[PROVIDER: …]`
   require completion by your organisation.
2. Retain the finalised documents for 10 years (Art. 18) in your document
   management system. Store the ZIP alongside as the machine-readable backup.
3. Route serious incidents via Art. 73 at `/incidents`.
4. Refresh this bundle whenever the underlying system version changes; the
   platform will flag stale compliance documents automatically.

*Generated by agents.renemurrell.de.*
"""
