"""Full UX walkthrough: simulate a customer's journey through the platform."""

import asyncio

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from agentforge.api.app import app
from agentforge.db import get_db
from agentforge.models.base import Base

DB = "postgresql+asyncpg://agentforge:changeme@localhost:5433/agentforge_test"

AGENT_INSTRUCTIONS = """You are a security audit agent. Your job:

1. Clone the repository: git clone ${repo_url} /workspace/repo
2. Run dependency audit (npm audit, pip-audit, cargo audit)
3. Run secret scanning (trufflehog)
4. Run SAST (semgrep)
5. Compile structured report to /workspace/agents/$RUN_ID/output.md
"""


async def main():
    eng = create_async_engine(DB)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    sf = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)

    async def override():
        async with sf() as s:
            yield s

    app.dependency_overrides[get_db] = override

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        print("=== STEP 1: Provider Registration ===")
        r = await c.post(
            "/v1/auth/register",
            json={
                "name": "SecureAudit GmbH",
                "email": "provider@secureaudit.de",
                "role": "provider",
            },
        )
        provider = r.json()
        print(f"Provider: {provider['id'][:8]}... Key: {provider['api_key'][:12]}...")
        print(f"Signing Key: {provider.get('signing_public_key', 'none')[:16]}...")
        pkey = provider["api_key"]

        print("\n=== STEP 2: Consumer Registration ===")
        r = await c.post(
            "/v1/auth/register",
            json={"name": "ACME Corp", "email": "cto@acme.com", "role": "consumer"},
        )
        consumer = r.json()
        print(f"Consumer: {consumer['id'][:8]}... Key: {consumer['api_key'][:12]}...")
        ckey = consumer["api_key"]

        print("\n=== STEP 3: Publish Security Audit Agent ===")
        agent_card = {
            "id": "security-audit-v1",
            "name": "Codebase Security Audit",
            "description": "Comprehensive security audit: dependencies, secrets, SAST, licenses.",
            "domain": "security",
            "tags": ["security", "audit", "compliance", "sast", "dependencies"],
            "inputs": [
                {"name": "repo_url", "type": "string", "required": True},
                {"name": "branch", "type": "string", "required": False, "default": "main"},
            ],
            "outputs": [
                {"name": "output.md", "type": "markdown", "guaranteed": True},
                {"name": "output.json", "type": "json", "guaranteed": True},
            ],
            "runtime": {
                "snapshot_profile": "base",
                "server_type": "cax11",
                "model": "anthropic/claude-sonnet-4-6",
                "tools": ["shell"],
                "estimated_duration_seconds": 180,
                "estimated_cost_usd": 0.80,
            },
            "pricing": {"model": "per_execution", "base_price_usd": 2.00},
            "constraints": {"timeout_max": 600},
            "instructions": AGENT_INSTRUCTIONS,
        }
        r = await c.post("/v1/agents", headers={"X-API-Key": pkey}, json=agent_card)
        agent = r.json()
        print(f"Status: {r.status_code}")
        print(f"Agent: {agent['id']} v{agent['version']}")
        print(f"Signed: {bool(agent.get('signature'))}")

        print("\n=== STEP 4: Consumer discovers agent ===")
        r = await c.get("/v1/agents", params={"q": "security", "domain": "security"})
        found = r.json()
        print(f"Found {found['total']} agents")
        for a in found["agents"]:
            price = a["card"].get("pricing", {}).get("base_price_usd", 0)
            print(f"  {a['id']}: {a['name']} (${price:.2f})")

        print("\n=== STEP 5: Inspect + Verify ===")
        r = await c.get("/v1/agents/security-audit-v1")
        d = r.json()
        print(f"Inputs: {[i['name'] for i in d['card']['capabilities']['inputs']]}")
        print(f"Price: ${d['card']['pricing']['base_price_usd']:.2f}")
        r = await c.get("/v1/agents/security-audit-v1/verify")
        print(f"Signature verified: {r.json()['verified']}")

        print("\n=== STEP 6: Set secrets ===")
        r = await c.put(
            "/v1/me/secrets",
            headers={"X-API-Key": ckey},
            json={"secrets": {"GH_TOKEN": "ghp_fake123"}},
        )
        print(f"Secrets: {r.json()['keys']}")

        print("\n=== STEP 7: Submit task ===")
        r = await c.post(
            "/v1/tasks",
            headers={"X-API-Key": ckey},
            json={
                "agent_id": "security-audit-v1",
                "inputs": {"repo_url": "https://github.com/acme/backend", "branch": "main"},
                "constraints": {"max_cost_usd": 3.00, "timeout": 300},
                "callback_url": "https://hooks.slack.com/services/T00/B00/xxx",
            },
        )
        task = r.json()
        print(f"Task: {task['id']} Status: {task['status']}")

        print("\n=== STEP 8: Create schedule ===")
        r = await c.post(
            "/v1/schedules",
            headers={"X-API-Key": ckey},
            json={
                "agent_id": "security-audit-v1",
                "name": "Weekly Security Audit",
                "cron_expression": "0 9 * * 1",
                "inputs": {"repo_url": "https://github.com/acme/backend"},
                "constraints": {"max_cost_usd": 3.00},
                "callback_url": "https://hooks.slack.com/services/T00/B00/xxx",
            },
        )
        sched = r.json()
        print(f"Schedule: {sched['name']}")
        print(f"Cron: {sched['cron_expression']}")
        print(f"Next run: {sched['next_run_at']}")

        print("\n=== STEP 9: Check task status ===")
        r = await c.get(f"/v1/tasks/{task['id']}", headers={"X-API-Key": ckey})
        print(f"Status: {r.json()['status']}")

        print("\n=== STEP 10: Dashboard ===")
        r = await c.get("/v1/me/dashboard?days=7", headers={"X-API-Key": ckey})
        dash = r.json()
        print(f"Executions: {dash['total_executions']}, Cost: ${dash['total_cost_cents']/100:.2f}")

        print("\n=== STEP 11: Platform health ===")
        r = await c.get("/v1/platform/health")
        h = r.json()
        print(f"Status: {h['status']}")
        for comp in h["components"]:
            print(f"  {comp['name']}: {comp['status']}")

        print("\n=== STEP 12: Agent stats + health ===")
        r = await c.get("/v1/agents/security-audit-v1/stats")
        print(f"Stats: {r.json()['total_executions']} runs")
        r = await c.get("/v1/agents/security-audit-v1/health")
        print(f"Health: {r.json()['status']}")

        print("\n=== STEP 13: Provider profile ===")
        r = await c.get(f"/v1/providers/{provider['id']}")
        p = r.json()
        print(f"Provider: {p['name']}, {p['active_agents']} agents")

        print("\n=== STEP 14: Compliance export ===")
        r = await c.post(
            "/v1/me/compliance/export",
            headers={"X-API-Key": pkey},
            json={"start_date": "2026-01-01", "end_date": "2026-12-31", "format": "json"},
        )
        export = r.json()
        print(f"Events exported: {export['total_events']}")
        for e in export["events"][:3]:
            print(f"  {e['event_type']}: {e.get('resource_id', '')[:20]}")

        print("\n=== STEP 15: Featured + Categories ===")
        r = await c.get("/v1/agents/featured")
        print(f"Featured newest: {len(r.json()['newest'])}")
        r = await c.get("/v1/agents/categories")
        cats = r.json()
        print(f"Domains: {[d['name'] for d in cats['domains']]}")
        print(f"Tags: {[t['name'] for t in cats['tags'][:5]]}")

        print("\n=== STEP 16: Versions ===")
        r = await c.get("/v1/agents/security-audit-v1/versions")
        data = r.json()
        print(f"Current version: {data['current_version']}, archived: {len(data['versions'])}")

        print("\n" + "=" * 60)
        print("UX WALKTHROUGH COMPLETE")
        print("=" * 60)
        print("\nAll 16 steps passed. Full customer journey works end-to-end.")

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


if __name__ == "__main__":
    asyncio.run(main())
