"""Unit tests for webhook payload formatters."""

import base64
import hashlib
import hmac
import json

import pytest

from agentforge.webhook_formatters import (
    WEBHOOK_TYPES,
    format_datadog_logs,
    format_generic,
    format_jira,
    format_linear,
    format_payload,
    format_slack,
    format_splunk_hec,
)

EVENT = {
    "event_id": "ev-123",
    "event_type": "task.failed",
    "resource_type": "task",
    "resource_id": "tc-abc",
    "actor_id": "user-1",
    "actor_role": "consumer",
    "created_at": "2026-04-22T12:00:00+00:00",
    "payload": {
        "agent_id": "credit-scorer-v1",
        "risk_class": "high",
        "elapsed_seconds": 42,
        "exit_code": 1,
    },
}


class TestGeneric:
    def test_produces_hmac_signed_payload(self):
        body, headers = format_generic(EVENT, "task.failed", "secret-abc")
        assert headers["Content-Type"] == "application/json"
        assert headers["X-Webhook-Event"] == "task.failed"

        parsed = json.loads(body.decode())
        assert parsed["resource_id"] == "tc-abc"

        expected = hmac.new(b"secret-abc", body, hashlib.sha256).hexdigest()
        assert headers["X-Webhook-Signature"] == f"sha256={expected}"


class TestSlack:
    def test_slack_block_kit_shape(self):
        body, headers = format_slack(EVENT, "task.failed", "unused")
        parsed = json.loads(body.decode())
        assert headers == {"Content-Type": "application/json"}
        assert "attachments" in parsed
        assert parsed["attachments"][0]["color"] == "#ef4444"
        assert any(
            "Agent" in f["text"]
            for f in parsed["attachments"][0]["blocks"][1]["fields"]
        )


class TestSplunkHEC:
    def test_shape_and_auth_header(self):
        body, headers = format_splunk_hec(EVENT, "task.failed", "TOKEN-xyz")
        parsed = json.loads(body.decode())
        assert headers["Authorization"] == "Splunk TOKEN-xyz"
        assert parsed["sourcetype"] == "agentforge:event"
        assert parsed["event"]["event_type"] == "task.failed"
        assert parsed["event"]["severity"] == "error"
        assert parsed["fields"]["platform"] == "agentforge"
        # time is numeric epoch
        assert isinstance(parsed["time"], (int, float))
        assert parsed["time"] > 0

    def test_severity_inference_for_incident(self):
        body, _ = format_splunk_hec(
            {"event_id": "1", "payload": {}}, "incident.created", "T"
        )
        parsed = json.loads(body.decode())
        assert parsed["event"]["severity"] == "error"

    def test_severity_info_for_benign_event(self):
        body, _ = format_splunk_hec(
            {"event_id": "1", "payload": {}}, "agent.created", "T"
        )
        parsed = json.loads(body.decode())
        assert parsed["event"]["severity"] == "info"


class TestDatadog:
    def test_shape_and_api_key_header(self):
        body, headers = format_datadog_logs(EVENT, "task.failed", "dd-api-key-xyz")
        parsed = json.loads(body.decode())
        assert headers["DD-API-KEY"] == "dd-api-key-xyz"
        assert isinstance(parsed, list)
        entry = parsed[0]
        assert entry["service"] == "agentforge"
        assert entry["status"] == "error"
        assert "event_type:task.failed" in entry["ddtags"]
        assert entry["resource_id"] == "tc-abc"


class TestJira:
    def test_jira_requires_project_key(self):
        with pytest.raises(ValueError):
            format_jira(EVENT, "task.failed", "email@example.com:api-token")

    def test_jira_requires_email_token_pair(self):
        with pytest.raises(ValueError):
            format_jira(EVENT, "task.failed", "PROJ|onlyemail")

    def test_jira_issue_shape(self):
        body, headers = format_jira(
            EVENT, "task.failed", "PROJ|me@example.com:api-token"
        )
        parsed = json.loads(body.decode())
        assert parsed["fields"]["project"]["key"] == "PROJ"
        assert parsed["fields"]["issuetype"]["name"] == "Task"
        assert "agentforge" in parsed["fields"]["labels"]
        assert "task-failed" in parsed["fields"]["labels"]
        assert "error" in parsed["fields"]["labels"]
        assert "tc-abc" in parsed["fields"]["summary"]

        # Header must be basic-auth encoded
        expected = base64.b64encode(b"me@example.com:api-token").decode()
        assert headers["Authorization"] == f"Basic {expected}"


class TestLinear:
    def test_linear_requires_team_id(self):
        with pytest.raises(ValueError):
            format_linear(EVENT, "task.failed", "somekey")

    def test_linear_mutation_shape(self):
        body, headers = format_linear(EVENT, "task.failed", "TEAM-1|api-key")
        parsed = json.loads(body.decode())
        assert headers["Authorization"] == "api-key"
        assert "mutation" in parsed["query"]
        assert parsed["variables"]["input"]["teamId"] == "TEAM-1"
        assert "task.failed" in parsed["variables"]["input"]["title"]
        assert "tc-abc" in parsed["variables"]["input"]["description"]


class TestDispatcher:
    def test_unknown_type_falls_back_to_generic(self):
        body, headers = format_payload("weird-type", EVENT, "task.failed", "s")
        assert "X-Webhook-Signature" in headers
        assert json.loads(body.decode())["resource_id"] == "tc-abc"

    def test_all_declared_types_dispatch(self):
        samples = {
            "generic": "secret",
            "slack": "unused",
            "splunk_hec": "token",
            "datadog_logs": "api-key",
            "jira": "PROJ|e@x.com:t",
            "linear": "TEAM|key",
        }
        for t in WEBHOOK_TYPES:
            body, _ = format_payload(t, EVENT, "task.failed", samples[t])
            assert body
