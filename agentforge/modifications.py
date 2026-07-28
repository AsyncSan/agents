"""EU AI Act Art. 43 — substantial modification tracking.

Art. 43(4) requires providers of high-risk systems to repeat the
conformity assessment when a substantial modification is made, i.e. a
change to the system not foreseen in the initial conformity assessment
that affects compliance with Chapter III Section 2 requirements or the
intended purpose.

This module provides:

1. ``diff_cards`` — extract the subset of fields that changed between two
   capability cards, so an auditor can see exactly what was modified.
2. ``classify_auto`` — a conservative classifier that suggests whether a
   diff may be substantial, based on which fields changed. The final
   classification is always the provider's call (they must tick "reviewed"
   on the record) but the suggestion highlights what needs attention.
3. ``modifications_to_markdown`` — Annex IV addendum export.

The classifier errs on the side of flagging. False positives cost a
10-minute review; false negatives cost a broken conformity assessment.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

REGULATION_REF = "EU 2024/1689 Art. 43, 72"

# Fields whose change strongly suggests a substantial modification.
# These map to Chapter III Section 2 requirements or the intended purpose.
SUBSTANTIAL_SIGNALS = {
    "capabilities.description",     # intended purpose
    "capabilities.domain",          # intended purpose / domain scope
    "risk_class",                   # obvious trigger
    "runtime.model",                # accuracy/robustness baseline (Art. 15)
    "runtime.tools",                # attack surface / security (Art. 15)
    "runtime.server_type",          # security environment (Art. 15)
    "runtime.compute_tier",         # isolation boundary (Art. 15)
    "capabilities.inputs",          # data categories (Art. 10)
    "capabilities.outputs",         # user-facing effect (Art. 13)
    "capabilities.constraints",     # documented limits (Art. 13)
}

# Fields whose change is typically cosmetic / administrative.
NON_SUBSTANTIAL_SIGNALS = {
    "meta.name",
    "capabilities.tags",
    "pricing",
    "pricing.base_price_usd",
    "pricing.model",
}


def _flatten(d: Any, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(d, dict):
        for k, v in d.items():
            key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                out.update(_flatten(v, key))
            else:
                out[key] = v
    return out


def diff_cards(old: dict[str, Any], new: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return a shallow field-level diff between two capability cards.

    Keys are dotted paths; values are ``{"old": ..., "new": ...}``.
    """
    old_flat = _flatten(old or {})
    new_flat = _flatten(new or {})
    keys = set(old_flat) | set(new_flat)
    diff: dict[str, dict[str, Any]] = {}
    for k in keys:
        if old_flat.get(k) != new_flat.get(k):
            diff[k] = {"old": old_flat.get(k), "new": new_flat.get(k)}
    return diff


def classify_auto(diff: dict[str, Any]) -> str:
    """Suggest a classification based on which fields changed.

    Returns one of: ``substantial`` (provider must review), ``non_substantial``
    (likely cosmetic), or ``unclassified`` (unknown field, default to review).
    """
    if not diff:
        return "non_substantial"
    changed = set(diff.keys())
    substantial_prefixes = tuple(f"{s}." for s in SUBSTANTIAL_SIGNALS)
    if any(
        k in SUBSTANTIAL_SIGNALS or k.startswith(substantial_prefixes) for k in changed
    ):
        return "substantial"
    if changed and all(
        k in NON_SUBSTANTIAL_SIGNALS
        or any(k.startswith(f"{s}.") for s in NON_SUBSTANTIAL_SIGNALS)
        for k in changed
    ):
        return "non_substantial"
    return "unclassified"


def summarise_diff(diff: dict[str, Any]) -> str:
    if not diff:
        return "No card fields changed."
    keys = sorted(diff.keys())
    if len(keys) <= 5:
        return "Changed: " + ", ".join(keys)
    head = ", ".join(keys[:5])
    return f"Changed {len(keys)} fields including: {head}, …"


def modifications_to_markdown(
    agent_id: str,
    agent_name: str,
    records: list[dict[str, Any]],
) -> str:
    """Render a list of modification records as an Annex IV addendum."""
    generated = datetime.now(timezone.utc).isoformat()
    if not records:
        body = "*No modifications recorded for this system.*"
    else:
        lines = []
        for r in records:
            when = r.get("created_at") or "-"
            v_from = r.get("version_from")
            v_to = r.get("version_to")
            v_span = (
                f"v{v_from} → v{v_to}"
                if v_from is not None and v_to is not None
                else (f"v{v_to}" if v_to is not None else "-")
            )
            cls = r.get("classification", "unclassified")
            reassess = (
                "Yes — conformity assessment repeated" + (
                    f" on {r['reassessment_at']}" if r.get("reassessment_at") else ""
                )
                if r.get("triggered_reassessment")
                else "No"
            )
            rationale = r.get("rationale") or "-"
            lines.append(
                f"""### {when} · {r.get('modification_type')} · `{cls}`

- **Version:** {v_span}
- **Summary:** {r.get('summary', '-')}
- **Triggered reassessment:** {reassess}
- **Rationale:** {rationale}
"""
            )
        body = "\n".join(lines)

    return f"""# Annex IV addendum · Modification log

**Regulation:** {REGULATION_REF}
**System:** `{agent_id}` · {agent_name}
**Generated:** {generated}

Substantial modifications (Art. 43) trigger a new conformity assessment.
Non-substantial modifications are logged for audit traceability under
Art. 12 and Annex IV point 6 (changes made to the system through its
lifecycle).

---

{body}

---

*Generated by the agents.renemurrell.de modification tracker. The
auto-classifier suggests whether a change looks substantial based on
field-level diffs; the provider signs off on the final classification
and records any reassessment outcome.*
"""
