"""Logging configuration for the IBKR Agent project."""

from __future__ import annotations

import sys
import logging
from typing import TYPE_CHECKING
from loguru import logger

if TYPE_CHECKING:
  from loguru import Logger
from app.core.config import get_config


class InterceptHandler(logging.Handler):
  """Intercept handler for logging."""

  def emit(self, record: logging.LogRecord) -> None:
    """Emit a record."""
    # Get corresponding Loguru level if it exists
    try:
      level = logger.level(record.levelname).name
    except ValueError:
      level = record.levelno

    # Find caller from where originated the logged message
    frame, depth = logging.currentframe(), 2
    while frame.f_code.co_filename == logging.__file__:
      frame = frame.f_back
      depth += 1

    logger.opt(depth=depth, exception=record.exc_info).log(
      level,
      record.getMessage(),
    )


def setup_logging() -> Logger:
  """Set up logging configuration based on settings."""
  config = get_config()

  # Remove default logger
  logger.remove()

  # Configure console logging
  log_level = config.log_level

  # Add console handler
  logger.add(
    sys.stdout,
    level=log_level,
    colorize=True,
  )

  # Add file handler if enabled
  if config.enable_file_logging and config.log_file_path:
    logger.add(
      config.log_file_path,
      level=log_level,
      rotation="10 MB",
      retention="7 days",
    )

  logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

  logging.getLogger("ib_async").setLevel(logging.CRITICAL)
  logging.getLogger("uvicorn").setLevel(config.log_level)
  logging.getLogger("uvicorn.access").setLevel(config.log_level)
  logging.getLogger("uvicorn.error").setLevel(config.log_level)
  logging.getLogger("fastapi").setLevel(logging.CRITICAL)
  logging.getLogger("fastapi_mcp").setLevel(logging.CRITICAL)
  logging.getLogger("asyncio").setLevel(logging.CRITICAL)

  return logger


# Initialize logging
setup_logging()
