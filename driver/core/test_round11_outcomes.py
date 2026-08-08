"""ROUND-11 — the four reviewer gaps + three I found auditing my own work.

REVIEWER:
  1  the live store never maps its transient errors, and Neo4j's outage classes
     are NOT OSError, so a real outage failed loudly as a programming error
  2  there are FOUR outcomes, not three — the checklist omitted the ordinary
     park (`ProductionValidationError`), which the graph guard itself raises
  3  "all input validation before I/O" was FALSE: only the envelope was checked
     (list-ness, four keys, hash agreement); a malformed fact, blank concept,
     bad member_refs, mis-shaped hash or blank source_id all reached the graph
  4  a stale "ONE source event = ONE document" statement remained

MINE (found auditing, not raised by anyone):
  5  THREE absent-conditions were classified as CONTRACT REJECTIONS although
     written law calls each one PARK-RETRY — a rejection tells the channel to
     fix what it cannot fix, and the item never drains
  6  `xml_integer` violates its own contract on a long digit string: Python's
     4300-digit conversion limit raises ValueError instead of returning None
  7  a FIFTH escaping type — `SlotConversionError` out of `to_stored_fact`
"""
from decimal import Decimal

import pytest

from driver.core.test_round10_event_boundary import parts_for

from driver.core import prepared_fact_v2 as p2
from driver.core import xbrl_attach as xa
from driver.core.prepared_fact_v2 import (OUTCOME_CLASSES, ProductionValidationError,
                                          SchemaError, SourceUnavailable)
from driver.relocation.inline_html import xml_integer

_DOC = "<html xmlns:xbrli='http://www.xbrl.org/2003/instance' xmlns:xbrldi='http://xbrl.org/2006/xbrldi' xmlns:ix='http://www.xbrl.org/2013/inlineXBRL' xmlns:iso4217='http://www.xbrl.org/2003/iso4217' xmlns:utr='http://example.org/utr' xmlns:us-gaap='http://example.org/us-gaap' xmlns:dei='http://example.org/dei' xmlns:srt='http://example.org/srt' xmlns:a='http://example.org/a' xmlns:x='http://example.org/x' xmlns:aapl='http://example.org/aapl' xmlns:slg='http://example.org/slg' xmlns:accd='http://example.org/accd' xmlns:ed='http://example.org/ed' xmlns:dvn='http://example.org/dvn' xmlns:fcx='http://example.org/fcx' xmlns:nog='http://example.org/nog' xmlns:inst='http://example.org/inst' xmlns:dimns='http://example.org/dimns' xmlns:nope='http://example.org/nope' xmlns:geo='http://example.org/geo' xmlns:eqt='http://example.org/eqt' xmlns:geography='http://example.org/geography' xmlns:seg='http://example.org/seg' xmlns:country='http://example.org/country'><body></body></html>"
from driver.relocation.inline_html import prepare          # noqa: E402
from driver.core.test_round10_event_boundary import (_ns_dim, ev_of,
                                                     filing_evidence)
from driver.core.driver_neo4j_adapter import GraphFactRows
SHA = prepare(_DOC)["text_sha"]


class NeverAsked:
    """Any graph call means validation did NOT happen first."""
    def get_xbrl_representation_count(self, source_id):
        raise AssertionError("the graph was queried before input was validated")

    def get_xbrl_fact_dimensions(self, source_id, concept):
        raise AssertionError("the graph was queried before input was validated")

    def get_source_company_cik(self, source_id):
        raise AssertionError("the graph was queried before input was validated")


class Provider:
    def get_filing_document(self, source_id):
        raise AssertionError("the provider was called before input was validated")


def _item(**over):
    d = {"fact": {"fact_type": "metric", "part_ref": "p", "occurrence_in_part": None,
                  "per_x": None, "item": {}},
         "concept": "us-gaap:Revenues", "member_refs": [],
         "source_evidence": ev_of(SHA)}
    d.update(over)
    return d


def _attached(res, count=1):
    """A SUCCESS: `count` facts at their ORIGINAL indexes, and NO outcome row."""
    assert res.preflight_outcomes == (), [dict(o) for o in res.preflight_outcomes]
    assert [i for i, _f in res.facts] == list(range(count))
    return [f for _i, f in res.facts]


def _refused(res, exc_class, needle):
    """An ITEM-LOCAL refusal: exactly one indexed row, decision and code derived
    from the exception class the ORIGINAL test named (that mapping is pinned
    independently below and in the round-15 matrix), and a MANDATORY
    rule-specific reason."""
    want_decision, want_code = xa._default_outcome(exc_class("probe"))
    assert res.facts == (), "a refused item must attach nothing"
    assert len(res.preflight_outcomes) == 1, \
        [dict(o) for o in res.preflight_outcomes]
    row = res.preflight_outcomes[0]
    assert (row["index"], row["decision"], row["codes"]) == \
        (0, want_decision, (want_code,))
    assert needle in row["detail"], row["detail"]
    return row


# --- 3. EVERY pure check runs before ANY I/O -------------------------------

_ITEM_32 = "the item (the 32 model-owned fields, null where absent)"
_SHA_RULE = "representation_sha256: expected a 64-character lowercase"


@pytest.mark.parametrize("bad,why,rule", [
    ({"fact": "not-a-dict"}, "fact is not an object",
     "fact must be an object, got str"),
    ({"fact": {"fact_type": "metric"}}, "fact is missing keys",
     "the fact-level keys must carry exactly"),
    ({"concept": ""}, "blank concept", "each item needs a concept"),
    ({"concept": None}, "null concept", "each item needs a concept"),
    ({"member_refs": {}}, "member_refs is a dict", _ITEM_32),
    ({"member_refs": None}, "member_refs is null", _ITEM_32),
    ({"member_refs": [{"axis": "a"}]}, "member_ref missing keys", _ITEM_32),
    ({"source_evidence": ev_of("not-a-sha")}, "hash is not a sha256", _SHA_RULE),
    ({"source_evidence": ev_of("A" * 64)}, "hash is not lowercase hex", _SHA_RULE),
])
def test_malformed_item_CONTENT_never_reaches_the_graph(bad, why, rule):
    item = _item(**bad)
    # The stores raise if touched, so "never reaches the graph" is still proved
    # by construction; `rule` pins WHICH check refused, because a bare
    # SchemaError check passed for any of the nine.
    _refused(xa.attach_event_xbrl([item], source_id="x", store=NeverAsked(),
                                  filing_provider=Provider(),
                                  text_parts=parts_for([item])),
             SchemaError, rule)


def test_a_blank_source_id_never_reaches_the_graph():
    for bad in ("", "   ", None, 5):
        with pytest.raises(SchemaError):
            xa.attach_event_xbrl([_item()], source_id=bad, store=NeverAsked(),
                                 filing_provider=Provider(), text_parts=parts_for([_item()])).facts


def test_a_wellformed_event_DOES_reach_the_graph():
    """The guard above must not be passing for the wrong reason."""
    asked = []

    class Counting(NeverAsked):
        def get_xbrl_representation_count(self, source_id):
            asked.append(source_id)
            return 2                      # -> ordinary park, stops right there

    item = _item(fact=_valid_fact())
    _refused(xa.attach_event_xbrl([item], source_id="x", store=Counting(),
                                  filing_provider=Provider(),
                                  text_parts=parts_for([item])),
             ProductionValidationError, "reports 2 XBRL representation(s)")
    assert asked == ["x"]


# --- 2 + 7. the outcome map is EXHAUSTIVE ----------------------------------

def test_every_exception_RAISED_IN_THIS_MODULE_is_declared():
    """WHAT THIS PROVES, EXACTLY: every class named in a literal `raise` written
    in this module appears in the outcome map — which is worth keeping, because
    adding a new one by hand is how the fifth stayed hidden.

    WHAT IT CANNOT PROVE, and used to claim ("this test proves nothing escapes
    it"): a syntax scan cannot see an exception raised inside a function this
    module CALLS, nor follow control flow. Five did exactly that — KeyError and
    TypeError out of row access — while this test was green.

    THE REAL PROPERTY IS PROVED PER SCENARIO, by the malformed-row matrix below
    and its siblings: each injected fault is asserted to produce exactly one
    indexed outcome row with its own decision, code and rule-specific reason. A
    single broad pass over the same seventeen scenarios used to sit at the end of
    this file; it re-ran them to assert only that *something* declared came back,
    which is strictly weaker than what each case now proves individually."""
    import ast
    import inspect
    declared = {c.__name__ for c in OUTCOME_CLASSES}
    raised = set()
    from driver.core import xbrl_attach as _xa
    both = inspect.getsource(p2) + "\n" + inspect.getsource(_xa)
    for node in ast.walk(ast.parse(both)):
        if isinstance(node, ast.Raise) and node.exc is not None:
            f = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
            name = getattr(f, "id", None)
            if name and name[0].isupper():
                raised.add(name)
    caught = {h.type.id for h in ast.walk(ast.parse(both))
              if isinstance(h, ast.ExceptHandler)
              and isinstance(h.type, ast.Name)}
    escaping = raised - caught
    # A deliberate PROGRAMMING-ERROR raise is not an outcome and must never be
    # declared as one — its whole job is to stay loud. Those are Python's own
    # built-ins, while every declared outcome is a project class, so the
    # allowance is DERIVED from that structural fact rather than hand-listed
    # (a hand-kept exception list is what this test exists to prevent).
    import builtins
    programming = {n for n in escaping if hasattr(builtins, n)}
    assert escaping - programming <= declared, \
        f"undeclared escaping outcome(s): {escaping - programming - declared}"


def test_every_outcome_class_maps_to_a_PUBLIC_decision_word():
    """Distinctness was never the law, and asserting it CEMENTED a defect: the
    four classes only looked distinct because `SourceUnavailable` answered
    `parked_retry`, a sixth word the Channel Contract does not define. Three
    classes lawfully share `parked`; what must hold is that every value is one
    of the five public words, and that a rejection and a park are never the
    same type. The retry meaning rides on the exception CLASS and on the
    `SOURCE_UNAVAILABLE` code — not on a private decision."""
    from driver.core.slot_convert import SlotConversionError
    from driver.core.xbrl_attach import PUBLIC_DECISIONS
    decisions = {c: d for c, d in OUTCOME_CLASSES.items()}
    assert decisions[SchemaError] == "rejected"
    assert decisions[ProductionValidationError] == "parked"
    assert decisions[SourceUnavailable] == "parked"
    assert decisions[SlotConversionError] == "parked"
    assert set(decisions.values()) <= set(PUBLIC_DECISIONS)
    # a rejection and a park must never be the same type
    assert not issubclass(SourceUnavailable, SchemaError)
    assert not issubclass(ProductionValidationError, SchemaError)


def test_slot_conversion_failure_is_a_PARK_not_an_escape():
    """`validate_slot` checks structure; `convert_slot` does the arithmetic, so
    an unstorable product escaped `to_stored_fact` untyped."""
    from decimal import Decimal
    from driver.core.prepared_fact_v2 import ITEM_FIELDS, PreparedFactV2
    item = {k: None for k in ITEM_FIELDS}
    item.update(driver_name="revenue", driver_state="reported", quote="q",
                measurement_raw_spans=[], slice_parts=[], level_unit="usd",
                level_low={"value": Decimal("1E+9999"),
                           "scale_multiplier": Decimal(1),
                           "unit_scale_evidence": None},
                level_high=None, time_type="instant",
                period_end_date="2024-06-30")
    f = PreparedFactV2.from_dict({"fact_type": "metric", "part_ref": "p",
                                  "occurrence_in_part": None, "per_x": None,
                                  "item": item})
    with pytest.raises(ProductionValidationError):
        p2.to_stored_fact(f, driver={"name": "revenue", "fact_type": "metric"},
                          source={"date": "2026-04-23T08:30:00-04:00",
                                  "source_type": "8k", "ticker": "AAL",
                                  "source_id": "0000006201-26-000031"},
                          fye_month=12)


# --- 5. absent is a PARK, never "fix and resubmit" -------------------------

class Graph:
    def __init__(self, rows=None, cik="0000320193", n=1):
        self._rows, self._cik, self._n = rows if rows is not None else [], cik, n

    def get_xbrl_representation_count(self, s): return self._n
    def get_xbrl_fact_dimensions(self, s, c): return GraphFactRows(rows=self._rows, exclusions=())
    def get_source_company_cik(self, s): return self._cik


def _valid_fact():
    from decimal import Decimal
    from driver.core.prepared_fact_v2 import ITEM_FIELDS
    item = {k: None for k in ITEM_FIELDS}
    item.update(driver_name="revenue", driver_state="reported", quote="q",
                measurement_raw_spans=[], slice_parts=[], level_unit="m_usd",
                level_low={"value": Decimal("726"),
                           "scale_multiplier": Decimal(10) ** 6,
                           "unit_scale_evidence": None},
                level_high={"value": Decimal("726"),
                            "scale_multiplier": Decimal(10) ** 6,
                            "unit_scale_evidence": None},
                time_type="duration", period_start_date="2024-01-01",
                period_end_date="2024-06-30")
    return {"fact_type": "metric", "part_ref": "p1", "occurrence_in_part": None,
            "per_x": None, "item": item}


def _attach(store, provider):
    # MIGRATED (#821): through the ONE public event door.
    return xa.attach_event_xbrl(
        [{"fact": _valid_fact(), "concept": "us-gaap:Revenues",
          "member_refs": [], "source_evidence": ev_of(SHA)}],
        source_id="x", store=store, filing_provider=provider,
        text_parts=parts_for([{"fact": _valid_fact(),
                               "concept": "us-gaap:Revenues",
                               "member_refs": [],
                               "source_evidence": ev_of(SHA)}]))


def test_a_provider_with_NO_document_yet_is_PARK_RETRY_not_a_rejection():
    """ChannelContract 3: 'must exist in Neo4j; not there yet -> PARK-RETRY'.
    The cache/EDGAR simply not having the filing is not something a channel can
    fix by resubmitting."""
    class NoDoc:
        def get_filing_document(self, s): return None
    _refused(_attach(Graph(), NoDoc()), SourceUnavailable,
             "the filing provider has no document for")


def test_a_graph_with_NO_company_yet_is_an_ordinary_PARK():
    class Doc:
        def get_filing_document(self, s): return _DOC
    # THIS BRANCH OWNS ITS CODE, so the generic class default does not apply and
    # the row is asserted directly: the channel must be able to tell "no single
    # filing company" from every other park.
    res = _attach(Graph(cik=None), Doc())
    assert res.facts == () and len(res.preflight_outcomes) == 1
    row = res.preflight_outcomes[0]
    assert (row["index"], row["decision"], row["codes"]) == \
        (0, "parked", ("SOURCE_COMPANY_AMBIGUOUS",))
    assert "names no single filing company" in row["detail"], row["detail"]


def test_a_graph_with_NO_fact_for_the_concept_yet_is_an_ordinary_PARK():
    """Packet D.2: 'Report not in Neo4j yet (the graph runs ~1 qtr behind
    fiscal.ai) -> PARK-RETRY'; corpus_missing likewise."""
    class Doc:
        def get_filing_document(self, s): return _DOC
    _refused(_attach(Graph(rows=[]), Doc()), ProductionValidationError,
             "carries NO fact for concept")


# --- 1. the live store maps ITS OWN transient errors -----------------------

def _store_that_raises(exc):
    from driver.core.driver_neo4j_adapter import Neo4jStore
    store = object.__new__(Neo4jStore)          # no connection is made
    store._db = "neo4j"

    class Driver:
        def session(self, **kw):
            raise exc
    store._driver = Driver()
    return store


def test_the_live_store_maps_neo4j_outages_to_park_retry():
    """The store maps to `ConnectionError` — an OSError, which is the retryable
    set every consumer already honours — so no shared symbol has to cross the
    staged/production line. End to end through `_fetch` it becomes the
    PARK-RETRY type."""
    from neo4j.exceptions import ServiceUnavailable, SessionExpired, TransientError
    for exc in (ServiceUnavailable("down"), SessionExpired("expired"),
                TransientError("deadlock")):
        store = _store_that_raises(exc)
        with pytest.raises(xa.RETRYABLE_SOURCE_ERRORS):
            store._read("RETURN 1")
        with pytest.raises(SourceUnavailable):          # the outcome that counts
            xa._fetch("the graph", store._read, "RETURN 1")


def test_the_live_store_does_NOT_swallow_a_programming_error():
    from driver.core.driver_neo4j_adapter import Neo4jStore

    class Driver:
        def session(self, **kw):
            return {}["missing"]
    store = object.__new__(Neo4jStore)
    store._db, store._driver = "neo4j", Driver()
    with pytest.raises(KeyError):
        store._read("RETURN 1")


# --- 6. xml_integer keeps its own contract ---------------------------------

@pytest.mark.parametrize("digits", [4300, 4301, 5000, 20000])
def test_xml_integer_CONVERTS_a_lawful_integer_of_any_length(digits):
    """THIS TEST USED TO ASSERT THE DEFECT.

    It pinned `xml_integer(...) is None` for 4,301+ digits and called that the
    contract. It never was: `xs:integer` is unbounded, and the None came from
    CPython's 4,300-character string-conversion gate — OUR runtime's limit,
    turned into a verdict about the filing, reported by its reader as
    `malformed_scale`, the same reason a genuinely broken `6.9` gets.

    The contract is still 'int, or None'; what changed is which values are
    which. Neither the value nor the result is printed, because `f"{n}"` is the
    very conversion under test."""
    for raw in ("9" * digits, "-" + "9" * digits):
        got = xml_integer(raw)
        assert isinstance(got, int), f"a lawful {digits}-digit integer gave None"
        assert got == int(Decimal(raw))


@pytest.mark.parametrize("raw", ["6.9", "1_0", "", " ", "１２", "+ 6", "0x10"])
def test_xml_integer_still_refuses_what_is_NOT_an_xs_integer(raw):
    """MUST-CATCH twin: widening the LENGTH must not widen the GRAMMAR."""
    assert xml_integer(raw) is None


def test_xml_integer_still_accepts_a_long_but_lawful_value():
    assert xml_integer("1" * 100) == int("1" * 100)


# --- 4. no stale one-document wording --------------------------------------


# ---------------------------------------------------------------------------
# #819 — EXECUTABLE FAULT INJECTION: what a caller actually experiences.
# The static scan above cannot see an exception raised inside a called function,
# so these push real faults through the real door and assert the real outcome.
# ---------------------------------------------------------------------------

_FULL_DOC = ('<html xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:xbrldi="http://xbrl.org/2006/xbrldi" xmlns:ix="http://www.xbrl.org/2013/inlineXBRL" xmlns:iso4217="http://www.xbrl.org/2003/iso4217" xmlns:utr="http://example.org/utr" xmlns:us-gaap="http://example.org/us-gaap" xmlns:dei="http://example.org/dei" xmlns:srt="http://example.org/srt" xmlns:a="http://example.org/a" xmlns:x="http://example.org/x" xmlns:aapl="http://example.org/aapl" xmlns:slg="http://example.org/slg" xmlns:accd="http://example.org/accd" xmlns:ed="http://example.org/ed" xmlns:dvn="http://example.org/dvn" xmlns:fcx="http://example.org/fcx" xmlns:nog="http://example.org/nog" xmlns:inst="http://example.org/inst" xmlns:dimns="http://example.org/dimns" xmlns:nope="http://example.org/nope" xmlns:geo="http://example.org/geo" xmlns:eqt="http://example.org/eqt" xmlns:geography="http://example.org/geography" xmlns:seg="http://example.org/seg" xmlns:country="http://example.org/country"><body><ix:header><ix:resources><xbrli:context id="c1"><xbrli:entity>'
             '<xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193</xbrli:identifier></xbrli:entity>'
             '<xbrli:period><xbrli:startDate>2024-01-01</xbrli:startDate>'
             '<xbrli:endDate>2024-06-30</xbrli:endDate></xbrli:period>'
             # TWO `ix:header` ELEMENTS, DELIBERATELY — lawful, and what real
             # filings do (8 of 1,769 in the frozen cache carry more than one).
             # Inline XBRL 1.1 §8.1.3 requires AT LEAST ONE header in the
             # document set; §8.1.1 bounds only what sits INSIDE a header (at
             # most one `ix:hidden`, at most one `ix:resources`) and sets no
             # one-header maximum. I briefly merged these on a mistaken
             # "exactly one" reading, which removed real-world coverage for no
             # reason; that reading is withdrawn.
             '</xbrli:context></ix:resources></ix:header>'
             '<ix:header><ix:resources><xbrli:unit id="u1">'
             '<xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit></ix:resources></ix:header>'
             '<p><ix:nonFraction id="f1" name="us-gaap:X" contextRef="c1" '
             'unitRef="u1" scale="6" decimals="-6">726</ix:nonFraction></p>'
             '</body></html>')


def _row(**over):
    # THE SHAPE THE REAL ADAPTER RETURNS, including the concept's identity.
    # `concept_namespace` and `graph_concept_qname` are BOTH required: the
    # binder compares (namespace URI, local name) rather than a prefixed
    # string, and it takes both halves from the one Concept record the row was
    # read with. A fixture that omitted them would let the row contract and the
    # public door pass while the real adapter path delivered None.
    r = {"period_type": "duration", "start_date": "2024-01-01",
         "end_date": "2024-07-01", "dims": [], "fact_id": "f1",
         "context_id": "c1", "unit_ref": "u1", "unit_name": "iso4217:USD",
         "is_divide": "0", "value": "726,000,000", "decimals": "0",
         "concept_namespace": "http://example.org/us-gaap",
         "graph_concept_qname": "us-gaap:X"}
    r.update(over)
    return r


def _without(key):
    return {k: v for k, v in _row().items() if k != key}


def _xbrl_item():
    from decimal import Decimal

    from driver.core.prepared_fact_v2 import ITEM_FIELDS
    slot = {"value": Decimal("726"), "scale_multiplier": Decimal(10) ** 6,
            "unit_scale_evidence": None}
    # The BASELINE must genuinely attach, so every input here is lawful: the
    # evidence and the quote come from the element the fault-injection rows
    # point at. A baseline that fails at an earlier gate would make every
    # injected fault look like it worked.
    evidence, filing_quote = filing_evidence(_FULL_DOC, "f1")
    it = {k: None for k in ITEM_FIELDS}
    it.update(driver_name="thing", driver_state="reported", quote=filing_quote,
              measurement_raw_spans=[], slice_parts=[], level_unit="usd",
              level_low=dict(slot), level_high=dict(slot), time_type="duration",
              period_start_date="2024-01-01", period_end_date="2024-06-30")
    return {"fact": {"fact_type": "metric", "part_ref": "p1",
                     "occurrence_in_part": None, "per_x": None, "item": it},
            "concept": "us-gaap:X", "member_refs": [],
            "source_evidence": evidence}


def _attach_rows(rows):
    class Graph:
        def get_xbrl_representation_count(self, s):
            return 1

        def get_xbrl_fact_dimensions(self, s, c):
            return GraphFactRows(rows=rows, exclusions=())

        def get_source_company_cik(self, s):
            return "0000320193"

    class Doc:
        def get_filing_document(self, s):
            return _FULL_DOC

    item = _xbrl_item()
    return xa.attach_event_xbrl([item], source_id="x", store=Graph(),
                                filing_provider=Doc(),
                                text_parts=parts_for([item]))


def test_the_fault_injection_BASELINE_actually_attaches():
    """Assert the premise FIRST: without a working baseline every fault below
    could be parking at some unrelated earlier gate and proving nothing."""
    assert len(_attached(_attach_rows([_row()]))) == 1


# ONE TABLE: the label, the malformed row, and the RULE that must refuse it.
# These were two tables joined by a hand-written label, so all fifteen labels
# were written twice and had to be kept in sync by hand. A row added without a
# rule raised KeyError, but a row REMOVED was silent — the parametrize simply ran
# fewer cases. Merging them removes the possibility rather than asserting it did
# not happen, so no guard is needed.
_MALFORMED_ROWS = [
    ("row is not a mapping", "not-a-row",
     "the graph row is str, not a mapping"),
    ("missing period_type", _without("period_type"),
     "has no ['period_type'] column"),
    ("missing start_date", _without("start_date"),
     "has no ['start_date'] column"),
    ("missing end_date", _without("end_date"),
     "has no ['end_date'] column"),
    ("missing dims", _without("dims"), "has no ['dims'] column"),
    ("missing value", _without("value"), "has no ['value'] column"),
    ("missing fact_id key", _without("fact_id"), "has no ['fact_id'] column"),
    ("dims is not a list", _row(dims=5),
     "the row's dims is int, not a list"),
    ("dims holds a non-dict", _row(dims=["oops"]),
     "each row dimension carries exactly"),
    ("dim lacks its label", _row(dims=[{"axis": "a", "member": "m"}]),
     "each row dimension carries exactly"),
    # OTHERWISE COMPLETE, with ONLY the axis blank — so the blank-string rule
    # is what fires. A three-key dim was refused first for its missing
    # namespaces, and this case then proved the wrong law under its own name.
    ("dim axis is blank", _row(dims=[dict(_ns_dim("a:Ax", "a:M", "L"), axis=" ")]),
     "must all be non-blank strings"),
    ("blank unit_ref", _row(unit_ref=""),
     "row field 'unit_ref' must be a non-blank string"),
    ("blank period_type", _row(period_type="   "),
     "row field 'period_type' must be a non-blank string"),
    ("null value", _row(value=None),
     "row field 'value' must be a non-blank string"),
    ("duration with a null end_date", _row(end_date=None),
     "a duration row needs its end_date"),
]


@pytest.mark.parametrize("why,row,rule", _MALFORMED_ROWS,
                         ids=[w for w, _, _ in _MALFORMED_ROWS])
def test_a_malformed_graph_ROW_parks_and_never_crashes(why, row, rule):
    """A broken row is a DATA SHAPE this route cannot bind — not a programming
    error, and not something a channel can fix by resubmitting. These escaped as
    raw KeyError/TypeError from inside `match_xbrl_fact`, which is the signal
    reserved for OUR OWN bugs."""
    _refused(_attach_rows([row]), ProductionValidationError, rule)


def test_CONFLICTING_rows_park_exactly_as_their_own_message_says():
    """The message already said 'park'; the TYPE said reject, which tells a
    channel to go and fix a filing it does not own."""
    _refused(_attach_rows([_row(), _row(value="999000000")]),
             ProductionValidationError, "CONFLICTING facts for this concept")
# ---------------------------------------------------------------------------
# #819 REPAIR — the checked row must be CHECKED and IMMUTABLE, not merely
# non-blank. `str(v).strip()` accepted every wrong type in every scalar, an
# integer value attached, a list value stayed aliased to the caller, and a
# dimension label accepted null/list/dict/int/bool.
# ---------------------------------------------------------------------------

_HOSTILE = (726000000, 1.5, True, False, None, ["x"], {"a": 1},
            __import__("decimal").Decimal("7"), b"bytes", (1,), frozenset({1}))


@pytest.mark.parametrize("field", [k for k in xa._ROW_FIELDS if k != "dims"])
def test_every_row_SCALAR_refuses_every_wrong_type(field):
    """GENERATED — every consumed scalar crossed with every hostile type, not a
    hand-written list of the ones someone happened to think of."""
    for v in _HOSTILE:
        if field == "fact_id" and v is None:
            continue                       # the ONE lawful null (see below)
        with pytest.raises(ProductionValidationError):
            xa._checked_row(_row(**{field: v}))


def test_the_LAWFUL_optional_row_forms_still_pass():
    """POSITIVE CONTROL — over-tightening here would park real facts.
    `fact_id` may be null or blank (that is what the identity fallback serves).
    F5 reconcile: the graph's LITERAL "null" instants (3,058/3,058) are now
    the ADAPTER'S alias — it emits None at the boundary, so the checked row
    lawfully sees None only; the string sentinel parks here (the retirement
    twin below)."""
    assert xa._checked_row(_row(fact_id=None))["fact_id"] is None
    assert xa._checked_row(_row(fact_id=""))["fact_id"] == ""
    row = xa._checked_row(_row(period_type="instant", end_date=None))
    assert row["end_date"] is None
    with pytest.raises(ProductionValidationError):
        xa._checked_row(_row(period_type="instant", end_date="null"))


def test_a_DURATION_still_requires_its_end_date():
    for end in (None, "", "   "):
        with pytest.raises(ProductionValidationError):
            xa._checked_row(_row(end_date=end))


@pytest.mark.parametrize("bad", [None, [], {}, 5, True, b"x", "   ", 1.5])
def test_a_dimension_LABEL_must_be_a_real_non_blank_string(bad):
    """`check_member_refs` RECOMPUTES the slice token from the label, so a null
    or non-string label can verify nothing."""
    with pytest.raises(ProductionValidationError):
        xa._checked_row(_row(dims=[{"axis": "a:Ax", "member": "a:M",
                                    "label": bad}]))


def test_a_dimension_carries_EXACTLY_its_three_fields():
    for d in ({"axis": "a", "member": "m", "label": "L", "extra": "x"},
              {"axis": "a", "member": "m"}):
        with pytest.raises(ProductionValidationError):
            xa._checked_row(_row(dims=[d]))


def test_the_checked_row_carries_ONLY_the_checked_fields():
    """`decimals` is produced by the reader and consumed by nobody; an unchecked
    extra must not ride along inside a record that calls itself checked."""
    checked = xa._checked_row(_row(decimals="0", something_new=["unchecked"]))
    assert set(checked) == set(xa._ROW_FIELDS)


def test_the_checked_row_is_NOT_reachable_through_the_callers_objects():
    """A list `value` stayed the caller's own object, so mutating it after the
    check changed the supposedly immutable row."""
    dim = _ns_dim("a:Ax", "a:M", "Europe")
    dims = [dim]
    raw = _row(dims=dims)
    checked = xa._checked_row(raw)
    dims.append({"axis": "b", "member": "c", "label": "d"})     # mutate the list
    dim["label"] = "MUTATED"                                    # mutate the dict
    raw["value"] = "999"                                        # mutate the row
    assert len(checked["dims"]) == 1
    assert checked["dims"][0]["label"] == "Europe"
    assert checked["value"] == "726,000,000"
    with pytest.raises(TypeError):
        checked["value"] = "0"
    with pytest.raises(TypeError):
        checked["dims"][0]["label"] = "x"


def test_an_INTEGER_value_no_longer_attaches_end_to_end():
    """The graph stores values as comma-bearing STRINGS ("4,824,698,000"), which
    is the whole reason `parse_raw` exists; an int bypassed that contract."""
    _refused(_attach_rows([_row(value=726000000)]), ProductionValidationError,
             "row field 'value' must be a non-blank string")


# --------------------------------------------------------------------------
# #827 finding 5 — the outcome MAP itself, DERIVED.
#
# The behaviours are already proven above and in the round-10/15 suites
# (malformed -> reject, unbindable -> park, SourceUnavailable ->
# park/SOURCE_UNAVAILABLE, programming errors propagate, an item's failure
# preserves its lawful siblings). What no test owned was the MAP: three
# vocabularies — `OUTCOME_CLASSES`, `xbrl_attach._DEFAULT_CODES` and
# `PUBLIC_DECISIONS` — that must agree, and that a hand-written list would
# silently let drift apart.
# --------------------------------------------------------------------------

def test_827_the_outcome_MAP_is_internally_consistent_and_derived():
    from driver.core import prepared_fact_v2 as p2
    from driver.core import xbrl_attach as xa

    # every class the door can classify has exactly one decision word, and
    # that word is a PUBLIC decision
    for exc, decision in p2.OUTCOME_CLASSES.items():
        assert decision in xa.PUBLIC_DECISIONS, (exc, decision)
    # every class the door classifies per item is in the outcome map
    for exc in xa.OUTCOME_ITEM_CLASSES:
        assert exc in p2.OUTCOME_CLASSES, f"{exc.__name__} has no decision word"
    # every default code belongs to a class the map knows, and codes are unique
    coded = [exc for exc, _code in xa._DEFAULT_CODES]
    assert set(coded) <= set(p2.OUTCOME_CLASSES), \
        f"a default code exists for a class outside the map: {coded}"
    codes = [code for _exc, code in xa._DEFAULT_CODES]
    assert len(codes) == len(set(codes)), f"duplicate default codes: {codes}"
    # the five public decisions are exactly the five, in the owner's order
    assert xa.PUBLIC_DECISIONS == ("written", "merged", "parked", "skipped",
                                   "rejected")
    # the two refusal families are distinguishable: a contract breach REJECTS,
    # everything else PARKS — the distinction the whole ladder rests on
    assert p2.OUTCOME_CLASSES[p2.SchemaError] == "rejected"
    assert {p2.OUTCOME_CLASSES[c] for c in p2.OUTCOME_CLASSES
            if c is not p2.SchemaError} == {"parked"}
    # a retryable source failure is an OSError family member, not a contract
    # breach — so it can never be mapped to `rejected`
    assert all(issubclass(e, OSError) for e in xa.RETRYABLE_SOURCE_ERRORS)
    assert p2.SourceUnavailable in p2.OUTCOME_CLASSES


# ---------------------------------------------------------------------------
# #827 round 8 — THE CONCEPT'S IDENTITY MUST SURVIVE THE WHOLE PATH.
#
# The binder compares (namespace URI, local name) and refuses without it. That
# was proved against `bind_graph_fact` directly — which is exactly why it went
# wrong: the query selected the fields, but the adapter's row mapping dropped
# them and `_ROW_FIELDS` never named them, so `_checked_row` dropped whatever
# survived. Through the REAL path every lawful fact would have parked as
# `missing_graph_concept_namespace`, and a direct-binder probe cannot see that.
#
# These run through the row contract and the production public door instead.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field", ["concept_namespace", "graph_concept_qname"])
def test_827R8_the_row_contract_REQUIRES_the_concepts_identity(field):
    """A reader that cannot supply either half is a broken reader — an ordinary
    park at the boundary, never a silent None the binder would read as absent."""
    with pytest.raises(ProductionValidationError):
        xa._checked_row(_without(field))
    for blank in ("", "   ", None):
        with pytest.raises(ProductionValidationError):
            xa._checked_row(_row(**{field: blank}))


@pytest.mark.parametrize("field", ["concept_namespace", "graph_concept_qname"])
def test_827R8_the_checked_row_CARRIES_the_concepts_identity_onward(field):
    """MUST-ALLOW twin: the lawful row keeps both halves, so the door can hand
    them to the binder. Dropping them here is the defect this pins."""
    assert xa._checked_row(_row())[field] == _row()[field]


def test_827R8_a_lawful_fact_still_ATTACHES_through_the_public_door():
    """THE POSITIVE CONTROL for the whole path. If the identity did not reach
    the binder, this fact would park instead of attaching, and every other
    refusal test in this file would still have passed."""
    _attached(_attach_rows([_row()]))


def test_827R8_a_MISMATCHED_graph_concept_qname_parks_through_the_public_door():
    """RED twin of the control above, through the same door: the Concept
    record's own qname must agree with the concept being bound before either
    half of the expanded name is trusted."""
    _refused(_attach_rows([_row(graph_concept_qname="us-gaap:SomethingElse")]),
             ProductionValidationError, "")
