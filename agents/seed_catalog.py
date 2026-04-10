#!/usr/bin/env python3
"""Seed the AgentForge registry with initial agents.

Run: python agents/seed_catalog.py --api-url http://localhost:8400 --api-key af_xxx
"""

import argparse
import json
import sys

import httpx

SEED_AGENTS = [
    {
        "id": "deep-research",
        "name": "Deep Web Research Agent",
        "description": (
            "Performs comprehensive web research on any topic using curl, "
            "producing structured reports with sources, competitive analysis, "
            "and gap identification."
        ),
        "domain": "research",
        "tags": ["research", "web", "analysis", "report"],
        "inputs": [
            {"name": "topic", "type": "string", "required": True},
            {"name": "focus_areas", "type": "string", "required": False,
             "default": "all"},
        ],
        "outputs": [
            {"name": "output.md", "type": "markdown", "guaranteed": True},
        ],
        "runtime": {
            "snapshot_profile": "base",
            "server_type": "cax11",
            "model": "anthropic/claude-sonnet-4-6",
            "tools": ["shell"],
            "estimated_duration_seconds": 300,
            "estimated_cost_usd": 1.50,
        },
        "pricing": {"model": "per_execution", "base_price_usd": 3.00},
        "instructions": (
            "IMPORTANT: You are root. Run commands directly. Use curl for web research.\n\n"
            "# Research Mission: ${topic}\n\n"
            "Perform comprehensive research on the given topic.\n"
            "Focus areas: ${focus_areas}\n\n"
            "## Research Approach\n"
            "1. Use curl to fetch relevant web pages, blog posts, documentation\n"
            "2. Analyze and synthesize findings\n"
            "3. Identify key players, trends, and gaps\n\n"
            "## Output Format\n"
            "Write a comprehensive report as output.md with:\n"
            "- Executive Summary (3-5 bullet points)\n"
            "- Detailed findings per focus area\n"
            "- Competitive matrix (if applicable)\n"
            "- Gap analysis and opportunities\n"
            "- Sources with URLs\n\n"
            "Be specific with URLs, pricing, and adoption numbers where available."
        ),
    },
    {
        "id": "competitor-analysis",
        "name": "Market Competitor Analysis Agent",
        "description": (
            "Analyzes the competitive landscape for a product or market segment. "
            "Identifies competitors, pricing, features, strengths, weaknesses, "
            "and market positioning."
        ),
        "domain": "research",
        "tags": ["research", "market", "competitors", "strategy"],
        "inputs": [
            {"name": "product", "type": "string", "required": True},
            {"name": "market", "type": "string", "required": True},
        ],
        "outputs": [
            {"name": "output.md", "type": "markdown", "guaranteed": True},
        ],
        "runtime": {
            "snapshot_profile": "base",
            "server_type": "cax11",
            "model": "anthropic/claude-sonnet-4-6",
            "tools": ["shell"],
            "estimated_duration_seconds": 600,
            "estimated_cost_usd": 2.00,
        },
        "pricing": {"model": "per_execution", "base_price_usd": 5.00},
        "instructions": (
            "IMPORTANT: You are root. Run commands directly. Use curl for web research.\n\n"
            "# Competitor Analysis: ${product} in the ${market} market\n\n"
            "## Tasks\n"
            "1. Identify top 10-15 competitors\n"
            "2. For each: name, URL, pricing, features, target audience\n"
            "3. Create a feature comparison matrix\n"
            "4. Identify strengths and weaknesses of each\n"
            "5. Find market gaps and opportunities\n"
            "6. Provide pricing strategy recommendations\n\n"
            "## Output\n"
            "Write output.md with:\n"
            "- Market overview and size estimates\n"
            "- Competitor profiles (detailed)\n"
            "- Comparison matrix (table)\n"
            "- SWOT per competitor\n"
            "- Recommendations for positioning\n"
            "- All sources with URLs"
        ),
    },
    {
        "id": "blog-article-writer",
        "name": "Technical Blog Article Writer",
        "description": (
            "Writes well-researched, technical blog articles with SEO optimization. "
            "Produces markdown with frontmatter, internal linking suggestions, "
            "and meta descriptions."
        ),
        "domain": "content",
        "tags": ["blog", "writing", "seo", "content"],
        "inputs": [
            {"name": "title", "type": "string", "required": True},
            {"name": "keywords", "type": "string", "required": True},
            {"name": "target_audience", "type": "string", "required": False,
             "default": "developers"},
            {"name": "word_count", "type": "string", "required": False,
             "default": "2000"},
        ],
        "outputs": [
            {"name": "output.md", "type": "markdown", "guaranteed": True},
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
        "instructions": (
            "IMPORTANT: You are root. Run commands directly.\n\n"
            "# Write Blog Article: ${title}\n\n"
            "Target audience: ${target_audience}\n"
            "Target word count: ${word_count}\n"
            "Primary keywords: ${keywords}\n\n"
            "## Research Phase\n"
            "1. Use curl to research the topic thoroughly\n"
            "2. Find recent data, statistics, and examples\n"
            "3. Identify unique angles not covered by competitors\n\n"
            "## Writing Guidelines\n"
            "- Write in a clear, technical but accessible style\n"
            "- No em-dashes or en-dashes, use commas or periods instead\n"
            "- Use bold text with colons for list items (not dashes)\n"
            "- Include code examples where relevant\n"
            "- Add frontmatter: title, description, keywords, date\n"
            "- Suggest 3 internal linking opportunities\n\n"
            "## Output\n"
            "Write the complete article as output.md with YAML frontmatter."
        ),
    },
    {
        "id": "gui-benchmark",
        "name": "GUI Application Benchmark Agent",
        "description": (
            "Installs and benchmarks GUI applications on a fresh server. "
            "Captures screenshots, measures startup time, memory usage, "
            "and produces comparison reports."
        ),
        "domain": "benchmark",
        "tags": ["benchmark", "gui", "screenshots", "performance"],
        "inputs": [
            {"name": "app_a", "type": "string", "required": True},
            {"name": "app_b", "type": "string", "required": True},
            {"name": "category", "type": "string", "required": False,
             "default": "general"},
        ],
        "outputs": [
            {"name": "output.md", "type": "markdown", "guaranteed": True},
        ],
        "constraints": {
            "timeout_max": 2400,
        },
        "runtime": {
            "snapshot_profile": "gui",
            "server_type": "cax11",
            "model": "anthropic/claude-sonnet-4-6",
            "tools": ["shell"],
            "estimated_duration_seconds": 600,
            "estimated_cost_usd": 2.50,
        },
        "pricing": {"model": "per_execution", "base_price_usd": 5.00},
        "instructions": (
            "IMPORTANT: You are running as root on this server. You have FULL root access.\n"
            "You CAN and MUST run apt-get, service, dpkg, and all commands directly.\n\n"
            "# Benchmark: ${app_a} vs ${app_b}\n"
            "Category: ${category}\n\n"
            "## Setup\n"
            "1. Start Xvfb if not running: Xvfb :99 -screen 0 1920x1080x24 &\n"
            "2. export DISPLAY=:99\n"
            "3. Install both applications via apt-get or download\n\n"
            "## Benchmark Steps\n"
            "1. Measure cold startup time for each app\n"
            "2. Measure memory usage (RSS) after startup\n"
            "3. Take screenshots with scrot\n"
            "4. Test basic operations and measure responsiveness\n"
            "5. Compare UI/UX qualitatively\n\n"
            "## Output\n"
            "Write output.md with:\n"
            "- Installation notes\n"
            "- Startup time comparison\n"
            "- Memory usage comparison\n"
            "- Feature comparison matrix\n"
            "- Screenshots referenced\n"
            "- Verdict and recommendation"
        ),
    },
    {
        "id": "code-review-python",
        "name": "Python Code Review Agent",
        "description": (
            "Reviews Python code for security vulnerabilities, performance issues, "
            "code quality, and best practices. Clones a repo and produces a "
            "structured review report."
        ),
        "domain": "code-quality",
        "tags": ["code-review", "python", "security", "quality"],
        "inputs": [
            {"name": "repo_url", "type": "git_repo", "required": True},
            {"name": "branch", "type": "string", "required": False,
             "default": "main"},
            {"name": "focus", "type": "string", "required": False,
             "default": "security,performance,quality"},
        ],
        "outputs": [
            {"name": "output.md", "type": "markdown", "guaranteed": True},
            {"name": "findings.json", "type": "json", "guaranteed": False},
        ],
        "runtime": {
            "snapshot_profile": "base",
            "server_type": "cax11",
            "model": "anthropic/claude-sonnet-4-6",
            "tools": ["shell"],
            "estimated_duration_seconds": 300,
            "estimated_cost_usd": 1.50,
        },
        "pricing": {"model": "per_execution", "base_price_usd": 3.00},
        "instructions": (
            "IMPORTANT: You are root. Run commands directly.\n\n"
            "# Code Review: ${repo_url} (branch: ${branch})\n"
            "Focus areas: ${focus}\n\n"
            "## Setup\n"
            "1. Clone the repository: git clone ${repo_url} /workspace/repo\n"
            "2. cd /workspace/repo && git checkout ${branch}\n"
            "3. Understand the project structure\n\n"
            "## Review Steps\n"
            "1. **Security**: Check for injection, hardcoded secrets, unsafe deserialization\n"
            "2. **Performance**: Identify N+1 queries, unnecessary allocations, blocking I/O\n"
            "3. **Quality**: Check naming, structure, test coverage, error handling\n"
            "4. **Dependencies**: Check for known vulnerabilities, outdated packages\n\n"
            "## Output\n"
            "Write output.md with:\n"
            "- Summary (critical/high/medium/low counts)\n"
            "- Detailed findings with file:line references\n"
            "- Severity rating per finding\n"
            "- Suggested fixes\n"
            "- Overall assessment and score (1-10)\n\n"
            "Also write findings.json with structured finding objects."
        ),
    },
]


def seed(api_url: str, api_key: str, dry_run: bool = False) -> None:
    """Register seed agents via the API."""
    client = httpx.Client(
        base_url=api_url,
        headers={"X-API-Key": api_key, "Content-Type": "application/json"},
        timeout=30,
    )

    for agent_data in SEED_AGENTS:
        agent_id = agent_data["id"]
        print(f"  Registering {agent_id}...", end=" ")

        if dry_run:
            print("(dry-run, skipped)")
            continue

        resp = client.post("/v1/agents", json=agent_data)
        if resp.status_code == 201:
            print(f"OK (trust_score: {resp.json().get('trust_score')})")
        elif resp.status_code == 409:
            print("already exists, updating...")
            resp = client.put(f"/v1/agents/{agent_id}", json=agent_data)
            if resp.status_code == 200:
                print(f"  Updated OK")
            else:
                print(f"  Update failed: {resp.status_code} {resp.text}")
        else:
            print(f"FAILED: {resp.status_code} {resp.text}")

    # List registered agents
    resp = client.get("/v1/agents")
    if resp.status_code == 200:
        data = resp.json()
        print(f"\nCatalog: {data['total']} agents registered")
        for a in data["agents"]:
            print(f"  {a['id']}: {a['name']} (executions: {a['total_executions']})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed AgentForge catalog")
    parser.add_argument("--api-url", default="http://localhost:8400")
    parser.add_argument("--api-key", required=True, help="Provider API key")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    seed(args.api_url, args.api_key, args.dry_run)
