"""HTTP runtime for mcp-neo4j-cypher, hardened for Phase H.

Differences from the inline Deployment version:
  * Fail-fast env validation (clear error if NEO4J_URI/USERNAME/PASSWORD missing).
  * /health route that runs 'RETURN 1' against Neo4j (for kubelet HTTP probe).
  * SIGTERM handler closes the async driver cleanly before uvicorn shutdown.
"""
import asyncio
import os
import signal
import sys

import uvicorn
from neo4j import AsyncGraphDatabase
from starlette.responses import JSONResponse
from starlette.routing import Route

from mcp_neo4j_cypher.server import create_mcp_server, healthcheck


def _require(name: str) -> str:
    v = os.getenv(name)
    if not v:
        print(f"FATAL: required env var {name} is missing or empty", file=sys.stderr)
        sys.exit(2)
    return v


def main() -> None:
    db_url   = _require("NEO4J_URI")
    username = _require("NEO4J_USERNAME")
    password = _require("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    # Synchronous startup healthcheck (3 retries, up to ~12s).
    # Fail here means CrashLoopBackOff until Neo4j is reachable.
    healthcheck(db_url, username, password, database)

    driver = AsyncGraphDatabase.driver(db_url, auth=(username, password))
    mcp = create_mcp_server(driver, database)

    async def health(_request):
        try:
            async with driver.session(database=database) as s:
                await (await s.run("RETURN 1 AS x")).single()
            return JSONResponse({"status": "ok"})
        except Exception as e:
            return JSONResponse(
                {"status": "unhealthy", "error": f"{type(e).__name__}: {e}"},
                status_code=503,
            )

    app = mcp.streamable_http_app()
    app.routes.append(Route("/health", health, methods=["GET"]))

    loop = asyncio.new_event_loop()

    async def _close_driver():
        try:
            await driver.close()
        except Exception:
            pass

    def _on_sigterm(signum, frame):
        # Close driver, let uvicorn propagate shutdown
        try:
            loop.run_until_complete(_close_driver())
        except Exception:
            pass

    signal.signal(signal.SIGTERM, _on_sigterm)

    print("Starting HTTP server on port 8000...", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
