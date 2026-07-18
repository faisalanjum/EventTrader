"""Anchor schema probe — durable, zero-write, zero-token (Universal Locator v5.5 §2).

Proves: the id/fact_scope grammar + stored fields + edges carry EVERY anchor component, with a
STRICT metric-only decoder that (a) rejects `surprise=` and unknown slots, (b) asserts
Driver-name/type agreement, (c) asserts stored fact_scope == id suffix, and (d) resolves the
company ONLY from the source id PARSED OUT OF THE FACT ID via an edge map. The edge map is TRUSTED
internal output of the exactly-one graph-edge query: the probe proves parsed-source lookup and
rejects missing/cross-wired KEYS — it does not authenticate a fabricated VALUE under the correct
key (duplicating graph validation here would be pointless).

Scope, stated exactly: ids are composed by Core's AUTHORITATIVE pure id law
(`driver/core/driver_ids.py`, test-only import) and the decoder under test is independent.
ONLY the source→Company edges are loaded LIVE (exactly one per pinned accession, else FAIL);
quote/unit/Driver payloads are PINNED FIXTURES. Fixtures use legal period forms, but this probe
does NOT validate period legality — Core's validators own that and nothing here duplicates them.
ZERO fiscal.ai/channel imports (Neo4j env read neutrally from the repo .env).

    venv/bin/python -m pytest driver/relocation/test_anchor_schema_probe.py -q

Skip policy: ONLY a genuinely unavailable graph skips; query errors or missing pinned edges FAIL.
NOT proven here (mandatory S4/WP2 gate): reconstruction from live graph nodes, birth_quotes
persistence on real nodes, locator accuracy from rebuilt anchors.
"""
import os
import sys
import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", ".."))
sys.path.insert(0, os.path.join(_REPO, "driver", "core"))   # test-only: the authoritative id law
import driver_ids as DI                                      # pure functions, no I/O


# ---------- neutral Neo4j env (no channel imports) ----------
def _neo4j_env():
    env = {}
    with open(os.path.join(_REPO, ".env")) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.removeprefix("export ").strip()] = v.strip().strip("'\"")
    return env


def _one_company_edge(session, accession):
    """The source→Company edge for one accession — must be EXACTLY one, else FAIL (never skip)."""
    rows = list(session.run(
        """MATCH (r:Report {accessionNo:$a})-[:PRIMARY_FILER]->(c:Company)
           RETURN c.cik AS cik""", a=accession))
    assert len(rows) == 1, f"expected exactly one company edge for {accession}, got {len(rows)}"
    return rows[0]["cik"]


def _graph_session():
    """Connect or skip — ONLY on genuine unavailability. Query errors later still fail."""
    env = _neo4j_env()
    try:
        from neo4j import GraphDatabase
        from neo4j.exceptions import ServiceUnavailable
    except ImportError:
        pytest.skip("neo4j driver not installed")
    try:
        g = GraphDatabase.driver(env["NEO4J_URI"],
                                 auth=(env.get("NEO4J_USERNAME", "neo4j"), env["NEO4J_PASSWORD"]))
        g.verify_connectivity()
        return g
    except (ServiceUnavailable, OSError, KeyError) as e:
        pytest.skip(f"live graph genuinely unavailable: {e}")


# ---------- THE strict metric-only decoder under test (independent of core) ----------
ALLOWED_SLOTS = ("period", "slice", "measurement", "quote_hash")   # surprise= NOT allowed


def strict_decode(fact_id, props, driver_node, edge_map):
    """edge_map: {source_id: company_key} — the ONLY way a company enters. The decoder looks up
    the source id PARSED FROM THE FACT ID; a fact whose own source is not in the map FAILS.
    (The decoder is as right as the resolver; in real tests the resolver is a live
    exactly-one-edge graph query keyed by the same accession.)"""
    seg = fact_id.split(":", 3)
    assert len(seg) == 4 and seg[0] == "du", f"bad id shape: {fact_id!r}"
    _, source_id, driver, scope = seg
    if props["fact_scope"] != scope:
        raise ValueError(f"stored fact_scope != id suffix: {props['fact_scope']!r} vs {scope!r}")
    parsed = {}
    for slot in scope.split("|"):
        k, _, v = slot.partition("=")
        if k not in ALLOWED_SLOTS:
            raise ValueError(f"metric-only decoder: forbidden/unknown slot {k!r}")
        if k in parsed:
            raise ValueError(f"duplicate slot {k!r}")
        parsed[k] = v
    assert "period" in parsed, "period slot missing"
    if driver_node["name"] != driver:
        raise ValueError(f"Driver node name {driver_node['name']!r} != id driver {driver!r}")
    if driver_node["fact_type"] != "metric":
        raise ValueError(f"not a metric Driver: {driver_node['fact_type']!r}")
    company = edge_map.get(source_id)
    if company is None:
        raise ValueError(f"no company edge for THIS fact's source id {source_id!r} "
                         f"(cross-wired or missing edge)")
    anchor = {
        "source_id": source_id,
        "company": company,
        "driver": driver,
        "slice": parsed.get("slice", ""),
        "measurement": parsed.get("measurement", ""),
        "series_unit": props["series_unit"],
        "time_type": props["time_type"],
        "fact_type": driver_node["fact_type"],
        "wording": tuple(driver_node["definitional_evidence"]["birth_quotes"]),
    }
    return anchor, sorted(k for k in ("period", "quote_hash") if k in parsed)


def drv(name, bq):
    return {"name": name, "fact_type": "metric",
            "definitional_evidence": {"birth_quotes": list(bq)}}


def props(fid, series_unit, time_type):
    """simulated stored node props: fact_scope mirrors the writer (= the id suffix)."""
    return {"fact_scope": fid.split(":", 3)[3], "series_unit": series_unit, "time_type": time_type}


# ---------- pinned accessions (from part1 harvest data); edges loaded LIVE in their tests ----------
AA_ACC = "0000950170-25-024242"    # Alcoa 10-K
AAL_ACC = "0000006201-25-000010"   # American Airlines


def test_1_real_edge_aa_numeric_text():
    fid, _ = DI.build_id(AA_ACC, "revenue", period_id="gp_2024-01-01_2024-12-31",
                         slice_parts=(("geography", "United States"),))
    assert fid == ("du:0000950170-25-024242:revenue:"
                   "period=gp_2024-01-01_2024-12-31|slice=geography:united_states")
    g = _graph_session()
    with g.session() as s:
        edge_map = {AA_ACC: _one_company_edge(s, AA_ACC)}
    g.close()
    a, stripped = strict_decode(fid, props(fid, "m_usd", "duration"),
                                drv("revenue", ("United States (1) $ 5,365",)), edge_map)
    assert a["slice"] == "geography:united_states" and a["company"] == edge_map[AA_ACC]
    assert stripped == ["period"]


def test_2_synthetic_dimensionless():
    fid, _ = DI.build_id("SYN-ACC-A", "revenue", period_id="gp_2023-10-01_2024-09-28")
    a, stripped = strict_decode(fid, props(fid, "m_usd", "duration"),
                                drv("revenue", ("Total revenue $ 6,707",)), {"SYN-ACC-A": "SYNCIK-A"})
    assert a["slice"] == "" and a["measurement"] == "" and stripped == ["period"]


def test_3_synthetic_dimensioned_segment_normalized():
    fid, _ = DI.build_id("SYN-ACC-B", "revenue", period_id="gp_2024-11-01_2025-01-31",
                         slice_parts=(("segment", "Life Sciences & Applied Markets"),))
    a, _ = strict_decode(fid, props(fid, "m_usd", "duration"),
                         drv("revenue", ("Life sciences and applied markets $ 968",)),
                         {"SYN-ACC-B": "SYNCIK-B"})
    assert a["slice"].startswith("segment:life_sciences")


def test_4_synthetic_numberless_duration_series_unit_none():
    fid, _ = DI.build_id("SYN-ACC-C", "weather_condition", period_id="gp_2024-01-01_2024-03-31")
    a, _ = strict_decode(fid, props(fid, None, "duration"),
                         drv("weather_condition", ("unusually cold winter across texas",)),
                         {"SYN-ACC-C": "SYNCIK-C"})
    assert a["series_unit"] is None and a["time_type"] == "duration"
    assert a["wording"] == ("unusually cold winter across texas",)


def test_5_synthetic_instant_uses_legal_gp_date_date():
    fid, _ = DI.build_id("SYN-ACC-D", "store_count", period_id="gp_2025-12-31_2025-12-31")
    a, _ = strict_decode(fid, props(fid, "count", "instant"),
                         drv("store_count", ("International Stores 86 at fiscal year end",)),
                         {"SYN-ACC-D": "SYNCIK-D"})
    assert a["time_type"] == "instant"


def test_6_synthetic_collision_member_hash_stripped():
    qh = DI.signature_hash([None] * 8 + ["a", None])
    bare, _ = DI.build_id("SYN-ACC-E", "inventory_writedown", period_id="gp_2024-01-01_2024-03-31")
    member = DI.member_id(bare, qh)
    d = drv("inventory_writedown", ("inventory write-down of $ 12",))
    em = {"SYN-ACC-E": "SYNCIK-E"}
    a1, s1 = strict_decode(bare, props(bare, "m_usd", "duration"), d, em)
    a2, s2 = strict_decode(member, props(member, "m_usd", "duration"), d, em)
    assert a1 == a2 and s1 == ["period"] and s2 == ["period", "quote_hash"]


def test_7_synthetic_two_series_one_driver():
    d = drv("operating_margin", ("operating margin was 12.4%",))
    em = {"SYN-ACC-F": "SYNCIK-F"}
    f1, _ = DI.build_id("SYN-ACC-F", "operating_margin", period_id="gp_2024-01-01_2024-12-31")
    f2, _ = DI.build_id("SYN-ACC-F", "operating_margin", period_id="gp_2024-01-01_2024-12-31",
                        measurement_tokens=("adjusted",))
    a, _ = strict_decode(f1, props(f1, "percent", "duration"), d, em)
    b, _ = strict_decode(f2, props(f2, "percent", "duration"), d, em)
    assert a != b and b["measurement"] == "adjusted"


def test_8_synthetic_replaced_lww_quote_uses_birth_quotes():
    d = drv("store_count", ("International Stores 86 at fiscal year end",))
    fid, _ = DI.build_id("SYN-ACC-G", "store_count", period_id="gp_2025-12-31_2025-12-31")
    a, _ = strict_decode(fid, props(fid, "count", "instant"), d, {"SYN-ACC-G": "SYNCIK-G"})
    assert a["wording"] == ("International Stores 86 at fiscal year end",)


def test_9_metric_decoder_rejects_surprise_and_unknown_slots():
    fid, _ = DI.build_id("SYN-ACC-H", "eps", period_id="gp_2024-01-01_2024-03-31",
                         surprise="actual_vs_consensus")
    with pytest.raises(ValueError, match="forbidden/unknown"):
        strict_decode(fid, props(fid, "usd", "duration"), drv("eps", ("EPS of $ 1.23",)),
                      {"SYN-ACC-H": "C"})
    plain, _ = DI.build_id("SYN-ACC-H", "eps", period_id="gp_2024-01-01_2024-03-31")
    bogus = plain + "|bogus=1"
    with pytest.raises(ValueError, match="forbidden/unknown"):
        strict_decode(bogus, {"fact_scope": bogus.split(":", 3)[3],
                              "series_unit": "usd", "time_type": "duration"},
                      drv("eps", ("EPS of $ 1.23",)), {"SYN-ACC-H": "C"})


def test_10_driver_name_mismatch_rejected():
    fid, _ = DI.build_id("SYN-ACC-I", "revenue", period_id="gp_2024-01-01_2024-12-31")
    with pytest.raises(ValueError, match="!= id driver"):
        strict_decode(fid, props(fid, "m_usd", "duration"), drv("gross_margin", ("q",)),
                      {"SYN-ACC-I": "C"})


def test_11_stored_fact_scope_must_match_id_suffix():
    fid, _ = DI.build_id("SYN-ACC-J", "revenue", period_id="gp_2024-01-01_2024-12-31")
    bad = props(fid, "m_usd", "duration")
    bad["fact_scope"] = "period=gp_2020-01-01_2020-12-31"
    with pytest.raises(ValueError, match="stored fact_scope != id suffix"):
        strict_decode(fid, bad, drv("revenue", ("q",)), {"SYN-ACC-J": "C"})


def test_12_cross_wired_company_rejected():
    """The round-9 defect, pinned: a company supplied for a DIFFERENT source must never bind.
    The decoder may only use the edge of the fact's OWN parsed source id."""
    fid, _ = DI.build_id(AA_ACC, "revenue", period_id="gp_2024-01-01_2024-12-31")
    wrong_map = {AAL_ACC: "0000006201"}          # an edge — but for ANOTHER source
    with pytest.raises(ValueError, match="cross-wired or missing edge"):
        strict_decode(fid, props(fid, "m_usd", "duration"), drv("revenue", ("q",)), wrong_map)
    with pytest.raises(ValueError, match="cross-wired or missing edge"):
        strict_decode(fid, props(fid, "m_usd", "duration"), drv("revenue", ("q",)), {})


def test_13_real_cross_company_isolation_two_live_edges():
    """Same driver name, two REAL companies — edges loaded live, exactly one each, keyed by
    each fact's own accession."""
    g = _graph_session()
    with g.session() as s:
        edge_map = {AA_ACC: _one_company_edge(s, AA_ACC),
                    AAL_ACC: _one_company_edge(s, AAL_ACC)}
    g.close()
    assert edge_map[AA_ACC] != edge_map[AAL_ACC], "pinned accessions must be distinct companies"
    d = drv("revenue", ("q",))
    f1, _ = DI.build_id(AA_ACC, "revenue", period_id="gp_2024-01-01_2024-12-31")
    f2, _ = DI.build_id(AAL_ACC, "revenue", period_id="gp_2024-01-01_2024-12-31")
    x, _ = strict_decode(f1, props(f1, "m_usd", "duration"), d, edge_map)
    y, _ = strict_decode(f2, props(f2, "m_usd", "duration"), d, edge_map)
    assert x != y and x["company"] != y["company"]
