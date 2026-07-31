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


@pytest.mark.live
def test_source_metadata_reads(store):
    src = store.get_source(ACC)
    assert src["source_type"] == "8k" and src["ticker"] == "ACMR"
    assert src["fye_month"] == 12                  # string in the graph, int here
    assert src["date"].startswith("2023-01-04")
    assert store.get_source("no-such-accession") is None


@pytest.mark.live
def test_ownership_relationship_exactly_one_company(store):
    assert store.get_source_companies(ACC) == ["ACMR"]


@pytest.mark.live
def test_driver_siblings_periods_empty_pre_production(store):
    assert store.get_driver("revenue") is None     # no Driver nodes exist yet
    assert store.get_sibling_facts("du:x:revenue:period=gp_ST") == []
    assert store.get_period("gp_2025-06-29_2025-09-27") is None


@pytest.mark.live
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
@pytest.mark.live
def test_company_slice_menu_retrieval_runs(store):
    # the REAL fold-menu retrieval (prior 10-K/10-Q members + used
    # fact_scopes), PIT-cut — executes live
    src = store.get_source(ACC)
    menu = store.get_company_slice_menu(ACC, src["date"])
    assert set(menu) == {"xbrl_members", "used_scopes"}
    assert menu["used_scopes"] == []               # pre-production: no facts yet
    for row in menu["xbrl_members"]:
        assert set(row) == {"axis", "member", "label"}
    assert store.get_xbrl_fact_dimensions(ACC, "us-gaap:Revenues").rows == ()  # 8-K


AAPL_10Q = "0000320193-26-000006"                  # Q1-FY26 10-Q, verified live


@pytest.mark.live
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


@pytest.mark.live
def test_xbrl_fact_level_verification_live_aapl(store):
    # the REAL fact-level match: AAPL Q1-FY26 product/service revenue —
    # concept + exact period (stored end EXCLUSIVE) + complete dimension set,
    # pinned live 2026-07-17
    from driver.core.slice_menu import match_xbrl_fact
    rows = store.get_xbrl_fact_dimensions(AAPL_10Q, "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax").rows
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


@pytest.mark.live
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


@pytest.mark.live
def test_writes_refused_outright(store):
    with pytest.raises(RuntimeError, match="DISABLED"):
        store.transaction()


@pytest.mark.live
def test_preflight_reports_honestly_and_creates_nothing(store):
    rep = preflight(store)
    assert rep["ready"] is False                   # nothing set up yet — HONEST
    assert rep["constraint_driver_name"] is False  # Driver.name uniqueness required
    assert set(rep["sentinels_missing"]) == {"gp_ST", "gp_MT", "gp_LT", "gp_UNDEF"}


# ---------------------------------------------------------------------------
# #822 — Dimension/Member id resolution must not be last-write-wins.
# ---------------------------------------------------------------------------

def test_identical_duplicate_id_records_COLLAPSE():
    from driver.core.driver_neo4j_adapter import _resolve_id_records
    rec = {"id": "1:d", "kind": "Dimension", "qname": "us-gaap:Ax",
           "label": None}
    out = _resolve_id_records([rec, dict(rec), dict(rec)])
    assert out == {"1:d": rec}, out


def test_CONFLICTING_duplicate_id_records_poison_the_lookup():
    """Last-write-wins meant the axis or member a fact bound against depended on
    the order the driver happened to return rows in. A poisoned id is falsy, and
    the caller already drops any fact whose pair will not resolve."""
    from driver.core.driver_neo4j_adapter import _resolve_id_records
    a = {"id": "1:d", "kind": "Member", "qname": "us-gaap:Ax", "label": "Foo"}
    b = {"id": "1:d", "kind": "Member", "qname": "us-gaap:Ax", "label": "Bar"}
    c = {"id": "1:d", "kind": "Member", "qname": "srt:Other", "label": "Foo"}
    for pair in ((a, b), (b, a), (a, c), (c, a)):
        out = _resolve_id_records(list(pair))
        assert out["1:d"] is None, f"{pair} resolved to {out['1:d']}"
        assert not out["1:d"], "a poisoned id must be falsy so callers park"


def test_a_poisoned_id_does_not_poison_its_NEIGHBOURS():
    """POSITIVE CONTROL — one ambiguous id must not cost the lawful ones."""
    from driver.core.driver_neo4j_adapter import _resolve_id_records
    good = {"id": "1:m", "kind": "Member", "qname": "x:M", "label": "Europe"}
    out = _resolve_id_records([
        {"id": "1:d", "kind": "Member", "qname": "a", "label": "A"},
        {"id": "1:d", "kind": "Member", "qname": "b", "label": "B"}, good])
    assert out["1:d"] is None and out["1:m"] == good


@pytest.mark.parametrize("bad", ["not-a-dict", None, 5,
                                 {"qname": "x", "label": "L"},
                                 {"id": ["unhashable"], "qname": "q", "label": "L"},
                                 {"id": None, "qname": "q", "label": "L"}])
def test_a_MALFORMED_definition_record_never_raises_a_raw_error(bad):
    """I added `_resolve_id_records` one turn ago WHILE fixing the raw-crash
    class, and put the same defect straight back in: it raised ValueError,
    KeyError and TypeError on malformed records. A record we cannot read leaves
    its id UNRESOLVED, and the caller already drops such a fact fail-closed."""
    from driver.core.driver_neo4j_adapter import _resolve_id_records
    out = _resolve_id_records([bad])
    assert isinstance(out, dict)


def test_an_id_must_resolve_to_the_RIGHT_KIND_of_node():
    """The axis id must be a Dimension and the member id a Member. Nothing
    checked, so a member's qname could be written into the AXIS position."""
    from driver.core.driver_neo4j_adapter import _resolve_id_records
    out = _resolve_id_records([
        {"id": "1:d", "kind": "Dimension", "qname": "us-gaap:Ax", "label": None},
        {"id": "1:m", "kind": "Member", "qname": "x:M", "label": "Europe"}])
    assert out["1:d"]["kind"] == "Dimension" and out["1:m"]["kind"] == "Member"


def test_a_MEMBER_id_in_the_AXIS_slot_drops_the_fact_fail_closed():
    """#822: nothing checked the node KIND, so a member id sitting in the
    dimension array would have written a member's qname into the AXIS position
    — fabricating an axis that does not exist."""
    from driver.core.driver_neo4j_adapter import Neo4jStore

    def fake_read(query, **params):
        if "HAS_XBRL" in query:
            return [{"fid": "f1", "period_type": "duration",
                     "start_date": "2025-06-29", "end_date": "2025-09-28",
                     "dus": ["1:ns:me"], "mus": ["1:ns:me"]}]   # a MEMBER as axis
        return [{"id": "1:ns:me", "kind": "Member", "qname": "ns:me",
                 "label": "Me"}]

    store = Neo4jStore.__new__(Neo4jStore)
    store._read = fake_read
    assert store.get_xbrl_fact_dimensions("acc", "us-gaap:Revenues").rows == ()



def test_a_row_MISSING_its_dimension_arrays_never_raises():
    from driver.core.driver_neo4j_adapter import Neo4jStore

    def fake_read(q, **p):
        if "HAS_XBRL" in q:
            return [{"fid": "f1", "period_type": "duration",
                     "start_date": "2025-06-29", "end_date": "2025-09-28"}]
        return []

    store = Neo4jStore.__new__(Neo4jStore)
    store._read = fake_read
    assert store.get_xbrl_fact_dimensions("acc", "c").rows == ()


@pytest.mark.parametrize("bad", [{"id": "1:d", "kind": "Bogus", "qname": "q",
                                  "label": None},
                                 {"id": "1:d", "kind": "Dimension", "qname": "",
                                  "label": None},
                                 {"id": "1:d", "kind": "Dimension", "qname": 5,
                                  "label": None},
                                 {"id": "1:d", "kind": "Member", "qname": "q",
                                  "label": 5}])
def test_definition_rows_need_a_COMPLETE_shape_not_just_an_id(bad):
    """An id alone was checked; kind, qname and label were trusted."""
    from driver.core.driver_neo4j_adapter import _resolve_id_records
    assert _resolve_id_records([bad]) == {}


def test_the_id_resolver_is_PRIVATE():
    from driver.core import driver_neo4j_adapter as ad
    assert not [n for n in ad.__all__ if "resolve" in n]
    assert hasattr(ad, "_resolve_id_records")


@pytest.mark.parametrize("bad", [5, None, 3.5, True, {"dus", "mus"}])
def test_a_NON_DICT_graph_row_never_raises_a_raw_error(bad):
    """`"dus" not in r` raises TypeError when the row is an int or None."""
    from driver.core.driver_neo4j_adapter import Neo4jStore

    def fake_read(q, **p):
        return [bad] if "HAS_XBRL" in q else []

    store = Neo4jStore.__new__(Neo4jStore)
    store._read = fake_read
    assert store.get_xbrl_fact_dimensions("acc", "c").rows == ()


@pytest.mark.parametrize("label", [None, "", "   ", 5])
def test_a_MEMBER_without_a_usable_label_is_dropped_at_the_source(label):
    """`check_member_refs` RECOMPUTES the slice token from the label, so a
    Member without one verifies nothing. Census: 0 of 1,499,049 Members have a
    null label, so dropping it at the source costs no recall."""
    from driver.core.driver_neo4j_adapter import _resolve_id_records
    assert _resolve_id_records([{"id": "1:m", "kind": "Member", "qname": "x:M",
                                 "label": label}]) == {}


def test_a_DIMENSION_may_lawfully_have_a_null_label():
    """POSITIVE CONTROL — the definition query returns `null AS label` for a
    Dimension, so the label rule is kind-specific, never blanket."""
    from driver.core.driver_neo4j_adapter import _resolve_id_records
    out = _resolve_id_records([{"id": "1:d", "kind": "Dimension",
                                "qname": "us-gaap:Ax", "label": None}])
    assert out["1:d"]["qname"] == "us-gaap:Ax"


@pytest.mark.parametrize("label", ["Foo", "", "   ", 5])
def test_a_DIMENSION_with_a_NON_NULL_label_is_unlawful(label):
    """The definition query returns `null AS label` for a Dimension, so any
    other value is a shape our own query cannot produce — an unseen shape."""
    from driver.core.driver_neo4j_adapter import _resolve_id_records
    assert _resolve_id_records([{"id": "1:d", "kind": "Dimension",
                                 "qname": "us-gaap:Ax", "label": label}]) == {}


def test_a_MEMBER_without_a_label_is_dropped_through_the_PUBLIC_path():
    """The protection was only proved on the private helper. This drives the
    PUBLIC reader: a fact whose member cannot be resolved must not come back."""
    from driver.core.driver_neo4j_adapter import Neo4jStore

    def fake_read(q, **p):
        if "HAS_XBRL" in q:
            return [{"fid": "f1", "period_type": "duration",
                     "start_date": "2025-06-29", "end_date": "2025-09-28",
                     "dus": ["1:ns:ax"], "mus": ["1:ns:me"]}]
        return [{"id": "1:ns:ax", "kind": "Dimension", "qname": "ns:ax",
                 "label": None},
                {"id": "1:ns:me", "kind": "Member", "qname": "ns:me",
                 "label": None}]                       # <- unusable Member

    store = Neo4jStore.__new__(Neo4jStore)
    store._read = fake_read
    assert store.get_xbrl_fact_dimensions("acc", "us-gaap:Revenues").rows == ()


def test_the_SAME_fact_with_a_usable_member_label_DOES_come_back():
    """POSITIVE CONTROL for the public path — otherwise the test above could
    pass because the fixture never worked."""
    from driver.core.driver_neo4j_adapter import Neo4jStore

    def fake_read(q, **p):
        if "HAS_XBRL" in q:
            return [{"fid": "f1", "period_type": "duration",
                     "start_date": "2025-06-29", "end_date": "2025-09-28",
                     "dus": ["1:ns:ax"], "mus": ["1:ns:me"]}]
        return [{"id": "1:ns:ax", "kind": "Dimension", "qname": "ns:ax",
                 "label": None},
                {"id": "1:ns:me", "kind": "Member", "qname": "ns:me",
                 "label": "Europe"}]

    store = Neo4jStore.__new__(Neo4jStore)
    store._read = fake_read
    rows = store.get_xbrl_fact_dimensions("acc", "us-gaap:Revenues").rows
    # the dims are frozen mappings now; compare their CONTENT, which is what
    # this test is about — the label survives the public path
    assert [[dict(d) for d in r["dims"]] for r in rows] == [
        [{"axis": "ns:ax", "member": "ns:me", "label": "Europe"}]]
