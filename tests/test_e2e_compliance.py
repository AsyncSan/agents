"""E2E tests for the compliance document workspace."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_list_fria(
    client: AsyncClient, consumer_key: tuple[str, dict], seed_agent: dict
):
    api_key, _ = consumer_key
    payload = {"section_1": "scaffold", "status": "draft"}
    create = await client.post(
        "/v1/compliance/documents",
        headers={"X-API-Key": api_key},
        json={
            "doc_type": "fria",
            "title": "FRIA draft for credit scoring",
            "payload": payload,
            "agent_id": seed_agent["id"],
            "agent_version": seed_agent["version"],
        },
    )
    assert create.status_code == 201, create.text
    doc = create.json()
    assert doc["status"] == "draft"
    assert doc["is_stale"] is False
    assert doc["current_agent_version"] == seed_agent["version"]

    listing = await client.get(
        "/v1/compliance/documents?doc_type=fria",
        headers={"X-API-Key": api_key},
    )
    assert listing.status_code == 200
    data = listing.json()
    assert data["total"] == 1
    assert data["stale_count"] == 0
    assert data["documents"][0]["id"] == doc["id"]


@pytest.mark.asyncio
async def test_ownership_is_enforced(
    client: AsyncClient,
    consumer_key: tuple[str, dict],
    seed_agent: dict,
):
    api_key_a, _ = consumer_key
    # Create another consumer
    from secrets import token_hex

    other = await client.post(
        "/v1/auth/register",
        json={
            "name": "Other",
            "email": f"other-{token_hex(4)}@test.com",
            "role": "consumer",
        },
    )
    api_key_b = other.json()["api_key"]

    create = await client.post(
        "/v1/compliance/documents",
        headers={"X-API-Key": api_key_a},
        json={"doc_type": "fria", "title": "Mine", "payload": {"x": 1}},
    )
    doc_id = create.json()["id"]

    # Other consumer must not be able to read it
    probe = await client.get(
        f"/v1/compliance/documents/{doc_id}",
        headers={"X-API-Key": api_key_b},
    )
    assert probe.status_code == 404


@pytest.mark.asyncio
async def test_stale_detection_fires_when_agent_version_advances(
    client: AsyncClient,
    consumer_key: tuple[str, dict],
    seed_agent: dict,
    db_session,
):
    api_key, _ = consumer_key

    create = await client.post(
        "/v1/compliance/documents",
        headers={"X-API-Key": api_key},
        json={
            "doc_type": "annex_iv",
            "title": "Annex IV draft",
            "payload": {"section_1": "yes"},
            "agent_id": seed_agent["id"],
            "agent_version": seed_agent["version"],
        },
    )
    doc = create.json()
    assert doc["is_stale"] is False

    # Bump the agent's version directly in the DB
    from sqlalchemy import update

    from agentforge.models.agent import Agent

    await db_session.execute(
        update(Agent)
        .where(Agent.id == seed_agent["id"])
        .values(version=seed_agent["version"] + 1)
    )
    await db_session.commit()

    refreshed = await client.get(
        f"/v1/compliance/documents/{doc['id']}",
        headers={"X-API-Key": api_key},
    )
    refreshed_doc = refreshed.json()
    assert refreshed_doc["current_agent_version"] > refreshed_doc["agent_version"]
    assert refreshed_doc["is_stale"] is True


@pytest.mark.asyncio
async def test_approve_workflow(
    client: AsyncClient, consumer_key: tuple[str, dict]
):
    api_key, _ = consumer_key
    create = await client.post(
        "/v1/compliance/documents",
        headers={"X-API-Key": api_key},
        json={"doc_type": "fria", "title": "Approvable", "payload": {"a": 1}},
    )
    doc_id = create.json()["id"]

    approve = await client.post(
        f"/v1/compliance/documents/{doc_id}/approve",
        headers={"X-API-Key": api_key},
        json={"notes": "ok from reviewer"},
    )
    assert approve.status_code == 200
    approved = approve.json()
    assert approved["status"] == "approved"
    assert approved["approved_by"] is not None
    assert approved["approved_at"] is not None
    assert approved["notes"] == "ok from reviewer"

    # Archive
    archive = await client.post(
        f"/v1/compliance/documents/{doc_id}/archive",
        headers={"X-API-Key": api_key},
    )
    assert archive.status_code == 200
    assert archive.json()["status"] == "archived"

    # Cannot approve archived
    reapprove = await client.post(
        f"/v1/compliance/documents/{doc_id}/approve",
        headers={"X-API-Key": api_key},
        json={},
    )
    assert reapprove.status_code == 409


@pytest.mark.asyncio
async def test_summary_counts(
    client: AsyncClient, consumer_key: tuple[str, dict]
):
    api_key, _ = consumer_key
    for doc_type in ["fria", "fria", "annex_iv", "literacy_completion"]:
        await client.post(
            "/v1/compliance/documents",
            headers={"X-API-Key": api_key},
            json={"doc_type": doc_type, "title": "t", "payload": {}},
        )

    resp = await client.get(
        "/v1/compliance/documents/summary",
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 200
    summary = resp.json()
    assert summary["by_doc_type"]["fria"] == 2
    assert summary["by_doc_type"]["annex_iv"] == 1
    assert summary["by_doc_type"]["literacy_completion"] == 1
    assert summary["by_status"]["draft"] == 4


@pytest.mark.asyncio
async def test_update_status_resets_approval(
    client: AsyncClient, consumer_key: tuple[str, dict]
):
    api_key, _ = consumer_key
    create = await client.post(
        "/v1/compliance/documents",
        headers={"X-API-Key": api_key},
        json={"doc_type": "fria", "title": "t", "payload": {"a": 1}},
    )
    doc_id = create.json()["id"]

    await client.post(
        f"/v1/compliance/documents/{doc_id}/approve",
        headers={"X-API-Key": api_key},
        json={},
    )

    # Revert to draft
    patch = await client.patch(
        f"/v1/compliance/documents/{doc_id}",
        headers={"X-API-Key": api_key},
        json={"status": "draft"},
    )
    assert patch.status_code == 200
    updated = patch.json()
    assert updated["status"] == "draft"
    assert updated["approved_by"] is None
    assert updated["approved_at"] is None


@pytest.mark.asyncio
async def test_invalid_doc_type_rejected(
    client: AsyncClient, consumer_key: tuple[str, dict]
):
    api_key, _ = consumer_key
    resp = await client.post(
        "/v1/compliance/documents",
        headers={"X-API-Key": api_key},
        json={"doc_type": "totally_made_up", "title": "t", "payload": {}},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_delete(
    client: AsyncClient, consumer_key: tuple[str, dict]
):
    api_key, _ = consumer_key
    create = await client.post(
        "/v1/compliance/documents",
        headers={"X-API-Key": api_key},
        json={"doc_type": "fria", "title": "t", "payload": {}},
    )
    doc_id = create.json()["id"]

    delete = await client.delete(
        f"/v1/compliance/documents/{doc_id}",
        headers={"X-API-Key": api_key},
    )
    assert delete.status_code == 204

    get = await client.get(
        f"/v1/compliance/documents/{doc_id}",
        headers={"X-API-Key": api_key},
    )
    assert get.status_code == 404
