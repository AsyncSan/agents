# agents.renemurrell.de — Market Research & Strategy

**Stand:** 2026-04-12
**Recherchiert via:** Hetzner Agent (competitor-analysis) + Claude Code Deep Research

---

## 1. Executive Summary

agents.renemurrell.de ist eine AI Agent Commerce Platform: Registry + Ephemeral Compute + Payments + Trust Scoring. Providers publishen Agents, Consumers submitten Tasks, die Plattform provisioniert isolierte Hetzner Server pro Execution mit Secret Brokerage und automatischem Teardown. 20% Platform Fee. EU-basiert.

**Kernaussage:** Kein Competitor bietet die Kombination aus neutralem Marketplace + ephemerer VM-Isolation + Secret Brokerage + Trust Scoring + Fiat Payments. Die Commerce-Schicht für AI Agents fehlt komplett.

---

## 2. Competitive Landscape

### 2.1 Segmente & Competitors (15 profiled)

| Kategorie | Competitors | Was sie machen | Was fehlt |
|---|---|---|---|
| **Ephemeral Compute** | E2B, Modal, Fly.io | Raw Compute (Sandboxes, Serverless, VMs) | Kein Registry, kein Marketplace, kein Billing |
| **Agent Orchestration** | CrewAI, AutoGen, LangGraph, Langbase | Agent-Building Frameworks | Kein Hosting, keine Payments, keine Isolation |
| **Agent Marketplaces** | Relevance AI, AgentOps, Wordware | Discovery + Low-Code Agents | Keine isolierte Execution, kein Trust Scoring |
| **Crypto Agent Networks** | OLAS/Autonolas, Fetch.ai, SingularityNET | Dezentrale Agent-Registries | Enterprise-hostile, kein ephemeres Compute |
| **Enterprise** | AWS Bedrock Agents, Google Vertex Agent Builder, Azure Foundry | Hyperscaler Agent Platforms | Vendor Lock-in, kein neutraler Marketplace |

### 2.2 Pricing Matrix

| Provider | Modell | Einstieg | Pro Execution | Inkludiert |
|---|---|---|---|---|
| **E2B** | Per-second compute | $150/mo (Pro) | ~$0.05/min (1 vCPU) | Sandboxed VMs, Storage |
| **Modal** | Per-second compute | $250/mo (Team) | $0.047/core/hr CPU | Serverless Container, GPUs |
| **Fly.io** | Per-second VMs | ~$2/mo (kleinste VM) | $0.0028/sec | Edge VMs, Volumes |
| **CrewAI** | Per-execution | 50 free/mo | $0.50/execution | Visual Editor, Orchestration |
| **LangSmith** | Per-trace | $39/seat/mo | $2.50/1k traces | Observability, Deployments |
| **Langbase** | Subscription | $100/mo | Credits-basiert | Pipes, Memory (RAG) |
| **Relevance AI** | Per-action | $19/mo (Pro) | 200 actions inkl. | 2000+ Integrations |
| **AgentOps** | Per-event | $40/mo (Pro) | 5,000 events free | LLM Cost Tracking |
| **AWS Bedrock** | Token consumption | Pay-as-you-go | $0.02-0.15/call | Orchestration free, Token-Kosten |
| **Google Vertex** | vCPU-hour + Tokens | $300 Credits | $0.086/vCPU-hr | Agent Engine, Gemini |
| **Azure Foundry** | Token consumption | Free to explore | Token costs only | Orchestration free |
| **agents.renemurrell.de** | **Per-execution** | **TBD** | **$2-5 flat** | **Compute + LLM + Result** |

**Einordnung:** $2-5/Execution ist All-inclusive (Compute + LLM + Result). CrewAI am nächsten ($0.50, aber ohne Compute/LLM). Hyperscaler $0 für Orchestration, nur Token-Kosten. Vorteil: Kein Token-Math, kein Infra-Management, ein Preis, ein Ergebnis.

**Risiko:** Power User finden $2/Execution teuer vs. Raw Infra ($0.01-0.05 auf Modal). Volume Tier oder Subscription mit inkludierten Executions notwendig.

**Empfehlung Pricing-Staffelung:**
- 20% Take Rate bis $5K/mo GMV
- 15% ab $5K/mo
- 10% ab $25K/mo

---

## 3. Market Sizing (TAM/SAM/SOM)

### Datenquellen
- MarketsandMarkets: AI Agents Market $52.6B by 2030
- Grand View Research: AI Agents $50.3B by 2030 (CAGR 45.8%)
- IDC: EU AI Spending 34% CAGR through 2029
- Infra-Layer = 30-40% vom Gesamtmarkt

### Projektion

| | 2026 | 2028 | 2030 |
|---|---|---|---|
| **TAM** (Global Agent Infra) | $3.5B | ~$9B | ~$18B |
| **SAM** (EU Agent Compute/Marketplace) | $700M-770M | $1.5B-2B | $3.6B-4B |
| **SOM** (Year 1, bootstrapped) | $120K-240K ARR | - | - |
| **SOM Stretch** | $480K-720K ARR | - | - |

### Year-1 Unit Economics
- 100 aktive Devs x $200/mo Plattform-Spend = $240K ARR
- Bei 20% Take Rate: $1.2M GMV nötig
- Stretch: 200-300 Devs = $480K-720K ARR

### Kontext
- CrewAI: 5.2M Downloads/Monat
- LangGraph: 47M Downloads/Monat
- EU hat nur 5% des globalen AI Compute (EUobserver)
- Partnering mit EU Cloud (Hetzner, OVH, Scaleway) = Differentiator

---

## 4. Strategic Positioning

### 4.1 Unique Value Proposition

**"App Store for AI Agents, not Xcode."**

Nicht Agents bauen, sondern die Plattform sein. CrewAI/LangGraph/AutoGen Agent-Creation überlassen, Discovery/Execution/Payment Layer ownen.

### 4.2 Core Differentiators

1. **Secret Brokerage:** Agent-to-Agent Credential Delegation ohne API Key Exposure. Runtime-Injection, Post-Execution Destruction.
2. **Ephemeral Compute:** Jeder Task auf frischem Server. VPC Isolation, Firewall, kein SMTP Egress. Zero Trail.
3. **Trust Scoring:** 5-Faktor gewichtet (Success Rate 35%, Duration Accuracy 25%, Volume 20%, Recency 10%, Ratings 10%). Nach 100+ Runs entsteht ein Moat.
4. **EU Data Residency:** "Your agent tasks never leave German soil." Fast alle Competitors US-basiert.
5. **Fiat Payments:** Stripe, kein Crypto. Enterprise-friendly.

### 4.3 EU AI Act Angle

- Enforcement: 2. August 2026
- Verpflichtungen phasen bis 2027 ein
- Compliance-as-a-Feature: Audit Trail (Event Log), Execution Isolation, Data Residency
- Positionierung: EU-native Plattform, built for compliance from day one

### 4.4 Top Strategic Move

**Google A2A Protocol implementieren.** Erster Non-Hyperscaler Marketplace mit A2A Support = signifikanter Vorteil für Agent Interoperability.

---

## 5. SEO & Content Strategy

### 5.1 Target Keywords

**Transactional (kaufbereit):**
- ai agent marketplace
- ai agent as a service
- ai agent hosting
- deploy ai agent
- ai agent execution platform
- agent sandbox environment
- run ai agent cloud

**Competitor-Compare (hochkonvertierend):**
- CrewAI alternative
- E2B alternative europe
- modal labs alternative

**EU/Compliance (Nische, wenig Competition):**
- eu compliant ai platform
- eu ai act compliant saas
- ai agent platform europe

### 5.2 Content Pillars

1. **Agent Infrastructure** (technisch, Dev-Audience)
2. **EU AI Compliance** (EU-native Positioning, AI Act Guides)
3. **Agent Commerce** (Marketplace-Ökonomie, Pricing, Monetisierung)

### 5.3 Blog Post Roadmap (10 Artikel)

1. "E2B vs Modal vs agents.renemurrell.de: Agent Execution Compared"
2. "Deploy a CrewAI Agent to Production in 5 Minutes"
3. "EU AI Act: What It Means for Agent Platforms (2026 Guide)"
4. "Ephemeral Sandboxes: Why Your AI Agent Needs Isolated Compute"
5. "GDPR-Compliant Agent Execution: A Technical Walkthrough"
6. "From LLM Wrapper to Autonomous Agent: The Infrastructure Gap"
7. "Agent Pricing Models: Per-Task, Per-Minute, or Subscription?"
8. "Running Untrusted Agent Code Safely: Sandbox Patterns"
9. "Building an Agent Marketplace: Architecture Decisions"
10. "Why EU-Based AI Infrastructure Matters for Enterprise"

### 5.4 Distribution (ROI-Ranking, bootstrapped)

1. **Hacker News** — Show HN, Agent-Threads kommentieren. Free, High Leverage.
2. **Reddit** — r/LocalLLaMA, r/artificial, r/selfhosted. Genuine Participation.
3. **Dev Twitter/X** — Technical Threads, Demo Videos.
4. **DEV.to / Hashnode** — Blog Cross-posting, free Distribution.
5. **GitHub** — SDK/Runtime open-sourcen. README drives Signups.
6. **Product Hunt** — One-shot Launch.
7. **LinkedIn** — EU Enterprise Angle, Compliance Narrative.
8. **Podcasts** — Latent Space, Practical AI, AI Engineering.

### 5.5 PR Angles

| Publikation | Story |
|---|---|
| **Sifted, Heise, The Register** | "EU-native Alternative zu US Agent Infrastructure" |
| **TechCrunch** | "The Agent Economy Needs a Marketplace, Not Just SDKs" |
| **t3n, iX Magazin** | "Deutsche Plattform für AI Agent Commerce" |
| **The New Stack** | "Ephemeral Compute for Untrusted AI" |

---

## 6. 30-Tage Roadmap (Empfehlung)

### Woche 1-2: Foundation
- [ ] CLI Tool (`agentforge publish`, `agentforge run`) fertigstellen
- [ ] Dispatcher Bug fixen (output.md Collection vom OpenClaw Workspace)
- [ ] SSH Key Management für Production automatisieren
- [ ] Schedules-Migration auf Production deployen
- [ ] Volume Pricing Tier implementieren

### Woche 2-3: Content & Launch Prep
- [ ] Blog Post #1: "E2B vs Modal vs agents.renemurrell.de"
- [ ] Blog Post #3: "EU AI Act: What It Means for Agent Platforms"
- [ ] GitHub Repo aufräumen, README mit Value Prop
- [ ] Product Hunt Listing vorbereiten

### Woche 3-4: Go-to-Market
- [ ] Show HN Post
- [ ] Reddit Threads (r/LocalLLaMA, r/artificial)
- [ ] Twitter/X Launch Thread
- [ ] Heise/t3n Pitch senden
- [ ] A2A Protocol Support evaluieren

---

## 7. Quellen

- [MarketsandMarkets: AI Agents Market $52.62B by 2030](https://www.marketsandmarkets.com/PressReleases/ai-agents.asp)
- [Grand View Research: AI Agents $50.31B by 2030](https://www.prnewswire.com/news-releases/ai-agents-market-size-to-hit-50-31-billion-by-2030-at-cagr-45-8---grand-view-research-inc-302447060.html)
- [IDC: EU AI Spending 34% CAGR](https://www.telecompaper.com/news/european-ai-spending-set-for-34-cagr-from-2025-2029-idc--1567431)
- [Forrester: Europe 2026 Tech Spend](https://www.forrester.com/blogs/europes-2026-tech-spend-exceeds-e1-5-trillion-driven-by-ai-cloud-and-sovereignty/)
- [EUobserver: EU 5% of global AI compute](https://euobserver.com/202965/why-is-the-eu-struggling-to-scale-artificial-intelligence/)
- [E2B Pricing](https://e2b.dev/pricing)
- [Modal Pricing](https://modal.com/pricing)
- [CrewAI Pricing](https://www.crewai.com/pricing)
- [LangChain Pricing](https://www.langchain.com/pricing)
- [AWS Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)
