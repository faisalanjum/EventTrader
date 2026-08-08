"""ROUND-8 corrections — RED-first, one failing test per reviewer finding.

Every test here was written BEFORE its fix and reproduced against live data
first (probe transcripts in the round-8 record). The eight findings:

  1  semantic unit map        graph 'shares' vs filing 'xbrli:shares' -> every
                              share and per-share fact failed to bind
  2  unit MEANING vs level_unit   a real $5.262bn fact was accepted as `count`
  3  duplicate xbrli:unit ids  silently last-wins (contexts already abstain)
  4  ONE exclusive-date rule   `_plus_day` existed twice, byte-identical
  5  ASCII XML-integer parse   int() accepts 1_0, full-width １２, Arabic ٦,
                              NBSP-padded — none legal in XML
  6  Option C                  injected filing provider · non-circular hash ·
                              CIK from CORE's graph, never the provider
  7  dated measurements        the id-count comment carried an undated,
                              scope-dropped number
  8  the real path             USD / shares / EPS through the COMPLETE
                              the public event door, not the low-level binder
"""
import pytest

from driver.core.test_round10_event_boundary import (_FIXTURE_NS, _XMLNS,
                                                     parts_for)

from driver.relocation import exact_numbers as XN
from driver.relocation.inline_html import (bind_graph_fact, prepare, reconcile,
                                           xml_integer)
from driver.core.prepared_fact_v2 import SchemaError
from driver.core.xbrl_attach import _default_outcome, attach_event_xbrl

# --------------------------------------------------------------------------
# 5. ONE ASCII XML-integer parser
# --------------------------------------------------------------------------

@pytest.mark.parametrize("raw,want", [
    ("6", 6), ("+6", 6), (" 6 ", 6), ("\n6\t", 6), ("-3", -3), ("0", 0),
    ("012", 12),                       # leading zeros are lawful xsd:integer
])
def test_xml_integer_accepts_every_lawful_form(raw, want):
    assert xml_integer(raw) == want


@pytest.mark.parametrize("raw", [
    "6.9",      # decimal
    "true",     # word
    "",         # empty
    "1e3",      # exponent
    "1_0",      # PYTHON underscore separator — int() says 10, XML says no
    "１２",      # FULL-WIDTH digits — int() says 12
    "٦",        # ARABIC-INDIC digit — int() says 6
    "६",        # DEVANAGARI digit — int() says 6
    "\xa06",    # NON-BREAKING space — int() strips it, XML does not
    "+ 6",      # sign detached from the digits
    "--3",
    None, 6, True, 6.0, [6],
])
def test_xml_integer_rejects_everything_xml_forbids(raw):
    assert xml_integer(raw) is None


def test_reconcile_takes_a_real_int_only():
    # 726 x 10^6 == 726,000,000 — the lawful call (grouped: the canonical
    # graph lexical contract's spelling)
    assert reconcile("726", None,6, "", "726,000,000") is True
    # a bool is not a scale: `isinstance(True, int)` is True, so only
    # `type(x) is int` is strict enough
    assert reconcile("726", None,True, "", "7,260") is False
    # a float silently TRUNCATED to 6 and reconciled before this fix
    assert reconcile("726", None,6.9, "", "726,000,000") is False
    assert reconcile("726", None,"6", "", "726,000,000") is False


# --------------------------------------------------------------------------
# 4. ONE exclusive-date rule, in ONE place
# --------------------------------------------------------------------------

def test_the_exclusive_date_rule_has_exactly_one_implementation():
    from driver.core import slice_menu
    from driver.relocation import inline_html
    assert XN.stored_period_end("2023-06-30") == "2023-07-01"
    # both consumers must be THE SAME function object, not copies that agree
    assert slice_menu.stored_period_end is XN.stored_period_end
    assert not hasattr(slice_menu, "_plus_day")
    assert not hasattr(inline_html, "_plus_day")
    # #827 finding 2: the FILING side now reads the shared dateUnion parser —
    # a filing may lawfully state xs:date OR xs:dateTime, which the graph's
    # date-only contract (`stored_period_end`, still slice_menu's owner) does
    # not model. Same rule of identity: the same function object, no copy.
    assert inline_html.filing_boundary_graph_end is XN.filing_boundary_graph_end
    assert not hasattr(inline_html, "_plus_one")


def test_stored_period_end_refuses_malformed_dates():
    for bad in ("2023-13-01", "not-a-date", "", None, 20230630):
        with pytest.raises(XN.ExactError):
            XN.stored_period_end(bad)


# --------------------------------------------------------------------------
# 3. duplicate unit ids abstain (contexts already did)
# --------------------------------------------------------------------------

def _doc(units_xml, scale="6", unit_ref="u1"):
    return (
        f'<html {_XMLNS}><body>'
        '<ix:header><ix:resources><xbrli:context id="c1"><xbrli:entity>'
        '<xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193</xbrli:identifier></xbrli:entity>'
        '<xbrli:period><xbrli:startDate>2024-01-01</xbrli:startDate>'
        '<xbrli:endDate>2024-06-30</xbrli:endDate></xbrli:period>'
        '</xbrli:context></ix:resources></ix:header>' + units_xml +
        f'<p><ix:nonFraction id="f1" name="us-gaap:Revenues" contextRef="c1" '
        f'unitRef="{unit_ref}" scale="{scale}" decimals="-6">726'
        f'</ix:nonFraction>'
        '</p></body></html>')


_USD = '<ix:header><ix:resources><xbrli:unit id="u1"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit></ix:resources></ix:header>'
_SHARES = ('<ix:header><ix:resources><xbrli:unit id="u1"><xbrli:measure>xbrli:shares</xbrli:measure>'
           '</xbrli:unit></ix:resources></ix:header>')


def test_a_duplicated_unit_id_is_poisoned_not_last_wins():
    prepared = prepare(_doc(_USD + _SHARES))
    # The poison NAMES ITSELF (#827 round 5): it used to be a bare `None`
    # shared with malformed structure, so consumers reported both as a
    # duplicated id and one of the two was always a lie.
    assert prepared["units"]["u1"] == 'duplicate_unit_id'   # not 'shares'


def test_a_fact_on_a_duplicated_unit_id_abstains():
    bound, why = bind_graph_fact(
        _doc(_USD + _SHARES), inline_element_id="f1",
        concept="us-gaap:Revenues", context_id="c1", unit_ref="u1",
        unit_name="iso4217:USD", is_divide="0", period_type="duration",
        start_date="2024-01-01", end_date="2024-07-01", dims=(),
        entity_cik="0000320193", raw_value="726,000,000", **_IDENTITY)
    assert bound is None and "duplicate" in why


# --------------------------------------------------------------------------
# 1. the semantic unit map — the filing's xbrli: prefix vs the graph's name
# --------------------------------------------------------------------------

#: THE CONCEPT IDENTITY every binder call in this file states, read from the
#: SAME declaration `_doc` is built from — so the row and the document agree.
#: The binder compares (namespace URI, local name), not a prefixed string.
_IDENTITY = {"concept_namespace": _FIXTURE_NS["us-gaap"],
             "graph_concept_qname": "us-gaap:Revenues"}


def _bind(units_xml, unit_name, is_divide, raw="726,000,000", scale="6"):
    return bind_graph_fact(
        _doc(units_xml, scale=scale), inline_element_id="f1",
        concept="us-gaap:Revenues", context_id="c1", unit_ref="u1",
        unit_name=unit_name, is_divide=is_divide, period_type="duration",
        start_date="2024-01-01", end_date="2024-07-01", dims=(),
        entity_cik="0000320193", raw_value=raw, **_IDENTITY)


def test_a_shares_fact_binds_although_the_filing_writes_xbrli_shares():
    """THE round-8 headline: the graph drops the `xbrli:` prefix (census
    2026-07-27: 0 of 6,957 Unit nodes carry it). Comparing the two spellings
    directly made every share fact in every real filing abstain."""
    bound, why = _bind(_SHARES, "shares", "0")
    assert bound is not None, why
    # the published semantic unit IS the expanded identity (#827 bundle B):
    # the storage spelling was verified inside the binder before this returned
    assert bound["unit_measures_expanded"] == \
        (("http://www.xbrl.org/2003/instance", "shares"),)


def test_an_eps_fact_binds_and_reports_usd_per_share():
    divide = ('<ix:header><ix:resources><xbrli:unit id="u1"><xbrli:divide>'
              '<xbrli:unitNumerator><xbrli:measure>iso4217:USD</xbrli:measure>'
              '</xbrli:unitNumerator><xbrli:unitDenominator>'
              '<xbrli:measure>xbrli:shares</xbrli:measure>'
              '</xbrli:unitDenominator></xbrli:divide></xbrli:unit></ix:resources></ix:header>')
    bound, why = _bind(divide, "iso4217:USDshares", "1", raw="726,000,000")
    assert bound is not None, why
    assert bound["unit_numerator_expanded"] == \
        (("http://www.xbrl.org/2003/iso4217", "USD"),)
    assert bound["unit_measures_expanded"] == ()   # a divide has no plain measures


def test_a_usd_fact_reports_usd():
    bound, why = _bind(_USD, "iso4217:USD", "0")
    assert bound is not None, why
    assert bound["unit_measures_expanded"] == \
        (("http://www.xbrl.org/2003/iso4217", "USD"),)


def test_the_binder_REPORTS_the_unit_and_the_caller_decides():
    """AMENDED TWICE by review (2026-07-27):

    * `pure` moved INTO the candidate table by owner ruling — it backs count /
      the percent family / x (see test_round12_pure_unit_law.py).
    * the BINDER no longer applies ANY candidate policy. It is shared with the
      DORMANT materializer, whose policy differs, so it verifies the unit
      against the FILING and reports it; ONE caller-owned check then decides
      compatibility. Two policy checks in two layers was the defect.
    """
    from driver.core.xbrl_attach import candidate_units_for
    cny = ('<ix:header><ix:resources><xbrli:unit id="u1"><xbrli:measure>iso4217:CNY</xbrli:measure>'
           '</xbrli:unit></ix:resources></ix:header>')
    bound, why = _bind(cny, "iso4217:CNY", "0")
    assert bound is not None, f"the binder must REPORT, not judge: {why}"
    assert bound["unit_measures_expanded"] == \
        (("http://www.xbrl.org/2003/iso4217", "CNY"),)
    # ...and non-USD money is lawful as `unknown` (FINAL_DESIGN:206), never a
    # blanket refusal — an earlier test of mine asserted the opposite.
    # THE BINDER'S OWN EXPANDED MEASURES, which is the policy's only input now.
    # Passing `"iso4217:CNY"` asked which prefix the filer typed; the namespace
    # is what makes it money.
    assert candidate_units_for(bound["unit_measures_expanded"], ()) \
        == frozenset({"unknown"})

    pure = ('<ix:header><ix:resources><xbrli:unit id="u1"><xbrli:measure>xbrli:pure</xbrli:measure>'
            '</xbrli:unit></ix:resources></ix:header>')
    bound, why = _bind(pure, "pure", "0")
    assert bound is not None, why
    assert bound["unit_measures_expanded"] == \
        (("http://www.xbrl.org/2003/instance", "pure"),)

    # a unit this route genuinely cannot read still has NO compatible canonical
    # unit — the caller refuses it, and the empty set is how it says so
    btu = ('<ix:header><ix:resources><xbrli:unit id="u1"><xbrli:measure>'
           'utr:Btu</xbrli:measure></xbrli:unit></ix:resources></ix:header>')
    bound, why = _bind(btu, "utr:Btu", "0")
    assert bound is not None, why
    assert candidate_units_for(bound["unit_measures_expanded"], ()) \
        == frozenset()


def test_the_graph_name_must_still_match_the_filings_own_measure():
    """Normalisation is NOT permission to disagree: a filing declaring shares
    can never satisfy a graph fact claiming dollars."""
    bound, why = _bind(_SHARES, "iso4217:USD", "0")
    assert bound is None and "measure" in why


@pytest.mark.parametrize("flag", [0, 1, True, False, "yes", "2", "", None, 1.0])
def test_is_divide_uses_the_certified_string_law(flag):
    """`ROUTE_A_BOOLS` accepts ONLY the exact graph strings '0' and '1' —
    Python ints and bools abstain. My hand-rolled `str(x) in ('0','1')` accepted
    the ints."""
    bound, _why = _bind(_USD, "iso4217:USD", flag)
    assert bound is None


# --------------------------------------------------------------------------
# 2 + 6. the COMPLETE Core path: meaning bound to level_unit, injected
#        provider, non-circular hash, CIK from Core's graph
# --------------------------------------------------------------------------

from driver.core.prepared_fact_v2 import ITEM_FIELDS
from decimal import Decimal
from driver.core.test_round10_event_boundary import (ev_of,
                                                     filing_evidence)
from driver.core.driver_neo4j_adapter import GraphFactRows

_DOC = _doc(_USD)
_SHA = prepare(_DOC)["text_sha"]
ACC = "0000320193-24-000001"


class _Graph:
    """CORE's own graph. Rows + the CIK. It serves NO document."""
    def __init__(self, rows=None, cik="0000320193"):
        self._rows = rows if rows is not None else [{
            "period_type": "duration", "start_date": "2024-01-01",
            "end_date": "2024-07-01", "dims": [], "fact_id": "f1",
            "context_id": "c1", "unit_ref": "u1", "unit_name": "iso4217:USD",
            "is_divide": "0", "value": "726,000,000", "decimals": "-6",
            # the concept identity the real adapter returns, from the SAME
            # declaration `_DOC` is built from
            **_IDENTITY}]
        self._cik = cik

    def get_xbrl_representation_count(self, source_id):
        return 1

    def get_xbrl_fact_dimensions(self, source_id, concept):
        return GraphFactRows(rows=self._rows, exclusions=())

    def get_source_company_cik(self, source_id):
        return self._cik


class _Provider:
    """FISCAL's injected filing provider. It returns the DOCUMENT ONLY — it
    cannot supply a hash, so the hash check can never be circular."""
    def __init__(self, doc=_DOC):
        self._doc = doc

    def get_filing_document(self, source_id):
        return self._doc


def _fact(level_unit="m_usd", value="726", mult=10 ** 6):
    item = {k: None for k in ITEM_FIELDS}
    item.update(driver_name="revenue", driver_state="reported", quote="revenue",
                measurement_raw_spans=[], slice_parts=[], level_unit=level_unit,
                level_low={"value": Decimal(value),
                           "scale_multiplier": Decimal(mult),
                           "unit_scale_evidence": None},
                level_high={"value": Decimal(value),
                            "scale_multiplier": Decimal(mult),
                            "unit_scale_evidence": None},
                time_type="duration", period_start_date="2024-01-01",
                period_end_date="2024-06-30")
    return {"fact_type": "metric", "part_ref": "p1", "occurrence_in_part": None,
            "per_x": None, "item": item}


def _attach(fact=None, graph=None, provider=None, sha=None):
    # MIGRATED (#821): the per-item binder is private; every caller — tests
    # included — goes through the ONE public event door.
    #
    # When no `sha` is forced, the evidence is LAWFUL against this file's own
    # document and the fact carries the filing's own quote, so execution reaches
    # the unit/binding rules these tests are about. When a `sha` IS forced the
    # test is attacking the representation guard, which fires before any of
    # that, so the shape-only form is the right input there.
    fact = fact or _fact()
    if sha is None:
        evidence, filing_quote = filing_evidence(_DOC, "f1")
        fact["item"]["quote"] = filing_quote
    else:
        evidence = ev_of(sha)
    item = {"fact": fact, "concept": "us-gaap:Revenues", "member_refs": [],
            "source_evidence": evidence}
    return attach_event_xbrl([item], source_id=ACC, store=graph or _Graph(),
                             filing_provider=provider or _Provider(),
                             text_parts=parts_for([item]))


def _one(**kw):
    """The ONE verified fact, for a test whose subject is a SUCCESS."""
    res = _attach(**kw)
    assert res.preflight_outcomes == (), [dict(o) for o in res.preflight_outcomes]
    assert [i for i, _f in res.facts] == [0]
    return res.facts[0][1]


def _refused(exc_class, needle, code=None, **kw):
    """An item-local refusal, as the outcome row the door now returns (#825).

    THE EXPECTED DECISION COMES FROM THE EXCEPTION CLASS THIS TEST ALREADY
    NAMED, looked up through the one outcome owner — never from what the run
    produces, so the assertion cannot become a mirror. Exactly one indexed row,
    and the reason is mandatory. `code` is given only where a branch owns a more
    specific one than its class default; the missing-company branch below does.
    """
    want_decision, want_code = _default_outcome(exc_class("probe"))
    res = _attach(**kw)
    assert res.facts == (), "a refused item must attach nothing"
    assert len(res.preflight_outcomes) == 1, \
        [dict(o) for o in res.preflight_outcomes]
    row = res.preflight_outcomes[0]
    assert (row["index"], row["decision"], row["codes"]) == \
        (0, want_decision, (want_code if code is None else code,))
    assert needle in row["detail"], row["detail"]
    return row


def test_the_lawful_money_fact_attaches():
    assert _one() is not None


@pytest.mark.parametrize("bad_unit", ["count", "unknown", "x", "basis_points"])
def test_a_money_fact_is_refused_under_a_non_money_level_unit(bad_unit):
    """THE round-8 second headline: a real $5.262bn fact was ACCEPTED as
    `count`, because count and usd do identical arithmetic."""
    _refused(SchemaError, f"not level_unit={bad_unit!r}",
             fact=_fact(level_unit=bad_unit))


def test_usd_admits_both_usd_and_m_usd():
    assert _one(fact=_fact(level_unit="m_usd")) is not None
    assert _one(fact=_fact(level_unit="usd")) is not None


def test_the_expected_hash_is_required_and_binding():
    # a WELL-FORMED but wrong hash reaches the served-document comparison...
    _refused(SchemaError, "does not hash to the representation", sha="0" * 64)
    # ...while a MISSING one is refused earlier, by the evidence shape itself.
    # Same verdict, different gate: naming each stops one silently covering for
    # the other if the earlier check is ever moved.
    _refused(SchemaError, "expected a 64-character lowercase hex", sha="")


def test_a_provider_serving_a_DIFFERENT_document_is_caught():
    other = _doc(_USD).replace("726", "999")
    _refused(SchemaError, "does not hash to the representation",
             provider=_Provider(other))


def test_the_cik_comes_from_cores_graph_not_the_provider():
    """The provider is channel-supplied under Option C; letting it also name the
    company would let one side supply both the claim and its proof.

    OUTCOME CORRECTED AT #824, and the source of the failure was proved before
    the assertion was touched: the graph and the filing disagree about the
    company, so the BINDER abstains and execution reaches `bound is None` —
    structurally, that raise site is inside that branch — which is a
    graph/filing binding failure and therefore an ordinary PARK, not a contract
    rejection. Nothing here is decided by reading the message text; a
    contradiction submitted AFTER a successful bind still rejects, which the
    evidence tests cover separately.
    """
    from driver.core.prepared_fact_v2 import ProductionValidationError
    # graph says a DIFFERENT company: the binder abstains, exactly as the note
    # above says, so the reason names that gate rather than the company branch.
    _refused(ProductionValidationError, "entity_mismatch",
             graph=_Graph(cik="0001306830"))


def test_a_missing_cik_parks():
    from driver.core.prepared_fact_v2 import ProductionValidationError
    # THE BRANCH OWNS ITS CODE here — this is the one place in the migrated
    # files where a specific code is pinned at the site rather than derived.
    _refused(ProductionValidationError, "names no single filing company",
             code="SOURCE_COMPANY_AMBIGUOUS", graph=_Graph(cik=None))


@pytest.mark.parametrize("cik,why", [
    (320193, "an integer — the door must not stringify it into a lawful CIK"),
    ("00000320193", "eleven digits: padded past the stored spelling"),
    ("0000000000", "the non-registrant marker names no actual Company"),
])
def test_a_malformed_graph_cik_attaches_NOTHING_at_the_event_door(cik, why):
    """827 Packet 17, at the REAL event door. The lawful ten-digit twin already
    binds through `_Graph()`'s default; these are the values that must not.
    F13 reconcile: the refusal moved EARLIER (the owner precheck at the source
    read) and got SPECIFIC — the same park, no longer the generic
    malformed_entity_cik abstention far downstream."""
    from driver.core.prepared_fact_v2 import ProductionValidationError
    _refused(ProductionValidationError, "names no single filing company",
             code="SOURCE_COMPANY_AMBIGUOUS", graph=_Graph(cik=cik))


def test_the_store_is_never_asked_for_a_document():
    """Option C: the graph store stays graph-only."""
    graph = _Graph()
    assert not hasattr(graph, "get_filing_document")
    assert _one(graph=graph) is not None
    from driver.core.driver_neo4j_adapter import Neo4jStore
    assert not hasattr(Neo4jStore, "get_filing_document")
    assert hasattr(Neo4jStore, "get_source_company_cik")


def test_all_xbrl_items_of_one_event_must_agree_on_the_representation():
    """F1 reconcile (checkpoint's own words: tests preserving dead defences
    are evidence, not need): the LIVE rule is AGREEMENT — disagreement and
    the empty event still refuse; the malformed-sha shapes ([None], ["",""])
    can no longer reach this helper, because every evidence object passed
    _checked_source_evidence at the door first (the deleted second
    validation duplicated it)."""
    from driver.core.xbrl_attach import _one_representation_for_event
    assert _one_representation_for_event([_SHA, _SHA, _SHA]) == _SHA
    for bad in ([_SHA, "0" * 64], [], [_SHA, None]):
        with pytest.raises(SchemaError):
            _one_representation_for_event(bad)


# --------------------------------------------------------------------------
# #827 finding 1 — the SAME ASCII class, one level down: `_NUM_DOT`.
#
# Finding 5 above fixed the XML-INTEGER parser. The printed-value grammar kept
# `\d`, which in Python matches EVERY Unicode decimal digit, and `Decimal()`
# then accepts those digits too — so a full-width or Arabic-Indic numeral was
# read as a number by a rule whose whole job is ASCII source syntax. Proven
# live before the fix: printed_value('７２６', '', None) returned Decimal 726.
#
# This regex validates SYNTAX; it does not infer meaning. The fix replaces only
# its `\d` tokens with `[0-9]`.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("shown", [
    "７２６",        # FULL-WIDTH digits
    "٧٢٦",          # ARABIC-INDIC digits
    "६",            # DEVANAGARI digit
    "1２3",         # MIXED ascii + full-width
    "１,２３４.５",   # full-width through the comma/decimal grammar
])
def test_printed_value_rejects_NON_ASCII_numerals(shown):
    from driver.relocation.inline_html import printed_value
    assert printed_value(shown, None, None) is None


@pytest.mark.parametrize("shown,want", [
    ("726", "726"), ("0", "0"), (".5", "0.5"),
    ("12345", "12345"), ("0.001", "0.001"),
])
def test_printed_value_still_accepts_every_lawful_ASCII_form(shown, want):
    """THE POSITIVE CONTROL: tightening the class must not cost one lawful
    ASCII spelling — bare integers and leading-dot decimals included."""
    from decimal import Decimal

    from driver.relocation.inline_html import printed_value
    assert printed_value(shown, None, None) == Decimal(want)


@pytest.mark.parametrize("shown", ["1,234.50", "1,234"])
def test_a_COMMA_GROUPED_number_needs_a_TRANSFORM_to_be_read(shown):
    """MIGRATED, not weakened — the comma cases were in the list above and
    asserted that a no-format fact could state `1,234.50`.

    It cannot. Inline XBRL 1.1 §10.1.2 says a fact with NO `format` states the
    number itself as an XSD decimal, and that grammar admits no thousands
    separator — confirmed against Arelle's own `decimalPattern`, which is the
    authority this reader defers to. A comma-grouped presentation is exactly
    what a transform exists to interpret, so without one the honest answer is
    refusal, and with `num-dot-decimal` the same text reads correctly.
    """
    from decimal import Decimal

    from driver.relocation.inline_html import printed_value
    assert printed_value(shown, None, None) is None
    ndd = ("http://www.xbrl.org/inlineXBRL/transformation/2020-02-12",
           "num-dot-decimal")
    assert printed_value(shown, ndd, "") == Decimal(shown.replace(",", ""))


# --------------------------------------------------------------------------
# #827 finding 2 — the exclusive-end rule had a THIRD copy, and it was lenient.
#
# Round-8 finding 4 removed two byte-identical `_plus_day` copies. A third
# survived inside locator's Route-A branch as `_plus_one`, built on
# `date.fromisoformat` — which accepts the COMPACT `20230630` that XML
# `xs:date` forbids. Proven live before the fix: the copy returned
# '2023-07-01' for '20230630' while the shared owner refused it.
#
# BOUNDED BY EVIDENCE (receipt 09_filing_date_inventory.json): all 1,103,247
# xbrli period values across the 1,769 cached filings are DATE-ONLY — zero
# dateTime, zero timezone forms, zero non-conforming. So the strict date-only
# owner covers the entire observed domain; every other lexical form visibly
# fails to bind rather than being repaired, and no dateTime/leap-second/
# arbitrary-year machinery is built for a form that does not occur.
# --------------------------------------------------------------------------

def test_the_exclusive_end_rule_has_ONE_owner_and_locator_parses_no_dates():
    """STRUCTURAL: locator must not parse a date itself — `exact_numbers`
    owns the rule. A private copy is a second definition of what a filing
    says, which is the one thing a verifier may not have."""
    import ast
    import io
    import os
    path = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "relocation", "locator.py")
    tree = ast.parse(io.open(path, encoding="utf-8").read())
    leniences = [n for n in ast.walk(tree)
                 if isinstance(n, ast.Attribute) and n.attr == "fromisoformat"]
    assert not leniences, (
        "locator calls fromisoformat again — the lenient date parser is back")


@pytest.mark.parametrize("raw,want", [
    ("2023-06-30", "2023-07-01"),           # the ordinary lawful case
    ("2024-02-28", "2024-02-29"),           # leap day
    ("2024-12-31", "2025-01-01"),           # year boundary
    ("0224-03-31", "0224-04-01"),           # THE PINNED LAW: lawful year 224
])
def test_stored_period_end_accepts_every_lawful_DATE_ONLY_form(raw, want):
    assert XN.stored_period_end(raw) == want


@pytest.mark.parametrize("raw", [
    "20230630",                  # COMPACT — what the deleted copy accepted
    "224-04-01",                 # the malformed 3-digit graph year: NEVER 2024
    "2023-06-30T00:00:00",       # xs:dateTime — unobserved; must not bind
    "2023-06-30T00:00:00Z",      # …with Z
    "2023-06-30T00:00:00+14:00", # …with a lawful extreme offset
    "2023-06-30T24:00:00",       # the XBRL midnight spelling
    "2023-13-01", "2024-02-30",  # impossible calendar dates
    "２０２３-０６-３０",             # full-width digits
    " 2023-06-30", "2023-06-30 ",  # padded
    "", None, 20230630,
])
def test_stored_period_end_REFUSES_everything_else_visibly(raw):
    """Every one of these must raise the owner's own error — a visible park —
    never a silent repair and never a guess."""
    with pytest.raises(XN.ExactError):
        XN.stored_period_end(raw)


# --------------------------------------------------------------------------
# #827 finding 2, REOPENED — the shared XBRL dateUnion parser.
#
# MY ERROR, corrected here: the cache census (1,103,247 period values, all
# date-only) justified using the STANDARD LIBRARY and adding no Arelle /
# leap-second table / arbitrary-year library. It never licensed REFUSING
# lawful `xs:dateTime`. XBRL 2.1 §4.7.2 defines the period children as
# `xbrli:dateUnion` — `xs:date` OR `xs:dateTime` — so both are accepted law
# regardless of what today's corpus happens to contain.
#
# THE LAW THIS PINS:
#   * lexical: xs:date and xs:dateTime, timezone absent / Z / ±hh:mm to the
#     ±14:00 limit; 14:01 and beyond are malformed;
#   * XML whitespace collapse is SPACE, TAB, CR, LF only — NBSP, vertical tab,
#     form feed and other Unicode spaces are NOT whitespace here;
#   * a DATE-ONLY boundary means the following midnight, so the graph's
#     exclusive end ADDS ONE DAY; a dateTime already IS the instant, so it
#     adds nothing;
#   * a timezone is never invented and a time is never truncated to fit the
#     graph's date-only contract — either binds exactly or PARKS visibly;
#   * duration ordering compares aware/aware or naive/naive; a mixed pair is
#     INDETERMINATE and parks rather than guessing a zone;
#   * lawful-but-unrepresentable (negative year, >4-digit year, leap second)
#     PARKS; year zero is malformed per XML Schema 1.0;
#   * `<forever>` is lawful source data that cannot back a dated fact, so it
#     parks with a named detail — never a sixth decision word.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("raw,kind,tz", [
    ("2023-06-30", "date", False),
    ("2023-06-30T00:00:00", "dateTime", False),
    ("2023-06-30T23:59:59", "dateTime", False),
    ("2023-06-30T00:00:00.000", "dateTime", False),
    ("2023-06-30T00:00:00Z", "dateTime", True),
    ("2023-06-30T00:00:00+14:00", "dateTime", True),
    ("2023-06-30T00:00:00-14:00", "dateTime", True),
    ("2023-06-30T00:00:00+05:30", "dateTime", True),
    ("2023-06-30Z", "date", True),
    (" \t\r\n2023-06-30 \t\r\n", "date", False),      # XML whitespace collapse
])
def test_filing_boundary_PARSES_every_lawful_dateUnion_form(raw, kind, tz):
    got = XN.parse_filing_boundary(raw)
    assert got.kind == kind and got.has_timezone is tz, got


@pytest.mark.parametrize("raw", [
    "20230630",                       # compact — not xs:date
    "2023-6-30",                      # unpadded
    "0000-01-01",                     # year zero is forbidden by XML Schema
    "2023-13-01", "2024-02-30",       # impossible calendar dates
    "2023-06-30T24:00:01",            # past the 24:00:00 spelling
    "2023-06-30T00:00:00+14:01",      # beyond the ±14:00 limit
    "2023-06-30T00:00:00+15:00",
    "2023-06-30T00:00:00+05:60",      # minutes out of range
    "2023-06-30T00:00",               # seconds required
    "\xa02023-06-30",                 # NBSP is NOT XML whitespace
    "\x0b2023-06-30", "\x0c2023-06-30",   # vertical tab / form feed
    " 2023-06-30",               # Unicode line separator
    "２０２３-０６-３０",                  # full-width digits
    "", "   ", None, 20230630, "forever",
])
def test_filing_boundary_REFUSES_every_malformed_form(raw):
    with pytest.raises(XN.ExactError):
        XN.parse_filing_boundary(raw)


@pytest.mark.parametrize("raw,want", [
    ("2023-06-30", "2023-07-01"),          # DATE-ONLY: the following midnight
    ("0224-03-31", "0224-04-01"),          # the pinned lawful year 224
    ("2024-02-28", "2024-02-29"),
    ("2023-07-01T00:00:00", "2023-07-01"),  # dateTime IS the instant: no +1
])
def test_filing_boundary_binds_the_graph_exclusive_end(raw, want):
    assert XN.filing_boundary_graph_end(raw) == want


@pytest.mark.parametrize("raw", ["2023-06-30T24:00:00", "9999-12-31T24:00:00",
                                 "2024-01-01T24:00:00Z"])
def test_XBRL_forbids_T24_00_00_even_though_XSD_allows_it(raw):
    """XML Schema permits `24:00:00`; **XBRL 2.1 §4.7.2 does not** — the
    end-of-day instant must be written as the next day's `00:00:00`.

    I got this wrong TWICE. First I had it parking as "a time of day"; then I
    "corrected" that to BINDING as the following midnight and pinned it in the
    table above. The narrower specification governs. `9999-12-31T24:00:00`
    additionally raised OverflowError straight out of the parser — arithmetic
    at the calendar edge now parks instead of escaping as an exception.
    """
    with pytest.raises(XN.ExactError):
        XN.parse_filing_boundary(raw)


@pytest.mark.parametrize("raw,needle", [
    ("2023-06-30T12:30:00", "time"),         # truncation would be required
    ("2023-06-30T00:00:00.500", "time"),
    ("2023-06-30T23:59:59", "time"),         # a real time of day
    ("2023-06-30T00:00:00Z", "timezone"),    # inventing a zone is forbidden
    ("2023-06-30T00:00:00+05:30", "timezone"),
    ("2023-06-30Z", "timezone"),
    ("-0500-06-30", "representable"),        # lawful negative year
    ("12023-06-30", "representable"),        # lawful >4-digit year
    ("2023-06-30T23:59:60", "representable"),   # leap second
])
def test_a_LAWFUL_boundary_that_cannot_bind_PARKS_visibly(raw, needle):
    """Never a repair, never a guess: the parser says WHY it cannot bind."""
    parsed = XN.parse_filing_boundary(raw)
    assert parsed.park, f"{raw} should park, not bind"
    assert needle in parsed.park, f"{raw}: park reason {parsed.park!r}"
    assert XN.filing_boundary_graph_end(raw) is None


@pytest.mark.parametrize("start,end,want", [
    ("2023-01-01", "2023-06-30", True),                       # naive/naive
    ("2023-06-30", "2023-01-01", False),                      # reversed
    # EQUAL date-only boundaries are a lawful ONE-DAY period, because the end
    # means the FOLLOWING midnight — corrected after the live corpus showed
    # 1,774 such contexts in a 400-filing sample.
    ("2023-01-01", "2023-01-01", True),
    ("2023-01-01T00:00:00Z", "2023-06-30T00:00:00Z", True),   # aware/aware
    ("2023-01-01T00:00:00+14:00", "2023-01-01T00:00:00-14:00", True),
    # MIXED PAIRS ARE ORDERED WHEN THEY ARE FAR APART. XML Schema 1.0 §3.2.7.4
    # gives an untimezoned value the instant range [Q@+14:00 .. Q@-14:00]; a
    # timezoned value OUTSIDE that 28-hour window is definitively ordered
    # against it, and only an overlap is indeterminate. Every mixed pair used
    # to return None, which pinned an over-broad refusal as though it were the
    # standard.
    ("2023-01-01T00:00:00Z", "2023-06-30T00:00:00", True),     # 6 months apart
    ("2023-01-01", "2023-06-30T00:00:00+01:00", True),
    ("2023-06-30T00:00:00Z", "2023-01-01T00:00:00", False),    # far, backwards
    # ...and only genuinely close pairs park. 6h < the 14h uncertainty, so the
    # two possible readings disagree and no answer exists.
    ("2024-01-01T00:00:00Z", "2024-01-01T06:00:00", None),
    ("2024-01-01T12:00:00", "2024-01-01T12:00:00Z", None),
])
def test_duration_ordering_handles_aware_naive_and_parks_when_indeterminate(
        start, end, want):
    assert XN.filing_duration_ordered(start, end) is want


#: (raw, is_lawful_dateUnion) — one table, two INDEPENDENT implementations.
_XSD_LEGALITY = [
    ("2023-06-30", True),                   # plain xs:date
    ("2023-06-30Z", True),                  # a DATE may carry a timezone
    ("2023-06-30+05:00", True),
    ("2023-06-30T00:00:00", True),
    ("2023-06-30T12:00:00+14:00", True),    # the exact ±14:00 limit
    ("2023-06-30T12:00:00-14:00", True),
    ("0224-06-30", True),                   # zero-padded four-digit year
    ("12023-06-30", True),                  # lawful >4-digit year
    ("-0044-03-15", True),                  # lawful negative year
    ("2023-06-30T23:59:60", True),          # leap second: lexically lawful
    ("02023-06-30", False),                 # >4 digits may NOT lead with zero
    ("224-06-30", False),                   # fewer than four digits
    ("0000-01-01", False),                  # year zero is forbidden
    ("2023-06-30T12:00:00+15:00", False),   # beyond ±14:00
    ("2023-06-30T12:00:00+14:01", False),
    ("2023-06-30T12:00:00+05:60", False),   # timezone minutes out of range
    ("2023-06-30T24:00:00", False),         # XBRL 2.1 §4.7.2 forbids 24:00:00
    ("2023-02-30", False),                  # impossible calendar date
    ("2023-13-01", False),
    ("20230630", False),                    # compact form is not xs:date
    ("2023-6-30", False),                   # unpadded
    ("2023-06-30xyz", False),               # a lawful PREFIX is not a value
    ("\xa02023-06-30", False),              # NBSP is not XML whitespace
]


@pytest.mark.parametrize("raw,lawful", _XSD_LEGALITY)
def test_the_date_CENSUS_and_the_PRODUCTION_parser_agree_on_legality(raw, lawful):
    """TWO IMPLEMENTATIONS, DELIBERATELY NOT SHARED — and therefore checked.

    The census (`receipts_827/scan_filing_dates.py`) exists to BOUND this
    parser, so it must not import it: a census that asked the parser would only
    prove the parser agrees with itself, which is the self-reference this
    programme has been caught by repeatedly.

    The cost of two copies is drift, and drift is exactly what happened — the
    census accepted `+15:00`, `+14:01`, `+05:60` and `02023-06-30`, and refused
    lawful timezone-bearing dates, while the parser had all four right. This
    table is the cheap thing that makes two intentional copies honest.
    """
    import importlib.util
    import pathlib
    census_path = (pathlib.Path(__file__).resolve().parents[2]
                   / ".claude/plans/Drivers/experiments/harness/receipts_827"
                   / "scan_filing_dates.py")
    spec = importlib.util.spec_from_file_location("_census_dates", census_path)
    census = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(census)

    census_says_lawful = "OTHER" not in census.classify(raw)[0]
    try:
        XN.parse_filing_boundary(raw)
        parser_says_lawful = True
    except XN.ExactError:
        parser_says_lawful = False

    assert parser_says_lawful is lawful, (
        f"the PRODUCTION parser disagrees with the XSD table on {raw!r}")
    assert census_says_lawful is lawful, (
        f"the CENSUS disagrees with the XSD table on {raw!r}")


def test_forever_is_lawful_source_data_that_PARKS_with_a_named_detail():
    """`<forever>` cannot back this contract's dated fact. It parks under the
    EXISTING parked decision with a reason — never a sixth decision word.

    THIS USED TO ASSERT ON A CONSTANT NOTHING PRODUCED. `FOREVER_PARK_REASON`
    lived in `exact_numbers` and no production path ever returned it — the
    binder returns its own `forever_or_undated_period` — so the constant and
    the code were two unrelated strings that together read as a proven rule.
    The constant is deleted; the reason a CALLER actually receives is asserted
    in `test_FOREVER_parks_under_its_own_named_reason_not_malformed` below,
    against the real binder. What remains here is the decision-word law.
    """
    from driver.core.prepared_fact_v2 import OUTCOME_CLASSES
    from driver.core.xbrl_attach import PUBLIC_DECISIONS
    assert "forever" not in [d.lower() for d in PUBLIC_DECISIONS], \
        "`forever` must never become a sixth public decision word"
    assert set(OUTCOME_CLASSES.values()) <= set(PUBLIC_DECISIONS)


# --------------------------------------------------------------------------
# #827 REOPENED, blocker 1 — the parser rounded, and rounding a boundary moves
# a FACT'S DATE.
#
# Reproduced before this fix: fractional seconds went through
# `float("0."+digits) * 1e6` into `timedelta(microseconds=...)`, which ROUNDS.
# `23:59:59.9999999` became `2023-07-01 00:00:00` — not merely midnight, THE
# NEXT DAY — and bound. `.0000004` silently became midnight and bound too. And
# `9999-12-31` raised OverflowError out of `filing_boundary_graph_end`.
#
# A boundary is an identity, so it is exact or it parks.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("raw", [
    "2023-06-30T23:59:59.9999999",   # rounded UP a whole day and bound
    "2023-06-30T00:00:00.0000004",   # rounded DOWN to midnight and bound
    "2023-06-30T00:00:00.5",
    "2023-06-30T12:00:00.000001",
])
def test_SUB_SECOND_precision_never_rounds_into_a_binding(raw):
    """Any non-zero fraction is a time of day: it must PARK, never round."""
    b = XN.parse_filing_boundary(raw)
    assert b.park, f"{raw} bound instead of parking"
    assert XN.filing_boundary_graph_end(raw) is None


def test_a_ZERO_fraction_is_still_exactly_midnight():
    """The lawful control: `.000` is zero, so it binds like plain midnight —
    tightening must not cost a lawful spelling."""
    assert XN.filing_boundary_graph_end("2023-07-01T00:00:00.000") == "2023-07-01"
    assert XN.parse_filing_boundary("2023-07-01T00:00:00.000").park is None


@pytest.mark.parametrize("raw,want", [
    # DATE-ONLY: means the FOLLOWING midnight, which is off the calendar -> park
    ("9999-12-31", None),
    # dateTime: already IS the instant, adds no day, so it still binds
    ("9999-12-31T00:00:00", "9999-12-31"),
])
def test_the_CALENDAR_EDGE_parks_and_never_crashes(raw, want):
    """`9999-12-31` + one day leaves the representable calendar. It must be a
    visible park, not an OverflowError escaping the parser.

    THIS ASSERTION USED TO READ `is None or == "9999-12-31"` for BOTH inputs.
    The two spellings have two DIFFERENT correct answers, and accepting either
    for either pinned neither — the crash below lived underneath it, green,
    for a whole review round. Each case is now asserted exactly.
    """
    assert XN.filing_boundary_graph_end(raw) == want


# --------------------------------------------------------------------------
# #827 ROUND 2, blocker 1 — the calendar edge escaped as an OverflowError from
# every date-adding site EXCEPT the parser.
#
# `parse_filing_boundary` parked correctly, so the test above passed, while
# `filing_duration_ordered`, `stored_period_end` and therefore the LIVE fact
# matcher `slice_menu.match_xbrl_fact` all raised OverflowError. One rule —
# "the day after this date" — with three different failure behaviours.
#
# The contract is the module's own: MALFORMED -> ExactError; lawful but
# unusable -> a visible refusal. An OverflowError is neither.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("start,end", [
    ("9999-12-30", "9999-12-31"),      # the end's following midnight overflows
    ("9999-12-31", "9999-12-31"),      # equal, at the edge
])
def test_duration_ordering_at_the_CALENDAR_EDGE_is_indeterminate_not_a_crash(
        start, end):
    """An unrepresentable following midnight makes the comparison unanswerable.
    `None` is that answer; OverflowError is a crash."""
    assert XN.filing_duration_ordered(start, end) is None


def test_stored_period_end_REFUSES_the_calendar_edge_as_an_ExactError():
    """`stored_period_end` is the graph's exclusive-end rule. At the edge it
    raised OverflowError, which no caller catches — while every caller already
    catches this module's own `ExactError`."""
    with pytest.raises(XN.ExactError):
        XN.stored_period_end("9999-12-31")
    assert XN.stored_period_end("2023-06-30") == "2023-07-01"   # control


def test_the_LIVE_fact_matcher_survives_the_calendar_edge():
    """The consumer proof, through the real production door: an edge-dated
    claim must simply fail to match, never take the process down."""
    from driver.core.slice_menu import match_xbrl_fact
    claim = {"time_type": "duration", "start": "9999-12-30",
             "end": "9999-12-31", "dims": set()}
    rows = [{"period_type": "duration", "start_date": "9999-12-30",
             "end_date": "9999-12-31", "dims": []}]
    assert match_xbrl_fact(claim, rows) is None


def test_an_EXTENDED_year_still_gets_a_real_calendar_check():
    """LAWFULNESS IS DECIDED BEFORE REPRESENTABILITY, and my first expectation
    here had it backwards.

    A >4-digit year that is calendrically REAL parks as unrepresentable. One
    that is IMPOSSIBLE is malformed — `12023-02-30` is not a date in any year,
    so calling it "lawful but unrepresentable" would launder a broken value.
    The calendar rule is arithmetic, so it applies to every year."""
    for impossible in ("12023-02-30", "-0500-02-30", "12023-04-31"):
        with pytest.raises(XN.ExactError, match="impossible calendar date"):
            XN.parse_filing_boundary(impossible)
    for lawful_but_unrepresentable in ("12023-02-28", "-0500-06-30",
                                       "12024-02-29"):   # 12024 IS a leap year
        b = XN.parse_filing_boundary(lawful_but_unrepresentable)
        assert b.park and "representable" in b.park, b


@pytest.mark.parametrize("digits", [5, 400, 4_300, 20_000])
def test_827R6_an_ENORMOUS_year_parks_and_never_crashes(digits):
    """XML Schema puts NO BOUND on the number of year digits, and the parser
    converted the whole field with `int()`. Python refuses to build an integer
    from more than 4,300 digits, so a lexically lawful filing CRASHED the
    parser instead of parking — reproduced at 5,000 digits.

    Nothing here needs the whole number: zero-ness is a digit test, the leap
    rule depends only on year mod 400 and 10**4 is a multiple of 400 (so the
    LAST FOUR DIGITS settle it for any year), and representability is decided
    by the sign and the digit count alone."""
    boundary = XN.parse_filing_boundary("9" * digits + "-06-30")
    assert boundary.park and "representable" in boundary.park


@pytest.mark.parametrize("year,month_day,impossible", [
    ("9" * 4_400, "-02-30", True),      # impossible in EVERY year
    ("9" * 4_400, "-02-28", False),     # real date, unrepresentable year
    ("1" + "0" * 4_399, "-02-29", True),   # ...0000 IS a leap year -> but 02-29
])                                          # is real, so this one is LAWFUL
def test_827R6_the_calendar_rule_still_applies_to_ENORMOUS_years(
        year, month_day, impossible):
    """The calendar check must not be skipped just because the year is huge —
    parking an impossible date would launder a broken value. `...0000` is
    divisible by 400, so 29 February is real there."""
    raw = year + month_day
    if impossible and month_day == "-02-30":
        with pytest.raises(XN.ExactError, match="impossible calendar date"):
            XN.parse_filing_boundary(raw)
    else:
        assert XN.parse_filing_boundary(raw).park


# --------------------------------------------------------------------------
# #827 REOPENED, blockers 2+3 — THROUGH THE REAL BINDER, not the parser alone.
#
# The parser tests passed while the binder ignored half of what they proved:
# it read the filing's START as a raw string, never checked order, and had no
# answer for `<forever>`. These drive `bind_graph_fact` ITSELF.
#
# ROUND-3 CORRECTION to this very note: it went on to say
# `filing_duration_ordered` and `FOREVER_PARK_REASON` "had ZERO production
# callers", present tense, after both had been dealt with — the binder now
# calls the ordering rule, and the constant is DELETED because nothing ever
# produced it. A comment describing machinery that no longer exists is the
# same defect as a test asserting on it.
# --------------------------------------------------------------------------

def _period_doc(start, end, instant=None):
    period = (f'<xbrli:instant>{instant}</xbrli:instant>' if instant is not None
              else f'<xbrli:startDate>{start}</xbrli:startDate>'
              f'<xbrli:endDate>{end}</xbrli:endDate>')
    return (f'<html {_XMLNS}><body><ix:header><ix:resources><xbrli:context id="c1"><xbrli:entity>'
            '<xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193</xbrli:identifier></xbrli:entity>'
            f'<xbrli:period>{period}</xbrli:period></xbrli:context></ix:resources></ix:header>' + _USD +
            '<p><ix:nonFraction id="f1" name="us-gaap:Revenues" contextRef="c1" '
            'unitRef="u1" scale="6" decimals="-6">726</ix:nonFraction></p>'
            '</body></html>')


def _bind_period(start, end, *, instant=None, want_start="2024-01-01",
                 want_end="2024-07-01", period_type="duration"):
    return bind_graph_fact(
        _period_doc(start, end, instant), inline_element_id="f1",
        concept="us-gaap:Revenues", context_id="c1", unit_ref="u1",
        unit_name="iso4217:USD", is_divide="0", period_type=period_type,
        start_date=want_start, end_date=want_end, dims=(),
        entity_cik="0000320193", raw_value="726,000,000", **_IDENTITY)


def test_the_binder_binds_a_lawful_MIDNIGHT_dateTime_start():
    """A start at exact midnight IS the date-only start's instant, so it must
    bind. The raw string compare could never match it."""
    bound, why = _bind_period("2024-01-01T00:00:00", "2024-06-30")
    assert bound is not None, why


def test_the_binder_still_binds_the_ordinary_date_only_duration():
    bound, why = _bind_period("2024-01-01", "2024-06-30")
    assert bound is not None, why


@pytest.mark.parametrize("start,end,needle", [
    ("20240101", "2024-06-30", "malformed"),          # compact start
    ("2024-01-01T12:30:00", "2024-06-30", "unbindable"),   # start carries a time
    ("2024-01-01T00:00:00Z", "2024-06-30", "unbindable"),  # start carries a zone
    ("2024-06-30", "2024-01-01", "not_forward"),      # REVERSED
    ("2024-01-02T00:00:00", "2024-01-01T00:00:00", "not_forward"),  # dateTime reversed
])
def test_the_binder_REFUSES_an_unlawful_or_backwards_period(start, end, needle):
    bound, why = _bind_period(start, end)
    assert bound is None, f"{start}..{end} bound and should not have"
    assert needle in why, why


@pytest.mark.parametrize("start,end", [
    ("2024-01-01T00:00:00Z", "2024-06-30"),      # aware START, naive end
    ("2024-01-01", "2024-06-30T00:00:00Z"),      # naive start, aware END
])
def test_a_TIMEZONE_INDETERMINATE_duration_refuses_rather_than_guessing(start, end):
    """One boundary aware, one naive: XML Schema gives no order without
    inventing a zone, so the binder must refuse.

    THE EXACT REASON IS PINNED. This accepted `"unbindable" in why or
    "not_forward" in why` — two different refusals, either of which passed, so
    the test could not say WHICH branch ran and would have kept passing if the
    timezone case started failing for the ordering reason instead. Both
    directions are checked, because an aware END and an aware START reach the
    refusal by different paths.
    """
    bound, why = _bind_period(start, end)
    assert bound is None
    assert why == "unbindable_period", why


def test_FOREVER_parks_under_its_own_named_reason_not_malformed():
    """`<forever>` is lawful source data with no dated boundary. It must not be
    reported as malformed, and it must not invent a date."""
    doc = (f'<html {_XMLNS}><body><ix:header><ix:resources><xbrli:context id="c1"><xbrli:entity>'
           '<xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193</xbrli:identifier></xbrli:entity>'
           '<xbrli:period><xbrli:forever/></xbrli:period></xbrli:context></ix:resources></ix:header>'
           + _USD +
           '<p><ix:nonFraction id="f1" name="us-gaap:Revenues" contextRef="c1" '
           'unitRef="u1" scale="6" decimals="-6">726</ix:nonFraction></p>'
           '</body></html>')
    bound, why = bind_graph_fact(
        doc, inline_element_id="f1", concept="us-gaap:Revenues",
        context_id="c1", unit_ref="u1", unit_name="iso4217:USD",
        is_divide="0", period_type="duration", start_date="2024-01-01",
        end_date="2024-07-01", dims=(), entity_cik="0000320193",
        raw_value="726,000,000", **_IDENTITY)
    assert bound is None
    # THE EXACT reason the caller receives — not a substring, and not a
    # constant standing beside the code. This is the only place the forever
    # law is pinned, so it pins the real returned value.
    assert why == "forever_or_undated_period", why


def test_the_new_period_machinery_has_REAL_production_callers():
    """The fake-green guard: these were tested while nothing in production
    called them. A rule with no caller is not a rule."""
    import io as _io
    import os as _os
    src = _io.open(_os.path.join(_os.path.dirname(_os.path.dirname(
        _os.path.abspath(__file__))), "relocation", "inline_html.py"),
        encoding="utf-8").read()
    for symbol in ("filing_boundary_graph_start", "filing_boundary_graph_end",
                   "filing_duration_ordered"):
        assert src.count(symbol) >= 2, \
            f"{symbol} is imported but never CALLED by the binder"


@pytest.mark.parametrize("start,end", [
    ("2025-03-31", "2025-03-31"),          # the ONE-DAY period, 1,774 live contexts
    ("2024-02-28", "2024-02-28"),
])
def test_a_ONE_DAY_duration_with_equal_date_only_boundaries_is_LAWFUL(start, end):
    """MY OWN REGRESSION, caught by asking the corpus instead of my intuition.

    XBRL's date-only END means the FOLLOWING midnight, so `start == end` is a
    lawful ONE-DAY period — [start T00:00, start+1 T00:00) — not a zero-length
    one. A 400-filing sample of the live cache holds **1,774** such contexts.
    My first ordering rule compared the raw lexical values and refused every
    one of them, and my own test had pinned that refusal as if it were law.

    Ordering therefore compares INSTANTS: the start's own midnight against the
    end's following midnight.
    """
    assert XN.filing_duration_ordered(start, end) is True
    # ...and it binds through the real binder, against the graph's exclusive end
    from datetime import date, timedelta
    graph_end = (date.fromisoformat(end) + timedelta(days=1)).isoformat()
    bound, why = _bind_period(start, end, want_start=start, want_end=graph_end)
    assert bound is not None, why


def test_a_TRULY_zero_length_dateTime_period_is_still_refused():
    """The other side of the same rule: two identical dateTime instants really
    are zero-length, because a dateTime adds no day."""
    assert XN.filing_duration_ordered("2024-01-01T00:00:00",
                                      "2024-01-01T00:00:00") is False


def test_W4_the_representation_sha_grammar_has_one_owner():
    """W4: the 64-hex digest grammar has ONE owner — the public predicate at
    the id-law module; pf2's second regex is gone; both consuming sites
    route through the owner and refuse a 63-char and an UPPERCASE digest
    identically (lowercase-only is the stored spelling)."""
    import inspect
    import pytest as _pt
    from driver.core import driver_ids as di
    from driver.core import prepared_fact_v2 as p2
    from driver.core import xbrl_attach as xa
    assert di.sha256_hex_ok("a" * 64)
    assert not di.sha256_hex_ok("A" * 64)
    assert not di.sha256_hex_ok("a" * 63)
    assert not di.sha256_hex_ok(64)
    assert not hasattr(p2, "_SHA256")
    for bad in ("a" * 63, "A" * 64):
        with _pt.raises(p2.SchemaError):
            p2._sha256_or_raise(bad, "representation_sha256")
    p2._sha256_or_raise("a" * 64, "representation_sha256")   # lawful twin
    # the grammar text lives NOWHERE but the owner:
    assert "[0-9a-f]{64}" not in inspect.getsource(p2)
    assert "[0-9a-f]{64}" not in inspect.getsource(xa)
    assert "[0-9a-f]{64}" in inspect.getsource(di)


@pytest.mark.parametrize("with_start", [True, False],
                         ids=["instant_with_start", "instant_without_start"])
def test_W7_an_instant_bundle_carries_ONLY_its_end_date(with_start):
    """W7 (XBRL 2.1 corrected-errata 2013-02-20 §4.7.2: an instant period has
    NO start): through the PUBLIC attach door — an instant carrying a start
    is rejected for the exact W7 reason; the same instant without the start
    attaches exactly one fact (the graph stores instants exclusive-end:
    start = doc instant + 1 day, end None — F5 retired the stored-'null' alias at the adapter)."""
    idoc = _DOC.replace(
        '<xbrli:period><xbrli:startDate>2024-01-01</xbrli:startDate>'
        '<xbrli:endDate>2024-06-30</xbrli:endDate></xbrli:period>',
        '<xbrli:period><xbrli:instant>2024-06-30</xbrli:instant></xbrli:period>')
    assert idoc != _DOC
    fact = _fact()
    fact["item"].update(time_type="instant",
                        period_start_date="2024-06-30" if with_start else None,
                        period_end_date="2024-06-30")
    evidence, quote = filing_evidence(idoc, "f1")
    fact["item"]["quote"] = quote
    row = dict(_Graph()._rows[0])
    row.update(period_type="instant", start_date="2024-07-01",
               end_date=None)   # F5: the adapter emits None, never "null"
    item = {"fact": fact, "concept": "us-gaap:Revenues", "member_refs": [],
            "source_evidence": evidence}
    res = attach_event_xbrl([item], source_id=ACC, store=_Graph(rows=[row]),
                            filing_provider=_Provider(doc=idoc),
                            text_parts=parts_for([item]))
    if with_start:
        assert len(res.facts) == 0
        (out,) = res.preflight_outcomes
        assert out["decision"] == "rejected"
        assert out["codes"] == ("XBRL_CONTRACT_INVALID",)
        assert out["detail"] == \
            "XBRL context: an instant carries ONLY period_end_date"
    else:
        assert len(res.facts) == 1
        assert res.preflight_outcomes == ()


@pytest.mark.parametrize("exc,parks", [
    (ConnectionError, True), (TimeoutError, True), (InterruptedError, True),
    (PermissionError, False), (FileNotFoundError, False),
    (IsADirectoryError, False), (NotADirectoryError, False),
    (OSError, False),
], ids=["connection-parks", "timeout-parks", "interrupted-parks",
        "permission-fails-loud", "missing-file-fails-loud",
        "is-a-directory-fails-loud", "not-a-directory-fails-loud",
        "bare-oserror-fails-loud"])
def test_F2_only_genuinely_transient_provider_errors_park(exc, parks):
    """F2, corrected per SEQ 805: the transient set is a POSITIVE contract
    (ConnectionError family, TimeoutError, InterruptedError — the OS
    exceptions whose documented meaning is retry-may-succeed). EVERY other
    OSError — the base class and unknown path-shape subclasses included —
    passes through LOUDLY: unknown fails closed, and a negative blacklist
    over an open domain was the reopened defect (IsADirectoryError and
    NotADirectoryError parked forever under it)."""
    class _Raising:
        def get_filing_document(self, source_id):
            raise exc("boom")
    if parks:
        res = _attach(provider=_Raising())
        assert len(res.facts) == 0
        (out,) = res.preflight_outcomes
        assert out["decision"] == "parked"
        assert out["codes"] == ("SOURCE_UNAVAILABLE",)
    else:
        with pytest.raises(exc):
            _attach(provider=_Raising())


def test_F3_an_unreadable_served_document_parks_with_document_blame():
    """F3 (owner-ruled, sheet #6 verbatim: "PARK + DOCUMENT-BLAME, retryable;
    never fact-blame, never silent"): a served document the parser refuses
    (here: a forbidden DOCTYPE) is the DOCUMENT'S fault — the outcome is a
    retryable PARK carrying a document/source-scoped reason, never a
    contract rejection telling the channel to fix a fact it does not own.
    Control: the representation-hash mismatch keeps its own outcome class."""
    class _BadDoc:
        def get_filing_document(self, source_id):
            return '<?xml version="1.0"?><!DOCTYPE r []>' + _DOC
    res = _attach(provider=_BadDoc())
    assert len(res.facts) == 0
    (out,) = res.preflight_outcomes
    assert out["decision"] == "parked"
    assert out["codes"] == ("SOURCE_UNAVAILABLE",)
    assert "document" in out["detail"] and ACC in out["detail"]


# --------------------------------------------------------------------------
# F8 (#827): the channel-declared concept's QName grammar is judged by the
# STANDARDS OWNER at the contract gate — refused as contract input, never
# misreported as a missing fact.
# --------------------------------------------------------------------------

def _attach_concept(concept):
    """The public door with an EMPTY graph and a caller-chosen concept: the
    one variable under test is the concept spelling itself."""
    class _EmptyGraph(_Graph):
        def get_xbrl_fact_dimensions(self, source_id, c):
            return GraphFactRows(rows=[], exclusions=())
    fact = _fact()
    evidence, filing_quote = filing_evidence(_DOC, "f1")
    fact["item"]["quote"] = filing_quote
    item = {"fact": fact, "concept": concept, "member_refs": [],
            "source_evidence": evidence}
    return attach_event_xbrl([item], source_id=ACC, store=_EmptyGraph(),
                             filing_provider=_Provider(),
                             text_parts=parts_for([item]))


@pytest.mark.parametrize("bad", ["us gaap:Revenues", "a:b:c", ":Revenues",
                                 "us-gaap: Rev", "1st:Rev"])
def test_F8_a_malformed_concept_QName_is_refused_as_contract_input(bad):
    """F8 (#827): the door asks driver.xml_names (the ONE QName grammar owner,
    already judging the graph's dimension spellings) about the CHANNEL concept
    BEFORE any graph lookup. A spelling that is not a QName is broken CONTRACT
    INPUT — rejected XBRL_CONTRACT_INVALID — never 'this source carries NO
    fact for it' -> park (the measured misreport: every one of these five
    parked XBRL_BINDING_UNAVAILABLE before the change)."""
    (o,) = _attach_concept(bad).preflight_outcomes
    assert o["decision"] == "rejected", dict(o)
    assert o["codes"] == ("XBRL_CONTRACT_INVALID",)
    assert "QName" in o["detail"]


@pytest.mark.parametrize("lawful", ["us-gaap:Revenues", "Revenues",
                                    "gaap:Ümsatz", "概念:収益"])
def test_F8_a_lawful_QName_concept_reaches_the_graph_answer(lawful):
    """MUST-ALLOW twin: lawful QNames — prefixless and Unicode NCNames
    included (the grammar is the XML library's, never a regex) — pass the
    gate; against an empty graph the honest answer is then the PARK a
    genuinely unbacked concept has always received."""
    (o,) = _attach_concept(lawful).preflight_outcomes
    assert o["decision"] == "parked", dict(o)
    assert o["codes"] == ("XBRL_BINDING_UNAVAILABLE",)


# --------------------------------------------------------------------------
# F11 (#827): the unit-eligibility map — the EMPTY candidate set is a ROUTE
# limitation (park), never a channel contract violation (reject).
# --------------------------------------------------------------------------

_UTR_GAL = ('<ix:header><ix:resources><xbrli:unit id="u1">'
            '<xbrli:measure xmlns:utr="http://www.xbrl.org/2009/utr">utr:gal'
            '</xbrli:measure></xbrli:unit></ix:resources></ix:header>')


def _attach_unit(units_xml, unit_name, level_unit):
    """The public door with a caller-chosen filing unit + matching graph
    unit_name: the one variable under test is the unit's eligibility."""
    doc = _doc(units_xml)
    rows = [{"period_type": "duration", "start_date": "2024-01-01",
             "end_date": "2024-07-01", "dims": [], "fact_id": "f1",
             "context_id": "c1", "unit_ref": "u1", "unit_name": unit_name,
             "is_divide": "0", "value": "726,000,000", **_IDENTITY}]
    fact = _fact(level_unit=level_unit)
    evidence, filing_quote = filing_evidence(doc, "f1")
    fact["item"]["quote"] = filing_quote
    item = {"fact": fact, "concept": "us-gaap:Revenues", "member_refs": [],
            "source_evidence": evidence}
    return attach_event_xbrl([item], source_id=ACC, store=_Graph(rows=rows),
                             filing_provider=_Provider(doc=doc),
                             text_parts=parts_for([item]))


def test_F11_an_EMPTY_candidate_set_parks_as_route_limitation():
    """F11 (#827): a lawful graph unit this route cannot canonicalise
    (utr:gal — census 2026-08-08: 130,231 numeric non-nil facts across 6,764
    unit names sit in this bucket, 1.05%) admits NO level_unit at all, so no
    resubmission can ever succeed — by the door's own decision law that is a
    PARK (drains if the route later canonicalises it), not a channel
    violation. It was published rejected/XBRL_CONTRACT_INVALID (measured
    2026-08-08, the F11 probe)."""
    (o,) = _attach_unit(_UTR_GAL, "utr:gal", "m_usd").preflight_outcomes
    assert o["decision"] == "parked", dict(o)
    assert o["codes"] == ("XBRL_BINDING_UNAVAILABLE",)
    assert "no canonical unit on this route" in o["detail"]


def test_F11_a_wrong_claim_against_a_MAPPED_unit_still_rejects():
    """CONTROL: the graph unit maps to real candidates (iso4217:USD ->
    usd/m_usd) and the channel claimed one it may not ('count') — a
    resubmittable channel error, so the REJECT stands exactly as before."""
    (o,) = _attach_unit(_USD, "iso4217:USD", "count").preflight_outcomes
    assert o["decision"] == "rejected", dict(o)
    assert o["codes"] == ("XBRL_CONTRACT_INVALID",)
    assert "may back" in o["detail"]


# --------------------------------------------------------------------------
# F13 (#827): the company precheck is TRUTHFUL (the one graph_cik rule), and
# the concept-availability outcome states what the graph actually holds.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("bad_cik", [320193, {"cik": "0000320193"},
                                     " 0000320193 "],
                         ids=["int", "dict", "padded"])
def test_F13_a_non_canonical_graph_company_parks_at_the_PRECHECK(bad_cik):
    """F13 (#827): `str(entity_cik or '').strip()` let an int and a dict
    pass, and the REAL gate (driver_ids.graph_cik) then refused them far
    later under the GENERIC 'Route-A binding abstained (malformed_entity_cik)'
    (measured 2026-08-08). The precheck now asks the one owner and parks
    with its own branch code at the source read."""
    (o,) = _attach(graph=_Graph(cik=bad_cik)).preflight_outcomes
    assert o["decision"] == "parked", dict(o)
    assert o["codes"] == ("SOURCE_COMPANY_AMBIGUOUS",)
    assert "no single filing company" in o["detail"]


def test_F13_an_all_excluded_read_states_the_TRUTHFUL_availability():
    """F13 (#827): rows==[] has TWO truths — the graph genuinely carries no
    fact for the concept, or it carries rows the adapter excluded fail-closed.
    Reporting the second as 'carries NO fact' is false and durable; the
    outcome now says none were USABLE and counts the exclusions."""
    class _ExcludedGraph(_Graph):
        def get_xbrl_fact_dimensions(self, source_id, c):
            return GraphFactRows(rows=[], exclusions=(
                {"event": "dimension_definition_unresolved", "count": 2},))
    (o,) = _attach(graph=_ExcludedGraph()).preflight_outcomes
    assert o["decision"] == "parked", dict(o)
    assert o["codes"] == ("XBRL_BINDING_UNAVAILABLE",)
    assert "none were usable" in o["detail"].lower(), o["detail"]
    assert "carries NO fact" not in o["detail"]


# --------------------------------------------------------------------------
# F6 (#827): the census-built envelope contract — UNLISTED VOCABULARY PARKS
# (owner condition 2), while malformed PINNED grammar keeps rejecting.
# --------------------------------------------------------------------------

def _evidence_item(mutate_evidence=None, mutate_item=None):
    fact = _fact()
    evidence, filing_quote = filing_evidence(_DOC, "f1")
    fact["item"]["quote"] = filing_quote
    ev = {k: (list(v) if isinstance(v, tuple) and k != "pieces" else v)
          for k, v in dict(evidence).items()}
    ev["pieces"] = [dict(p) for p in evidence["pieces"]] \
        if evidence["pieces"] else []
    if mutate_evidence:
        mutate_evidence(ev)
    item = {"fact": fact, "concept": "us-gaap:Revenues", "member_refs": [],
            "source_evidence": ev}
    if mutate_item:
        mutate_item(item)
    return item


def _door(item):
    return attach_event_xbrl([item], source_id=ACC, store=_Graph(),
                             filing_provider=_Provider(),
                             text_parts=parts_for([item]))


def test_F6_an_UNLISTED_evidence_field_parks_never_rejects():
    """F6 (#827), owner condition 2: an EXTRA key beside the four pinned ones
    is unlisted VOCABULARY — possibly a lawful contract evolution — so it
    PARKS (drains when the contract widens with census evidence + authority);
    resubmitting unchanged fixes nothing, which is what rejection would
    demand. Census 2026-08-08: zero such shapes in the accepted corpus."""
    (o,) = _door(_evidence_item(
        lambda ev: ev.update(novel_field="x"))).preflight_outcomes
    assert o["decision"] == "parked", dict(o)
    assert o["codes"] == ("XBRL_BINDING_UNAVAILABLE",)
    assert "unlisted" in o["detail"]


def test_F6_a_MISSING_pinned_evidence_key_still_rejects():
    """CONTROL: a missing PINNED key is the channel failing the pinned
    contract — fix and resubmit works, so the rejection stands."""
    def drop(ev):
        del ev["raw_label_span"]
    (o,) = _door(_evidence_item(drop)).preflight_outcomes
    assert o["decision"] == "rejected", dict(o)
    assert o["codes"] == ("XBRL_CONTRACT_INVALID",)


def test_F6_an_UNKNOWN_piece_kind_parks_never_rejects():
    """The kind vocabulary is a closed allowlist; a member outside it is
    unlisted, and unlisted parks (owner condition 2)."""
    def newkind(ev):
        ev["pieces"] = [{"kind": "footnote", "text": "t", "span": [0, 1]}]
    (o,) = _door(_evidence_item(newkind)).preflight_outcomes
    assert o["decision"] == "parked", dict(o)
    assert "unlisted" in o["detail"]


def test_F6_an_UNLISTED_piece_field_parks_and_a_missing_one_rejects():
    def extra(ev):
        ev["pieces"] = [{"kind": "header", "text": "t", "span": [0, 1],
                         "novel": "x"}]
    (o,) = _door(_evidence_item(extra)).preflight_outcomes
    assert o["decision"] == "parked", dict(o)

    def missing(ev):
        ev["pieces"] = [{"kind": "header", "text": "t"}]
    (o2,) = _door(_evidence_item(missing)).preflight_outcomes
    assert o2["decision"] == "rejected", dict(o2)


def test_F6_an_UNLISTED_item_field_parks_and_a_missing_one_rejects():
    """The event-item envelope under the same law: extra key -> unlisted ->
    park; missing pinned key -> reject."""
    (o,) = _door(_evidence_item(
        mutate_item=lambda i: i.update(novel="x"))).preflight_outcomes
    assert o["decision"] == "parked", dict(o)
    assert "unlisted" in o["detail"]

    def drop(i):
        del i["member_refs"]
    (o2,) = _door(_evidence_item(mutate_item=drop)).preflight_outcomes
    assert o2["decision"] == "rejected", dict(o2)
