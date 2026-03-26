"""Main module for the IBKR MCP Server."""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mcp import FastApiMCP
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from app.api import gateway
from app.api.ibkr import ibkr_router
from app.core.config import get_config
from app.core.auth import auth_dependency
from app.core.setup_logging import logger


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
  """Lifespan events for the application."""
  logger.info("Starting IBKR MCP Server...")

  # Only start internal gateway during startup, external gateway is handled on-demand
  if not gateway.gateway_manager.is_external:
    try:
      success = await gateway.gateway_manager.start_gateway()
      if not success:
        logger.error("Failed to start internal IBKR Gateway.")
    except Exception:
      logger.exception("Error starting internal IBKR Gateway.")
  else:
    logger.info("External gateway mode - connection will be established on-demand")

  yield

  # Shutdown
  logger.info("Shutting down IBKR MCP Server...")

  # Cleanup gateway
  try:
    await gateway.gateway_manager.cleanup()
  except Exception:
    logger.exception("Error during cleanup.")


config = get_config()

# FastAPI with authentication dependency
app = FastAPI(
  title="IBKR MCP Server",
  description="Interactive Brokers MCP Server",
  version="0.1.0",
  docs_url="/docs",
  openapi_url="/openapi.json",
  lifespan=lifespan,
  dependencies=[Depends(auth_dependency)],
)

# Add CORS middleware
logger.debug(f"CORS allowed origins: {config.get_cors_origins_list()}")
app.add_middleware(
  CORSMiddleware,
  allow_origins=config.get_cors_origins_list(),
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

# Include routers
app.include_router(gateway.router)
app.include_router(ibkr_router)


@app.get("/")
def read_root() -> dict:
  """Return the root endpoint."""
  return {
    "message": "Welcome to the IBKR MCP Server",
    "docs": "/docs",
    "status": "/gateway/status",
  }


@app.get("/health", include_in_schema=False)
def health() -> dict:
  """Liveness check — proves the Python process is alive."""
  return {"status": "ok"}


# MCP server, attached to the FastAPI app, excludes the gateway router
if config.enable_mcp:
  mcp = FastApiMCP(
    app,
    exclude_tags=["gateway"],
  )
  mcp.mount()
