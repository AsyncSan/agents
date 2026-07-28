"""Webhook payload formatters.

Each formatter converts a platform event dict into the payload shape
expected by the target service (Slack Block Kit, Splunk HEC, Datadog
Logs API, Jira REST, or the default HMAC-signed generic shape). The
formatter also supplies the HTTP headers required for authentication.

Formatters are pure functions: ``(body, event_type, secret)`` ->
``(bytes, dict)``. ``secret`` is the webhook's HMAC secret for generic
webhooks; for third-party adapters it is interpreted as the API token
(Splunk HEC token, Datadog API key, Jira API token in the form
``email:token`` base64-encoded by the caller, etc).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any

WEBHOOK_TYPES = (
    "generic",
    "slack",
    "splunk_hec",
    "datadog_logs",
    "jira",
    "linear",
)

_SEVERITY_BY_EVENT = {
    "task.failed": "error",
    "incident.created": "error",
    "incident.reported": "warning",
    "task.awaiting_approval": "warning",
    "agent.deleted": "warning",
    "task.approved": "info",
    "task.completed": "info",
    "agent.created": "info",
    "agent.updated": "info",
    "task.created": "info",
}


def _severity(event_type: str) -> str:
    if event_type in _SEVERITY_BY_EVENT:
        return _SEVERITY_BY_EVENT[event_type]
    if event_type.endswith(".failed") or event_type.endswith(".error"):
        return "error"
    if event_type.endswith(".warning") or "incident" in event_type:
        return "warning"
    return "info"


def _normalise(body: dict[str, Any], event_type: str) -> dict[str, Any]:
    """Extract common fields used by most formatters."""
    payload = body.get("payload") or {}
    return {
        "event_id": body.get("event_id") or body.get("id") or "",
        "event_type": event_type,
        "resource_type": body.get("resource_type"),
        "resource_id": body.get("resource_id"),
        "actor_id": body.get("actor_id"),
        "actor_role": body.get("actor_role"),
        "occurred_at": body.get("created_at") or body.get("timestamp"),
        "severity": _severity(event_type),
        "payload": payload,
    }


# ---------- Generic (HMAC signed) ----------


def format_generic(
    body: dict[str, Any], event_type: str, secret: str
) -> tuple[bytes, dict[str, str]]:
    body_bytes = json.dumps(body, default=str).encode()
    signature = hmac.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": f"sha256={signature}",
        "X-Webhook-Event": event_type,
    }
    return body_bytes, headers


# ---------- Slack Block Kit ----------


def format_slack(
    body: dict[str, Any], event_type: str, _secret: str
) -> tuple[bytes, dict[str, str]]:
    resource_id = body.get("resource_id", "")
    payload = body.get("payload") or {}
    event_label = event_type.replace(".", " ").title()

    colors = {
        "completed": "#10b981",
        "failed": "#ef4444",
        "approved": "#8b5cf6",
        "awaiting_approval": "#a855f7",
        "created": "#3b82f6",
    }
    status = event_type.split(".")[-1] if "." in event_type else ""
    color = colors.get(status, "#64748b")

    fields = []
    if payload.get("agent_id"):
        fields.append({"type": "mrkdwn", "text": f"*Agent:* `{payload['agent_id']}`"})
    if payload.get("risk_class"):
        fields.append({"type": "mrkdwn", "text": f"*Risk:* {payload['risk_class']}"})
    if payload.get("elapsed_seconds"):
        fields.append(
            {"type": "mrkdwn", "text": f"*Duration:* {payload['elapsed_seconds']}s"}
        )
    if payload.get("exit_code") is not None:
        fields.append({"type": "mrkdwn", "text": f"*Exit:* {payload['exit_code']}"})
    if payload.get("requires_approval"):
        fields.append(
            {"type": "mrkdwn", "text": ":warning: *Requires human approval*"}
        )

    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*{event_label}*\n`{resource_id}`"},
        },
    ]
    if fields:
        blocks.append({"type": "section", "fields": fields})

    slack_body = {
        "text": f"{event_label}: {resource_id}",
        "attachments": [{"color": color, "blocks": blocks}],
    }
    return json.dumps(slack_body).encode(), {"Content-Type": "application/json"}


# ---------- Splunk HTTP Event Collector ----------


def format_splunk_hec(
    body: dict[str, Any], event_type: str, secret: str
) -> tuple[bytes, dict[str, str]]:
    """Splunk HEC event format.

    Secret is the HEC token. The event wrapper follows the HEC single-event
    schema with ``sourcetype``, ``source``, ``host`` and ``event`` fields.
    """
    n = _normalise(body, event_type)
    hec = {
        "time": _epoch(n["occurred_at"]),
        "sourcetype": "agentforge:event",
        "source": "agents.renemurrell.de",
        "host": "agentforge",
        "event": {
            "event_type": event_type,
            "event_id": n["event_id"],
            "resource_type": n["resource_type"],
            "resource_id": n["resource_id"],
            "actor_id": n["actor_id"],
            "actor_role": n["actor_role"],
            "severity": n["severity"],
            "payload": n["payload"],
        },
        "fields": {
            "platform": "agentforge",
            "regulation": "EU 2024/1689",
        },
    }
    return json.dumps(hec).encode(), {
        "Authorization": f"Splunk {secret}",
        "Content-Type": "application/json",
    }


# ---------- Datadog Logs API ----------


def format_datadog_logs(
    body: dict[str, Any], event_type: str, secret: str
) -> tuple[bytes, dict[str, str]]:
    """Datadog Logs intake format.

    Secret is the Datadog API key. Sends a single-entry array compatible with
    the v2 logs API.
    """
    n = _normalise(body, event_type)
    entry = {
        "ddsource": "agentforge",
        "ddtags": (
            f"service:agentforge,env:prod,event_type:{event_type},"
            f"severity:{n['severity']}"
        ),
        "hostname": "agents.renemurrell.de",
        "service": "agentforge",
        "message": (
            f"{event_type} · {n['resource_type'] or '-'} · {n['resource_id'] or '-'}"
        ),
        "status": n["severity"],
        "event_type": event_type,
        "resource_type": n["resource_type"],
        "resource_id": n["resource_id"],
        "actor_id": n["actor_id"],
        "actor_role": n["actor_role"],
        "payload": n["payload"],
        "timestamp": n["occurred_at"],
    }
    return json.dumps([entry]).encode(), {
        "DD-API-KEY": secret,
        "Content-Type": "application/json",
    }


# ---------- Jira issue create ----------


def format_jira(
    body: dict[str, Any], event_type: str, secret: str
) -> tuple[bytes, dict[str, str]]:
    """Jira Cloud REST issue-create payload.

    Secret must encode ``<project_key>|<email>:<api_token>``. The project
    key is the target project for the created issue. Email + API token are
    base64-encoded for Basic auth.
    """
    project_key, auth = _split_jira_secret(secret)
    n = _normalise(body, event_type)
    payload = n["payload"]
    summary = f"[agentforge] {event_type}"
    if n["resource_id"]:
        summary += f" · {n['resource_id']}"

    description_lines = [
        f"Event: {event_type}",
        f"Severity: {n['severity']}",
        f"Resource: {n['resource_type'] or '-'} / {n['resource_id'] or '-'}",
        f"Actor: {n['actor_role'] or '-'} / {n['actor_id'] or '-'}",
        f"Occurred at: {n['occurred_at'] or '-'}",
        "",
        "Payload:",
        json.dumps(payload, indent=2, default=str),
    ]

    issue = {
        "fields": {
            "project": {"key": project_key},
            "summary": summary[:250],
            "description": "\n".join(description_lines),
            "issuetype": {"name": "Task"},
            "labels": ["agentforge", event_type.replace(".", "-"), n["severity"]],
        }
    }
    encoded = base64.b64encode(auth.encode()).decode()
    return json.dumps(issue).encode(), {
        "Authorization": f"Basic {encoded}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _split_jira_secret(secret: str) -> tuple[str, str]:
    if "|" not in secret:
        raise ValueError(
            "Jira webhook secret must be '<PROJECT_KEY>|<email>:<api_token>'"
        )
    project_key, auth = secret.split("|", 1)
    if not project_key or ":" not in auth:
        raise ValueError(
            "Jira secret malformed. Expected '<PROJECT_KEY>|<email>:<api_token>'"
        )
    return project_key, auth


# ---------- Linear issue create (GraphQL) ----------


def format_linear(
    body: dict[str, Any], event_type: str, secret: str
) -> tuple[bytes, dict[str, str]]:
    """Linear GraphQL issue-create mutation.

    Secret must be ``<TEAM_ID>|<api_key>``. TEAM_ID is the Linear team the
    issue is created in. API key is a personal or service key.
    """
    team_id, api_key = _split_linear_secret(secret)
    n = _normalise(body, event_type)
    payload = n["payload"]
    title = f"[agentforge] {event_type}"
    if n["resource_id"]:
        title += f" · {n['resource_id']}"

    description = (
        f"Event: `{event_type}`\n"
        f"Severity: `{n['severity']}`\n"
        f"Resource: `{n['resource_type'] or '-'}` / `{n['resource_id'] or '-'}`\n"
        f"Actor: `{n['actor_role'] or '-'}` / `{n['actor_id'] or '-'}`\n"
        f"Occurred at: `{n['occurred_at'] or '-'}`\n\n"
        f"```json\n{json.dumps(payload, indent=2, default=str)}\n```"
    )

    mutation = """
    mutation IssueCreate($input: IssueCreateInput!) {
      issueCreate(input: $input) { success issue { id identifier url } }
    }
    """
    body_obj = {
        "query": mutation,
        "variables": {
            "input": {
                "teamId": team_id,
                "title": title[:250],
                "description": description,
            }
        },
    }
    return json.dumps(body_obj).encode(), {
        "Authorization": api_key,
        "Content-Type": "application/json",
    }


def _split_linear_secret(secret: str) -> tuple[str, str]:
    if "|" not in secret:
        raise ValueError("Linear webhook secret must be '<TEAM_ID>|<api_key>'")
    team_id, api_key = secret.split("|", 1)
    if not team_id or not api_key:
        raise ValueError("Linear secret malformed. Expected '<TEAM_ID>|<api_key>'")
    return team_id, api_key


# ---------- Dispatcher ----------


_FORMATTERS = {
    "generic": format_generic,
    "slack": format_slack,
    "splunk_hec": format_splunk_hec,
    "datadog_logs": format_datadog_logs,
    "jira": format_jira,
    "linear": format_linear,
}


def format_payload(
    webhook_type: str,
    body: dict[str, Any],
    event_type: str,
    secret: str,
) -> tuple[bytes, dict[str, str]]:
    fmt = _FORMATTERS.get(webhook_type) or _FORMATTERS["generic"]
    return fmt(body, event_type, secret)


def _epoch(ts: str | datetime | None) -> float:
    if ts is None:
        return datetime.now(timezone.utc).timestamp()
    if isinstance(ts, datetime):
        return ts.timestamp()
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError):
        return datetime.now(timezone.utc).timestamp()
