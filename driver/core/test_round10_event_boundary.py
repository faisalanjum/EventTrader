"""ROUND-10 — the event boundary's input contract and its THREE failure classes.

The owner's two precision rules:

  1. The one-representation guard must ask CORE'S GRAPH how many XBRL nodes the
     source has (exactly one, else park). Repeated hashes from the channel are
     the channel agreeing with itself, which proves nothing.
     Census 2026-07-27: 10,468 XBRL-bearing reports, every one with exactly one
     XBRLNode, zero facts spanning two — so the guard never fires on today's
     corpus and exists for the case we have not seen.

  2. THREE distinct outcomes, never one blanket catch:
       malformed four-key input        -> CONTRACT REJECTION (fix and resubmit)
       known temporary Fiscal/Neo4j    -> PARK-RETRY (drains by itself)
       an unexpected programming error -> FAILS LOUDLY (never swallowed)
"""
from decimal import Decimal
import pytest

from driver.core import prepared_fact_v2 as p2
from driver.core.xbrl_attach import _ROW_FIELDS, _row_signature, attach_event_xbrl
from driver.core import xbrl_attach as xa
from driver.core.prepared_fact_v2 import (ProductionValidationError, SchemaError,
                                          SourceUnavailable)

_DOC = "<html xmlns:xbrli='http://www.xbrl.org/2003/instance' xmlns:xbrldi='http://xbrl.org/2006/xbrldi' xmlns:ix='http://www.xbrl.org/2013/inlineXBRL' xmlns:iso4217='http://www.xbrl.org/2003/iso4217' xmlns:utr='http://example.org/utr' xmlns:us-gaap='http://example.org/us-gaap' xmlns:dei='http://example.org/dei' xmlns:srt='http://example.org/srt' xmlns:a='http://example.org/a' xmlns:x='http://example.org/x' xmlns:aapl='http://example.org/aapl' xmlns:slg='http://example.org/slg' xmlns:accd='http://example.org/accd' xmlns:ed='http://example.org/ed' xmlns:dvn='http://example.org/dvn' xmlns:fcx='http://example.org/fcx' xmlns:nog='http://example.org/nog' xmlns:inst='http://example.org/inst' xmlns:dimns='http://example.org/dimns' xmlns:nope='http://example.org/nope' xmlns:geo='http://example.org/geo' xmlns:eqt='http://example.org/eqt' xmlns:geography='http://example.org/geography' xmlns:seg='http://example.org/seg' xmlns:country='http://example.org/country'><body></body></html>"
# the REAL hash of the document the provider serves, so the representation
# check passes and execution actually reaches the graph calls under test
from driver.relocation.inline_html import prepare          # noqa: E402
SHA = prepare(_DOC)["text_sha"]


def ev_of(sha):
    """Shape-only `source_evidence` carrying THIS representation hash.

    For tests that never reach the filing verification — the item-key contract,
    the one-representation guard, and the park/reject outcomes that fire before
    any binding. It is deliberately NOT lawful against a document, so if one of
    those tests ever did reach the verification it would fail loudly rather than
    quietly pass on a stand-in. Tests that DO reach it use `filing_evidence`.
    """
    return {"representation_sha256": sha, "quote_span": [0, 1],
            "raw_label_span": None, "pieces": []}


def filing_evidence(doc, element_id, **override):
    """THE test-fixture owner for LAWFUL evidence — one builder, not thirty-four.

    Built by the SAME shared owner production uses, then its premises are
    ASSERTED here before any test leans on them: the hash reproduces from this
    very document, the quote span slices non-blank text, the label span lies
    inside the quote span, and every piece is reproduced exactly by its own
    span. A fixture that cannot prove those is not evidence, and a test built on
    it would prove nothing.

    `override` alters EXACTLY the field under attack, so an attack test changes
    one thing and leaves every other input lawful — otherwise an earlier gate
    fires and the test passes for the wrong reason.

    Returns (evidence, filing_quote). The quote is what `fact.item.quote` must
    equal: the exact quote is the only bridge between the event view and the
    filing.
    """
    from driver.relocation.inline_html import (element_evidence, prepare,
                                               source_evidence)
    prep = prepare(doc)
    ev, why = element_evidence(prep, element_id)
    assert ev is not None, f"fixture element {element_id} did not resolve: {why}"
    se = source_evidence(prep, ev)
    assert se is not None, f"fixture element {element_id} has no lawful evidence"
    assert se["representation_sha256"] == prep["text_sha"]
    q0, q1 = se["quote_span"]
    quote = prep["text"][q0:q1]
    assert quote.strip(), "the fixture quote must be non-blank"
    if se["raw_label_span"] is not None:
        l0, l1 = se["raw_label_span"]
        assert q0 <= l0 and l1 <= q1, "the fixture label must sit in its quote"
    for piece in se["pieces"]:
        a, b = piece["span"]
        assert prep["text"][a:b] == piece["text"], piece
    se.update(override)
    return se, quote


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


def _item(**over):
    d = {"fact": _valid_fact(), "concept": "us-gaap:Revenues", "member_refs": [],
         "source_evidence": ev_of(SHA)}
    d.update(over)
    return d


class Graph:
    """Core's graph. `xbrl_nodes` is what the guard actually consults."""
    def __init__(self, xbrl_nodes=1, cik="0000320193"):
        # F13 reconcile: the default was the ARCHIVE 6-digit spelling, which
        # the owner precheck (driver_ids.graph_cik at the door) now refuses —
        # the fixture carries the graph's real ten-digit form.
        self._n, self._cik = xbrl_nodes, cik

    def get_xbrl_representation_count(self, source_id):
        return self._n

    def get_xbrl_fact_dimensions(self, source_id, concept):
        return GraphFactRows(rows=[], exclusions=())

    def get_source_company_cik(self, source_id):
        return self._cik


class Provider:
    def get_filing_document(self, source_id):
        return _DOC


def _run(items, store=None, provider=None):
    """The door, returning its RESULT RECORD (#825) — not a bare fact list.

    Twelve of the thirteen call sites here discard the return inside
    `pytest.raises`, so this hands back what the door actually returns and each
    test asks the record for the part it is about: `.facts` for a success,
    `.preflight_outcomes` for an item-local refusal.
    """
    return xa.attach_event_xbrl(items, source_id="x",
                                store=store or Graph(),
                                filing_provider=provider or Provider(),
                                text_parts=parts_for(items))


def _attached(res, count=1):
    """A SUCCESS: `count` facts, at their ORIGINAL indexes, and NO outcome row."""
    assert res.preflight_outcomes == (), [dict(o) for o in res.preflight_outcomes]
    assert [i for i, _f in res.facts] == list(range(count))
    return [f for _i, f in res.facts]


def _refused(res, exc_class, needle, count=1):
    """An ITEM-LOCAL refusal: exactly `count` indexed rows, decision and code
    derived from the exception class the ORIGINAL test named (that mapping is
    pinned independently in the round-15 matrix), and a MANDATORY rule-specific
    reason — a bare class check passes for any other reason."""
    want_decision, want_code = xa._default_outcome(exc_class("probe"))
    assert res.facts == (), "a refused item must attach nothing"
    assert [o["index"] for o in res.preflight_outcomes] == list(range(count)), \
        [dict(o) for o in res.preflight_outcomes]
    for row in res.preflight_outcomes:
        assert (row["decision"], row["codes"]) == (want_decision, (want_code,))
        assert needle in row["detail"], row["detail"]
    return res.preflight_outcomes[0]


# --- the input contract ----------------------------------------------------

def test_a_GENERATOR_is_not_silently_consumed_into_an_empty_result():
    """It returned [] — 'no XBRL facts here' — having verified nothing."""
    with pytest.raises(SchemaError, match="list or tuple"):
        _run(_item() for _ in range(3))


@pytest.mark.parametrize("items", [None, {"a": 1}, "abc", 5, {_item()["concept"]}])
def test_the_ITEM_LIST_must_be_a_list_or_tuple(items):
    with pytest.raises(SchemaError, match="list or tuple"):
        _run(items)


def test_an_event_with_NO_xbrl_items_is_lawful_and_returns_nothing():
    """An 8-K carries no XBRL at all (census: zero XBRL-bearing 8-Ks). That is
    an empty result, not an error.

    IT IS THE RESULT RECORD, the same shape every other path returns. This
    branch really did hand back a bare `[]`, so a caller reading `.facts`
    crashed on the commonest event there is — and `== []` could not tell an
    empty result from a different return TYPE, which is exactly what was wrong.
    """
    for empty in ([], ()):
        res = _run(empty)
        assert res.facts == () and res.preflight_outcomes == ()
        assert res.source_id == "x"
        assert dict(res.member_menu["folds"]) == {}
        assert res.member_menu["exclusions"] == ()


@pytest.mark.parametrize("bad", [
    {"concept": "c", "member_refs": [], "source_evidence": ev_of(SHA)},
    {"fact": {}, "member_refs": [], "source_evidence": ev_of(SHA)},
    {"fact": {}, "concept": "c", "source_evidence": ev_of(SHA)},
    {"fact": {}, "concept": "c", "member_refs": []},
])
def test_a_MISSING_key_is_a_contract_rejection_not_a_KeyError(bad):
    _refused(_run([bad]), SchemaError, "each item is a dict carrying EXACTLY the keys")


@pytest.mark.parametrize("bad", ["not-a-dict", None, 5, [], ()])
def test_a_NON_DICT_item_is_a_contract_rejection_not_an_AttributeError(bad):
    _refused(_run([bad]), SchemaError, "each item is a dict carrying EXACTLY the keys")


# --- rule 1: the guard consults CORE'S GRAPH -------------------------------

def test_more_than_one_xbrl_representation_PARKS():
    _refused(_run([_item()], store=Graph(xbrl_nodes=2)),
             ProductionValidationError, "reports 2 XBRL representation(s)")


def test_a_source_with_NO_xbrl_cannot_carry_an_xbrl_item():
    """The channel claims XBRL for a source the graph says has none."""
    _refused(_run([_item()], store=Graph(xbrl_nodes=0)),
             ProductionValidationError, "reports 0 XBRL representation(s)")


def test_the_guard_asks_the_GRAPH_not_only_the_channels_hashes():
    """Identical hashes are the channel agreeing with itself. The count comes
    from Core."""
    asked = []

    class Watched(Graph):
        def get_xbrl_representation_count(self, source_id):
            asked.append(source_id)
            return 1

    # it proceeds past the guard and parks later (no rows for the concept);
    # what this test pins is that the COUNT came from the graph, once.
    # BOTH items park, each keeping its own index — the concept has no rows.
    _refused(_run([_item(), _item()], store=Watched()),
             ProductionValidationError, "carries NO fact for concept", count=2)
    assert asked == ["x"], "the graph was never consulted"


# --- rule 2: three distinguishable failure classes -------------------------

class DeadProvider:
    def get_filing_document(self, source_id):
        raise ConnectionError("EDGAR unreachable")


class DeadGraph(Graph):
    def get_source_company_cik(self, source_id):
        raise TimeoutError("neo4j timed out")


class BuggyGraph(Graph):
    def get_source_company_cik(self, source_id):
        return {}["missing"]                      # a real programming error




def test_a_TEMPORARY_provider_failure_is_PARK_RETRY():
    _refused(_run([_item(fact=_valid_fact())], provider=DeadProvider()),
             SourceUnavailable, "the filing provider is temporarily unavailable")


def test_a_TEMPORARY_graph_failure_is_PARK_RETRY():
    _refused(_run([_item(fact=_valid_fact())], store=DeadGraph()),
             SourceUnavailable, "the graph is temporarily unavailable")


def test_park_retry_is_NOT_a_contract_rejection():
    """A channel must not 'fix and resubmit' an outage — the two outcomes drive
    different behaviour, so they must be different types."""
    assert not issubclass(SourceUnavailable, SchemaError)
    assert not issubclass(SchemaError, SourceUnavailable)


def test_an_UNEXPECTED_programming_error_FAILS_LOUDLY():
    """Never blanket-caught: a KeyError from our own code is a bug, and hiding
    it as a park would make the bug invisible forever."""
    with pytest.raises(KeyError):
        _run([_item(fact=_valid_fact())], store=BuggyGraph())


def test_the_retryable_set_is_named_not_a_bare_except():
    """On the AST, never the source text: the first version of this test matched
    the prose of the very comment forbidding a blanket catch. Substring checks
    over source have now produced a false positive three times in this arc."""
    import ast
    import inspect
    blanket = []
    for node in ast.walk(ast.parse(inspect.getsource(p2))):
        if isinstance(node, ast.ExceptHandler):
            t = node.type
            if t is None or (isinstance(t, ast.Name)
                             and t.id in ("Exception", "BaseException")):
                blanket.append(getattr(node, "lineno", "?"))
    assert not blanket, f"blanket except at line(s) {blanket}"
    assert xa.RETRYABLE_SOURCE_ERRORS, "the retryable classes must be explicit"
    assert OSError in xa.RETRYABLE_SOURCE_ERRORS


# --- the stale note --------------------------------------------------------


# ---------------------------------------------------------------------------
# #820 + #821 — ONE public door, ONE set of reads per event, everything checked
# before any I/O.
# ---------------------------------------------------------------------------

#: THE FIXTURE'S NAMESPACE DECLARATION — defined ONCE, before the documents,
#: and interpolated into both the markup and the row identity so the document
#: and the row it is bound against cannot drift apart. `iso4217` names the
#: OFFICIAL XBRL currency namespace because these fixtures claim a LAWFUL USD
#: unit; the taxonomy URIs stay deliberately synthetic (example.org) because
#: no test here claims their official identity.
_FIXTURE_NS = {
    'xbrli': 'http://www.xbrl.org/2003/instance',
    'xbrldi': 'http://xbrl.org/2006/xbrldi',
    'ix': 'http://www.xbrl.org/2013/inlineXBRL',
    'iso4217': 'http://www.xbrl.org/2003/iso4217',
    # THE TRANSFORMATION REGISTRY, declared because a real filing declares it.
    # `format` is xs:QName, so `ixt:num-dot-decimal` names nothing unless its
    # prefix is bound — and every fixture here wrote that value while declaring
    # no such prefix, which made them invalid controls: they asserted a
    # transform by a name that resolved to nothing. Measured over the frozen
    # cache, real filings bind `ixt` to an OFFICIAL registry namespace (1,418
    # to 2020-02-12, 230 to 2022-02-16, 121 to 2015-02-26); the most common is
    # used here. `ixt-sec` is the SEC's own registry, present on 11,728 tags.
    'ixt': 'http://www.xbrl.org/inlineXBRL/transformation/2020-02-12',
    'ixt-sec': 'http://www.sec.gov/inlineXBRL/transformation/2015-08-31',
    'utr': 'http://example.org/utr',
    'us-gaap': 'http://example.org/us-gaap',
    'dei': 'http://example.org/dei',
    'srt': 'http://example.org/srt',
    'a': 'http://example.org/a',
    'x': 'http://example.org/x',
    'aapl': 'http://example.org/aapl',
    'slg': 'http://example.org/slg',
    'accd': 'http://example.org/accd',
    'ed': 'http://example.org/ed',
    'dvn': 'http://example.org/dvn',
    'fcx': 'http://example.org/fcx',
    'nog': 'http://example.org/nog',
    'inst': 'http://example.org/inst',
    'dimns': 'http://example.org/dimns',
    'nope': 'http://example.org/nope',
    'geo': 'http://example.org/geo',
    'eqt': 'http://example.org/eqt',
    'geography': 'http://example.org/geography',
    'seg': 'http://example.org/seg',
    'country': 'http://example.org/country',
}
_XMLNS = " ".join(f'xmlns:{p}="{u}"' for p, u in _FIXTURE_NS.items())
_NS_GAAP = _FIXTURE_NS["us-gaap"]


_DOOR_DOC = (f'<html {_XMLNS}><body><ix:header><ix:resources><xbrli:context id="c1"><xbrli:entity>'
             '<xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193</xbrli:identifier></xbrli:entity>'
             '<xbrli:period><xbrli:startDate>2024-01-01</xbrli:startDate>'
             '<xbrli:endDate>2024-06-30</xbrli:endDate></xbrli:period>'
             '</xbrli:context></ix:resources></ix:header><ix:header><ix:resources><xbrli:unit id="u1">'
             '<xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit></ix:resources></ix:header>'
             '<p><ix:nonFraction id="fA" name="us-gaap:A" contextRef="c1" '
             'unitRef="u1" scale="6" decimals="-6">726</ix:nonFraction>'
             '<ix:nonFraction id="fB" name="us-gaap:B" contextRef="c1" '
             'unitRef="u1" scale="6" decimals="-6">726</ix:nonFraction></p>'
             '</body></html>')
_ACC = "0000006201-26-000031"






def parts_for(items):
    """Lawful `text_parts` derived from the items themselves — each fact's own
    quote, in the part it names.

    TEST-SIDE ONLY. Production callers supply the real event view the model saw;
    this exists so tests about OTHER rules are not each hand-writing an event
    view. Deliberately defensive: the attack fixtures pass deliberately
    malformed items, and those must still reach the door and be refused THERE,
    not crash in a helper on the way in.
    """
    seen = {}
    if type(items) not in (list, tuple):
        return []            # the door judges the container; this helper never
    for i in items:          # pre-empts it, or the wrong error would be raised
        try:
            fact = i["fact"]
            seen.setdefault(fact["part_ref"], fact["item"]["quote"])
        # EXACTLY THE ERRORS SUBSCRIPTING A MALFORMED CONTAINER RAISES. The
        # attack fixtures are deliberately malformed and must reach the door to
        # be refused THERE — but `except Exception` would also swallow a defect
        # in this helper itself, and a silent helper bug turns every test that
        # uses it into a test of an empty event view.
        except (KeyError, TypeError, IndexError):
            continue
    return [{"part": p, "content": c} for p, c in seen.items()
            if type(p) is str and p.strip() and type(c) is str]


def _door_row(fact_id, concept="us-gaap:X"):
    # THE CONCEPT'S IDENTITY IS PART OF THE ROW. The binder compares
    # (namespace URI, local name) rather than a prefixed string, and takes both
    # halves from the one Concept record the row was read with, so a fixture row
    # that omitted them would not be the shape the real adapter returns.
    return {"period_type": "duration", "start_date": "2024-01-01",
            "end_date": "2024-07-01", "dims": [], "fact_id": fact_id,
            "context_id": "c1", "unit_ref": "u1", "unit_name": "iso4217:USD",
            "is_divide": "0", "value": "726,000,000", "decimals": "0",
            "concept_namespace": _NS_GAAP, "graph_concept_qname": concept}


def _door_item(concept, fact_id, doc=None, **override):
    """A door item whose evidence is LAWFUL against `_DOOR_DOC`, from the one
    fixture owner. `override` reaches `filing_evidence`, so an attack changes
    exactly one field and every other input stays valid."""
    from decimal import Decimal

    from driver.core.prepared_fact_v2 import ITEM_FIELDS
    evidence, quote = filing_evidence(_DOOR_DOC if doc is None else doc,
                                      fact_id, **override)
    slot = {"value": Decimal("726"), "scale_multiplier": Decimal(10) ** 6,
            "unit_scale_evidence": None}
    it = {k: None for k in ITEM_FIELDS}
    it.update(driver_name="thing", driver_state="reported", quote=quote,
              measurement_raw_spans=[], slice_parts=[], level_unit="usd",
              level_low=dict(slot), level_high=dict(slot), time_type="duration",
              period_start_date="2024-01-01", period_end_date="2024-06-30")
    return {"fact": {"fact_type": "metric", "part_ref": fact_id,
                     "occurrence_in_part": None, "per_x": None, "item": it},
            "concept": concept, "member_refs": [],
            "source_evidence": evidence}


class _Counting:
    """Counts EVERY read, so 'once per event' is measured, never asserted."""

    def __init__(self, count=1):
        self.representation = self.cik = 0
        self.row_reads = []
        self._count = count

    def get_xbrl_representation_count(self, source_id):
        self.representation += 1
        return self._count

    def get_source_company_cik(self, source_id):
        self.cik += 1
        return "0000320193"

    def get_xbrl_fact_dimensions(self, source_id, concept):
        self.row_reads.append(concept)
        return GraphFactRows(
            rows=[_door_row("fA" if concept.endswith("A") else "fB",
                            concept=concept)], exclusions=())


class _CountingProvider:
    def __init__(self):
        self.fetches = 0

    def get_filing_document(self, source_id):
        self.fetches += 1
        return _DOOR_DOC


def test_FOUR_items_across_TWO_concepts_read_everything_ONCE_per_event():
    """The measured defect: four facts cost four document fetches, four CIK
    reads and four row reads even when they shared one concept."""
    from driver.core.xbrl_attach import attach_event_xbrl
    store, provider = _Counting(), _CountingProvider()
    items = [_door_item("us-gaap:A", "fA"), _door_item("us-gaap:B", "fB"),
             _door_item("us-gaap:A", "fA"), _door_item("us-gaap:B", "fB")]
    out = attach_event_xbrl(items, source_id=_ACC, store=store,
                            filing_provider=provider, text_parts=parts_for(items)).facts
    assert len(out) == 4
    assert store.representation == 1, store.representation
    assert provider.fetches == 1, provider.fetches
    assert store.cik == 1, store.cik
    assert store.row_reads == ["us-gaap:A", "us-gaap:B"], store.row_reads


def test_INPUT_ORDER_IS_OUTPUT_ORDER():
    from driver.core.xbrl_attach import attach_event_xbrl
    items = [_door_item("us-gaap:B", "fB"), _door_item("us-gaap:A", "fA")]
    facts = _attached(attach_event_xbrl(
        items, source_id=_ACC, store=_Counting(),
        filing_provider=_CountingProvider(), text_parts=parts_for(items)),
        count=2)
    assert [f.part_ref for f in facts] == ["fB", "fA"]


def test_TWO_separate_events_each_do_their_own_reads_no_global_cache():
    """A cache that survived between events would be a hidden global."""
    from driver.core.xbrl_attach import attach_event_xbrl
    for _ in range(2):
        store, provider = _Counting(), _CountingProvider()
        attach_event_xbrl([_door_item("us-gaap:A", "fA")], source_id=_ACC,
                          store=store, filing_provider=provider, text_parts=parts_for([_door_item("us-gaap:A", "fA")])).facts
        assert (store.representation, provider.fetches, store.cik,
                store.row_reads) == (1, 1, 1, ["us-gaap:A"])


def test_a_legal_accession_is_the_POSITIVE_control():
    from driver.core.xbrl_attach import attach_event_xbrl
    item = _door_item("us-gaap:A", "fA")
    facts = _attached(attach_event_xbrl(
        [item], source_id=_ACC, store=_Counting(),
        filing_provider=_CountingProvider(), text_parts=parts_for([item])))
    assert facts[0].item.xbrl_concept_raw == "us-gaap:A"


def test_an_EMPTY_item_list_performs_ZERO_io():
    from driver.core.xbrl_attach import attach_event_xbrl
    store, provider = _Counting(), _CountingProvider()
    assert attach_event_xbrl([], source_id=_ACC, store=store,
                             filing_provider=provider,
                             text_parts=parts_for([])).facts == ()
    assert (store.representation, provider.fetches, store.cik) == (0, 0, 0)


class _NeverRead:
    def get_xbrl_representation_count(self, s):
        raise AssertionError("the graph was read before validation finished")

    def get_source_company_cik(self, s):
        raise AssertionError("the graph was read before validation finished")

    def get_xbrl_fact_dimensions(self, s, c):
        raise AssertionError("the graph was read before validation finished")


class _NeverFetched:
    def get_filing_document(self, s):
        raise AssertionError("the provider was called before validation finished")


_BAD_EVENTS = [
    ("source id with a slash", {"source_id": "x/y"}),
    ("source id with a colon", {"source_id": "a:b"}),
    ("blank source id", {"source_id": "  "}),
    ("null source id", {"source_id": None}),
    ("numeric source id", {"source_id": 5}),
    ("items is a str", {"items": "abc"}),
    ("items is a dict", {"items": {"a": 1}}),
    ("items is a set", {"items": {1, 2}}),
    ("items is a generator", {"items": (x for x in [1])}),
    ("items is a list SUBCLASS", {"items": type("L", (list,), {})()}),
    ("item is not a dict", {"items": ["nope"]}),
    ("item has MIXED-TYPE keys", {"items": [{1: "a", "concept": "c"}]}),
    ("item has an extra key", {"items": [dict(_door_item("us-gaap:A", "fA"),
                                              extra=1)]}),
    ("item is missing a key", {"items": [{k: v for k, v in
                                          _door_item("us-gaap:A", "fA").items()
                                          if k != "concept"}]}),
]


@pytest.mark.parametrize("why,over", _BAD_EVENTS, ids=[w for w, _ in _BAD_EVENTS])
def test_nothing_malformed_reaches_the_graph_or_the_provider(why, over):
    """EVERY pure check before ANY I/O — including the error MESSAGE, which used
    to sort the caller's keys and raise a raw TypeError on mixed key types."""
    from driver.core.prepared_fact_v2 import SchemaError
    kw = {"items": [_door_item("us-gaap:A", "fA")], "source_id": _ACC}
    kw.update(over)

    def call():
        return attach_event_xbrl(kw["items"], source_id=kw["source_id"],
                                 store=_NeverRead(),
                                 filing_provider=_NeverFetched(),
                                 text_parts=parts_for(kw["items"]))

    # THE INVARIANT IS UNCHANGED — zero I/O, proved by stores that raise if
    # touched at all. What differs is WHERE the refusal is reported. An envelope
    # that cannot be indexed into items still RAISES, because there is no item
    # list to report against; a malformed ITEM inside a usable envelope becomes
    # that item's own rejection row (#825).
    #
    # The split is taken from the DOOR'S OWN LAW — a rejected source id, or a
    # container that is not exactly a list/tuple — rather than by matching a
    # test name, so a new case in the table lands on the right side by itself.
    if "source_id" in over or type(kw["items"]) not in (list, tuple):
        with pytest.raises(SchemaError):
            call()
        return
    # F6: the split still comes from the DOOR'S OWN LAW — a dict item carrying
    # every pinned key PLUS extras is unlisted vocabulary and PARKS; anything
    # else stays the contract rejection. Zero I/O either way (the invariant).
    from driver.core.xbrl_attach import _EVENT_ITEM_KEYS
    it = kw["items"][0]
    if type(it) is dict and set(_EVENT_ITEM_KEYS) < set(it):
        from driver.core.prepared_fact_v2 import ProductionValidationError
        _refused(call(), ProductionValidationError,
                 "unlisted item field(s)")
        return
    _refused(call(), SchemaError,
             "each item is a dict carrying EXACTLY the keys")


@pytest.mark.parametrize("count", [True, False, 1.0, "1", None,
                                   __import__("decimal").Decimal("1"), 2, 0])
def test_a_non_INTEGER_representation_count_parks_before_any_further_io(count):
    """`count != 1` alone accepted True, 1.0 and Decimal('1')."""
    from driver.core.prepared_fact_v2 import ProductionValidationError

    class Store(_Counting):
        def get_source_company_cik(self, s):
            raise AssertionError("execution continued past a bad count")

        def get_xbrl_fact_dimensions(self, s, c):
            raise AssertionError("execution continued past a bad count")

    provider = _CountingProvider()
    item = _door_item("us-gaap:A", "fA")
    _refused(attach_event_xbrl([item], source_id=_ACC, store=Store(count=count),
                               filing_provider=provider,
                               text_parts=parts_for([item])),
             ProductionValidationError, f"reports {count!r} XBRL representation")
    assert provider.fetches == 0, "the filing was fetched despite a bad count"


def test_there_is_EXACTLY_ONE_exported_xbrl_attachment_door():
    """DERIVED from the module's own __all__ and AST, not a hand list."""
    import ast
    import inspect

    from driver.core import prepared_fact_v2 as p2
    from driver.core import xbrl_attach as xa
    # the SCHEMA module must export no attachment door at all any more
    assert [n for n in p2.__all__ if "attach" in n] == []
    exported = [n for n in xa.__all__ if "attach" in n]
    assert exported == ["attach_event_xbrl"], exported
    tree = ast.parse(inspect.getsource(xa))
    public_attach = [n.name for n in ast.walk(tree)
                     if isinstance(n, ast.FunctionDef)
                     and "attach" in n.name and not n.name.startswith("_")]
    assert public_attach == ["attach_event_xbrl"], public_attach


def test_NO_production_module_bypasses_the_event_door():
    """DERIVED import scan: nothing in production may reach the private binder."""
    import ast
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1]
    offenders, scanned = [], 0
    for path in sorted(root.rglob("*.py")):
        if path.name.startswith("test_") or path.name in (
                "prepared_fact_v2.py", "xbrl_attach.py"):   # the owners
            continue
        scanned += 1
        for node in ast.walk(ast.parse(path.read_text())):
            names = []
            if isinstance(node, ast.ImportFrom):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.Attribute):
                names = [node.attr]
            for n in names:
                if n in ("_verify_and_attach", "_one_representation_for_event"):
                    offenders.append(f"{path.name}:{node.lineno} -> {n}")
    assert scanned >= 15, f"the scan covered only {scanned} modules"
    assert not offenders, offenders


# ---------------------------------------------------------------------------
# #819/#820 REMAINDER (reviewer, audit :451) — four defects the green suite
# missed, each reproduced live before this was written.
# ---------------------------------------------------------------------------

def test_a_row_that_MATCHES_NO_CLAIM_parks_it_does_not_reject():
    """Same #819 class: the concept EXISTS but no row carries the claimed exact
    period/context/dimensions. That is external filing/graph evidence we cannot
    bind YET — the graph runs about a quarter behind — so it is the ordinary
    park. Rejecting told the channel to fix a filing it does not own, and the
    item never drained. The previous test CEMENTED the wrong outcome."""
    from driver.core.prepared_fact_v2 import ProductionValidationError
    item = _door_item("us-gaap:A", "fA")
    item["fact"]["item"]["period_end_date"] = "2026-09-30"      # matches no row
    _refused(attach_event_xbrl([item], source_id=_ACC, store=_Counting(),
                               filing_provider=_CountingProvider(),
                               text_parts=parts_for([item])),
             ProductionValidationError,
             "no fact in this filing carries that concept")


def test_the_empty_event_shortcut_still_validates_the_SOURCE_ID():
    """A lawful zero-I/O return must not become a way to skip validation."""
    from driver.core.prepared_fact_v2 import SchemaError
    for bad in ("x/y", "a:b", "", None, 5):
        with pytest.raises(SchemaError):
            attach_event_xbrl([], source_id=bad, store=_NeverRead(),
                              filing_provider=_NeverFetched(), text_parts=parts_for([])).facts
    # ...and a LEGAL id still performs zero I/O and attaches nothing
    store, provider = _Counting(), _CountingProvider()
    assert attach_event_xbrl([], source_id=_ACC, store=store,
                             filing_provider=provider,
                             text_parts=parts_for([])).facts == ()
    assert (store.representation, provider.fetches, store.cik) == (0, 0, 0)


@pytest.mark.parametrize("bad", ["x/y", "a:b", "", "  ", None, 5, True])
def test_RunInputV2_uses_the_ONE_source_id_predicate_on_BOTH_paths(bad):
    """Its docstring claimed the run input calls `valid_source_id`; it did not.
    Both the direct constructor and `from_dict` must ask the same predicate."""
    from driver.core.prepared_fact_v2 import RunInputV2, SchemaError
    with pytest.raises(SchemaError):
        RunInputV2(source_id=bad, facts=[])
    with pytest.raises(SchemaError):
        RunInputV2.from_dict({"source_id": bad, "facts": []})


def test_a_LEGAL_source_id_still_builds_a_run_input():
    """Positive control — the guard above must not be passing by rejecting all."""
    from driver.core.prepared_fact_v2 import RunInputV2
    assert RunInputV2(source_id=_ACC, facts=[]).source_id == _ACC
    # a TUPLE now, per #823: fact collections are stored immutably, so the
    # invariant the constructor checked cannot be falsified afterwards.
    assert RunInputV2.from_dict({"source_id": _ACC, "facts": []}).facts == ()


def _mixed_key_doors():
    """Every door that compares a caller's key set. MIXED types are the trigger:
    a single extra key of one type sorts fine, which is exactly why a weaker
    probe of mine missed this."""
    from driver.core.prepared_fact_v2 import PreparedFactV2, RunInputV2
    good = _door_item("us-gaap:A", "fA")["fact"]
    return [
        ("fact level", lambda: PreparedFactV2.from_dict({**good, 1: "x", "zz": "y"})),
        ("item level", lambda: PreparedFactV2.from_dict(
            {**good, "item": {**good["item"], 2: "y", "zz": "w"}})),
        ("run input", lambda: RunInputV2.from_dict(
            {"source_id": _ACC, "facts": [], 3: "z", "zz": "w"})),
    ]


@pytest.mark.parametrize("where", [w for w, _ in _mixed_key_doors()])
def test_MIXED_TYPE_keys_are_refused_cleanly_at_every_door(where):
    """`sorted(extra)` on the caller's own keys raised a raw TypeError — a crash
    inside the guard that exists to prevent crashes. Fixed as a CLASS: no door
    sorts or echoes arbitrary caller keys."""
    from driver.core.prepared_fact_v2 import SchemaError
    fn = dict(_mixed_key_doors())[where]
    with pytest.raises(SchemaError):
        fn()


def test_the_filing_is_PARSED_once_per_event_not_once_per_item():
    """The saved I/O test counted the provider, CIK, representation and row
    reads — but not the parse. `prepare` is memoised by content sha, so a
    per-item parse regression would have stayed invisible."""
    from driver.core import xbrl_attach as xa
    calls = []
    real = xa.prepare

    def counting(doc):
        calls.append(1)
        return real(doc)

    xa.prepare = counting
    try:
        out = attach_event_xbrl(
            [_door_item("us-gaap:A", "fA"), _door_item("us-gaap:B", "fB"),
             _door_item("us-gaap:A", "fA"), _door_item("us-gaap:B", "fB")],
            source_id=_ACC, store=_Counting(), filing_provider=_CountingProvider(), text_parts=parts_for([_door_item("us-gaap:A", "fA"), _door_item("us-gaap:B", "fB"),
             _door_item("us-gaap:A", "fA"), _door_item("us-gaap:B", "fB")])).facts
    finally:
        xa.prepare = real
    assert len(out) == 4
    assert len(calls) == 1, f"the filing was parsed {len(calls)}x for one event"


def test_the_REMOVED_public_name_is_not_taught_to_a_future_caller():
    """The public name is `attach_event_xbrl`; the helper is private. A comment
    or error message naming the REMOVED public name sends the next reader
    looking for a function that no longer exists.

    The banned string is BUILT here rather than written out: spelling it in this
    docstring made the check match its own explanation — the fifth time a test
    of mine has done that."""
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1]
    offenders = []
    banned = "verify" + "_and_attach"          # never written literally
    for path in sorted(root.rglob("*.py")):
        for n, line in enumerate(path.read_text().splitlines(), 1):
            if banned in line.replace("_" + banned, ""):
                offenders.append(f"{path.name}:{n}")
    assert not offenders, f"the removed public name survives at: {offenders}"


def test_the_key_safety_class_is_fixed_in_V1_TOO_the_live_path():
    """The class sweep found the SAME raw-TypeError defect in the v1 contract,
    which is the LIVE writer input until the atomic switch. Fixing only v2 would
    have been 'fix the instance, not the class' for the sixth time."""
    from driver.core.prepared_fact import PreparedFactV1, RunInputV1, SchemaError
    with pytest.raises(SchemaError):
        PreparedFactV1.from_dict({"driver_name": "revenue", "driver_state": "reported",
                                  "quote": "q", 1: "x", "zz": "y"})
    with pytest.raises(SchemaError):
        RunInputV1.from_dict({"source_id": "a", "facts": [], 2: "y", "zz": "w"})


# ---------------------------------------------------------------------------
# #822 — the conflict identity must include EVERY field binding reads, and be
# order-free. Two rows differing only in a dimension LABEL used to accept or
# reject according to which one the reader happened to return first.
# ---------------------------------------------------------------------------

_AXIS, _MEMBER = "us-gaap:StatementBusinessSegmentsAxis", "x:FooMember"
_DIM_DOC = (f'<html {_XMLNS}><body><ix:header><ix:resources><xbrli:context id="c1"><xbrli:entity>'
            '<xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193</xbrli:identifier></xbrli:entity>'
            '<xbrli:period><xbrli:startDate>2024-01-01</xbrli:startDate>'
            '<xbrli:endDate>2024-06-30</xbrli:endDate></xbrli:period>'
            # THE MEMBER LIVES IN A SCENARIO (XBRL 2.1 §4.7.4). It used to sit
            # bare in the context — invalid markup standing in as the LAWFUL
            # positive control, so the control could not have caught a rule
            # that wrongly refused real filings.
            f'<xbrli:scenario><xbrldi:explicitMember dimension="{_AXIS}">'
            f'{_MEMBER}</xbrldi:explicitMember></xbrli:scenario>'
            '</xbrli:context></ix:resources></ix:header><ix:header><ix:resources><xbrli:unit id="u1">'
            '<xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit></ix:resources></ix:header>'
            '<p><ix:nonFraction id="f1" name="us-gaap:X" contextRef="c1" '
            'unitRef="u1" scale="6" decimals="-6">726</ix:nonFraction></p>'
            '</body></html>')


#: The namespaces this fixture's axis and member belong to. A graph row carries
#: these beside the qname because a prefix is an alias — `us-gaap:` in one
#: filing and `us-gaap:` in another need not name the same taxonomy — so the
#: binder compares (namespace URI, local name) and a row without both halves
#: parks. The real adapter decodes them from each record's composite id.
#:
#: DERIVED FROM THE DOCUMENT'S OWN MAP, never written out. I first hard-coded
#: both to the us-gaap URI because it read tidily — but `_MEMBER` is
#: `x:FooMember`, which `_DIM_DOC` binds to a DIFFERENT namespace, so the row
#: described a member the document does not contain and the fact parked. A
#: fixture that agrees with itself instead of with its document is not a
#: control. Taking both from `_FIXTURE_NS` makes that class of drift impossible.
_AXIS_NS = _FIXTURE_NS[_AXIS.partition(":")[0]]
_MEMBER_NS = _FIXTURE_NS[_MEMBER.partition(":")[0]]


def _ns_dim(axis, member, label):
    """A COMPLETE graph dimension row — all five `_DIM_KEYS`, with each
    namespace RESOLVED from the fixture's own prefix map rather than typed out.

    Every namespace a test dimension needs comes from here, so no test can
    quietly pair a qname with a URI the document does not bind to that prefix.
    A `KeyError` on an undeclared prefix is the point: it is the same failure a
    filing would produce, surfaced while writing the fixture instead of as a
    mysterious park later.
    """
    return {"axis": axis, "member": member, "label": label,
            "axis_namespace": _FIXTURE_NS[axis.partition(":")[0]],
            "member_namespace": _FIXTURE_NS[member.partition(":")[0]]}


def _dim_row(label, **over):
    r = dict(_door_row("f1"), dims=[_ns_dim(_AXIS, _MEMBER, label)])
    r.update(over)
    return r


def _sliced_item():
    """These tests are about the DIMENSION rules, so the element is incidental —
    but it must EXIST: `_DIM_DOC` is the document this fixture's provider
    actually serves, and it is the one that carries `f1`. Building the evidence
    from `_DOOR_DOC` named an element that document does not contain."""
    it = _door_item("us-gaap:X", "f1", doc=_DIM_DOC)
    it["fact"]["item"]["slice_parts"] = ["segment:foo"]
    it["member_refs"] = [{"axis": _AXIS, "member": _MEMBER,
                          "slice_part": "segment:foo"}]
    return it


def _attach_dim_rows(rows):
    class G:
        def get_xbrl_representation_count(self, s): return 1
        def get_xbrl_fact_dimensions(self, s, c): return GraphFactRows(rows=rows, exclusions=())
        def get_source_company_cik(self, s): return "0000320193"

    class P:
        def get_filing_document(self, s): return _DIM_DOC

    item = _sliced_item()
    return attach_event_xbrl([item], source_id=_ACC, store=G(),
                             filing_provider=P(), text_parts=parts_for([item]))




import itertools  # noqa: E402
from driver.core.driver_neo4j_adapter import GraphFactRows


def test_rows_differing_only_in_a_dimension_LABEL_park_in_EVERY_order():
    """The measured defect: [Foo, Bar] was ACCEPTED and [Bar, Foo] REJECTED.
    Two rows that disagree about a field binding reads are a conflict, and a
    conflict must not be settled by which one the reader returned first."""
    from driver.core.prepared_fact_v2 import ProductionValidationError
    rows = [_dim_row("Foo"), _dim_row("Bar")]
    for order in itertools.permutations(rows):
        _refused(_attach_dim_rows(list(order)), ProductionValidationError,
                 "CONFLICTING facts for this concept")


def test_rows_differing_only_in_a_dimension_NAMESPACE_park_in_EVERY_order():
    """THE SEQ-62 DEFECT, pinned at the public door where it was reproduced.

    Two rows naming the same axis and member SPELLING under DIFFERENT
    taxonomies are different dimensions, so a filing offering both disagrees
    with itself and the fact must park. The conflict identity had listed its
    dimension fields by hand and so never saw a namespace: the two rows looked
    identical, collapsed to one, and `[correct, wrong]` ATTACHED while
    `[wrong, correct]` did not — the answer decided by the order the graph
    happened to return rows in.

    Both orders are asserted because a one-order test passes on the very bug it
    is named for; the unit-level signature check upstream cannot see this,
    since only the real door does the collapsing.
    """
    from driver.core.prepared_fact_v2 import ProductionValidationError
    wrong = _dim_row("Foo")
    wrong["dims"] = [dict(wrong["dims"][0],
                          axis_namespace=_FIXTURE_NS["dimns"])]
    for order in itertools.permutations([_dim_row("Foo"), wrong]):
        _refused(_attach_dim_rows(list(order)), ProductionValidationError,
                 "CONFLICTING facts for this concept")


def test_IDENTICAL_complete_rows_still_collapse_in_every_order():
    """POSITIVE CONTROL — over-tightening would park a filing that simply
    returns the same row twice. It is the twin of the namespace park above:
    a "fix" that made every row distinct would satisfy that test by destroying
    collapsing altogether, and only this one would notice."""
    rows = [_dim_row("Foo"), _dim_row("Foo")]
    for order in itertools.permutations(rows):
        assert len(_attached(_attach_dim_rows(list(order)))) == 1


def test_a_SINGLE_lawful_dimensional_row_still_attaches():
    """The second positive control: the fixture itself must be able to pass,
    or every park above proves nothing."""
    assert len(_attached(_attach_dim_rows([_dim_row("Foo")]))) == 1


def test_the_row_signature_covers_EVERY_field_binding_reads():
    """Derived from `_ROW_FIELDS`, so a new row field cannot be silently left
    out of the conflict identity — the previous signature named six fields and
    omitted the period AND the dimensions."""
    from driver.core import xbrl_attach as xa
    base = xa._checked_row(_dim_row("Foo"))
    for field in xa._ROW_FIELDS:
        if field == "dims":
            # EVERY DIMENSION FIELD, ONE AT A TIME, DERIVED FROM `_DIM_KEYS`.
            # This branch used to vary the LABEL alone, so it certified "dims
            # is covered" while four of the five fields went unchecked — which
            # is precisely why it stayed green through the defect where the
            # signature omitted both namespaces and two rows differing only in
            # taxonomy collided. One changed field per pass is what makes each
            # field individually load-bearing.
            for key in xa._DIM_KEYS:
                dim = dict(base["dims"][0])
                # A LAWFUL DIFFERENT VALUE for any of the five: a QName keeps
                # its shape (`-other` is an ordinary NCName character) and a
                # namespace is an opaque string. No per-key table, so a sixth
                # `_DIM_KEYS` field is covered the moment it is added.
                dim[key] = dim[key] + "-other"
                other = xa._checked_row(_dim_row("Foo", dims=[dim]))
                assert xa._row_signature(base) != xa._row_signature(other), \
                    f"the conflict identity ignores the dimension {key!r}"
            continue
        elif field == "period_type":
            # NO SKIP. I had written `continue` here, so a test called "covers
            # EVERY field binding reads" silently covered nine of ten.
            other = xa._checked_row(_dim_row("Foo", period_type="instant",
                                              end_date=None))
        else:
            changed = {"fact_id": "f2", "value": "999,000,000", "unit_ref": "u2",
                       "unit_name": "shares", "is_divide": "1",
                       "context_id": "c2", "start_date": "2024-01-02",
                       "end_date": "2024-07-02",
                       # A DIFFERENT TAXONOMY, or a different concept under the
                       # same one, is a different FACT — so the conflict
                       # identity must separate them too.
                       "concept_namespace": "http://example.org/other-taxonomy",
                       "graph_concept_qname": "us-gaap:Y"}[field]
            other = xa._checked_row(_dim_row("Foo", **{field: changed}))
        assert xa._row_signature(base) != xa._row_signature(other), \
            f"the conflict identity ignores {field!r}"


def test_the_row_signature_is_DIMENSION_ORDER_free():
    """Two readings of one fact that list the same dimensions in a different
    order are the SAME fact, not a conflict."""
    from driver.core import xbrl_attach as xa
    d1 = _ns_dim(_AXIS, _MEMBER, "Foo")
    d2 = _ns_dim("srt:StatementGeographicalAxis", "x:EU", "Europe")
    a = xa._checked_row(_dim_row("Foo", dims=[d1, d2]))
    b = xa._checked_row(_dim_row("Foo", dims=[d2, d1]))
    assert xa._row_signature(a) == xa._row_signature(b)


# ---------------------------------------------------------------------------
# #822 REMAINDER — LAWFUL EQUIVALENCE. Two spellings of the same fact must not
# read as a conflict: the signature has to compare what BINDING compares.
# ---------------------------------------------------------------------------

def _sig(**over):
    from driver.core import xbrl_attach as xa
    return xa._row_signature(xa._checked_row(_dim_row("Foo", **over)))


def test_every_BLANK_fact_id_form_is_ONE_fact_not_a_conflict():
    """`bind_graph_fact` chooses its path on `(id or '').strip()`, so null, empty
    and whitespace are the SAME claim: this element carries no id."""
    forms = [_sig(fact_id=f) for f in (None, "", "   ", "\t")]
    assert len(set(forms)) == 1, "blank id forms read as different facts"


def test_an_INSTANTS_unused_end_date_is_not_part_of_its_identity():
    """F5 reconcile: the stored-"null" alias is the ADAPTER'S now — it emits
    None, so exactly ONE lawful checked-row form remains. The identity claim
    survives as: the unread end field contributes nothing (the signature of
    the lawful form equals itself with the field absent-by-None)."""
    forms = [_sig(period_type="instant", end_date=None)]
    assert len(set(forms)) == 1


def test_a_DURATIONS_end_date_IS_part_of_its_identity():
    """POSITIVE CONTROL — the field is only ignorable where it is unread."""
    assert _sig(end_date="2024-07-01") != _sig(end_date="2024-08-01")


def test_signed_zero_spellings_are_the_SAME_number_not_a_conflict():
    """IDENTITY CHANGE (SEQ 265 C / 268): the old assert equated an
    UNGROUPED spelling with the grouped one — impossible under the frozen
    lexical contract (the writer always groups; census zero) — and its
    first replacement was a tautology. The lawful two-spellings pair the
    writer really emits is signed zero: "0" and "-0" are one number, so
    their signatures must agree. Different numbers still conflict and
    unparseable strings stay distinct."""
    assert _sig(value="0") == _sig(value="-0")
    assert _sig(value="726,000,000") != _sig(value="726,000,001")
    # two DIFFERENT unparseable strings must stay distinct, not collapse to None
    assert _sig(value="abc") != _sig(value="xyz")


def test_a_REPEATED_dimension_AXIS_is_refused_before_any_graph_read():
    """One context carries at most one member per axis, so a claim naming the
    same axis twice is impossible on its face and must die with the other
    ref-shape checks — it was reaching `get_xbrl_representation_count`."""
    from driver.core.prepared_fact_v2 import SchemaError
    ax = "us-gaap:StatementBusinessSegmentsAxis"
    item = _sliced_item()
    item["member_refs"] = [{"axis": ax, "member": "x:A", "slice_part": "segment:a"},
                           {"axis": ax, "member": "x:B", "slice_part": "segment:b"}]
    _refused(attach_event_xbrl([item], source_id=_ACC, store=_NeverRead(),
                               filing_provider=_NeverFetched(),
                               text_parts=parts_for([item])),
             SchemaError, "names the same axis more than once")


def test_TWO_DIFFERENT_axes_are_still_lawful():
    """POSITIVE CONTROL — multi-axis facts are ordinary and must still pass."""
    from driver.core.prepared_fact_v2 import ITEM_FIELDS, PreparedFactV2
    from driver.core import prepared_fact_v2 as _p2
    refs = [{"axis": "us-gaap:StatementBusinessSegmentsAxis", "member": "x:A",
             "slice_part": "segment:a"},
            {"axis": "srt:StatementGeographicalAxis", "member": "x:EU",
             "slice_part": "geography:europe"}]
    item = {k: None for k in ITEM_FIELDS}
    item.update(driver_name="revenue", driver_state="reported", quote="q",
                measurement_raw_spans=[], slice_parts=[], time_type="instant",
                period_end_date="2024-06-30",
                # F12: an XBRL-backed fact states ONE reported value — the
                # owner now requires the level pair, so this minimal fixture
                # carries the smallest lawful one (its subject is unchanged).
                level_unit="usd",
                level_low={"value": Decimal(1), "scale_multiplier": Decimal(1),
                           "unit_scale_evidence": None},
                level_high={"value": Decimal(1), "scale_multiplier": Decimal(1),
                            "unit_scale_evidence": None})
    f = PreparedFactV2._build(
        {"fact_type": "metric", "part_ref": "p", "occurrence_in_part": None,
         "per_x": None, "item": item},
        {"xbrl_concept_raw": "us-gaap:X", "member_refs": refs})
    assert len(f.item.member_refs) == 2


# ---------------------------------------------------------------------------
# #822 SECOND REVIEW — the ROW side of rules I had fixed only on the CLAIM side,
# plus strict date shapes at the row boundary.
# ---------------------------------------------------------------------------

def test_a_graph_ROW_repeating_a_dimension_axis_is_refused():
    """I refused a repeated axis in the CLAIM and left the ROW
    accepting it — the instance, not the class. CENSUS 2026-07-28: 2,206,183
    multi-axis contexts, ZERO repeat an axis, so this costs no recall."""
    from driver.core import xbrl_attach as xa
    from driver.core.prepared_fact_v2 import ProductionValidationError
    # ASKED AT THE RULE'S CURRENT OWNER. `_checked_row` used to compare raw
    # prefix SPELLINGS; the law moved to `_row_expanded_dims`, which compares
    # EXPANDED axes and so also catches two different prefixes bound to one
    # namespace. This test kept pointing at the old boundary and passed only
    # because the weaker rule happened to live there — so it is re-aimed, NOT
    # satisfied by restoring the spelling check.
    dims = [{"axis": _AXIS, "member": "x:A", "label": "A",
             "axis_namespace": _AXIS_NS, "member_namespace": _MEMBER_NS},
            {"axis": _AXIS, "member": "x:B", "label": "B",
             "axis_namespace": _AXIS_NS, "member_namespace": _MEMBER_NS}]
    # THE ROWS ARE OTHERWISE COMPLETE, so the refusal below comes from the
    # repeated axis this test is named for and not from a missing field —
    # `_checked_row` accepting them first is what proves that.
    checked = xa._checked_row(_dim_row("Foo", dims=dims))
    with pytest.raises(ProductionValidationError):
        xa._row_expanded_dims(checked)


def test_TWO_DIFFERENT_axes_on_a_row_are_still_lawful():
    """POSITIVE CONTROL — multi-axis rows are ordinary (2.2M of them live)."""
    from driver.core import xbrl_attach as xa
    dims = [_ns_dim(_AXIS, "x:A", "A"),
            _ns_dim("srt:StatementGeographicalAxis", "x:EU", "Europe")]
    checked = xa._checked_row(_dim_row("Foo", dims=dims))
    assert len(checked["dims"]) == 2
    # THROUGH THE SAME BOUNDARY as the refusal twin above, so the two are
    # answered by one rule: distinct axes survive exactly where a repeated one
    # is refused. A must-refuse proven at a door its must-allow never reaches
    # would leave that door free to refuse everything.
    assert len(xa._row_expanded_dims(checked)) == 2


@pytest.mark.parametrize("bad", ["20240101", "2024-1-1", "not-a-date",
                                 "2024-13-01", "2024-02-30", "224-04-01",
                                 "2024-01-01T00:00:00", " 2024-01-01"])
def test_an_INVALID_date_shape_is_refused_at_the_row_boundary(bad):
    """XML `xs:date` requires the hyphenated form, and `date.fromisoformat`
    accepts more than that. CENSUS 2026-07-28: 11,415 of 11,416 Periods carry a
    strict YYYY-MM-DD start; the ONE exception is `224-04-01`, and it does NOT
    have zero facts as recorded — it carries 34 numeric non-nil ones. They park
    either way (a malformed date can never equal a well-formed claim), so this
    changes WHERE they park, not WHETHER."""
    from driver.core import xbrl_attach as xa
    from driver.core.prepared_fact_v2 import ProductionValidationError
    with pytest.raises(ProductionValidationError):
        xa._checked_row(_dim_row("Foo", start_date=bad))


def test_LAWFUL_dates_still_pass_including_a_leap_day():
    """POSITIVE CONTROL — real calendar validation, not just a shape regex."""
    from driver.core import xbrl_attach as xa
    for good in ("2024-01-01", "2024-02-29", "2023-12-31"):
        assert xa._checked_row(_dim_row("Foo", start_date=good))


# ---------------------------------------------------------------------------
# #822 THIRD REVIEW — the rules must hold in the SHARED matcher and the LIVE v1
# path, not only in the staged v2 row check. Census receipt:
# .claude/plans/Drivers/WIP/Core_822_GraphCensus_2026-07-28.md
# ---------------------------------------------------------------------------

def test_the_SHARED_matcher_refuses_a_row_repeating_an_axis():
    """`match_xbrl_fact` compares `{(axis, member) for d in dims}` — a SET, so an
    IDENTICAL duplicated dimension collapses and the row matches. It is the
    shared matcher, so this is the LIVE v1 path too, not just staged v2."""
    from driver.core.slice_menu import match_xbrl_fact
    row = {"period_type": "duration", "start_date": "2024-01-01",
           "end_date": "2024-07-01",
           "dims": [{"axis": _AXIS, "member": "x:A", "label": "A"},
                    {"axis": _AXIS, "member": "x:A", "label": "A"}]}
    claim = {"time_type": "duration", "start": "2024-01-01",
             "end": "2024-06-30", "dims": {(_AXIS, "x:A")}}
    assert match_xbrl_fact(claim, [row]) is None


def test_the_SHARED_matcher_still_matches_a_LAWFUL_row():
    """POSITIVE CONTROL — the ordinary single-dimension row must still match."""
    from driver.core.slice_menu import match_xbrl_fact
    row = {"period_type": "duration", "start_date": "2024-01-01",
           "end_date": "2024-07-01",
           "dims": [{"axis": _AXIS, "member": "x:A", "label": "A"}]}
    claim = {"time_type": "duration", "start": "2024-01-01",
             "end": "2024-06-30", "dims": {(_AXIS, "x:A")}}
    assert match_xbrl_fact(claim, [row]) is not None


def test_the_LIVE_v1_contract_refuses_duplicate_member_refs():
    """v2 refuses a repeated axis in its claim; v1 — the contract the production
    writer actually consumes — accepted it."""
    from driver.core.prepared_fact import PreparedFactV1, SchemaError
    ref = {"axis": _AXIS, "member": "x:A", "slice_part": "segment:a"}
    with pytest.raises(SchemaError):
        PreparedFactV1(driver_name="d", driver_state="reported", quote="q",
                       xbrl_concept_raw="us-gaap:X", time_type="duration",
                       period_start_date="2024-01-01",
                       period_end_date="2024-06-30",
                       member_refs=[dict(ref), dict(ref)])


def test_the_LIVE_v1_contract_still_accepts_TWO_DIFFERENT_axes():
    """POSITIVE CONTROL — multi-axis facts are ordinary (2.2M live contexts)."""
    from driver.core.prepared_fact import PreparedFactV1
    f = PreparedFactV1(
        driver_name="d", driver_state="reported", quote="q",
        xbrl_concept_raw="us-gaap:X", time_type="duration",
        period_start_date="2024-01-01", period_end_date="2024-06-30",
        member_refs=[{"axis": _AXIS, "member": "x:A", "slice_part": "segment:a"},
                     {"axis": "srt:StatementGeographicalAxis", "member": "x:EU",
                      "slice_part": "geography:europe"}])
    assert len(f.member_refs) == 2


@pytest.mark.parametrize("bad", ["garbage", "20240101", "", "   ", "not-a-date",
                                 "2024-13-01"])
def test_an_INSTANTS_end_date_still_has_a_lawful_SHAPE(bad):
    """Skipping the date check on the instant branch let ANY text through. The
    census says every stored end_date is a strict ISO date or the literal
    "null" — there is no third shape, so arbitrary text is not one of them."""
    from driver.core import xbrl_attach as xa
    from driver.core.prepared_fact_v2 import ProductionValidationError
    with pytest.raises(ProductionValidationError):
        xa._checked_row(_dim_row("Foo", period_type="instant", end_date=bad))


# ---------------------------------------------------------------------------
# #822 FOURTH REVIEW — one owner for the axis rule, and shapes the live data
# actually carries. Census: Core_822_GraphCensus_2026-07-28.md
# ---------------------------------------------------------------------------

def test_the_repeated_axis_rule_has_EXACTLY_ONE_owner():
    """I added this rule in three separate review rounds and ended with FOUR
    copies — the v1 claim, the v2 claim, the v2 row and the shared matcher.
    DERIVED scan: nobody may re-implement the uniqueness test locally."""
    import ast
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1]
    owner = root / "core" / "slice_menu.py"
    offenders, scanned = [], 0
    for path in sorted(root.rglob("*.py")):
        if path.name.startswith("test_") or path == owner:
            continue
        scanned += 1
        for node in ast.walk(ast.parse(path.read_text())):
            # THE RULE'S FINGERPRINT, not "any uniqueness test": collecting the
            # `axis` key out of a sequence is what you only do in order to check
            # the axes. My first version matched `len(x) != len(set(x))`
            # anywhere and flagged unrelated checks in `locator.py` — too broad,
            # the same crude-check habit this suite keeps catching.
            if not isinstance(node, (ast.ListComp, ast.GeneratorExp,
                                     ast.SetComp)):
                continue
            elt = node.elt
            # (a) collecting the axes — the uniqueness rule's fingerprint
            if (isinstance(elt, ast.Subscript)
                    and isinstance(getattr(elt, "slice", None), ast.Constant)
                    and elt.slice.value == "axis"):
                offenders.append(f"{path.name}:{node.lineno} (axis list)")
            # (b) building the (axis, member) PAIR SET — the same rule's other
            # half, and it was copied three times: the shared matcher, the v2
            # attach path and the live v1 CLI.
            if isinstance(elt, ast.Tuple) and len(elt.elts) == 2 and all(
                    isinstance(e, ast.Subscript)
                    and isinstance(getattr(e, "slice", None), ast.Constant)
                    for e in elt.elts) and [e.slice.value for e in elt.elts] == \
                    ["axis", "member"]:
                offenders.append(f"{path.name}:{node.lineno} (pair set)")
    assert scanned >= 15, f"the scan covered only {scanned} modules"
    assert not offenders, f"the axis rule is re-implemented at: {offenders}"


@pytest.mark.parametrize("end", ["2024-06-30", "2024-01-01"])
def test_an_INSTANT_end_date_may_not_be_a_real_date(end):
    """LIVE DATA: all 3,058 instants carry the literal "null" — not one carries
    a date. I had allowed a real date there, inventing a shape the graph does
    not have; an unseen shape parks."""
    from driver.core import xbrl_attach as xa
    from driver.core.prepared_fact_v2 import ProductionValidationError
    with pytest.raises(ProductionValidationError):
        xa._checked_row(_dim_row("Foo", period_type="instant", end_date=end))


def test_the_ONE_lawful_instant_end_date_form_passes():
    """POSITIVE CONTROL (F5 reconcile): the adapter owns the stored-"null"
    alias and emits None — exactly ONE lawful form reaches the checked row;
    the retired sentinel parks (the F5 twin in round11)."""
    from driver.core import xbrl_attach as xa
    assert xa._checked_row(_dim_row("Foo", period_type="instant", end_date=None))


def test_the_SPLIT_axis_helper_cannot_come_back():
    """`has_repeated_axis` was removed, not deprecated: two separable halves are
    unsafe because building the pair set is exactly what hides a repeat. This
    pins its absence so a future edit cannot quietly reintroduce the trap."""
    from driver.core import slice_menu
    assert not hasattr(slice_menu, "has_repeated_axis")
    assert "has_repeated_axis" not in slice_menu.__all__
    assert "has_repeated_axis" not in \
        __import__("inspect").getsource(slice_menu)


def test_the_pair_set_is_FROZEN():
    """A verified dimension identity must not be alterable after the check that
    made it trustworthy."""
    from driver.core.slice_menu import axis_member_pairs
    pairs = axis_member_pairs([{"axis": "a", "member": "m"}])
    assert isinstance(pairs, frozenset)
    with pytest.raises(AttributeError):
        pairs.add(("b", "n"))


# --- #823 class-wide: the PUBLIC DOOR is a constructor path too -------------

def test_823_the_attached_fact_survives_mutation_of_the_callers_item():
    """`attach_event_xbrl` is a public construction path. Mutating the caller's
    own item dict after attaching must not reach the returned fact."""
    item = _door_item("us-gaap:A", "fA")
    out = attach_event_xbrl([item], source_id=_ACC, store=_Counting(),
                            filing_provider=_CountingProvider(), text_parts=parts_for([item])).facts[0][1]
    item["fact"]["item"]["slice_parts"].append("segment:injected")
    item["fact"]["item"]["level_low"]["scale_multiplier"] = "TAMPERED"
    item["member_refs"].append({"axis": "x", "member": "y", "slice_part": "z"})
    assert out.item.slice_parts == ()
    assert out.item.level_low["scale_multiplier"] != "TAMPERED"
    assert out.item.member_refs == ()


def test_823_the_attached_fact_is_not_mutable_THROUGH_itself():
    out = attach_event_xbrl([_door_item("us-gaap:A", "fA")], source_id=_ACC,
                            store=_Counting(),
                            filing_provider=_CountingProvider(), text_parts=parts_for([_door_item("us-gaap:A", "fA")])).facts[0][1]
    for attempt in (lambda: out.item.level_low.__setitem__("value", 1),
                    lambda: out.item.slice_parts.append("x"),
                    lambda: setattr(out, "fact_type", "guidance"),
                    lambda: setattr(out.item, "quote", "x")):
        with pytest.raises((AttributeError, TypeError)):
            attempt()


def test_823_the_run_input_fact_collection_is_not_mutable_through_itself():
    from driver.core.prepared_fact_v2 import RunInputV2
    ri = RunInputV2(source_id=_ACC, facts=[])
    with pytest.raises(AttributeError):
        ri.facts.append("x")
    with pytest.raises(AttributeError):
        ri.facts = ()


@pytest.mark.parametrize("bad", [(), tuple(), ("a",)])
def test_823_the_run_input_did_NOT_widen_to_accept_a_tuple(bad):
    """Freezing first turned the list into a tuple, so the check had to accept
    tuples — silently widening a list-only input contract. Storage as a tuple is
    a decision we make, never a licence to be handed one."""
    from driver.core.prepared_fact_v2 import RunInputV2, SchemaError
    with pytest.raises(SchemaError):
        RunInputV2(source_id=_ACC, facts=bad)


# --- #823 reopened: TOCTOU, all five slots, mapping views, derived inventory -

def test_823_a_provider_CALLBACK_cannot_mutate_the_refs_it_was_handed():
    """The filing provider is CALLER-SUPPLIED code that runs BETWEEN validation
    and use. The door carried the caller's own refs list forward, so a callback
    could mutate it and a mutated entry escaped as a raw KeyError."""
    item = _door_item("us-gaap:A", "fA")

    class Hostile(_CountingProvider):
        def get_filing_document(self, s):
            item["member_refs"].append({"not": "a ref"})   # mid-call mutation
            return super().get_filing_document(s)

    facts = _attached(attach_event_xbrl(
        [item], source_id=_ACC, store=_Counting(), filing_provider=Hostile(),
        text_parts=parts_for([item])))
    assert facts[0].item.member_refs == ()


def test_823_ALL_FIVE_numeric_slots_are_frozen_and_caller_proof():
    """Only the two level slots had been proved; the item holds five."""
    from decimal import Decimal
    from driver.core.prepared_fact_v2 import ITEM_FIELDS, PreparedItemV2
    slots = {n: {"value": Decimal("1"), "scale_multiplier": Decimal(1),
                 "unit_scale_evidence": None}
             for n in ("level_low", "level_high", "change_value",
                       "comparison_low", "comparison_high")}
    d = {k: None for k in ITEM_FIELDS}
    # THE VERY OBJECTS, not copies. An earlier version passed `dict(v)` in and
    # then mutated `slots[n]` — a dict the object had never seen — so the test
    # could not have failed however broken the freezing was. Masked probe.
    d.update(driver_name="d", driver_state="reported", quote="q",
             measurement_raw_spans=[], slice_parts=[], level_unit="count",
             change_unit="count", level_shape_hint="point",
             comparison_shape_hint="point", **slots)
    item = PreparedItemV2(**d)
    for name, original in slots.items():
        assert getattr(item, name) is not original, f"{name} aliases the caller"
        original["scale_multiplier"] = Decimal(999)        # the SAME dict
        got = getattr(item, name)
        assert got["scale_multiplier"] == Decimal(1), name
        with pytest.raises(TypeError):
            got["value"] = Decimal(2)


def test_823_frozen_mappings_are_READ_ONLY_VIEWS_not_copies_of_convenience():
    from decimal import Decimal
    from types import MappingProxyType

    from driver.core.prepared_fact_v2 import ITEM_FIELDS, PreparedItemV2
    # BOTH inbound shapes, because they fail differently. A plain dict is the
    # obvious one. An ALREADY-frozen MappingProxyType is the dangerous one: it
    # is NOT a `dict` instance, so a freeze testing `isinstance(v, dict)` alone
    # would hand the caller's own VIEW straight through — read-only to us while
    # still live to them. Passing only a plain dict never exercises that branch.
    for wrap in (dict, MappingProxyType):
        backing_slot = {"value": Decimal("1"), "scale_multiplier": Decimal(1),
                        "unit_scale_evidence": None}
        backing_proof = {"polarity": "favorable", "basis": "source_framing",
                         "evidence": "e", "sentence": "s"}
        d = {k: None for k in ITEM_FIELDS}
        d.update(driver_name="d", driver_state="reported", quote="q",
                 measurement_raw_spans=[], slice_parts=[], level_unit="count",
                 level_low=wrap(backing_slot), level_high=wrap(backing_slot),
                 level_shape_hint="point", polarity_proof=wrap(backing_proof))
        item = PreparedItemV2(**d)
        assert isinstance(item.level_low, MappingProxyType), wrap
        assert isinstance(item.polarity_proof, MappingProxyType), wrap
        assert isinstance(item.measurement_raw_spans, tuple), wrap
        # A MappingProxyType is a VIEW. The freeze must COPY, so mutating the
        # caller's backing dict changes nothing here — whichever shape arrived.
        backing_slot["scale_multiplier"] = Decimal(999)
        backing_proof["polarity"] = "lower_favorable"
        assert item.level_low["scale_multiplier"] == Decimal(1), wrap
        assert item.polarity_proof["polarity"] == "favorable", wrap


def test_823_DERIVED_inventory_every_public_v2_dataclass_is_deeply_frozen():
    """The property the removed no-op loop only APPEARED to give: derived from
    the module's own dataclasses, so a mutable field added later fails here."""
    import dataclasses
    from decimal import Decimal
    from types import MappingProxyType

    from driver.core import prepared_fact_v2 as p2
    # DERIVED FROM THE MODULE'S OWN PUBLIC DATACLASSES (W15 reconcile,
    # recorded): `__all__` is the DISTRIBUTION surface and shrank at W15;
    # freeze coverage is the COVERAGE surface and must not shrink with it —
    # PreparedItemV2 left the wildcard export but stays a public dataclass
    # this check owns. Non-underscore names defined IN this module only, so
    # imported names still cannot drift in.
    classes = [obj for n, obj in vars(p2).items()
               if not n.startswith("_") and isinstance(obj, type)
               and dataclasses.is_dataclass(obj)
               and obj.__module__ == p2.__name__]
    assert classes, "no public dataclass found in the module"
    d = {k: None for k in p2.ITEM_FIELDS}
    d.update(driver_name="d", driver_state="reported", quote="q",
             measurement_raw_spans=["a"], slice_parts=["segment:a"],
             level_unit="count", level_shape_hint="point",
             level_low={"value": Decimal("1"), "scale_multiplier": Decimal(1),
                        "unit_scale_evidence": None},
             level_high={"value": Decimal("1"), "scale_multiplier": Decimal(1),
                         "unit_scale_evidence": None})
    built = [p2.PreparedItemV2(**d)]
    built.append(p2.PreparedFactV2(fact_type="metric", part_ref="p",
                                   occurrence_in_part=None, per_x=None,
                                   item=built[0]))
    built.append(p2.RunInputV2(source_id="acc-1", facts=[]))
    # THE COMPARISON THAT WAS MISSING. Deriving the public list proves nothing
    # on its own — it has to be TIED to the objects actually exercised below.
    # Without this, a public dataclass added later is derived into `classes`,
    # never built, and the loop simply does not test it: green, and blind.
    assert {type(o) for o in built} == set(classes), (
        "the public dataclasses in __all__ are not the ones tested here — "
        "construct the new class into `built` so the freeze check covers it")
    for obj in built:
        for f in dataclasses.fields(obj):
            v = getattr(obj, f.name)
            assert not isinstance(v, (list, dict, set, bytearray)), \
                f"{type(obj).__name__}.{f.name} is mutable: {type(v).__name__}"
            # Only the proxy branch proves anything WE did; the line above
            # already rules out every mutable container, and "a tuple has no
            # .append" is a fact about Python, not about this contract.
            if isinstance(v, MappingProxyType):
                with pytest.raises(TypeError):
                    v["x"] = 1


def test_TWO_EVENTS_are_INDEPENDENT_each_doing_its_own_work_once():
    """#827 STEP 2 — the two-event I/O pattern, the one shape no door test
    exercised: every other test calls the door ONCE.

    Empty, single, repeated-concept and multi-concept events are already
    covered (`..._NO_xbrl_items_is_lawful`, `..._FOUR_items_across_TWO_
    concepts_read_everything_ONCE_per_event`). What none of them can show is
    that nothing LEAKS ACROSS the event boundary: the work-once caching that
    makes one event cheap must not make the SECOND event reuse the first
    event's document, CIK or rows, and each result must carry its own
    source_id.

    Reuses the existing fixture owners (`_door_item`, `_Counting`,
    `_CountingProvider`, `parts_for`) — no second builder.
    """
    from driver.core.xbrl_attach import attach_event_xbrl
    store, provider = _Counting(), _CountingProvider()
    first = [_door_item("us-gaap:A", "fA")]
    second = [_door_item("us-gaap:B", "fB"), _door_item("us-gaap:B", "fB")]
    other_acc = "0000006201-26-000032"
    assert other_acc != _ACC, "the two events must be different sources"

    r1 = attach_event_xbrl(first, source_id=_ACC, store=store,
                           filing_provider=provider, text_parts=parts_for(first))
    after_first = (provider.fetches, store.representation, store.cik,
                   list(store.row_reads))
    r2 = attach_event_xbrl(second, source_id=other_acc, store=store,
                           filing_provider=provider,
                           text_parts=parts_for(second))

    # each event did its OWN work exactly once — the second is not served
    # from the first event's cache, and does not pay twice for its own repeat
    assert after_first == (1, 1, 1, ["us-gaap:A"]), after_first
    assert (provider.fetches, store.representation, store.cik) == (2, 2, 2), \
        (provider.fetches, store.representation, store.cik)
    assert store.row_reads == ["us-gaap:A", "us-gaap:B"], store.row_reads

    # each result is stamped with ITS OWN source_id and carries its own facts
    assert (r1.source_id, r2.source_id) == (_ACC, other_acc)
    assert [i for i, _f in r1.facts] == [0]
    assert [i for i, _f in r2.facts] == [0, 1]
    assert r1.preflight_outcomes == () and r2.preflight_outcomes == ()


# ---- ROUND 6 ITEM 7: the fact id is an identity, not a hint ---------------

def test_827R6_a_PADDED_fact_id_is_a_DIFFERENT_id_and_order_cannot_decide():
    """`bind_graph_fact` looks the id up EXACTLY as stored — a padded id is a
    different id, not a typo to repair. The row-identity key nevertheless
    `.strip()`-ed it, so `f1` and ` f1` folded into ONE fact while binding to
    DIFFERENT elements, and WHICH of them survived depended on the order the
    graph happened to return the rows in.

    Blankness is the only thing stripping may decide: null, empty and
    whitespace all mean "this element carries no id" and stay one claim."""
    import itertools
    seen = set()
    for rows in itertools.permutations([_dim_row("Foo"),
                                        _dim_row("Foo", fact_id=" f1")]):
        res = _attach_dim_rows(list(rows))
        seen.add((len(res.facts), len(res.preflight_outcomes)))
    assert len(seen) == 1, f"the outcome depended on row order: {seen}"

    blank = {_row_signature(_dim_row("Foo", fact_id=b))[
                 _ROW_FIELDS.index("fact_id")]
             for b in (None, "", "   ")}
    assert blank == {""}, f"blank ids must stay ONE claim, got {blank}"
    padded = {_row_signature(_dim_row("Foo", fact_id=i))[
                  _ROW_FIELDS.index("fact_id")]
              for i in ("f1", " f1", "f1 ")}
    assert len(padded) == 3, f"padded ids must stay DISTINCT, got {padded}"


def test_827R7_UNICODE_whitespace_is_NOT_a_blank_fact_id():
    """`raw_id.strip()` decided blankness with PYTHON's whitespace set, which
    includes U+000B, U+000C, U+00A0 and U+3000 — none of them XML 1.0 S. So a
    stored id made only of those folded into the SAME identity as "this element
    carries no id": two different claims about the filing, collapsed into one,
    and the binder then bound it through the identity fallback — a law that
    applies ONLY when the element genuinely has no id.

    The lawful fold is re-pinned beside it: null, empty and XML-space ARE one
    claim, and that must not change."""
    idx = _ROW_FIELDS.index("fact_id")

    def sig(fid):
        return _row_signature(_dim_row("Foo", fact_id=fid))[idx]

    for label, ws in [("NBSP", " "), ("VT", "\x0b"), ("FF", "\x0c"),
                      ("ideographic", "　")]:
        assert sig(ws) != sig(""), \
            f"{label}-only id folded into the blank identity"
        assert sig(ws) == ws, f"{label}-only id was not kept exactly"

    assert {sig(b) for b in (None, "", " ", "\t\r\n")} == {""}, \
        "XML-blank ids must stay ONE claim"


# ---- #827 B1 packet 1 (SEQ 275): the attach door's source-id diagnostic ----

def test_827B1_attach_source_id_diagnostic_states_local_truth_not_the_law():
    """The event door validates source_id FIRST (before any I/O), via the ONE
    owner driver_ids.valid_source_id; its message may not restate the owner's
    grammar. Exact anchor = reintroduction detector. store/provider are never
    touched: the raise precedes all reads."""
    with pytest.raises(SchemaError,
                       match=r"^attach_event_xbrl: source_id is invalid$"):
        attach_event_xbrl([], source_id="x:y", store=None,
                          filing_provider=None, text_parts=None)


def test_W15_the_declared_export_surface_is_exactly_the_retained_set():
    """W15: `__all__` is the DISTRIBUTION decision (wildcard export), and it
    is exactly the frozen 11 — the 8 with production consumers + the 3
    inactive clean-v2 component doors. Set equality alone is insufficient
    (a duplicate survives it, reproduced on the board), so BOTH membership
    and length are asserted. Coverage obligations live in the separate
    input inventory and did NOT move (split_slice_part stays covered
    there; export != inventory)."""
    from driver.core import prepared_fact_v2 as p2
    EXPECTED_11 = {"SchemaError", "ProductionValidationError",
                   "SourceUnavailable", "OUTCOME_CLASSES", "NUMERIC_SLOTS",
                   "PreparedFactV2", "ITEM_FIELDS", "verify_occurrence",
                   "RunInputV2", "to_stored_fact", "validate_via_production"}
    assert set(p2.__all__) == EXPECTED_11
    assert len(p2.__all__) == 11               # no duplicates
    # an explicit import of an unlisted name still succeeds (round-3 proof):
    from driver.core.prepared_fact_v2 import split_slice_part  # noqa: F401


def test_W13_B_D4_a_NON_EMPTY_raw_dict_fact_list_is_forwarded_and_constructed():
    """W13 route B·D4 (dep W10): every pre-existing test used facts:[] — the
    forwarding line never executed. A NON-EMPTY raw dict list is forwarded
    through Door B and comes back CONSTRUCTED."""
    from decimal import Decimal
    from driver.core.prepared_fact_v2 import (ITEM_FIELDS, PreparedFactV2,
                                              RunInputV2)
    item = {k: None for k in ITEM_FIELDS}
    item.update(driver_name="revenue", driver_state="reported",
                quote="q", measurement_raw_spans=[], slice_parts=[])
    run = RunInputV2.from_dict({
        "source_id": "acc-1", "calendar_override": False,
        "facts": [{"fact_type": "metric", "part_ref": "p1",
                   "occurrence_in_part": None, "per_x": None, "item": item}]})
    assert len(run.facts) == 1
    assert isinstance(run.facts[0], PreparedFactV2)


def test_F14_an_event_wide_failure_reaches_EVERY_item():
    """F14 (#827) scope control: one cause, not one victim — the event-wide
    fan-out stamps every affected index (the count guard, on a TWO-item
    event), each keeping its own index."""
    res = _run([_item(), _item()], store=Graph(xbrl_nodes=2))
    assert [o["index"] for o in res.preflight_outcomes] == [0, 1]
    assert all("reports 2 XBRL representation(s)" in o["detail"]
               for o in res.preflight_outcomes)
