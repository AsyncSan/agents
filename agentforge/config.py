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
    hcloud_ssh_key_path: str = ""
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
    stripe_connect_return_url: str = "https://agents.renemurrell.de/connect/return"
    stripe_connect_refresh_url: str = "https://agents.renemurrell.de/connect/refresh"
    stripe_checkout_success_url: str = "https://agents.renemurrell.de/payment/success"
    stripe_checkout_cancel_url: str = "https://agents.renemurrell.de/payment/cancel"

    # Solana
    solana_rpc_url: str = "https://api.mainnet-beta.solana.com"
    solana_usdc_mint: str = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # mainnet USDC
    solana_platform_wallet: str = ""  # platform receives fees here
    solana_platform_fee_bps: int = 2000  # 20% in basis points

    # Docker (container compute tier)
    docker_enabled: bool = True
    docker_default_image: str = "agentforge/runner:latest"
    docker_cpu_limit: str = "2.0"
    docker_memory_limit: str = "2g"
    docker_network: str = "bridge"
    docker_host: str = ""  # empty = local docker socket

    # Database pool
    db_pool_size: int = 10
    db_max_overflow: int = 5
    db_pool_timeout: int = 30

    # Limits
    max_concurrent_agents: int = 5
    default_task_timeout: int = 1800

    # Retention
    results_retention_days: int = 30
    event_log_retention_days: int = 90

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
