"""Authentication dependency for the IBKR MCP Server."""

import secrets
from fastapi import status, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import get_config

# A list of paths that do not require authentication
UNPROTECTED_PATHS = [
  "/",
  "/health",
  "/gateway/status",
]

# 1. Tell HTTPBearer not to raise an error if the token is missing
token_auth_scheme = HTTPBearer(auto_error=False)
token_dependency = Depends(token_auth_scheme)


async def auth_dependency(
  request: Request,
  token: HTTPAuthorizationCredentials | None = token_dependency,
) -> str | None:
  """Dependency to verify the bearer token, allowing for unprotected routes."""
  if request.url.path in UNPROTECTED_PATHS:
    return None

  if token is None:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Not authenticated",
      headers={"WWW-Authenticate": "Bearer"},
    )

  config = get_config()
  expected_token = config.get_effective_auth_token()

  if not expected_token:
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail="Authentication token not configured on the server.",
    )

  if not secrets.compare_digest(token.credentials, expected_token):
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Invalid authentication token",
      headers={"WWW-Authenticate": "Bearer"},
    )

  return token.credentials
