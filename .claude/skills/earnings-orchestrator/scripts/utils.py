"""Shared utilities for earnings scripts."""
import os
from contextlib import contextmanager
from dotenv import load_dotenv
from neo4j import GraphDatabase

ENV_PATH = "/home/faisal/EventMarketDB/.env"

def load_env():
    load_dotenv(ENV_PATH, override=True)

def get_neo4j_config():
    return (
        os.getenv("NEO4J_URI", "bolt://localhost:30687"),
        os.getenv("NEO4J_USERNAME", "neo4j"),
        os.getenv("NEO4J_PASSWORD")
    )

@contextmanager
def neo4j_session():
    """Context manager for Neo4j session. Yields (session, error_string)."""
    uri, user, password = get_neo4j_config()
    if not password:
        yield None, error("CONFIG", "NEO4J_PASSWORD not set")
        return
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            yield session, None
        driver.close()
    except Exception as e:
        yield None, parse_exception(e, uri)

def error(code: str, msg: str, hint: str = "") -> str:
    return f"ERROR|{code}|{msg}|{hint}" if hint else f"ERROR|{code}|{msg}"

def ok(code: str, msg: str, hint: str = "") -> str:
    return f"OK|{code}|{msg}|{hint}" if hint else f"OK|{code}|{msg}"

def parse_exception(e: Exception, uri: str = "") -> str:
    err_str = str(e).lower()
    if "connection" in err_str or "unavailable" in err_str or "refused" in err_str:
        return error("CONNECTION", "Database unavailable", f"Check Neo4j at {uri}")
    return error(type(e).__name__, str(e))

def fmt(v, dec: int = 2) -> str:
    return f"{v:.{dec}f}" if v is not None else "N/A"

def vol_status(days) -> str:
    return "OK" if days and days >= 60 else ("INSUFFICIENT" if days else "NO_DATA")
