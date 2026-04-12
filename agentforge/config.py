"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://agentforge:changeme@localhost:5433/agentforge"

    # Auth
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24h
    api_key_salt: str = "change-me"

    # Hetzner
    hcloud_token: str = ""
    hcloud_ssh_key_name: str = "async@pi5"
    hcloud_network_name: str = "renemurrell-vpc"
    hcloud_firewall_name: str = "renemurrell-agents-firewall"
    hcloud_location: str = "nbg1"
    hcloud_default_server_type: str = "cax11"

    # Snapshots
    snapshot_base: str = "370464673"
    snapshot_gui: str = "370465176"
    snapshot_gui_x86: str = "370835039"

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_platform_fee_percent: int = 20  # 20% take rate

    # Limits
    max_concurrent_agents: int = 5
    default_task_timeout: int = 1800

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
