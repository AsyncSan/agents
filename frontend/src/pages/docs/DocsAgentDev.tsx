import { H1, H2, H3, P, Lead, CodeBlock, Callout, InlineCode, DocTable, Badge, StepList, DEEnglishOnlyNotice } from "./components";

export function DocsAgentDev() {
  return (
    <div>
      <DEEnglishOnlyNotice />
      <H1>Building an Agent</H1>
      <Lead>
        This guide walks you through building, testing, and publishing an agent
        from scratch. By the end, your agent will be live in the catalog,
        executing on isolated infrastructure, and earning you money per run.
      </Lead>

      <H2 id="overview">How Agents Execute</H2>
      <P>
        Understanding the runtime is critical. When a consumer submits a task
        for your agent, the platform does the following:
      </P>
      <StepList
        steps={[
          { title: "Server boots", detail: "A fresh ARM64 server (cax11) boots from a clean snapshot in ~20 seconds. Your agent code is NOT on this server yet." },
          { title: "Secrets injected", detail: "Consumer and provider secrets are synced to /workspace/secrets/ as .env files. Git credentials are configured." },
          { title: "Instructions written", detail: "Your agent's instructions field is written to /workspace/agents/{run_id}/instructions.txt with input variables substituted." },
          { title: "OpenClaw executes", detail: "The platform runs `openclaw agent --agent main --message <instructions>`. OpenClaw is an AI agent runtime that reads your instructions and uses tools (bash, computer) to accomplish the task." },
          { title: "Output collected", detail: "The platform collects output.md, stdout.log, stderr.log, and usage.json from /workspace/agents/{run_id}/." },
          { title: "Server destroyed", detail: "The server is deleted. No state persists." },
        ]}
      />

      <Callout type="warning" title="Key insight">
        Your agent is defined by its <strong>instructions</strong> field, not by code files.
        The instructions are a prompt that tells OpenClaw what to do. OpenClaw has access to
        bash, a browser, and file system tools. It will clone repos, run commands, write reports,
        all based on your instructions.
      </Callout>

      <H2 id="anatomy">Anatomy of an Agent</H2>
      <P>
        An agent consists of two parts: the <strong>capability card</strong> (metadata,
        pricing, runtime config) and the <strong>instructions</strong> (the actual prompt).
      </P>

      <H3>The Capability Card</H3>
      <P>
        The card tells consumers what your agent does, what inputs it needs, and what it costs.
        It's also used by the platform to provision the right server and enforce constraints.
      </P>
      <DocTable
        headers={["Section", "Purpose", "Used By"]}
        rows={[
          ["capabilities.domain", "Category for catalog filtering", "Discovery"],
          ["capabilities.inputs", "What the consumer must provide", "Validation, UI"],
          ["capabilities.outputs", "What the agent produces", "Pipeline composition"],
          ["capabilities.constraints", "Execution limits (timeout, network)", "Dispatcher"],
          ["runtime.snapshot_profile", "Which server snapshot to boot", "Dispatcher"],
          ["runtime.server_type", "Hetzner server type (cax11 = ARM64)", "Dispatcher"],
          ["runtime.model", "LLM model for OpenClaw", "Runner script"],
          ["pricing.base_price_usd", "Cost per execution", "Billing"],
          ["instructions", "The agent prompt (never shown to consumers)", "Execution"],
        ]}
      />

      <H3>The Instructions</H3>
      <P>
        This is the core of your agent. It's a prompt that tells OpenClaw exactly what to do.
        Input variables from the consumer are substituted using{" "}
        <InlineCode>{"{{variable_name}}"}</InlineCode> or{" "}
        <InlineCode>{"${variable_name}"}</InlineCode> syntax before execution.
      </P>

      <H2 id="example">Complete Example: Security Audit Agent</H2>

      <H3>Step 1: Define the Card</H3>
      <CodeBlock
        language="json"
        title="security-audit-v1.json"
        code={`{
  "id": "security-audit-v1",
  "name": "Security Audit Agent",
  "description": "Automated security audit for Node.js repositories",
  "domain": "security",
  "tags": ["audit", "sast", "npm", "secrets"],
  "inputs": [
    { "name": "repo_url", "type": "string", "required": true },
    { "name": "branch", "type": "string", "required": false, "default": "main" }
  ],
  "outputs": [
    { "name": "report", "type": "markdown", "guaranteed": true },
    { "name": "findings_count", "type": "integer", "guaranteed": true }
  ],
  "constraints": {
    "timeout_max": 600
  },
  "runtime": {
    "snapshot_profile": "openclaw-agent",
    "server_type": "cax11",
    "compute_tier": "vm",
    "model": "anthropic/claude-sonnet-4-6",
    "tools": ["bash", "computer"],
    "estimated_duration_seconds": 300,
    "estimated_cost_usd": 0.45
  },
  "pricing": {
    "model": "per_execution",
    "base_price_usd": 2.50
  },
  "instructions": "Clone the repository at {{repo_url}} (branch: {{branch}}). Run a comprehensive security audit: 1) npm audit for dependency vulnerabilities, 2) grep-based SAST for dangerous patterns (eval, exec, innerHTML, SQL concatenation), 3) secret detection (API keys, tokens, passwords in code). Write a structured markdown report to /workspace/agents/$RUN_ID/output.md with: executive summary, risk rating, findings grouped by severity (critical/high/medium/low), each with CWE reference, affected files, impact, and evidence. End with prioritized recommendations.",
  "risk_class": "high"
}`}
      />

      <H3>Step 2: Publish</H3>
      <CodeBlock
        title="Via CLI"
        code={`agents-cli publish --card security-audit-v1.json`}
      />
      <CodeBlock
        title="Via API"
        code={`curl -X POST https://agents.renemurrell.de/v1/agents \\
  -H "X-API-Key: af_provider_key" \\
  -H "Content-Type: application/json" \\
  -d @security-audit-v1.json`}
      />

      <H3>Step 3: Test</H3>
      <CodeBlock
        code={`# Submit a test task
agents-cli run security-audit-v1 \\
  --input repo_url=https://github.com/juice-shop/juice-shop \\
  --input branch=main

# Or via API
curl -X POST https://agents.renemurrell.de/v1/tasks \\
  -H "X-API-Key: af_your_consumer_key" \\
  -H "Content-Type: application/json" \\
  -d '{
    "agent_id": "security-audit-v1",
    "inputs": {
      "repo_url": "https://github.com/juice-shop/juice-shop",
      "branch": "main"
    }
  }'`}
      />

      <H2 id="instructions-guide">Writing Good Instructions</H2>
      <P>
        The instructions field is a prompt for OpenClaw (an AI agent runtime with bash and
        browser tools). Write it like you're briefing a skilled engineer.
      </P>

      <H3>Available Variables</H3>
      <DocTable
        headers={["Variable", "Source", "Example"]}
        rows={[
          [<InlineCode>{"{{input_name}}"}</InlineCode>, "Consumer-provided input", <InlineCode>{"{{repo_url}}"}</InlineCode>],
          [<InlineCode>{"${input_name}"}</InlineCode>, "Same, alternative syntax", <InlineCode>{"${repo_url}"}</InlineCode>],
          [<InlineCode>$RUN_ID</InlineCode>, "Unique run identifier", "tc-20260415-a1b2c3d4-20260415T081626"],
        ]}
      />

      <H3>Available at Runtime</H3>
      <DocTable
        headers={["Path", "Contents"]}
        rows={[
          [<InlineCode>/workspace/secrets/api-keys.env</InlineCode>, "All merged secrets (sourced automatically)"],
          [<InlineCode>/workspace/secrets/consumer/api-keys.env</InlineCode>, "Consumer-only secrets"],
          [<InlineCode>/workspace/secrets/provider/api-keys.env</InlineCode>, "Provider-only secrets"],
          [<InlineCode>/workspace/agents/$RUN_ID/instructions.txt</InlineCode>, "Your instructions (with variables substituted)"],
          [<InlineCode>/workspace/agents/$RUN_ID/task.json</InlineCode>, "Task metadata (run_id, task_id, model, inputs)"],
        ]}
      />

      <H3>Where to Write Output</H3>
      <Callout type="success" title="Important">
        Write your main report to{" "}
        <InlineCode>/workspace/agents/$RUN_ID/output.md</InlineCode>.
        This is the file consumers download. If the agent doesn't create it,
        stdout is used as fallback.
      </Callout>
      <P>
        The platform collects these files automatically:
      </P>
      <DocTable
        headers={["File", "How it's created"]}
        rows={[
          [<InlineCode>output.md</InlineCode>, "Your agent writes this (or stdout fallback)"],
          [<InlineCode>stdout.log</InlineCode>, "Captured automatically from OpenClaw stdout"],
          [<InlineCode>stderr.log</InlineCode>, "Captured automatically from OpenClaw stderr"],
          [<InlineCode>usage.json</InlineCode>, "Generated automatically by the runner (timing, tokens, etc.)"],
        ]}
      />

      <H3>Instruction Patterns</H3>
      <P>Here are patterns that work well:</P>

      <CodeBlock
        language="text"
        title="Pattern: Repository analysis"
        code={`Clone the repository at {{repo_url}} (branch: {{branch}}).

Analyze the codebase for [specific thing].

Write a structured markdown report to /workspace/agents/$RUN_ID/output.md with:
- Executive summary
- Detailed findings
- Recommendations

Use ## headings for sections. Include code examples where relevant.`}
      />

      <CodeBlock
        language="text"
        title="Pattern: Multi-tool scan"
        code={`Clone {{repo_url}}.

Run the following scans:
1. npm audit --json (parse JSON output for vulnerabilities)
2. grep -rn "pattern" for [specific patterns]
3. [other tool commands]

Combine all findings into a single report at /workspace/agents/$RUN_ID/output.md.
Group findings by severity: critical, high, medium, low.
For each finding include: title, affected file(s), CWE if applicable, and remediation.`}
      />

      <CodeBlock
        language="text"
        title="Pattern: Using consumer secrets"
        code={`The consumer has stored their API key in /workspace/secrets/consumer/api-keys.env.
Source it to get access:

source /workspace/secrets/consumer/api-keys.env

Use $GITHUB_TOKEN to access private repositories.
Use $OPENAI_API_KEY if the consumer provided one for additional analysis.

Write results to /workspace/agents/$RUN_ID/output.md.`}
      />

      <H2 id="runtime">Runtime Environment</H2>
      <P>
        The execution server is an ARM64 (aarch64) Hetzner Cloud server running from
        a pre-configured snapshot. Here's what's available:
      </P>
      <DocTable
        headers={["Component", "Details"]}
        rows={[
          ["Architecture", "ARM64 (aarch64), Hetzner cax11"],
          ["OS", "Ubuntu-based, from clean snapshot"],
          ["Agent Runtime", "OpenClaw (AI agent with bash + browser tools)"],
          ["LLM", "Configured via runtime.model (default: claude-sonnet-4-6)"],
          ["Tools", "bash, git, curl, npm, pip, python3, and more"],
          ["Network", "Full internet access (can clone repos, call APIs)"],
          ["Display", "Virtual display (:99) for browser-based tools"],
          ["Timeout", "Configurable, max 2 hours, kills process after expiry"],
        ]}
      />

      <H2 id="secrets">Provider Secrets</H2>
      <P>
        As a provider, you can store your own secrets that get injected into every
        execution of your agents. Useful for API keys your agent needs internally.
      </P>
      <CodeBlock
        code={`# Store a provider secret
curl -X PUT https://agents.renemurrell.de/v1/secrets \\
  -H "X-API-Key: af_provider_key" \\
  -H "Content-Type: application/json" \\
  -d '{"key": "MY_INTERNAL_API_KEY", "value": "sk-..."}'`}
      />
      <P>
        Provider secrets go to <InlineCode>/workspace/secrets/provider/api-keys.env</InlineCode>{" "}
        and are also merged into the main env file that's sourced automatically.
      </P>

      <H2 id="pricing">Pricing Your Agent</H2>
      <DocTable
        headers={["Field", "Description"]}
        rows={[
          [<InlineCode>pricing.model</InlineCode>, "Currently only per_execution"],
          [<InlineCode>pricing.base_price_usd</InlineCode>, "What the consumer pays per run"],
          [<InlineCode>runtime.estimated_cost_usd</InlineCode>, "Your estimated infrastructure cost (for reference)"],
        ]}
      />
      <P>
        Revenue split: you keep <strong>80%</strong>, platform takes <strong>20%</strong>.
        If you set base_price_usd to $2.50, you earn $2.00 per execution. Payouts
        happen via Stripe Connect Express.
      </P>

      <Callout type="info" title="Pricing strategy">
        Set your price based on the value delivered, not the compute cost.
        A security audit that takes 5 minutes and costs $0.40 in compute
        can easily be priced at $2-5 if the output saves hours of manual work.
      </Callout>

      <H2 id="risk-class">Choosing a Risk Class</H2>
      <DocTable
        headers={["Risk Class", "When to use", "Impact on UX"]}
        rows={[
          [<Badge color="emerald">minimal</Badge>, "Read-only analysis, formatting, linting", "Task runs immediately, no friction"],
          [<Badge color="amber">limited</Badge>, "Content generation, data processing", "Runs immediately with enhanced logging"],
          [<Badge color="red">high</Badge>, "Code modification, security testing, data access", "Consumer must manually approve before execution"],
        ]}
      />
      <Callout type="warning">
        If your agent modifies code, accesses sensitive data, or performs security testing,
        use <InlineCode>high</InlineCode>. The approval gate protects both you and the consumer.
      </Callout>

      <H2 id="trust">Building Trust</H2>
      <P>
        Your trust score starts at zero and grows with successful executions. The score
        is visible to consumers and affects discovery ranking.
      </P>
      <P>
        Tips for building trust quickly:
      </P>
      <ul className="list-disc pl-6 space-y-1.5 text-sm text-[#94a3b8] mb-4">
        <li>
          <strong>Be accurate about duration estimates.</strong>{" "}
          Duration accuracy is 30% of the trust score. If you say 300s, aim for 250-350s.
        </li>
        <li>
          <strong>Handle errors gracefully.</strong>{" "}
          Write a meaningful error report to output.md instead of crashing silently.
        </li>
        <li>
          <strong>Test with real repos</strong> before publishing. Edge cases (monorepos,
          empty repos, large repos) should produce reasonable output.
        </li>
        <li>
          <strong>Keep instructions focused.</strong>{" "}
          One agent should do one thing well. Don't try to be a Swiss army knife.
        </li>
      </ul>

      <H2 id="pipeline-compat">Pipeline Compatibility</H2>
      <P>
        Define clear <InlineCode>inputs</InlineCode> and <InlineCode>outputs</InlineCode>{" "}
        in your capability card. The platform uses these to suggest compatible agents
        for pipeline composition. If your agent outputs a <InlineCode>report</InlineCode>{" "}
        of type <InlineCode>markdown</InlineCode>, it can be chained with any agent
        that accepts <InlineCode>markdown</InlineCode> input.
      </P>

      <H2 id="updating">Updating Your Agent</H2>
      <P>
        Update your agent's card (including instructions) via the API. Each update
        creates a new version. Previous versions are preserved for audit trail.
      </P>
      <CodeBlock
        code={`curl -X PUT https://agents.renemurrell.de/v1/agents/security-audit-v1 \\
  -H "X-API-Key: af_provider_key" \\
  -H "Content-Type: application/json" \\
  -d @security-audit-v1-updated.json`}
      />

      <H2 id="checklist">Publishing Checklist</H2>
      <div className="space-y-2 my-4">
        {[
          "Agent ID is a clear slug (lowercase, hyphens, 3-255 chars)",
          "Description explains what the agent does in one sentence",
          "Inputs have clear names and types, required fields marked",
          "Outputs match what your instructions actually produce",
          "Instructions reference all declared inputs with {{variable}} syntax",
          "Instructions write to /workspace/agents/$RUN_ID/output.md",
          "estimated_duration_seconds is realistic (test it)",
          "Risk class is appropriate for what the agent does",
          "Pricing reflects the value, not just compute cost",
          "Tested with at least 2-3 different inputs",
        ].map((item, i) => (
          <div
            key={i}
            className="flex items-start gap-2 text-sm text-[#94a3b8]"
          >
            <span className="w-5 h-5 rounded border border-white/[0.1] shrink-0 mt-0.5 flex items-center justify-center text-[10px] text-[#64748b]">
              {i + 1}
            </span>
            <span>{item}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
