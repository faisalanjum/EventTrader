"""Endpoints for the IBKR MCP server."""

from fastapi import APIRouter
from app.services.interfaces import IBInterface

ibkr_router = APIRouter(prefix="/ibkr", tags=["ibkr"])

# Initialize shared interface
ib_interface = IBInterface()

# Import all endpoints
from .positions import *
from .contracts import *
from .scanners import *
from .market_data import *
from .history import *
from .account import *
from .orders import *
