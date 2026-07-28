"""Password auth + login E2E tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_with_password_then_login(client: AsyncClient):
    from secrets import token_hex

    email = f"pw-{token_hex(4)}@test.example"
    reg = await client.post(
        "/v1/auth/register",
        json={
            "name": "Pwd User",
            "email": email,
            "role": "consumer",
            "password": "correct horse battery staple",
        },
    )
    assert reg.status_code == 200, reg.text
    first_api_key = reg.json()["api_key"]

    login = await client.post(
        "/v1/auth/login",
        json={"email": email, "password": "correct horse battery staple"},
    )
    assert login.status_code == 200, login.text
    body = login.json()
    assert body["email"] == email
    assert body["role"] == "consumer"
    # Login issues a fresh key, different from register-time key
    assert body["api_key"] != first_api_key

    # New key works
    probe = await client.get("/v1/compliance/documents", headers={"X-API-Key": body["api_key"]})
    assert probe.status_code == 200


@pytest.mark.asyncio
async def test_login_wrong_password_fails(client: AsyncClient):
    from secrets import token_hex

    email = f"pwd-bad-{token_hex(4)}@test.example"
    await client.post(
        "/v1/auth/register",
        json={
            "name": "Bad",
            "email": email,
            "role": "consumer",
            "password": "rightpass123",
        },
    )
    resp = await client.post(
        "/v1/auth/login",
        json={"email": email, "password": "wrongpass123"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email_fails(client: AsyncClient):
    resp = await client.post(
        "/v1/auth/login",
        json={"email": "nobody@test.example", "password": "whatever1"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_user_without_password_fails(client: AsyncClient):
    from secrets import token_hex

    email = f"nopwd-{token_hex(4)}@test.example"
    # Register without password
    await client.post(
        "/v1/auth/register",
        json={"name": "NoPwd", "email": email, "role": "consumer"},
    )
    resp = await client.post(
        "/v1/auth/login",
        json={"email": email, "password": "anything12"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_register_short_password_rejected(client: AsyncClient):
    resp = await client.post(
        "/v1/auth/register",
        json={
            "name": "Short",
            "email": "short@test.example",
            "role": "consumer",
            "password": "a",  # under 8 chars
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_provider_login_works(client: AsyncClient):
    from secrets import token_hex

    email = f"prov-{token_hex(4)}@test.example"
    reg = await client.post(
        "/v1/auth/register",
        json={
            "name": "Provider",
            "email": email,
            "role": "provider",
            "password": "providerpass1",
        },
    )
    assert reg.status_code == 200
    login = await client.post(
        "/v1/auth/login",
        json={"email": email, "password": "providerpass1"},
    )
    assert login.status_code == 200
    assert login.json()["role"] == "provider"
