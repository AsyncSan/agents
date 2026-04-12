"""CLI configuration: API key and endpoint storage."""

import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".agentforge"
CONFIG_FILE = CONFIG_DIR / "config.json"


def _load() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def _save(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2))


def get_api_key() -> str | None:
    return _load().get("api_key")


def get_endpoint() -> str:
    return _load().get("endpoint", "https://agents.renemurrell.de")


def save_config(api_key: str, endpoint: str | None = None) -> None:
    data = _load()
    data["api_key"] = api_key
    if endpoint:
        data["endpoint"] = endpoint
    _save(data)


def clear_config() -> None:
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()
