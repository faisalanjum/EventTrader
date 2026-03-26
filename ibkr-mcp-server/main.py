"""Simple entry point for the IBKR MCP Server."""

import argparse
import uvicorn
import sys

from app.core.config import init_config
from app.core.setup_logging import setup_logging

logger = setup_logging()


def parse_args() -> argparse.Namespace:
  """Parse command line arguments."""
  parser = argparse.ArgumentParser(description="IBKR MCP Server")

  # Common arguments
  parser.add_argument(
    "--application-host",
    type=str,
    help="Application host (default: 127.0.0.1)",
  )
  parser.add_argument(
    "--application-port",
    type=int,
    default=8000,
    help="Application port (default: 8000)",
  )
  parser.add_argument(
    "--log-level",
    type=str,
    default="INFO",
    help="Log level (default: INFO)",
  )

  # Gateway mode
  parser.add_argument(
    "--gateway-mode",
    type=str,
    choices=["internal", "external"],
    help="Gateway mode: internal (start own gateway) or external (connect to existing)",
  )

  # Internal gateway arguments
  parser.add_argument(
    "--ib-gateway-username",
    help="IBKR Gateway username (required for internal mode)",
  )
  parser.add_argument(
    "--ib-gateway-password",
    help="IBKR Gateway password (required for internal mode)",
  )

  # External gateway arguments
  parser.add_argument(
    "--ib-gateway-host",
    type=str,
    help="IBKR Gateway host (for external mode)",
  )
  parser.add_argument(
    "--ib-gateway-port",
    type=int,
    help="IBKR Gateway port (for external mode)",
  )

  # CORS arguments
  parser.add_argument(
    "--cors-allowed-origins",
    type=str,
    help="Comma-separated list of allowed CORS origins (default: *)",
  )

  # Authentication arguments
  parser.add_argument(
    "--auth-token",
    type=str,
    help="Bearer token for API authentication (optional)",
  )

  # MCP toggle
  parser.add_argument(
    "--mcp",
    dest="enable_mcp",
    action=argparse.BooleanOptionalAction,
    default=None,
    help="Enable MCP server (default: enabled, disable with --no-mcp)",
  )
  return parser.parse_args()


def main() -> None:
  """Run the app."""
  cli_args_dict = vars(parse_args())
  provided_cli_args = {
    key: value for key, value in cli_args_dict.items() if value is not None
  }

  # Initialize config. Pydantic gives priority to the arguments passed here.
  config = init_config(**provided_cli_args)

  # Validate required fields
  if config.gateway_mode == "internal" and (
    not config.ib_gateway_username or not config.ib_gateway_password
  ):
    print("Error: IB Gateway username and password are required for internal mode")  # noqa: T201
    print("Set via CLI: --ib-gateway-username and --ib-gateway-password")  # noqa: T201
    print("Or via env: IBKR_IB_GATEWAY_USERNAME and IBKR_IB_GATEWAY_PASSWORD")  # noqa: T201
    sys.exit(1)

  from app.main import app  # noqa: PLC0415

  # Display authentication information
  auth_token = config.get_effective_auth_token()
  if config.is_token_generated():
    logger.info("🔐 SECURITY: Auto-generated authentication token")
    logger.info(f"🔑 Bearer Token: {auth_token}")
    logger.info("💡 Use this token in Authorization header: Bearer <token>")
    logger.info("💡 Set IBKR_AUTH_TOKEN env var to use a custom token")
  else:
    logger.info("🔐 SECURITY: Using provided authentication token")
  logger.info(f"CORS allowed origins: {config.get_cors_origins_list()}")

  logger.info(f"Starting on http://{config.application_host}:{config.application_port}")
  uvicorn.run(
    app,
    host=config.application_host,
    port=config.application_port,
    log_config=None,
    access_log=True,
  )


if __name__ == "__main__":
  main()
