"""Docker service for the IBKR Gateway."""

import time
import asyncio
import docker
from datetime import datetime, UTC
from ib_async import IB
from typing import Any
from app.core.setup_logging import logger
from app.core.config import get_config

config = get_config()

VNC_PORT = 6080
API_PORT = 8888
IBC_COMMAND_SERVER_PORT = 7462

docker_config = {
  "image": "ghcr.io/extrange/ibkr:stable",
  "ports": {
    VNC_PORT: VNC_PORT,
    API_PORT: API_PORT,
    IBC_COMMAND_SERVER_PORT: IBC_COMMAND_SERVER_PORT,
  },
  "environment": {
    "USERNAME": config.ib_gateway_username,
    "PASSWORD": config.ib_gateway_password,
    "TWOFA_TIMEOUT_ACTION": "restart",
    "GATEWAY_OR_TWS": "gateway",
    "IBC_TradingMode": "live",
    "IBC_ReadOnlyApi": "no",
    "IBC_ReloginAfterSecondFactorAuthenticationTimeout": "yes",
    "IBC_AutoRestartTime": "08:35 AM",
    "IBC_CommandServerPort": config.ib_command_server_port,
    "IBC_ControlFrom": "127.0.0.1",
    "IBC_BindAddress": "127.0.0.1",
  },
}


class IBKRGatewayDockerService:
  """Service for managing IBKR Gateway Docker container."""

  def __init__(self) -> None:
    """Initialize the IBKR Gateway Docker service."""
    self.client = docker.from_env()
    self.container_name = "ibkr-gateway"
    self.container: docker.models.containers.Container | None = None
    self._health_check_semaphore = asyncio.Semaphore(1)
    self._last_health_check = 0
    self._health_check_interval = 2
    self._connection_timeout = 120

  async def start_gateway(self) -> bool:
    """Start the IBKR Gateway container."""
    try:
      # Check if container already exists
      try:
        existing_container = self.client.containers.get(self.container_name)
        if existing_container.status == "running":
          logger.debug(f"Container {self.container_name} is already running")
          self.container = existing_container
          return True
        existing_container.remove()
      except docker.errors.NotFound:
        pass

      # Pull the IBKR Gateway image
      self.client.images.pull(docker_config["image"])

      # Container configuration
      container_config = {
        "image": docker_config["image"],
        "name": self.container_name,
        "ports": docker_config["ports"],
        "environment": docker_config["environment"],
        "detach": True,
        "restart_policy": {"Name": "unless-stopped"},
      }

      # Start the container
      logger.debug("Starting IBKR Gateway container...")
      self.container = self.client.containers.run(**container_config)

      # Wait for container to be ready
      if not await self.wait_for_container_ready():
        logger.error("Container failed to become ready")
        return False

    except Exception:
      logger.exception("Failed to start IBKR Gateway container")
      return False
    else:
      logger.debug("IBKR Gateway container started successfully")
      return True

  async def health_check(self) -> bool:
    """Check if the IBKR Gateway container is running (non-blocking, async)."""
    current_time = time.time()

    # Rate limiting: don't check too frequently
    if current_time - self._last_health_check < self._health_check_interval:
      await asyncio.sleep(
        self._health_check_interval - (current_time - self._last_health_check),
      )

    async with self._health_check_semaphore:
      self._last_health_check = time.time()
      return await self._sync_health_check()

  async def _sync_health_check(self) -> bool:
    """Check health asynchronously."""
    ib = None
    try:
      ib = IB()
      await ib.connectAsync(
        config.ib_gateway_host,
        config.ib_gateway_port,
        1111,
        readonly=True,
      )
      return ib.isConnected()
    except Exception:
      return False
    finally:
      if ib:
        ib.disconnect()

  async def wait_for_container_ready(self) -> bool:
    """Wait for the IBKR Gateway container to be ready."""
    timer = 0
    while not await self.health_check():
      if timer > self._connection_timeout:
        logger.error(f"IBKR Gateway not ready after {self._connection_timeout} seconds")
        return False
      await asyncio.sleep(2)
      timer += 2
    logger.debug(f"IBKR Gateway container is ready after {timer} seconds")
    return True

  async def get_container_status(self) -> dict[str, Any]:
    """Get the status of the IBKR Gateway container."""
    try:
      # Check if container exists and get its status
      if self.container:
        logger.debug("Getting container status from existing container")
        container_info = self.container.attrs
      else:
        try:
          container = self.client.containers.get(self.container_name)
          container_info = container.attrs
        except docker.errors.NotFound:
          return {
            "status": "not_found",
            "health": "unknown",
            "created": None,
            "started": None,
            "finished": None,
            "age": None,
          }

      # Extract container state information
      state = container_info["State"]
      status = state["Status"]

      # Get timestamps
      created = container_info.get("Created")
      started = state.get("StartedAt")
      finished = state.get("FinishedAt")
      created_time = datetime.fromisoformat(created)
      age = (datetime.now(UTC) - created_time).total_seconds()

      # Perform health check if container is running
      health_status = "unknown"
      if status == "running":
        try:
          is_healthy = await self.health_check()
          health_status = "healthy" if is_healthy else "unhealthy"
        except Exception:
          health_status = "health_check_failed"

    except Exception:
      logger.exception("Failed to get container status")
      return {
        "status": "error",
        "health": "unknown",
        "created": None,
        "started": None,
        "finished": None,
        "age": None,
      }
    else:
      return {
        "status": status,
        "health": health_status,
        "created": created,
        "started": started,
        "finished": finished,
        "age": age,
      }

  async def get_container_logs(self, tail: int = 100) -> str:
    """Get the logs from the IBKR Gateway container."""
    if self.container:
      return self.container.logs(tail=tail).decode("utf-8")
    return "Container not found"

  async def stop_gateway(self, *, persist: bool = False) -> bool:
    """Stop the IBKR Gateway container."""
    if persist:
      logger.debug("Persisting IBKR Gateway container")
      return True

    try:
      if self.container:
        logger.debug("Stopping IBKR Gateway container...")
        self.container.stop(timeout=self._connection_timeout)
        self.container.remove()
        self.container = None
        logger.debug("IBKR Gateway container stopped and removed")
        return True
      try:
        container = self.client.containers.get(self.container_name)
        container.stop(timeout=self._connection_timeout)
        container.remove()
        logger.debug("IBKR Gateway container stopped and removed")
      except docker.errors.NotFound:
        logger.debug("No IBKR Gateway container found to stop")
        return True
    except Exception:
      logger.exception("Failed to stop IBKR Gateway container")
      return False
    else:
      return True

  def __del__(self) -> None:
    """Cleanup when the service is destroyed."""
    try:
      if hasattr(self, "client"):
        self.client.close()
    except Exception:
      logger.exception("Failed to cleanup IBKR Gateway Docker service")
