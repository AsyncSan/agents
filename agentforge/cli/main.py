"""CLI: manage agents, tasks, and pipelines from the terminal.

Usage:
    agents-cli login          Store API key
    agents-cli whoami         Show current user info
    agents-cli publish        Register or update an agent from YAML
    agents-cli agents         List/search agents
    agents-cli run            Submit a task to an agent
    agents-cli status         Check task or pipeline status
    agents-cli results        Download task results
    agents-cli logs           View task stdout/stderr
    agents-cli health         Platform health check
"""

import json
import time
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from agentforge.cli.client import get_client, handle_error
from agentforge.cli.config import clear_config, get_api_key, get_endpoint, save_config

app = typer.Typer(
    name="agents-cli",
    help="Managed Agent Runtime CLI",
    no_args_is_help=True,
)
console = Console()


# --- Auth ---


@app.command()
def login(
    api_key: str = typer.Option(..., prompt=True, hide_input=True, help="Your API key"),
    endpoint: str = typer.Option(None, help="API endpoint URL"),
):
    """Store API key for authentication."""
    save_config(api_key, endpoint)
    console.print("[green]Logged in.[/green] Key saved to ~/.agents-cli/config.json")


@app.command()
def logout():
    """Remove stored credentials."""
    clear_config()
    console.print("Logged out.")


@app.command()
def whoami():
    """Show current authentication status and account summary."""
    key = get_api_key()
    if not key:
        console.print("[red]Not logged in.[/red] Run: agents-cli login")
        raise typer.Exit(1)

    client = get_client()
    resp = client.get("/v1/me")
    if resp.status_code != 200:
        console.print(f"Endpoint: {get_endpoint()}")
        console.print(f"API Key: {key[:8]}...{key[-4:]}")
        console.print(f"[red]Auth failed ({resp.status_code})[/red]")
        raise typer.Exit(1)

    me = resp.json()
    console.print(f"\n[bold]{me['name']}[/bold] ({me['role']})")
    console.print(f"Email: {me['email']}")
    console.print(f"Endpoint: {get_endpoint()}")
    console.print(f"Secrets: {me['secrets_count']}")
    console.print(f"Webhooks: {me['webhooks_count']}")
    console.print(f"Tasks: {me['tasks_count']}")
    if me.get("schedules_count") is not None:
        console.print(f"Schedules: {me['schedules_count']}")
    if me.get("agents_count") is not None:
        console.print(f"Agents: {me['agents_count']}")
    stripe_status = (
        "[green]configured[/green]" if me["stripe_configured"] else "[yellow]not set up[/yellow]"
    )
    console.print(f"Payments: {stripe_status}")


# --- Agents ---


@app.command()
def agents(
    query: str = typer.Option(None, "-q", help="Search query"),
    domain: str = typer.Option(None, "-d", help="Filter by domain"),
    sort: str = typer.Option("executions", "-s", help="Sort: trust|price|executions|newest"),
    limit: int = typer.Option(20, "-n", help="Number of results"),
):
    """List and search agents."""
    client = get_client()
    params = {"sort_by": sort, "limit": limit}
    if query:
        params["q"] = query
    if domain:
        params["domain"] = domain

    resp = client.get("/v1/agents", params=params)
    handle_error(resp)
    data = resp.json()

    table = Table(title=f"Agents ({data['total']} total)")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name")
    table.add_column("Domain")
    table.add_column("Trust", justify="right")
    table.add_column("Runs", justify="right")
    table.add_column("Price", justify="right")

    for a in data["agents"]:
        trust = f"{a['trust_score']:.2f}" if a["trust_score"] else "-"
        price = a["card"].get("pricing", {}).get("base_price_usd", "-")
        domain_val = a["card"].get("capabilities", {}).get("domain", "-")
        table.add_row(
            a["id"],
            a["name"],
            str(domain_val),
            trust,
            str(a["total_executions"]),
            f"${price}" if price != "-" else "-",
        )

    console.print(table)


@app.command()
def inspect(agent_id: str = typer.Argument(..., help="Agent ID")):
    """Show detailed agent info."""
    client = get_client()
    resp = client.get(f"/v1/agents/{agent_id}")
    handle_error(resp)
    data = resp.json()

    console.print(f"\n[bold]{data['name']}[/bold] ({data['id']})")
    console.print(f"Status: {data['status']}")
    console.print(f"Provider: {data.get('provider_name', 'unknown')}")
    trust = f"{data['trust_score']:.2f}" if data["trust_score"] else "unrated"
    console.print(f"Trust: {trust}")
    console.print(f"Executions: {data['total_executions']} ({data['success_count']} success)")

    card = data["card"]
    caps = card.get("capabilities", {})
    console.print(f"\nDomain: {caps.get('domain', '-')}")
    console.print(f"Tags: {', '.join(caps.get('tags', []))}")

    runtime = card.get("runtime", {})
    console.print(f"\nModel: {runtime.get('model', '-')}")
    console.print(f"Server: {runtime.get('server_type', '-')}")
    console.print(f"Est. Duration: {runtime.get('estimated_duration_seconds', '-')}s")

    pricing = card.get("pricing", {})
    console.print(f"Price: ${pricing.get('base_price_usd', 0):.2f}")

    if data.get("signature"):
        console.print(f"\n[green]Signed[/green] (sig: {data['signature'][:16]}...)")
    else:
        console.print("\n[yellow]Unsigned[/yellow]")


# --- Publish ---


@app.command()
def publish(
    card_file: Path = typer.Argument(..., help="Path to agent YAML/JSON file"),
    update: bool = typer.Option(False, "--update", "-u", help="Update existing agent"),
):
    """Register or update an agent from a YAML/JSON capability card."""
    import yaml

    if not card_file.exists():
        console.print(f"[red]File not found: {card_file}[/red]")
        raise typer.Exit(1)

    content = card_file.read_text()
    if card_file.suffix in (".yaml", ".yml"):
        data = yaml.safe_load(content)
    else:
        data = json.loads(content)

    client = get_client()

    if update:
        agent_id = data.get("id")
        if not agent_id:
            console.print("[red]Agent ID required for update[/red]")
            raise typer.Exit(1)
        resp = client.put(f"/v1/agents/{agent_id}", json=data)
    else:
        resp = client.post("/v1/agents", json=data)

    handle_error(resp)
    result = resp.json()
    console.print(f"[green]Published:[/green] {result['id']} ({result['name']})")
    if result.get("signature"):
        console.print("[green]Signed[/green] by provider")


# --- Run ---


@app.command()
def run(
    agent_id: str = typer.Argument(..., help="Agent ID to run"),
    inputs: str = typer.Option("{}", "-i", help='JSON inputs, e.g. \'{"topic": "AI"}\''),
    max_cost: float = typer.Option(None, "--budget", help="Max cost in USD"),
    timeout: int = typer.Option(None, "--timeout", help="Timeout in seconds"),
    callback: str = typer.Option(None, "--callback", help="Callback URL"),
    wait: bool = typer.Option(False, "--wait", "-w", help="Wait for completion"),
):
    """Submit a task to an agent."""
    client = get_client()

    try:
        input_data = json.loads(inputs)
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON inputs: {e}[/red]")
        raise typer.Exit(1)

    payload = {
        "agent_id": agent_id,
        "inputs": input_data,
        "constraints": {},
    }
    if max_cost is not None:
        payload["constraints"]["max_cost_usd"] = max_cost
    if timeout is not None:
        payload["constraints"]["timeout"] = timeout
    if callback:
        payload["callback_url"] = callback

    resp = client.post("/v1/tasks", json=payload)
    handle_error(resp)
    task = resp.json()

    console.print(f"[green]Task submitted:[/green] {task['id']}")
    console.print(f"Agent: {task['agent_id']}")
    console.print(f"Status: {task['status']}")

    if wait:
        _wait_for_task(client, task["id"])


def _wait_for_task(client, task_id: str) -> None:
    """Poll task status until completion."""
    console.print("\nWaiting for completion...", end="")
    while True:
        resp = client.get(f"/v1/tasks/{task_id}")
        if resp.status_code != 200:
            break
        status = resp.json()["status"]
        if status in ("completed", "failed"):
            console.print(f"\n[{'green' if status == 'completed' else 'red'}]{status}[/]")
            break
        console.print(".", end="")
        time.sleep(5)


# --- Status ---


@app.command()
def status(
    task_id: str = typer.Argument(None, help="Task ID (omit to list recent)"),
    pipeline: bool = typer.Option(False, "--pipeline", "-p", help="Show pipeline status"),
    limit: int = typer.Option(10, "-n", help="Number of recent tasks"),
):
    """Check task or pipeline status."""
    client = get_client()

    if task_id and pipeline:
        resp = client.get(f"/v1/pipelines/{task_id}")
        handle_error(resp)
        p = resp.json()
        console.print(f"\n[bold]Pipeline {p['id']}[/bold]")
        console.print(f"Status: {p['status']}")
        console.print(f"Step: {p['current_step'] + 1}/{len(p['steps'])}")
        console.print(f"Trust: {p.get('chain_trust_score', '-')}")
        console.print(f"Cost: ${p['total_captured_cents'] / 100:.2f}")

        table = Table(title="Steps")
        table.add_column("#")
        table.add_column("Agent")
        table.add_column("Task ID")
        table.add_column("Status")
        for i, step in enumerate(p["steps"]):
            task_info = p["tasks"][i] if i < len(p["tasks"]) else None
            table.add_row(
                str(i + 1),
                step["agent_id"],
                task_info["id"] if task_info else "-",
                task_info["status"] if task_info else "pending",
            )
        console.print(table)
        return

    if task_id:
        resp = client.get(f"/v1/tasks/{task_id}")
        handle_error(resp)
        t = resp.json()
        console.print(f"\n[bold]Task {t['id']}[/bold]")
        console.print(f"Agent: {t['agent_id']}")
        console.print(f"Status: {t['status']}")
        console.print(f"Created: {t['created_at']}")
        return

    # List recent tasks
    resp = client.get("/v1/tasks", params={"limit": limit})
    handle_error(resp)
    data = resp.json()

    table = Table(title=f"Recent Tasks ({data['total']} total)")
    table.add_column("ID", style="cyan")
    table.add_column("Agent")
    table.add_column("Status")
    table.add_column("Created")

    for t in data["tasks"]:
        color = {"completed": "green", "failed": "red", "running": "yellow"}.get(
            t["status"], "white"
        )
        table.add_row(
            t["id"],
            t["agent_id"],
            f"[{color}]{t['status']}[/{color}]",
            t["created_at"][:19],
        )
    console.print(table)


# --- Results ---


@app.command()
def results(
    task_id: str = typer.Argument(..., help="Task ID"),
    file: str = typer.Option("output.md", "-f", help="File to download"),
    output: Path = typer.Option(None, "-o", help="Save to file path"),
):
    """Download results from a completed task."""
    client = get_client()
    resp = client.get(f"/v1/tasks/{task_id}/result", params={"file": file})
    handle_error(resp)

    if output:
        output.write_text(resp.text)
        console.print(f"[green]Saved to {output}[/green]")
    else:
        console.print(resp.text)


@app.command()
def logs(
    task_id: str = typer.Argument(..., help="Task ID"),
    stderr: bool = typer.Option(False, "--stderr", help="Show stderr instead of stdout"),
):
    """View stdout or stderr from a task execution."""
    client = get_client()
    file = "stderr.log" if stderr else "stdout.log"
    resp = client.get(f"/v1/tasks/{task_id}/result", params={"file": file})
    handle_error(resp)
    console.print(resp.text)


# --- Health ---


@app.command()
def health():
    """Check platform health status."""
    import httpx

    endpoint = get_endpoint()
    try:
        resp = httpx.get(f"{endpoint}/v1/platform/health", timeout=10)
    except httpx.ConnectError:
        console.print(f"[red]Cannot connect to {endpoint}[/red]")
        raise typer.Exit(1)

    if resp.status_code != 200:
        console.print(f"[red]Health check failed ({resp.status_code})[/red]")
        raise typer.Exit(1)

    data = resp.json()
    status_color = {"ok": "green", "degraded": "yellow", "down": "red"}.get(
        data["status"], "white"
    )
    console.print(f"Platform: [{status_color}]{data['status']}[/{status_color}]")
    console.print(f"Version: {data['version']}")
    console.print(f"Agents: {data['total_agents']}")
    console.print(f"Pending: {data['pending_tasks']}")
    console.print(f"24h Executions: {data['total_executions_24h']}")

    table = Table(title="Components")
    table.add_column("Name")
    table.add_column("Status")
    table.add_column("Latency")
    for c in data["components"]:
        sc = {"ok": "green", "degraded": "yellow", "down": "red"}.get(c["status"], "white")
        latency = f"{c['latency_ms']:.1f}ms" if c.get("latency_ms") else "-"
        table.add_row(c["name"], f"[{sc}]{c['status']}[/{sc}]", latency)
    console.print(table)


# --- Rate ---


@app.command()
def rate(
    task_id: str = typer.Argument(..., help="Task ID to rate"),
    score: int = typer.Argument(..., help="Rating 1-5"),
    comment: str = typer.Option(None, "-c", help="Optional comment"),
):
    """Rate a completed task (1-5 stars)."""
    if score < 1 or score > 5:
        console.print("[red]Score must be 1-5[/red]")
        raise typer.Exit(1)

    client = get_client()
    payload = {"score": score}
    if comment:
        payload["comment"] = comment

    resp = client.post(f"/v1/tasks/{task_id}/rating", json=payload)
    handle_error(resp)
    data = resp.json()
    stars = "★" * data["score"] + "☆" * (5 - data["score"])
    console.print(f"[green]Rated {stars}[/green] ({data['agent_id']})")


def main():
    app()
