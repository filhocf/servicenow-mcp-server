"""Main MCP server implementation for ServiceNow."""

import asyncio
import logging
from typing import Any

import click
from mcp.server import Server
from mcp.server.lowlevel.server import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    TextContent,
    Tool,
)

from .client import ServiceNowClient
from .config import Config, ConfigManager
from .exceptions import ServiceNowError
from .tools import ToolRegistry


class ServiceNowMCPServer:
    """MCP Server for ServiceNow API integration."""

    def __init__(self, config: Config):
        """Initialize the ServiceNow MCP Server."""
        self.config = config
        self.client = ServiceNowClient(config.servicenow)
        self.server = Server(config.mcp.name)  # type: ignore[var-annotated]
        self.tools = ToolRegistry(config.features)

        # Setup logging
        self._setup_logging()

        # Register handlers
        self._register_handlers()

    def _setup_logging(self) -> None:
        """Configure logging based on configuration."""
        log_level = getattr(logging, self.config.logging.level.upper(), logging.INFO)

        formatter: logging.Formatter
        if self.config.logging.format == "json":
            import json

            class JsonFormatter(logging.Formatter):
                def format(self, record: logging.LogRecord) -> str:
                    log_data = {
                        "timestamp": self.formatTime(record),
                        "level": record.levelname,
                        "message": record.getMessage(),
                        "module": record.module,
                    }
                    if record.exc_info:
                        log_data["exception"] = self.formatException(record.exc_info)
                    return json.dumps(log_data)

            formatter = JsonFormatter()
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )

        logger = logging.getLogger("servicenow_mcp")
        logger.setLevel(log_level)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler if configured
        if self.config.logging.file:
            file_handler = logging.FileHandler(self.config.logging.file)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        self.logger = logger

    def _register_handlers(self) -> None:
        """Register MCP protocol handlers."""

        @self.server.list_tools()  # type: ignore[no-untyped-call,misc]
        async def list_tools() -> list[Tool]:
            """List all available tools."""
            return self.tools.get_enabled_tools()

        @self.server.call_tool()  # type: ignore[no-untyped-call,misc]
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Execute a tool and return results."""
            try:
                self.logger.info(f"Executing tool: {name} with args: {arguments}")

                # Get tool handler
                handler = self.tools.get_handler(name)
                if not handler:
                    return [
                        TextContent(type="text", text=f"Error: Unknown tool '{name}'")
                    ]

                # Execute tool
                async with self.client:
                    result = await handler(self.client, arguments)

                # Format result
                if isinstance(result, str):
                    return [TextContent(type="text", text=result)]
                elif isinstance(result, (dict, list)):
                    import json

                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                else:
                    return [TextContent(type="text", text=str(result))]

            except ServiceNowError as e:
                self.logger.error(f"ServiceNow error in tool {name}: {e}")
                return [TextContent(type="text", text=f"ServiceNow Error: {e!s}")]
            except Exception as e:
                self.logger.exception(f"Unexpected error in tool {name}")
                return [TextContent(type="text", text=f"Unexpected Error: {e!s}")]

    async def run(self) -> None:
        """Run the MCP server."""
        self.logger.info(f"Starting ServiceNow MCP Server v{self.config.mcp.version}")
        self.logger.info(f"Connected to instance: {self.config.servicenow.instance}")

        # Run the stdio server
        async with stdio_server() as (read_stream, write_stream):
            init_options = InitializationOptions(
                server_name=self.config.mcp.name,
                server_version=self.config.mcp.version,
                capabilities=self.server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            )

            await self.server.run(
                read_stream,
                write_stream,
                init_options,
            )


@click.command()
@click.option(
    "--config-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default="config",
    help="Configuration directory path",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    help="Override log level",
)
def main(config_dir: str, log_level: str | None) -> None:
    """Run the ServiceNow MCP Server."""
    # Load configuration
    from pathlib import Path

    config_manager = ConfigManager(Path(config_dir))
    config = config_manager.load()

    # Override log level if provided
    if log_level:
        config.logging.level = log_level

    # Create and run server
    server = ServiceNowMCPServer(config)

    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        server.logger.info("Server stopped by user")
    except Exception as e:
        server.logger.exception(f"Server crashed: {e}")
        raise


if __name__ == "__main__":
    main()
