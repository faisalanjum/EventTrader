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

OPT_IN = "RUN_NEO4J_ROUNDTRIP_PROBE"


def _require_opt_in():
    """The opt-in gate, INSIDE the test rather than at module level.

    WHY IT MOVED. As a module-level `pytest.skip(..., allow_module_level=True)`
    the skip fired during COLLECTION, before any marker could be considered — so
    `-m "not live_write"` could not deselect it, the clean lane collected it as a
    skip, and that skip then had to be pinned as an accepted exception. A write
    probe recorded as "an allowed skip" is not isolated from anything; it was one
    environment variable away from running, and the re-pin command ran with the
    full environment and no marker filter.

    With the gate here, the module is collected normally, `live_write` deselects
    it in every default lane, and it can only execute when someone deliberately
    selects that marker AND sets the variable.

    EXACTLY "1", not truthiness: under `if not get(OPT_IN)` the value "0" —
    which every reader understands as OFF — AUTHORIZED the write. An
    authorization token has ONE spelling; anything else, including "0",
    "false", "yes" or whitespace, refuses.
    """
    if os.environ.get(OPT_IN) != "1":
        pytest.skip(f"live write/delete probe is opt-in only (owner approval "
                    f"required) — set {OPT_IN}=1 (exactly)")

# ITS OWN LANE, not `live`. `live` is the READ-ONLY graph lane and every default
# gate runs it; this probe WRITES and DELETES, so it must never be reachable by
# widening a read-only selector. The env gate above already keeps it out of every
# run; the marker makes the distinction selectable and visible rather than
# implicit in one environment variable.
pytestmark = pytest.mark.live_write

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
    # FIRST STATEMENT, before anything can reach the graph. Selecting the
    # `live_write` marker alone must NEVER be enough to write: while this guard was
    # only at module level it fired during collection, so a marker could not
    # deselect it — and when the module-level skip was removed to fix that, a bare
    # `-m live_write` run executed the probe and it created and deleted a real node.
    # Two independent conditions are now required: the marker AND the variable.
    _require_opt_in()
    # INSIDE the test, AFTER the guard: at module level this fired during
    # COLLECTION, so on a machine without the neo4j package the clean lane
    # recorded a skip no marker could deselect.
    neo4j = pytest.importorskip("neo4j")
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
