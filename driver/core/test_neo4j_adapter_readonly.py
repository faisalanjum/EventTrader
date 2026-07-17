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


def test_writes_refused_outright(store):
    with pytest.raises(RuntimeError, match="DISABLED"):
        store.transaction()


def test_preflight_reports_honestly_and_creates_nothing(store):
    rep = preflight(store)
    assert rep["ready"] is False                   # nothing set up yet — HONEST
    assert rep["constraint_driver_name"] is False  # Driver.name uniqueness required
    assert set(rep["sentinels_missing"]) == {"gp_ST", "gp_MT", "gp_LT", "gp_UNDEF"}
