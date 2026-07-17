"""The REAL Neo4j round-trip proof of the owner exactness storage law (ordered
2026-07-17 — the ONE sanctioned Neo4j write in S3): a self-deleting probe node under
its own label proves that every value the writer classifies as storable comes back
EXACTLY, including whole numbers beyond float precision (why integers store as longs).
Skips cleanly when no Neo4j is reachable; deletes its node in all cases.

OPT-IN ONLY (owner ruling 2026-07-17): normal unit runs must perform ZERO live
writes. Run this probe only with explicit owner approval when storage behavior
changes:  RUN_NEO4J_ROUNDTRIP_PROBE=1 venv/bin/python -m pytest driver/core/test_neo4j_numeric_roundtrip.py"""
import os
import uuid
from decimal import Decimal
from pathlib import Path

import pytest

if not os.environ.get("RUN_NEO4J_ROUNDTRIP_PROBE"):
    pytest.skip("live write/delete probe is opt-in only (owner approval required) — "
                "set RUN_NEO4J_ROUNDTRIP_PROBE=1", allow_module_level=True)

neo4j = pytest.importorskip("neo4j")

from driver.core.driver_writer import storable  # noqa: E402

INT_SAMPLES = [1500, 9007199254740993, -42, 2 ** 62]          # incl. 2^53+1 (> float)
DEC_SAMPLES = [Decimal("4.9"), Decimal("1234567890123.45"), Decimal("0.001"),
               Decimal("-0.2"), Decimal("123.456789"), Decimal("0.1234567")]


def _config():
    env = dict(os.environ)
    env_file = Path(__file__).resolve().parents[2] / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, _, val = line.partition("=")
                env.setdefault(k.strip(), val.strip().strip('"').strip("'"))
    return env.get("NEO4J_URI"), env.get("NEO4J_USERNAME"), env.get("NEO4J_PASSWORD")


def test_real_neo4j_roundtrip_of_the_exactness_storage_law():
    uri, user, password = _config()
    if not uri or not user:
        pytest.skip("no Neo4j configuration available")
    props, exact = {}, {}
    for i, v in enumerate(INT_SAMPLES):
        kind, native = storable(v)
        assert kind == "int"
        props[f"i{i}"], exact[f"i{i}"] = native, v
    for i, d in enumerate(DEC_SAMPLES):
        kind, native = storable(d)
        assert kind == "float"
        props[f"d{i}"], exact[f"d{i}"] = native, d

    try:
        driver = neo4j.GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
    except Exception as e:
        pytest.skip(f"Neo4j unreachable: {e}")
    tid = uuid.uuid4().hex
    try:
        with driver.session() as s:
            s.run("CREATE (n:_DriverNumericRoundtripProbe {tid: $tid}) SET n += $props",
                  tid=tid, props=props)
            node = s.run("MATCH (n:_DriverNumericRoundtripProbe {tid: $tid}) RETURN n",
                         tid=tid).single()["n"]
        for key, original in exact.items():
            got = node[key]
            if isinstance(original, int):
                assert isinstance(got, int) and got == original, (key, got, original)
            else:
                # the read adapter's law: Decimal(repr(read_float)) recovers the
                # exact original decimal — because only round-trip-exact floats
                # are ever stored
                assert Decimal(repr(got)) == original, (key, got, original)
    finally:
        with driver.session() as s:
            s.run("MATCH (n:_DriverNumericRoundtripProbe {tid: $tid}) DETACH DELETE n",
                  tid=tid)
        driver.close()
