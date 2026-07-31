"""THE real end-to-end proof: the 726 Fiscal fact, its cached filing, and its
live Neo4j row — no synthetic anything.

The reviewer's instruction was explicit: use the real packet already at
`data/driver_catalog_seed/wp3_ce_compliant/packets.jsonl`, its cached filing,
and the live graph row; their hashes match and the lawful path passes. Every
earlier "end-to-end" claim in this arc rested on hand-written fixtures, and a
fixture can only ever prove that the code agrees with the fixture's author.

The graph read is READ-ONLY and is SKIPPED when Neo4j is unreachable, so the
rest of the suite never depends on a live database; the packet-and-filing half
always runs.
"""
import json
import os

from driver.core.test_round10_event_boundary import parts_for

import pytest

from driver.core.xbrl_attach import attach_event_xbrl

from driver.relocation.inline_html import bind_graph_fact, parse_raw, prepare
from driver.core.test_round10_event_boundary import filing_evidence


def _rows_of(store, source_id, concept):
    """The verified rows only — the exclusions have their own
    consumers and are never silently dropped here."""
    return store.get_xbrl_fact_dimensions(source_id, concept).rows

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PACKET = os.path.join(_ROOT, "data", "driver_catalog_seed",
                      "wp3_ce_compliant", "packets.jsonl")
FILING = os.path.join(_ROOT, "scripts", "driver_seed", "relocate_probe",
                      "inline_html_cache", "0001306830-24-000155.htm")
ACCESSION = "0001306830-24-000155"
CONCEPT_726 = "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"


def store_or_skip(source_id):
    """THE test-side store gate, backed by CORE'S OWN retry policy.

    It catches only what production calls retryable — `RETRYABLE_SOURCE_ERRORS`
    plus the `SourceUnavailable` a store raises after mapping its own
    transients, which is the contract every adapter must honour. A second list
    of "connection-ish" errors living in the tests would be a second retry
    policy: it drifted from production immediately, carrying auth/config errors
    production does not treat as retryable while omitting raw-driver transients.

    Everything else — a programming error, a schema change, a bad query — MUST
    fail loudly. A green skip on a broken reader is the worst result a suite can
    produce, because it reports success for a test that never ran.
    """
    if not os.environ.get("NEO4J_URI"):
        pytest.skip("NEO4J_URI is not set")
    from driver.core.driver_neo4j_adapter import Neo4jStore
    from driver.core.prepared_fact_v2 import SourceUnavailable
    from driver.core.xbrl_attach import RETRYABLE_SOURCE_ERRORS
    try:
        store = Neo4jStore()
        store.get_source_company_cik(source_id)
        return store
    except RETRYABLE_SOURCE_ERRORS + (SourceUnavailable,):
        pytest.skip("the graph is unavailable")


CE_CIK = "1306830"


def _packet_item():
    with open(PACKET, encoding="utf-8") as f:
        packet = json.loads(f.readline())
    return packet, packet["items"][0]


def _filing_text():
    with open(FILING, encoding="utf-8", errors="replace") as f:
        return f.read()


def test_the_packet_and_the_cached_filing_are_the_same_document():
    """The packet's `representation_sha256` must be the prepared filing's own
    text hash — this is what binds evidence to a specific document."""
    packet, item = _packet_item()
    assert packet["source_id"] == ACCESSION
    prepared = prepare(_filing_text())
    assert prepared["text_sha"] == \
        item["xbrl"]["source_evidence"]["representation_sha256"]


@pytest.mark.parametrize("field,expected", [
    ("value", "726"), ("period_start", "2023-01-01"), ("period_end", "2023-06-30"),
])
def test_the_packet_says_what_we_think_it_says(field, expected):
    _packet, item = _packet_item()
    got = item[field] if field in item else item["xbrl"][field]
    assert got == expected


def _live_row():
    """THE one 726 row for this fact, through the PRODUCTION adapter.

    Connectivity is already owned by `store_or_skip`. Once that has returned a
    store, ZERO or MULTIPLE matching rows are a data or reader regression — not
    an outage — so they FAIL. This used to return None on an empty result and
    four callers turned that into `skip("Neo4j unreachable")`, so a reader
    returning nothing reported GREEN: the masked-probe class, again.
    """
    store = store_or_skip(ACCESSION)
    try:
        rows = store.get_xbrl_fact_dimensions(ACCESSION, CONCEPT_726).rows
    finally:
        store.close()
    hits = [r for r in rows if str(r["value"]).startswith("726")]
    assert len(hits) == 1, (
        f"expected exactly ONE 726 row for {CONCEPT_726} in {ACCESSION}, "
        f"got {len(hits)} of {len(rows)} rows — a data or reader regression, "
        f"never an outage")
    return hits[0]


@pytest.mark.live
def test_the_REAL_726_fact_binds_to_its_live_row_and_its_filing():
    """The whole lawful path, on real data: live graph row -> cached filing ->
    exact element -> exact reconciliation."""
    row = _live_row()
    _packet, item = _packet_item()
    dims = tuple((d["axis"], d["member"]) for d in item["xbrl"]["dimensions"])

    bound, why = bind_graph_fact(
        _filing_text(), inline_element_id=row["fact_id"],
        concept="us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
        context_id=row["context_id"], unit_ref=row["unit_ref"],
        unit_name=row["unit_name"], is_divide=row["is_divide"],
        period_type=row["period_type"], start_date=row["start_date"],
        end_date=row["end_date"], dims=dims, entity_cik=CE_CIK,
        raw_value=row["value"])
    assert bound is not None, f"the lawful path abstained: {why}"

    # the graph stores commas; the value is exact
    assert "," in row["value"]
    assert bound["value"] == parse_raw(row["value"])
    # the filing PRINTS 726 and DECLARES scale 6 — the three-field description
    # the binder REPORTS; Core decides the stored multiplier
    assert bound["printed_value"] == parse_raw(item["value"])
    assert bound["ix_scale"] == item["xbrl"]["ix"]["scale"]
    # and the evidence is this document's
    assert bound["representation_sha256"] == \
        item["xbrl"]["source_evidence"]["representation_sha256"]


def _real_store_and_provider():
    """A PRODUCTION-CAPABLE pair, Option C shaped: Core's real graph store, and
    a filing provider standing in for Fiscal's certified loader (same in-repo
    cache the certified `scripts/driver_seed/route_a_source.py` reads)."""
    store = store_or_skip(ACCESSION)

    class _Provider:
        def get_filing_document(self, source_id):
            return _filing_text() if source_id == ACCESSION else None

    return store, _Provider()


@pytest.mark.live
@pytest.mark.parametrize("concept,level_unit,name,per_x,kind", [
    ("us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax", "m_usd",
     "revenue", None, "USD"),
    ("us-gaap:CommonStockSharesIssued", "count",
     "shares_outstanding", None, "shares"),
    # a per-share fact: the denominator lives in the NAME and the value keeps
    # the base unit (NAME-13); `eps` is the familiar exception in live law.
    ("us-gaap:EarningsPerShareBasic", "usd", "eps", "share", "EPS (USD/share)"),
])
def test_real_USD_shares_and_EPS_through_the_COMPLETE_core_path(
        concept, level_unit, name, per_x, kind):
    """The reviewer's instruction: the real proof must run Core's WHOLE
    `attach_event_xbrl` — injected provider, graph-owned CIK, harvested hash —
    on real USD, share and per-share facts. Every share and EPS fact used to
    abstain here, because the graph writes `shares` where the filing writes
    `xbrli:shares`."""
    from datetime import date, timedelta
    from driver.core.prepared_fact_v2 import ITEM_FIELDS

    store, provider = _real_store_and_provider()
    if store is None:
        pytest.skip("Neo4j unreachable — the live half of this proof is skipped")
    try:
        rows = store.get_xbrl_fact_dimensions(ACCESSION, concept).rows
        assert rows, f"no live row for {concept}"
        text = _filing_text()
        # THE HARVESTED hash, taken from the real packet — NOT recomputed from
        # the document we just fetched, which would have made the test itself
        # circular and would pass even if the packet disagreed. One filing =
        # one representation, so the same packet hash covers every fact in it.
        _packet, item = _packet_item()
        expected_sha = item["xbrl"]["source_evidence"]["representation_sha256"]

        attached = None
        for row in rows:
            dims = tuple((d["axis"], d["member"]) for d in row["dims"])
            bound, _why = bind_graph_fact(
                text, inline_element_id=row["fact_id"], concept=concept,
                context_id=row["context_id"], unit_ref=row["unit_ref"],
                unit_name=row["unit_name"], is_divide=row["is_divide"],
                period_type=row["period_type"], start_date=row["start_date"],
                end_date=row["end_date"], dims=dims, entity_cik=CE_CIK,
                raw_value=row["value"])
            if bound is None or dims:            # keep it dimensionless + simple
                continue
            # REAL-DATA TRAP: an INSTANT stores its (exclusive) date in
            # start_date and the literal string 'null' in end_date. Both the
            # binder and match_xbrl_fact already read start_date for instants;
            # only this test reached for end_date.
            stored_end = (row["start_date"] if row["period_type"] == "instant"
                          else row["end_date"])
            incl_end = (date.fromisoformat(stored_end)
                        - timedelta(days=1)).isoformat()
            from driver.core.xbrl_attach import expected_multiplier
            slot = {"value": bound["printed_value"],
                    "scale_multiplier": expected_multiplier(level_unit,
                                                            bound["ix_scale"]),
                    "unit_scale_evidence": None}
            # Lawful evidence for the element ACTUALLY BOUND. The pinned
            # packet hash above stays as the independent cross-check it already
            # was (packet hash == fetched document hash); this supplies the
            # coordinates for THIS row's element, which the packet — a single
            # CE revenue fact — cannot do for the shares and EPS cases.
            evidence, filing_quote = filing_evidence(text, row["fact_id"])
            assert evidence["representation_sha256"] == expected_sha
            fact_item = {k: None for k in ITEM_FIELDS}
            fact_item.update(driver_name=name, driver_state="reported",
                        quote=filing_quote, measurement_raw_spans=[],
                        slice_parts=[],
                        level_unit=level_unit, level_low=dict(slot),
                        level_high=dict(slot), time_type=row["period_type"],
                        period_end_date=incl_end,
                        period_start_date=(row["start_date"]
                                           if row["period_type"] == "duration"
                                           else None))
            # through the EVENT door, so the one-document-per-event rule runs
            attached = attach_event_xbrl(
                [{"fact": {"fact_type": "metric", "part_ref": "p1",
                           "occurrence_in_part": None, "per_x": per_x,
                           "item": fact_item},
                  "concept": concept, "member_refs": [],
                  "source_evidence": evidence}],
                source_id=ACCESSION, store=store, filing_provider=provider, text_parts=parts_for([{"fact": {"fact_type": "metric", "part_ref": "p1",
                           "occurrence_in_part": None, "per_x": per_x,
                           "item": fact_item},
                  "concept": concept, "member_refs": [],
                  "source_evidence": evidence}])).facts[0][1]
            break
        assert attached is not None, f"{kind}: no dimensionless fact bound"
        assert attached.item.xbrl_concept_raw == concept
    finally:
        store.close()


@pytest.mark.live
def test_the_REAL_fact_refuses_a_wrong_description_of_itself():
    """Same real fact, one field wrong: a per-share unit claim on a plain-USD
    fact, and a wrong context — both must abstain."""
    row = _live_row()
    _packet, item = _packet_item()
    dims = tuple((d["axis"], d["member"]) for d in item["xbrl"]["dimensions"])
    base = dict(
        inline_element_id=row["fact_id"],
        concept="us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
        context_id=row["context_id"], unit_ref=row["unit_ref"],
        unit_name=row["unit_name"], is_divide=row["is_divide"],
        period_type=row["period_type"], start_date=row["start_date"],
        end_date=row["end_date"], dims=dims, entity_cik=CE_CIK,
        raw_value=row["value"])
    for field, value in (("is_divide", "1"),
                         ("unit_name", "iso4217:USDshares"),
                         ("context_id", "c-1"),
                         ("entity_cik", "320193"),
                         ("raw_value", "999,000,000")):
        assert bind_graph_fact(_filing_text(), **dict(base, **{field: value}))[0] \
            is None, f"{field}={value} was accepted against the real filing"


@pytest.mark.live
def test_the_SAVED_PACKET_evidence_attaches_through_the_PUBLIC_DOOR_unchanged():
    """THE historical positive control, and deliberately NON-CIRCULAR.

    Every other real-data test here builds its evidence with `filing_evidence`,
    which calls the same production owner Core then compares against — fine as
    lawful INPUT for a test about some other rule, but useless as proof that the
    saved coordinates themselves still verify. This test submits the CE packet's
    LITERAL four-key `source_evidence`, exactly as it was written to disk on
    2026-07-23, through the public door with nothing recomputed.

    Its PREMISES are asserted first, against the fetched filing: the packet's
    hash must reproduce, its quote span must slice real text, its label span
    must lie inside that quote, and every piece must be the text at its own
    span. If any of those drift, this fails here rather than proving nothing.

    The event part is EXPLICIT SCAFFOLDING — derived from the packet's own
    quote, because the historical model view was never archived. It proves the
    occurrence plumbing runs, and nothing about what the reader actually saw.
    """
    from datetime import date, timedelta
    from decimal import Decimal

    from driver.core.prepared_fact_v2 import ITEM_FIELDS
    from driver.core.test_round10_event_boundary import parts_for
    from driver.core.xbrl_attach import attach_event_xbrl, expected_multiplier
    from driver.relocation.inline_html import prepare

    row = _live_row()
    store, provider = _real_store_and_provider()
    if store is None:
        pytest.skip("Neo4j unavailable")
    try:
        _packet, item = _packet_item()
        saved = item["xbrl"]["source_evidence"]            # the LITERAL four keys
        assert sorted(saved) == ["pieces", "quote_span",
                                 "raw_label_span", "representation_sha256"]

        text = prepare(_filing_text())["text"]
        assert saved["representation_sha256"] == prepare(_filing_text())["text_sha"]
        q0, q1 = saved["quote_span"]
        packet_quote = text[q0:q1]
        assert packet_quote.strip(), "the saved quote span slices blank text"
        if saved["raw_label_span"] is not None:
            l0, l1 = saved["raw_label_span"]
            assert q0 <= l0 and l1 <= q1, "the saved label is outside its quote"
            assert text[l0:l1].strip()
        for piece in saved["pieces"]:
            a, b = piece["span"]
            assert text[a:b] == piece["text"], piece

        stored_end = (row["start_date"] if row["period_type"] == "instant"
                      else row["end_date"])
        incl_end = (date.fromisoformat(stored_end) - timedelta(days=1)).isoformat()
        bound_scale = int(item["xbrl"]["ix"]["scale"])
        slot = {"value": Decimal(str(item["value"])),
                "scale_multiplier": expected_multiplier("m_usd", bound_scale),
                "unit_scale_evidence": None}
        fact_item = {k: None for k in ITEM_FIELDS}
        fact_item.update(driver_name="revenue", driver_state="reported",
                         quote=packet_quote, measurement_raw_spans=[],
                         slice_parts=[], level_unit="m_usd",
                         level_low=dict(slot), level_high=dict(slot),
                         time_type=row["period_type"], period_end_date=incl_end,
                         period_start_date=(row["start_date"]
                                            if row["period_type"] == "duration"
                                            else None))
        # THE FACT'S OWN DIMENSIONS, from the packet. Without them the claim is
        # dimensionless and the door lawfully binds a DIFFERENT row — the
        # evidence then rightly refuses, which is the gate working, not a
        # defect. The 726 fact is the North America / Acetyl Chain cell.
        # The slice token is RECOMPUTED from the filing's own member label by
        # the production owner — a supplied part is never trusted, so the test
        # must not invent one either.
        from driver.core.slice_menu import classify_axis, member_token
        graph_dims = {(d["axis"], d["member"]): d["label"]
                      for r in _rows_of(store, ACCESSION,
                                                              row_concept())
                      for d in r["dims"]}
        member_refs = []
        for d in item["xbrl"]["dimensions"]:
            label = graph_dims.get((d["axis"], d["member"]))
            assert label, f"the graph has no label for {d}"
            status, kind = classify_axis(d["axis"])
            assert status == "slice", (d, status)
            member_refs.append({"axis": d["axis"], "member": d["member"],
                                "slice_part": member_token(kind, label)})
        fact_item["slice_parts"] = [r["slice_part"] for r in member_refs]
        entry = {"fact": {"fact_type": "metric", "part_ref": "p1",
                          "occurrence_in_part": None, "per_x": None,
                          "item": fact_item},
                 "concept": row_concept(), "member_refs": member_refs,
                 "source_evidence": saved}          # UNCHANGED, not rebuilt
        res = attach_event_xbrl([entry], source_id=ACCESSION, store=store,
                                filing_provider=provider,
                                text_parts=parts_for([entry]))
        # The result record (#825): unwrap the (original_index, fact) pair, and
        # pin that NOTHING was parked — on the historical positive control that
        # distinction is the whole point, because a park here would mean the
        # saved coordinates no longer verify.
        assert res.preflight_outcomes == (), \
            [dict(o) for o in res.preflight_outcomes]
        assert [i for i, _f in res.facts] == [0]
        assert res.source_id == ACCESSION
        assert res.facts[0][1].item.quote == packet_quote
    finally:
        store.close()


def row_concept():
    return "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"


# ---- the blanket-catch defect, saved so it cannot come back ----------------

def _patched_store(monkeypatch, failure):
    """Point the one gate at a store whose reader raises `failure`."""
    from driver.core import driver_neo4j_adapter as adapter
    monkeypatch.setenv("NEO4J_URI", "bolt://unused")
    monkeypatch.setattr(adapter.Neo4jStore, "__init__",
                        lambda self, *a, **k: None)

    def _raise(self, source_id):
        raise failure
    monkeypatch.setattr(adapter.Neo4jStore, "get_source_company_cik", _raise)


def test_a_PROGRAMMING_error_in_the_graph_reader_FAILS_LOUDLY(monkeypatch):
    """THE saved regression for the defect repaired in #824.

    The gate caught bare `Exception` and turned everything into
    `skip("Neo4j unavailable")`, so a typo, a bad query or a schema change came
    back as a GREEN SKIP while the test never ran. Without this test that
    defect can return during any restructuring and nothing fails.
    """
    _patched_store(monkeypatch, RuntimeError("programming bug"))
    try:
        store_or_skip(ACCESSION)
    except RuntimeError as exc:
        assert "programming bug" in str(exc)
    except pytest.skip.Exception:
        # NOT `pytest.raises`: if the blanket catch comes back, the injected
        # error becomes a skip, and a skipped test reports GREEN — the exact
        # failure mode this regression exists to prevent. It must FAIL.
        pytest.fail("a programming error was swallowed into a SKIP — the "
                    "blanket-catch defect has returned")
    else:
        pytest.fail("the injected programming error never surfaced")


def test_a_REAL_outage_still_skips(monkeypatch):
    """The negative control, so the fix above cannot be 'catch nothing'. A
    genuine transport failure is retryable under Core's OWN policy
    (`ConnectionError` is an `OSError`) and must still skip."""
    _patched_store(monkeypatch, ConnectionError("down"))
    with pytest.raises(pytest.skip.Exception):
        store_or_skip(ACCESSION)


def test_a_store_mapped_outage_also_skips(monkeypatch):
    """The other half of the production contract: an adapter maps its own
    transients to `SourceUnavailable` before they cross the boundary."""
    from driver.core.prepared_fact_v2 import SourceUnavailable
    _patched_store(monkeypatch, SourceUnavailable("neo4j down"))
    with pytest.raises(pytest.skip.Exception):
        store_or_skip(ACCESSION)


def test_the_gate_uses_CORES_retry_policy_not_a_second_list():
    """DERIVED: the tests must not carry their own retry policy. The one gate
    reads `RETRYABLE_SOURCE_ERRORS`; a private list here drifted from
    production the moment it was written."""
    import ast
    import inspect
    import textwrap
    # THE HANDLER ITSELF, not the prose around it. Searching the source text
    # found the name in the DOCSTRING, so swapping the real `except` target for
    # a private list would have kept this ownership test green — a masked pass
    # guarding against a masked pass.
    tree = ast.parse(textwrap.dedent(inspect.getsource(store_or_skip)))
    handlers = [n for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler)]
    assert len(handlers) == 1, f"expected one handler, got {len(handlers)}"
    caught = handlers[0].type
    assert caught is not None, "a bare `except` is exactly the defect repaired"
    names = {n.id for n in ast.walk(caught) if isinstance(n, ast.Name)}
    assert names == {"RETRYABLE_SOURCE_ERRORS", "SourceUnavailable"}, names


def _rows_returning(monkeypatch, rows):
    """Point the production adapter's row reader at a fixed result."""
    from driver.core import driver_neo4j_adapter as adapter
    monkeypatch.setenv("NEO4J_URI", "bolt://unused")
    monkeypatch.setattr(adapter.Neo4jStore, "__init__", lambda self, *a, **k: None)
    monkeypatch.setattr(adapter.Neo4jStore, "get_source_company_cik",
                        lambda self, s: "1306830")
    from driver.core.driver_neo4j_adapter import GraphFactRows
    monkeypatch.setattr(adapter.Neo4jStore, "get_xbrl_fact_dimensions",
                        lambda self, s, c: GraphFactRows(rows=rows,
                                                         exclusions=()))
    monkeypatch.setattr(adapter.Neo4jStore, "close", lambda self: None)


def test_an_EMPTY_graph_result_FAILS_it_is_not_an_outage(monkeypatch):
    """Reproduced as a green skip before this repair: the reader returned
    nothing, `_live_row` returned None, and the callers read that as
    'Neo4j unreachable'. Connectivity is `store_or_skip`'s job; an empty result
    from a reachable graph is a data or reader regression."""
    _rows_returning(monkeypatch, [])
    try:
        _live_row()
    except AssertionError as exc:
        assert "exactly ONE 726 row" in str(exc)
    except pytest.skip.Exception:
        pytest.fail("an empty result was reported as an outage — the "
                    "masked-skip defect has returned")
    else:
        pytest.fail("an empty result was accepted")


def test_an_AMBIGUOUS_graph_result_FAILS_rather_than_picking_one(monkeypatch):
    """Two matching rows is not 'pick the first' — that is how a wrong row gets
    silently credited."""
    row = {"value": "726000000", "fact_id": "f-1360", "context_id": "c",
           "unit_ref": "u", "unit_name": "iso4217:USD", "is_divide": "0",
           "period_type": "duration", "start_date": "2024-01-01",
           "end_date": "2024-07-01", "dims": []}
    _rows_returning(monkeypatch, [row, dict(row, fact_id="f-other")])
    with pytest.raises(AssertionError, match="exactly ONE 726 row"):
        _live_row()
