"""Configuration management for ServiceNow MCP Server."""

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ServiceNowConfig(BaseModel):
    """ServiceNow connection configuration."""

    instance: str = Field(..., description="ServiceNow instance URL or subdomain")
    username: str = Field(default="", description="ServiceNow username (basic auth)")
    password: str = Field(default="", description="ServiceNow password (basic auth)")
    oauth_client_id: str | None = Field(
        default=None, description="OAuth2 client_credentials client_id"
    )
    oauth_client_secret: str | None = Field(
        default=None, description="OAuth2 client_credentials client_secret"
    )
    oauth_token_url: str | None = Field(
        default=None,
        description="OAuth2 token endpoint (default: {instance}/oauth_token.do)",
    )
    session_cookies: dict[str, str] | None = Field(
        default=None, description="Session cookies from SSO login"
    )
    api_version: str = Field(default="v2", description="ServiceNow API version")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum number of retry attempts")

    @field_validator("instance")
    @classmethod
    def validate_instance(cls, v: str) -> str:
        """Ensure instance URL is properly formatted."""
        if not v:
            raise ValueError("ServiceNow instance cannot be empty")

        if not v.startswith(("http://", "https://")):
            # If just subdomain provided, construct full URL
            v = f"https://{v}.service-now.com"

        return v.rstrip("/")


class MCPConfig(BaseModel):
    """MCP server configuration."""

    name: str = Field(default="servicenow-mcp", description="MCP server name")
    version: str = Field(default="0.1.0", description="MCP server version")
    description: str = Field(
        default="ServiceNow API integration via MCP",
        description="MCP server description",
    )


class FeaturesConfig(BaseModel):
    """Feature flags for enabling/disabling specific ServiceNow modules."""

    incident_management: bool = Field(default=True)
    change_management: bool = Field(default=True)
    problem_management: bool = Field(default=True)
    service_catalog: bool = Field(default=True)
    knowledge_base: bool = Field(default=True)
    user_management: bool = Field(default=True)
    cmdb: bool = Field(default=True)
    custom_tables: bool = Field(default=True)


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(default="json", description="Log format (json or text)")
    file: str | None = Field(default=None, description="Log file path")


class Config(BaseModel):
    """Main configuration model."""

    servicenow: ServiceNowConfig
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    features: FeaturesConfig = Field(default_factory=FeaturesConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


class ConfigManager:
    """Manages configuration loading and merging."""

    def __init__(self, config_dir: Path | None = None):
        """Initialize configuration manager."""
        self.config_dir = config_dir or Path("config")
        self._config: Config | None = None

    def load(self) -> Config:
        """Load configuration from files and environment variables."""
        if self._config is not None:
            return self._config

        # Load default configuration
        config_data = self._load_file("default.json")

        # Merge with local configuration if exists
        local_config = self._load_file("local.json")
        if local_config:
            config_data = self._deep_merge(config_data, local_config)

        # Override with environment variables
        config_data = self._apply_env_vars(config_data)

        # Validate and create config object
        self._config = Config(**config_data)
        return self._config

    def _load_file(self, filename: str) -> dict[str, Any]:
        """Load JSON configuration file."""
        file_path = self.config_dir / filename
        if not file_path.exists():
            return {}

        try:
            with open(file_path) as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception as e:
            raise ValueError(f"Failed to load config file {filename}: {e}") from e

    def _deep_merge(
        self, base: dict[str, Any], override: dict[str, Any]
    ) -> dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _apply_env_vars(self, config: dict[str, Any]) -> dict[str, Any]:
        """Apply environment variable overrides."""
        env_mappings = {
            "SERVICENOW_INSTANCE": ["servicenow", "instance"],
            "SERVICENOW_USERNAME": ["servicenow", "username"],
            "SERVICENOW_PASSWORD": ["servicenow", "password"],
            "SERVICENOW_OAUTH_CLIENT_ID": ["servicenow", "oauth_client_id"],
            "SERVICENOW_OAUTH_CLIENT_SECRET": ["servicenow", "oauth_client_secret"],
            "SERVICENOW_OAUTH_TOKEN_URL": ["servicenow", "oauth_token_url"],
            "SERVICENOW_SESSION_COOKIES": ["servicenow", "session_cookies"],
            "SERVICENOW_API_VERSION": ["servicenow", "api_version"],
            "SERVICENOW_TIMEOUT": ["servicenow", "timeout"],
            "MCP_LOG_LEVEL": ["logging", "level"],
            "MCP_LOG_FILE": ["logging", "file"],
        }

        for env_var, path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                self._set_nested(config, path, value)

        # Handle feature flags
        for feature in [
            "incident_management",
            "change_management",
            "problem_management",
            "service_catalog",
            "knowledge_base",
            "user_management",
            "cmdb",
            "custom_tables",
        ]:
            env_var = f"SERVICENOW_FEATURE_{feature.upper()}"
            value = os.getenv(env_var)
            if value is not None:
                config.setdefault("features", {})[feature] = value.lower() in (
                    "true",
                    "1",
                    "yes",
                    "on",
                )

        return config

    def _set_nested(self, data: dict[str, Any], path: list[str], value: Any) -> None:
        """Set a nested dictionary value using a path."""
        for key in path[:-1]:
            data = data.setdefault(key, {})

        # Convert value types as needed
        if path[-1] in ("timeout", "max_retries"):
            value = int(value)
        elif path[-1] == "session_cookies" and isinstance(value, str):
            value = json.loads(value)

        data[path[-1]] = value
