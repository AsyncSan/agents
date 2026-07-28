"""E2E tests for the incident reporting API."""

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


@pytest.mark.asyncio
async def test_create_and_list_incident(
    client: AsyncClient, consumer_key: tuple[str, dict], seed_agent: dict
):
    api_key, _ = consumer_key
    now = datetime(2026, 4, 22, 10, 0, tzinfo=timezone.utc)
    body = {
        "title": "Disparate impact on credit denials",
        "summary": "Statistical review shows 23% higher denial rate for applicants over 65.",
        "severity": "fundamental_rights",
        "detected_at": _iso(now),
        "agent_id": seed_agent["id"],
        "agent_version": seed_agent["version"],
        "affected_persons_estimate": 120,
    }
    create = await client.post(
        "/v1/incidents",
        headers={"X-API-Key": api_key},
        json=body,
    )
    assert create.status_code == 201, create.text
    inc = create.json()
    assert inc["severity"] == "fundamental_rights"
    assert inc["status"] == "draft"
    assert inc["deadline_days"] == 10
    assert inc["overdue"] is False

    listing = await client.get(
        "/v1/incidents",
        headers={"X-API-Key": api_key},
    )
    data = listing.json()
    assert data["total"] == 1
    assert data["open_count"] == 1


@pytest.mark.asyncio
async def test_rejects_invalid_severity(
    client: AsyncClient, consumer_key: tuple[str, dict]
):
    api_key, _ = consumer_key
    resp = await client.post(
        "/v1/incidents",
        headers={"X-API-Key": api_key},
        json={
            "title": "t",
            "summary": "s",
            "severity": "not_a_real_category",
            "detected_at": _iso(datetime.now(timezone.utc)),
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_mark_reported_updates_status(
    client: AsyncClient, consumer_key: tuple[str, dict]
):
    api_key, _ = consumer_key
    create = await client.post(
        "/v1/incidents",
        headers={"X-API-Key": api_key},
        json={
            "title": "t",
            "summary": "s",
            "severity": "serious_property_harm",
            "detected_at": _iso(datetime.now(timezone.utc)),
        },
    )
    inc_id = create.json()["id"]

    mark = await client.post(
        f"/v1/incidents/{inc_id}/report",
        headers={"X-API-Key": api_key},
        json={"authority_name": "BNetzA", "authority_reference": "MSA-2026-4242"},
    )
    assert mark.status_code == 200
    body = mark.json()
    assert body["status"] == "reported"
    assert body["authority_reference"] == "MSA-2026-4242"
    assert body["reported_to_authority_at"] is not None


@pytest.mark.asyncio
async def test_report_template_json_and_markdown(
    client: AsyncClient, consumer_key: tuple[str, dict], seed_agent: dict
):
    api_key, _ = consumer_key
    create = await client.post(
        "/v1/incidents",
        headers={"X-API-Key": api_key},
        json={
            "title": "Critical service disruption",
            "summary": "Service processed invalid inputs causing downstream failures.",
            "severity": "critical_infrastructure",
            "detected_at": _iso(datetime.now(timezone.utc)),
            "agent_id": seed_agent["id"],
            "agent_version": seed_agent["version"],
        },
    )
    inc_id = create.json()["id"]

    template = await client.post(
        f"/v1/incidents/{inc_id}/report-template",
        headers={"X-API-Key": api_key},
        json={"organisation": "Acme GmbH", "contact": "ops@acme.example"},
    )
    assert template.status_code == 200
    doc = template.json()
    assert doc["regulation"] == "EU 2024/1689 Art. 73"
    assert doc["provider"]["organisation"] == "Acme GmbH"
    assert doc["system"]["id"] == seed_agent["id"]

    md_resp = await client.post(
        f"/v1/incidents/{inc_id}/report-template/markdown",
        headers={"X-API-Key": api_key},
        json={},
    )
    assert md_resp.status_code == 200
    assert md_resp.headers["content-type"].startswith("text/markdown")
    assert "# Serious Incident Report" in md_resp.text


@pytest.mark.asyncio
async def test_ownership_is_enforced(
    client: AsyncClient, consumer_key: tuple[str, dict]
):
    from secrets import token_hex

    api_key_a, _ = consumer_key
    create = await client.post(
        "/v1/incidents",
        headers={"X-API-Key": api_key_a},
        json={
            "title": "owned by A",
            "summary": "s",
            "severity": "serious_property_harm",
            "detected_at": _iso(datetime.now(timezone.utc)),
        },
    )
    inc_id = create.json()["id"]

    other = await client.post(
        "/v1/auth/register",
        json={
            "name": "Other",
            "email": f"other-{token_hex(4)}@test.com",
            "role": "consumer",
        },
    )
    api_key_b = other.json()["api_key"]

    probe = await client.get(
        f"/v1/incidents/{inc_id}",
        headers={"X-API-Key": api_key_b},
    )
    assert probe.status_code == 404


@pytest.mark.asyncio
async def test_severities_catalog_lists_all(
    client: AsyncClient, consumer_key: tuple[str, dict]
):
    api_key, _ = consumer_key
    resp = await client.get(
        "/v1/incidents/severities",
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 200
    data = resp.json()["severities"]
    keys = {e["key"] for e in data}
    assert {"fundamental_rights", "critical_infrastructure", "widespread_infringement"} <= keys
