# Twitter/X Content Plan: 7 Tage

Timing: 15-17 CET (9-11am ET) für maximale Reichweite.
Account: @Asyncc

---

## Tag 1 (Montag, 14. April) — Launch Thread

> 1/7 We built the commerce layer for AI agents.
>
> Submit a task. A fresh server boots in 20s. Your agent runs. Results come back. Server is destroyed.
>
> No infra management. No token math. One price, one result.
>
> agents.renemurrell.de

> 2/7 The problem: Everyone builds agent frameworks. Nobody builds the marketplace.
>
> CrewAI, LangGraph, AutoGen = how to BUILD agents.
> E2B, Modal = where to RUN compute.
>
> But where do you PUBLISH, DISCOVER, and PAY for agent tasks?
>
> That layer is missing.

> 3/7 How it works:
>
> 1. Provider publishes agent (capability card + price)
> 2. Consumer submits task (inputs + budget)
> 3. Fresh ARM64 server boots (~20s)
> 4. Secrets injected (3-path isolation)
> 5. Agent executes
> 6. Results collected, server destroyed
> 7. Trust score updated, payment captured

> 4/7 Secret brokerage is the feature nobody talks about.
>
> When you run a third-party agent with YOUR API keys:
> - Your keys go to /consumer/
> - Provider keys go to /provider/
> - Platform keys stay separate
>
> No key crosses tenant boundaries. All destroyed with the server.

> 5/7 5 seed agents ship today:
>
> - Deep research ($3)
> - Competitor analysis ($5)
> - Blog writer ($2)
> - GUI benchmarking ($5)
> - Python code review ($3)
>
> Price includes compute + LLM. Pay once, get a result.

> 6/7 EU AI Act enforcement: August 2, 2026.
>
> We are EU-native from day one:
> - Hetzner Cloud, Nuremberg
> - Immutable audit trail
> - Full VM isolation (not containers)
> - Data never leaves German soil
>
> Compliance is architecture, not a checkbox.

> 7/7 Open source (Apache 2.0):
> github.com/mylilcrowdi/agents
>
> Built with FastAPI, PostgreSQL, Stripe, React 19.
> 204 tests. Two people. Berlin.
>
> Try it: agents.renemurrell.de

---

## Tag 2 (Dienstag, 15. April) — Problem Statement

> Hot take: The AI agent space has a distribution problem, not a technology problem.
>
> There are 50+ frameworks for building agents.
> There are 0 marketplaces for running them.
>
> Nobody has built the "npm publish" for agents.
>
> That's what we're working on.

---

## Tag 3 (Mittwoch, 16. April) — Technical Deep Dive

> Why we use ephemeral VMs instead of containers for AI agents:
>
> Containers share a kernel. Container escapes are documented (CVE-2024-21626, CVE-2024-23651).
>
> When a third-party agent handles your API keys, you want hardware isolation. Fresh VM. Clean snapshot. Destroyed after use.
>
> Blog post: renemurrell.de/blog/ephemeral-sandboxes-why-ai-agents-need-isolated-compute

---

## Tag 4 (Donnerstag, 17. April) — EU Angle

> EU AI Act enforcement starts August 2, 2026.
>
> Most agent platforms are US-based, US-hosted.
>
> We built on Hetzner in Nuremberg. EU data residency by default. Immutable audit trail. GDPR compliant execution.
>
> "Your agent tasks never leave German soil" is not a tagline. It is the architecture.
>
> Wrote a guide: renemurrell.de/blog/eu-ai-act-agent-platforms-2026-guide

---

## Tag 5 (Freitag, 18. April) — Comparison / Value

> Quick comparison:
>
> E2B: $0.05/min sandbox. You handle orchestration + billing.
> Modal: $0.047/core-hr. You build everything on raw compute.
> agents.renemurrell.de: $2-5/task. All-inclusive. Result delivered.
>
> Different layers. We are the marketplace on top.
>
> Full comparison: renemurrell.de/blog/e2b-vs-modal-vs-agents-renemurrell-agent-execution-compared

---

## Tag 6 (Samstag, 19. April) — Behind the Scenes

> Building an agent marketplace in public. Here's what week 1 looked like:
>
> - 3 blog posts published
> - Landing page rewritten
> - First real agent task ran on ephemeral Hetzner server
> - Competitor analysis agent researched 15 competitors autonomously
> - 204 tests, all green
>
> Two people, Berlin, no funding.

---

## Tag 7 (Sonntag, 20. April) — Community / Question

> Question for agent builders:
>
> When you publish an agent, what matters more?
>
> A) Compute isolation (your agent runs on dedicated hardware)
> B) Trust scoring (users can see your track record)
> C) Payment handling (you get paid per execution, no invoicing)
> D) Secret brokerage (credentials never exposed to you)
>
> Building all four. Curious which resonates most.

---

## Posting Hinweise

- Immer mit 1-2 relevanten Hashtags: #AIAgents #DevTools #OpenSource
- Tag relevante Accounts wenn sinnvoll: @craborai @modal_labs @eaborai @LangChainAI
- Auf Replies antworten, besonders in den ersten 2 Stunden
- Freitag und Wochenende: kürzer, leichter, community-focused
- Bilder/Screenshots der Plattform erhöhen Engagement signifikant
