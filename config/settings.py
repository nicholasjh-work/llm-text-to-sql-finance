"""
Application settings loaded from environment variables.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Settings:
    # Flask
    port: int = int(os.getenv("PORT", "5000"))
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Snowflake
    snowflake_account: str = os.getenv("SNOWFLAKE_ACCOUNT", "")
    snowflake_user: str = os.getenv("SNOWFLAKE_USER", "")
    snowflake_password: str = os.getenv("SNOWFLAKE_PASSWORD", "")
    snowflake_database: str = os.getenv("SNOWFLAKE_DATABASE", "FINANCE_DW")
    snowflake_schema: str = os.getenv("SNOWFLAKE_SCHEMA", "REPORTING")
    snowflake_warehouse: str = os.getenv("SNOWFLAKE_WAREHOUSE", "ANALYTICS_WH")

    # LLM
    llm_model: str = os.getenv("LLM_MODEL", "claude-sonnet-4-20250514")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_endpoint: str = os.getenv("LLM_ENDPOINT", "https://api.anthropic.com/v1/messages")

    # Role config (loaded from YAML)
    role_schemas: dict = field(default_factory=dict)

    def __post_init__(self):
        roles_path = Path(__file__).parent / "roles.yaml"
        if roles_path.exists():
            with open(roles_path) as f:
                data = yaml.safe_load(f) or {}
                self.role_schemas = data.get("roles", {})
