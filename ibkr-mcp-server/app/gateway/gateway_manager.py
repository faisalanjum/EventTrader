"""Gateway manager for IBKR TWS Gateway."""

import asyncio
from typing import Any

from .docker_service import IBKRGatewayDockerService
from app.core.setup_logging import logger
from app.core.config import get_config

config = get_config()


class IBKRGatewayManager:
  """Manager for IBKR Gateway container and interactions."""

  def __init__(self) -> None:
    """Initialize the IBKR Gateway manager."""
    self.is_external = config.gateway_mode == "external"
    self.docker_service = IBKRGatewayDockerService() if not self.is_external else None
    self.is_running = False

  async def start_container(self) -> bool:
    """Start the internal IBKR Gateway Docker container.

    Only works in internal mode. For external mode, use test_connectivity().
    """
    if self.is_external:
      logger.warning("Cannot start container in external mode")
      return False

    try:
      success = await self.docker_service.start_gateway()
      if success:
        self.is_running = True
        logger.debug("IBKR Gateway container started successfully")
    except Exception:
      logger.exception("Failed to start gateway container")
      return False
    else:
      return success

  async def test_external_connection(self) -> bool:
    """Check connectivity to external IBKR Gateway via TCP.

    Opens and immediately closes a TCP connection — does not consume an IB
    API session slot or create a socat child process that lingers on timeout.
    """
    try:
      _, writer = await asyncio.wait_for(
        asyncio.open_connection(config.ib_gateway_host, config.ib_gateway_port),
        timeout=3.0,
      )
      writer.close()
      await writer.wait_closed()
    except Exception:
      logger.debug(
        "External gateway not reachable at %s:%s",
        config.ib_gateway_host,
        config.ib_gateway_port,
      )
      return False
    else:
      return True

  async def start_gateway(self) -> bool:
    """Start the IBKR Gateway based on mode.

    For internal mode: starts the Docker container.
    For external mode: marks as ready (actual connectivity handled by IBKR endpoints).
    """
    if self.is_external:
      logger.debug("Using external gateway")
      return True

    # Internal mode: start container
    success = await self.start_container()
    if success:
      logger.info("Internal IBKR Gateway container started")
    return success

  async def stop_container(self) -> bool:
    """Stop the internal IBKR Gateway Docker container.

    Only works in internal mode.
    """
    if self.is_external:
      logger.warning("Cannot stop container in external mode")
      return False

    try:
      success = await self.docker_service.stop_gateway()
      if success:
        self.is_running = False
        logger.debug("IBKR Gateway container stopped successfully")
    except Exception:
      logger.exception("Failed to stop gateway container")
      return False
    else:
      return success

  async def stop_gateway(self) -> bool:
    """Stop the IBKR Gateway based on mode.

    For internal mode: stops the Docker container.
    For external mode: marks as stopped.
    """
    if self.is_external:
      # External mode: mark as stopped
      self.is_running = False
      logger.info("External IBKR Gateway marked as stopped")
      return True
    # Internal mode: stop the container
    return await self.stop_container()

  async def get_gateway_status(self) -> dict[str, Any]:
    """Get the current status of the IBKR Gateway."""
    if self.is_external:
      # For external gateway, test connectivity
      self.is_running = await self.test_external_connection()
      return {
        "is_running": self.is_running,
        "mode": "external",
        "host": config.ib_gateway_host,
        "port": config.ib_gateway_port,
        "connection_status": "reachable" if self.is_running else "unreachable",
      }
    # Internal gateway mode - get container status
    try:
      container_status = await self.docker_service.get_container_status()
    except Exception as e:
      logger.error(f"Failed to get gateway status: {e}")
      return {
        "is_running": False,
        "mode": "internal",
        "error": str(e),
      }
    else:
      return {
        "is_running": self.is_running,
        "mode": "internal",
        "container": container_status,
      }

  async def get_gateway_logs(self, tail: int = 100) -> dict[str, Any]:
    """Get the logs from the IBKR Gateway container."""
    if self.is_external:
      return {
        "logs": ["External gateway mode - logs not available"],
        "note": "Logs are not available for external gateway connections",
      }
    logs = await self.docker_service.get_container_logs(tail)
    log_lines = [line.strip() for line in logs.split("\n") if line.strip()]
    return {"logs": log_lines}

  async def cleanup(self) -> None:
    """Cleanup resources when shutting down."""
    try:
      if self.is_running:
        await self.stop_gateway()

      # Cleanup docker service resources (only for internal mode)
      if (
        not self.is_external
        and hasattr(self, "docker_service")
        and self.docker_service
        and hasattr(self.docker_service, "client")
      ):
        self.docker_service.client.close()
    except Exception as e:
      logger.error(f"Error during cleanup: {e}")
    finally:
      self.is_running = False

  def __del__(self) -> None:
    """Cleanup when the manager is destroyed."""
    if self.is_running:
      logger.warning(
        "IBKRGatewayManager destroyed while still running. "
        "Call await manager.cleanup() before destruction.",
      )
