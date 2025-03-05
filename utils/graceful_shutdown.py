import signal
import sys
import time
import logging
from typing import List, Any

logger = logging.getLogger("graceful_shutdown")

# List of active websocket connections
active_websockets = []

def register_websocket(websocket: Any) -> None:
    """Register a websocket connection for graceful shutdown
    
    Args:
        websocket: A websocket connection object with a disconnect() method
    """
    global active_websockets
    active_websockets.append(websocket)
    logger.debug(f"Registered websocket for graceful shutdown: {websocket.__class__.__name__}")

def deregister_websocket(websocket: Any) -> None:
    """Deregister a websocket connection
    
    Args:
        websocket: A websocket connection object to remove
    """
    global active_websockets
    if websocket in active_websockets:
        active_websockets.remove(websocket)
        logger.debug(f"Deregistered websocket: {websocket.__class__.__name__}")

def signal_handler(sig: int, frame: Any) -> None:
    """Handle termination signals by gracefully disconnecting websockets
    
    Args:
        sig: Signal number
        frame: Current stack frame
    """
    signal_name = "SIGINT" if sig == signal.SIGINT else "SIGTERM"
    logger.info(f"Received {signal_name}. Shutting down gracefully...")
    
    # Disconnect all active websockets
    for websocket in active_websockets:
        try:
            logger.info(f"Disconnecting {websocket.__class__.__name__}...")
            websocket.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting {websocket.__class__.__name__}: {e}")
    
    # Wait a moment for Redis operations to complete
    time.sleep(1)
    
    logger.info("Graceful shutdown complete.")
    sys.exit(0)

def register_signal_handlers() -> None:
    """Register signal handlers for graceful shutdown"""
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # kill command
    logger.info("Registered signal handlers for graceful shutdown") 