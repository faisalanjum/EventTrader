"""Phase-5 item 5 — the semantic Unit/divide handoff census gate.

Proves, on a REAL filing, that Fiscal's declared-unit handoff reaches the
neutral matcher for EVERY offered fact — exact row-for-row (multiset, never a
bare count), zero silent drops graph -> builder -> locate — and that
unsupported units abstain safely. The certified unit map is PINNED.

Census filing = the durable CE 10-Q `0001306830-24-000098` (tracked fixture,
hash-verified; the builder is POINTED AT the fixture dir in-test — the probe
cache is git-ignored and never relied on). Live tests skip ONLY on genuine
connection/config failure; assertion failures always surface.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from locator import ROUTE_A_BOOLS, locate  # noqa: E402

ACC = "0001306830-24-000098"
CONCEPT = "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"
FIX_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
SHA_OLD = "2c0a5134a44e6b930c16e8b2a4013d10fb02373c7005652aa328e6b2df681825"
TOTAL_FACTS = 899                     # HARD-PINNED census total for this filing


def _require_neo4j_env():
    """Config guard, up front: missing env = skip BEFORE any work."""
    if not (os.environ.get("NEO4J_URI") and os.environ.get("NEO4J_USERNAME")
            and os.environ.get("NEO4J_PASSWORD")):
        pytest.skip("Neo4j environment not configured")


def _skip_if_disconnected(e):
    """Narrow skip: ONLY genuine Neo4j connection-class failures. A missing
    fixture (OSError), a KeyError, or any logic/assertion error SURFACES."""
    names = {t.__name__ for t in type(e).__mro__}
    if {"ServiceUnavailable", "AuthError", "ConfigurationError",
            "SessionExpired"} & names:
        pytest.skip(f"Neo4j unavailable: {type(e).__name__}: {e}")
    raise e


def test_certified_unit_map_is_pinned_exactly():
    """The three certified readings, no drive-by growth — now asked of the
    identity-keyed tables. The graph-spelling map this used to pin
    (`ROUTE_A_SEM_UNIT`) was retired in #827 Stage 3: it keyed on prefixed text,
    so it refused the lawful alias `cur:USD` and accepted an `iso4217` prefix
    rebound to another namespace."""
    from exact_numbers import (ROUTE_A_SEM_UNIT_DIVIDE,
                               ROUTE_A_SEM_UNIT_SIMPLE)
    ISO = "http://www.xbrl.org/2003/iso4217"
    XBRLI = "http://www.xbrl.org/2003/instance"
    assert ROUTE_A_SEM_UNIT_SIMPLE == {((ISO, "USD"),): "usd",
                                       ((XBRLI, "shares"),): "count"}
    assert ROUTE_A_SEM_UNIT_DIVIDE == {
        (((ISO, "USD"),), ((XBRLI, "shares"),)): "usd_per_share"}
    assert ROUTE_A_BOOLS == {"0": False, "1": True}


def _graph_rows():
    from driver.core.driver_neo4j_adapter import Neo4jStore
    store = Neo4jStore()
    try:
        return store._read(
            "MATCH (x:XBRLNode {accessionNo:$acc})<-[:REPORTS]-(f:Fact) "
            "WHERE f.is_numeric='1' AND f.is_nil='0' "
            "MATCH (f)-[:HAS_UNIT]->(u:Unit) "
            "RETURN f.fact_id AS fact_id, f.value AS value, "
            "f.unit_ref AS unit_ref, u.name AS unit_name, "
            "u.is_divide AS is_divide", acc=ACC)
    finally:
        store.close()


def _fixture_source(monkeypatch):
    with open(os.path.join(FIX_DIR, ACC + ".htm"), "rb") as fh:
        data = fh.read()
    assert hashlib.sha256(data).hexdigest() == SHA_OLD, "fixture drifted"
    import route_a_source
    monkeypatch.setattr(route_a_source, "_CACHE", FIX_DIR)
    return route_a_source.build_source(ACC)


@pytest.mark.live
def test_ce_census_exact_rows_graph_to_builder(monkeypatch):
    _require_neo4j_env()
    sys.path.insert(0, str(Path(__file__).resolve()
                           .parents[2] / "scripts" / "driver_seed"))
    try:
        # INDEPENDENT unit-link invariant first: both comparison queries
        # require HAS_UNIT, so a unitless numeric fact could vanish from BOTH
        # sides — this query cannot be fooled that way
        from driver.core.driver_neo4j_adapter import Neo4jStore
        store = Neo4jStore()
        try:
            inv = store._read(
                "MATCH (x:XBRLNode {accessionNo:$acc})<-[:REPORTS]-(f:Fact) "
                "WHERE f.is_numeric='1' AND f.is_nil='0' "
                "OPTIONAL MATCH (f)-[:HAS_UNIT]->(u:Unit) "
                "WITH f, count(u) AS units "
                "RETURN count(f) AS numeric, "
                "sum(CASE WHEN units = 1 THEN 1 ELSE 0 END) AS exactly_one, "
                "sum(CASE WHEN units = 0 THEN 1 ELSE 0 END) AS missing, "
                "sum(CASE WHEN units > 1 THEN 1 ELSE 0 END) AS multiple",
                acc=ACC)[0]
        finally:
            store.close()
        graph = _graph_rows()
    except Exception as e:
        _skip_if_disconnected(e)
    assert inv == {"numeric": TOTAL_FACTS, "exactly_one": TOTAL_FACTS,
                   "missing": 0, "multiple": 0}, inv
    src = _fixture_source(monkeypatch)         # fixture errors SURFACE here
    assert src is not None
    # EXACT multiset comparison (never a bare count): one omitted fact plus
    # one duplicate must fail — every identity field compared row-for-row
    g = sorted((r["fact_id"], r["value"], r["unit_ref"],
                r["unit_name"], r["is_divide"]) for r in graph)
    b = sorted((fc["fact_id"], fc["value"], fc["unitRef"],
                fc["unit_name"], fc["is_divide"])
               for blob in src["xbrls"]
               for facts in json.loads(blob).values() for fc in facts)
    assert len(g) == TOTAL_FACTS                  # the hard-pinned total
    assert g == b                                 # row-for-row, both directions
    for _, _, ref, name, div in b:
        assert isinstance(ref, str) and ref.strip()
        assert isinstance(name, str) and name.strip()
        assert div in ("0", "1")


@pytest.mark.live
def test_full_source_end_to_end_recovers_the_388m_fact(tmp_path, monkeypatch):
    # TRULY end-to-end: the COMPLETE 899-row builder source (real decoys
    # included) through locate with the Core-rebuilt two-part anchor
    from test_multipart_anchor_ce import _core_anchor
    _require_neo4j_env()
    sys.path.insert(0, str(Path(__file__).resolve()
                           .parents[2] / "scripts" / "driver_seed"))
    anchor = _core_anchor(tmp_path)            # Core-side: no graph dependency
    try:
        src = _fixture_source(monkeypatch)     # graph query inside build_source
    except Exception as e:
        _skip_if_disconnected(e)
    assert src is not None
    out = locate(anchor, src)
    assert out["status"] is None, f"no recovery: {out['status']}"
    # the anchor carries NO period (relocation searches ACROSS periods — the
    # period is a RESULT): the real row "North America 388 365" prints the
    # series' TWO period instances, and each fact is proven against its OWN
    # printed value. Exactly these two, nothing else from 899 real decoys.
    from decimal import Decimal
    assert len(out["items"]) == 2
    by_period = {i["xbrl"]["period_start"][:4]: i for i in out["items"]}
    assert set(by_period) == {"2024", "2023"}
    assert by_period["2024"]["value"] == Decimal("388")   # our target fact
    assert by_period["2023"]["value"] == Decimal("365")   # its comparative
    for item in out["items"]:
        x = item["xbrl"]
        assert x["concept"] == CONCEPT
        assert sorted(tuple(p) for p in x["axis_members"]) == [
            ("srt:StatementGeographicalAxis", "srt:NorthAmericaMember"),
            ("us-gaap:StatementBusinessSegmentsAxis", "ce:AcetylChainMember")]
        assert item["quote"] == "North America 388\xa0 365\xa0"
        assert item["ix_evidence"]["scale"] == 6


def _anchor():
    return {"source_id": "0001306830-25-000105", "company": "CE",
            "driver": "revenue", "slice": "geography:north_america",
            "measurement": "", "series_unit": "m_usd",
            "time_type": "duration", "fact_type": "metric",
            "wording": ("North America 386\xa0 388",), "concept_clue": CONCEPT}


def _source_with(row):
    with open(os.path.join(FIX_DIR, ACC + ".htm"),
              encoding="utf-8", errors="replace") as fh:
        html = fh.read()
    return {"inline_html": html, "company_cik": "1306830",
            "xbrls": [json.dumps({CONCEPT: [row]})]}


def test_unsupported_and_malformed_units_abstain_safely():
    base = {"value": "388,000,000", "fact_id": "f-1025",
            "period": {"startDate": "2024-01-01", "endDate": "2024-04-01"},
            "segment": [{"explicitMember": [
                {"dimension": "srt:StatementGeographicalAxis",
                 "$t": "srt:NorthAmericaMember"},
                {"dimension": "us-gaap:StatementBusinessSegmentsAxis",
                 "$t": "ce:AcetylChainMember"}]}]}
    for unit_over in (
            {"unitRef": "eur", "unit_name": "iso4217:EUR", "is_divide": "0"},
            {"unitRef": "usd", "unit_name": "iso4217:USD", "is_divide": "2"},
            {"unitRef": "usd", "unit_name": "iso4217:USD", "is_divide": True},
            {"unitRef": "usd", "unit_name": None, "is_divide": "0"},
            {"unitRef": "", "unit_name": "iso4217:USD", "is_divide": "0"}):
        out = locate(_anchor(), _source_with({**base, **unit_over}))
        # the ONLY candidate carries an unsupported/malformed declared unit:
        # the matcher ABSTAINS (honest no_proven_match) — no crash, no guess
        assert out["status"] == "no_proven_match", unit_over
        assert out["items"] == []


def test_EU001_the_route_a_unit_maps_are_pinned_and_C1_membered():
    """EU-001 (#827): the three Route-A unit maps pinned member-for-member
    (the census gate above proves the live handoff; this pins the CONTRACT),
    and the canonical side is a subset of C1's one vocabulary
    (slot_convert.CANONICAL_UNITS) — asserted here because the shared binder
    may not import Core (the F7 both-sides pattern)."""
    from driver.core.slot_convert import CANONICAL_UNITS
    from driver.relocation.exact_numbers import (ISO_4217_NAMESPACE,
                                                 ROUTE_A_SEM_UNIT_DIVIDE,
                                                 ROUTE_A_SEM_UNIT_SIMPLE,
                                                 ROUTE_A_UNIT_COMPAT,
                                                 XBRL_INSTANCE_NAMESPACE)
    assert ROUTE_A_SEM_UNIT_SIMPLE == {
        ((ISO_4217_NAMESPACE, 'USD'),): 'usd',
        ((XBRL_INSTANCE_NAMESPACE, 'shares'),): 'count'}
    assert ROUTE_A_SEM_UNIT_DIVIDE == {
        (((ISO_4217_NAMESPACE, 'USD'),),
         ((XBRL_INSTANCE_NAMESPACE, 'shares'),)): 'usd_per_share'}
    assert ROUTE_A_UNIT_COMPAT == {
        'usd': frozenset({'usd', 'usd_per_share'}),
        'm_usd': frozenset({'usd'}),
        'count': frozenset({'count'})}
    assert set(ROUTE_A_UNIT_COMPAT) <= set(CANONICAL_UNITS), \
        "every canonical key is C1's (the one unit vocabulary)"


def test_EU033_the_semantic_reader_is_fail_closed_on_its_branch_keys():
    """EU-033 (#827): route_a_semantic_unit's branch keys (is_divide,
    expanded_numerator/denominator, expanded_measures) are statement-level
    audited — the divide branch must fire on the divide record (a drifted
    branch key would silently abstain every usd_per_share), and every
    unknown/malformed shape ABSTAINS (the fail-closed stance; recall
    measured in g2_evid_recall_EU-033.txt)."""
    from driver.relocation.exact_numbers import (ISO_4217_NAMESPACE,
                                                 XBRL_INSTANCE_NAMESPACE,
                                                 route_a_semantic_unit)
    usd = ((ISO_4217_NAMESPACE, 'USD'),)
    shares = ((XBRL_INSTANCE_NAMESPACE, 'shares'),)
    assert route_a_semantic_unit(
        {'is_divide': True, 'expanded_numerator': usd,
         'expanded_denominator': shares}) == 'usd_per_share'
    assert route_a_semantic_unit(
        {'is_divide': False, 'expanded_measures': usd}) == 'usd'
    # the fail-closed side: unknown, incomplete and non-mapping shapes abstain
    assert route_a_semantic_unit(
        {'expanded_numerator': usd, 'expanded_denominator': shares}) is None
    assert route_a_semantic_unit({'is_divide': True}) is None
    assert route_a_semantic_unit("usd") is None
    assert route_a_semantic_unit(None) is None
