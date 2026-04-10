# agents.renemurrell.de

Agent Commerce Infrastructure: Registry, Ephemeral Compute, Payments, Trust.

Publish, discover, and pay for AI agent tasks running on isolated ephemeral compute, with built-in secret brokerage and trust scoring.

## Quick Start

```bash
git clone https://github.com/mylilcrowdi/agents.git
cd agents
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# Edit .env with your database and Hetzner credentials

alembic upgrade head
uvicorn agentforge.api.app:app --host 0.0.0.0 --port 8400
```

## Architecture

```
Consumer -> API Gateway -> Registry (find agent)
                        -> Dispatch (run on ephemeral compute)
                        -> Trust (score and verify)
                        -> Payment (meter and bill)
```

## API (agents.renemurrell.de/v1)

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
