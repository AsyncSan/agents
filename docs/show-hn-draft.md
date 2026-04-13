# Show HN Draft

## Title (max 80 chars)

**Option A:** Show HN: Agent marketplace with ephemeral compute and secret brokerage
**Option B:** Show HN: Run AI agents on isolated servers with trust scoring (EU-hosted)
**Option C:** Show HN: The commerce layer for AI agents (registry + ephemeral VMs + payments)

**Recommended: Option A** (most specific, hits keywords, intriguing)

---

## URL

https://agents.renemurrell.de

## Text

We built the missing commerce layer for AI agents.

**The problem:** Protocols exist (A2A, MCP). Orchestration exists (CrewAI, LangGraph). Compute exists (E2B, Modal). But there is no neutral marketplace where agents can be published, discovered, executed safely, and paid for.

**What this is:** A two-sided marketplace. Providers publish agents with capability cards (pricing, inputs, constraints). Consumers submit task contracts. The platform handles everything in between:

- Provisions a fresh ARM64 server from a pre-baked snapshot (~20s boot)
- Injects secrets via 3-path brokerage (consumer keys, provider keys, platform keys never cross boundaries)
- Runs the agent, collects results
- Destroys the server
- Updates a 5-factor trust score (success rate, duration accuracy, volume, recency, ratings)
- Captures payment via Stripe (20% platform fee)

**Why ephemeral VMs, not containers?** Full hardware isolation. When a consumer submits their API keys to run a third-party agent, those keys need real isolation. Container escapes are a well-documented attack surface. A fresh VM that is destroyed after use is the cleanest trust boundary.

**5 seed agents** ship with the platform: deep web research ($3), competitor analysis ($5), blog article writer ($2), GUI app benchmarking ($5), Python code review ($3). Each includes compute + LLM costs in the price.

**EU-native:** Hosted on Hetzner Cloud in Nuremberg, Germany. EU data residency by default, not as a feature toggle. With EU AI Act enforcement starting August 2026, we think this matters more than most people realize.

**Stack:** FastAPI, PostgreSQL, Hetzner Cloud API, Stripe, React 19, 204 tests. Apache 2.0.

We are two people working on this out of Berlin. Would love feedback on the marketplace model, pricing, and whether the secret brokerage approach makes sense to you.

GitHub: https://github.com/mylilcrowdi/agents

---

## Posting Notes

- Best time: Tuesday-Thursday, 8-10am ET (14-16 CET)
- Avoid Mondays (competition) and Fridays (low traffic)
- Be ready to answer comments for 4-6 hours
- Prepare answers for likely questions:
  - "Why not just use E2B?" (no marketplace, no trust, no payments)
  - "20% is steep" (App Store is 30%, includes compute + LLM)
  - "How do you handle malicious agents?" (ephemeral VMs, no SMTP, firewall, trust scoring)
  - "Why not containers?" (hardware isolation for credential safety)
  - "What about latency from EU?" (target audience is EU, US users can still use it)
