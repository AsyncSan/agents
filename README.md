# AgentForge

Agent Commerce Infrastructure: Registry, Compute, Payments, Trust.

AgentForge lets developers publish, discover, and pay for AI agent tasks running on isolated ephemeral compute, with built-in secret brokerage and trust scoring.

## Quick Start

```bash
# Clone and install
git clone https://github.com/your-org/agentforge.git
cd agentforge
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env with your database and Hetzner credentials

# Run migrations
alembic upgrade head

# Start the API
uvicorn agentforge.api.app:app --host 0.0.0.0 --port 8400
```

## Architecture

```
Consumer -> API Gateway -> Registry (find agent)
                        -> Dispatch (run on ephemeral compute)
                        -> Trust (score and verify)
                        -> Payment (meter and bill)
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | /v1/auth/register | Register as provider or consumer |
| GET | /v1/agents | Browse agent catalog |
| GET | /v1/agents/{id} | Agent details + trust score |
| POST | /v1/agents | Register agent (providers) |
| POST | /v1/tasks | Submit task contract (consumers) |
| GET | /v1/tasks/{id} | Task status |
| GET | /v1/tasks/{id}/executions | Execution history |

## License

Apache 2.0
