"""HTTP client for CLI commands."""

import sys

import httpx

from agentforge.cli.config import get_api_key, get_endpoint


def get_client() -> httpx.Client:
    """Create an authenticated httpx client."""
    api_key = get_api_key()
    if not api_key:
        print("Not logged in. Run: agentforge login")
        sys.exit(1)

    return httpx.Client(
        base_url=get_endpoint(),
        headers={"X-API-Key": api_key},
        timeout=30,
    )


def handle_error(resp: httpx.Response) -> None:
    """Print error and exit if response is not successful."""
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        print(f"Error ({resp.status_code}): {detail}")
        sys.exit(1)
