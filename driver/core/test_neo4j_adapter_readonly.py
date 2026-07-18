"""LIVE read-only integration test for the thin adapter (S3.5 item 9). ZERO writes —
every call is a READ session; transaction() must refuse. Excluded from the default
gate (needs the live cluster); run explicitly like the numeric round-trip test."""
import pytest

from driver.core.driver_neo4j_adapter import Neo4jStore, preflight

ACC = "0001140361-23-000397"           # verified live 2026-07-17 (ACMR 8-K)


@pytest.fixture(scope="module")
def store():
    import os
    if not os.environ.get("NEO4J_URI"):
        from dotenv import load_dotenv
        load_dotenv()
    s = Neo4jStore()
    yield s
    s.close()


def test_source_metadata_reads(store):
    src = store.get_source(ACC)
    assert src["source_type"] == "8k" and src["ticker"] == "ACMR"
    assert src["fye_month"] == 12                  # string in the graph, int here
    assert src["date"].startswith("2023-01-04")
    assert store.get_source("no-such-accession") is None


def test_ownership_relationship_exactly_one_company(store):
    assert store.get_source_companies(ACC) == ["ACMR"]


def test_driver_siblings_periods_empty_pre_production(store):
    assert store.get_driver("revenue") is None     # no Driver nodes exist yet
    assert store.get_sibling_facts("du:x:revenue:period=gp_ST") == []
    assert store.get_period("gp_2025-06-29_2025-09-27") is None


def test_prior_guide_units_real_query_runs(store):
    # the REAL company/series/earlier-scoped query — empty result on the
    # pre-production graph, but the full Cypher (edges + datetime) executes live
    units = store.get_prior_guide_units(
        {"id": f"du:{ACC}:revenue_guidance:period=gp_2026-01-01_2026-12-31",
         "driver_name": "revenue_guidance",
         "fact_scope": "period=gp_2026-01-01_2026-12-31",
         "date": "2026-07-01T12:00:00-04:00", "time_type": "duration",
         "period_scope": "annual"})
    assert units == []


def test_company_slice_menu_retrieval_runs(store):
    # the REAL fold-menu retrieval (prior 10-K/10-Q members + used
    # fact_scopes), PIT-cut — executes live
    src = store.get_source(ACC)
    menu = store.get_company_slice_menu(ACC, src["date"])
    assert set(menu) == {"xbrl_members", "used_scopes"}
    assert menu["used_scopes"] == []               # pre-production: no facts yet
    for row in menu["xbrl_members"]:
        assert set(row) == {"axis", "member", "label"}
    assert store.get_xbrl_fact_dimensions(ACC, "us-gaap:Revenues") == []  # 8-K


AAPL_10Q = "0000320193-26-000006"                  # Q1-FY26 10-Q, verified live


def test_company_slice_menu_positive_aapl_regression(store):
    # THE padded/unpadded-CIK regression: AAPL has 1,886 dimensional contexts;
    # the un-normalized u_id join returned ZERO rows. The proven norm_uid fix
    # (strip leading zeros on the cik segment) must retrieve real members.
    src = store.get_source(AAPL_10Q)
    assert src["ticker"] == "AAPL" and src["source_type"] == "10q"
    menu = store.get_company_slice_menu(AAPL_10Q, src["date"])
    assert len(menu["xbrl_members"]) > 0           # prior filings' members
    axes = {r["axis"] for r in menu["xbrl_members"]}
    assert "us-gaap:StatementBusinessSegmentsAxis" in axes
    for row in menu["xbrl_members"]:
        assert row["axis"] and row["member"] and row["label"]


def test_xbrl_fact_level_verification_live_aapl(store):
    # the REAL fact-level match: AAPL Q1-FY26 product/service revenue —
    # concept + exact period (stored end EXCLUSIVE) + complete dimension set,
    # pinned live 2026-07-17
    from driver.core.slice_menu import match_xbrl_fact
    rows = store.get_xbrl_fact_dimensions(
        AAPL_10Q, "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax")
    assert rows                                    # the 10-Q has these facts
    matched = match_xbrl_fact(
        {"time_type": "duration", "start": "2025-09-28", "end": "2025-12-27",
         "dims": {("srt:ProductOrServiceAxis", "us-gaap:ProductMember")}}, rows)
    assert matched is not None                     # exact fact found
    assert matched[0]["label"]                     # label rides for recompute
    # and a NEVER-FILED dimension set must find nothing
    assert match_xbrl_fact(
        {"time_type": "duration", "start": "2025-09-28", "end": "2025-12-27",
         "dims": {("srt:ProductOrServiceAxis", "us-gaap:GhostMember")}},
        rows) is None


def test_uncatalogued_slice_axis_lives_in_graph_agilent(store):
    # the a:EndMarketsAxis lesson pinned LIVE: 246 real numeric end-market
    # facts exist (Pharmaceutical/Food/Diagnostics...) — an axis the catalog
    # never reviewed; classify_axis must send it down the provisional path
    from driver.core.slice_menu import classify_axis
    assert classify_axis("a:EndMarketsAxis") == ("unknown", None)
    n = store._read(
        "MATCH (d:Dimension {qname:'a:EndMarketsAxis'}) "
        "WITH collect(d.id) AS dids "
        "MATCH (c:Context) WHERE size(c.dimension_u_ids) > 0 "
        "UNWIND range(0, size(c.dimension_u_ids)-1) AS i "
        "WITH dids, c, c.dimension_u_ids[i] AS du "
        "WITH dids, c, split(du, ':')[0] AS ck, du "
        "WITH dids, c, toString(toInteger(ck)) + substring(du, size(ck)) AS ndu "
        "WHERE ndu IN dids "
        "MATCH (f:Fact)-[:IN_CONTEXT]->(c) WHERE f.is_numeric = '1' "
        "RETURN count(DISTINCT f) AS n")[0]["n"]
    assert n >= 246                                # append-only graph: safe floor


def test_writes_refused_outright(store):
    with pytest.raises(RuntimeError, match="DISABLED"):
        store.transaction()


def test_preflight_reports_honestly_and_creates_nothing(store):
    rep = preflight(store)
    assert rep["ready"] is False                   # nothing set up yet — HONEST
    assert rep["constraint_driver_name"] is False  # Driver.name uniqueness required
    assert set(rep["sentinels_missing"]) == {"gp_ST", "gp_MT", "gp_LT", "gp_UNDEF"}
