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

from driver.core.test_round10_event_boundary import parts_for

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
    # 726 x 10^6 == 726,000,000 — the lawful call
    assert reconcile("726", "", 6, "", "726000000") is True
    # a bool is not a scale: `isinstance(True, int)` is True, so only
    # `type(x) is int` is strict enough
    assert reconcile("726", "", True, "", "7260") is False
    # a float silently TRUNCATED to 6 and reconciled before this fix
    assert reconcile("726", "", 6.9, "", "726000000") is False
    assert reconcile("726", "", "6", "", "726000000") is False


# --------------------------------------------------------------------------
# 4. ONE exclusive-date rule, in ONE place
# --------------------------------------------------------------------------

def test_the_exclusive_date_rule_has_exactly_one_implementation():
    from driver.core import slice_menu
    from driver.relocation import inline_html
    assert XN.stored_period_end("2023-06-30") == "2023-07-01"
    # both consumers must be THE SAME function object, not copies that agree
    assert slice_menu.stored_period_end is XN.stored_period_end
    assert inline_html.stored_period_end is XN.stored_period_end
    assert not hasattr(slice_menu, "_plus_day")
    assert not hasattr(inline_html, "_plus_day")


def test_stored_period_end_refuses_malformed_dates():
    for bad in ("2023-13-01", "not-a-date", "", None, 20230630):
        with pytest.raises(XN.ExactError):
            XN.stored_period_end(bad)


# --------------------------------------------------------------------------
# 3. duplicate unit ids abstain (contexts already did)
# --------------------------------------------------------------------------

def _doc(units_xml, scale="6", unit_ref="u1"):
    return (
        '<html><body>'
        '<xbrli:context id="c1"><xbrli:entity>'
        '<xbrli:identifier>0000320193</xbrli:identifier></xbrli:entity>'
        '<xbrli:period><xbrli:startDate>2024-01-01</xbrli:startDate>'
        '<xbrli:endDate>2024-06-30</xbrli:endDate></xbrli:period>'
        '</xbrli:context>' + units_xml +
        f'<p><ix:nonFraction id="f1" name="us-gaap:Revenues" contextRef="c1" '
        f'unitRef="{unit_ref}" scale="{scale}" format="">726</ix:nonFraction>'
        '</p></body></html>')


_USD = '<xbrli:unit id="u1"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>'
_SHARES = ('<xbrli:unit id="u1"><xbrli:measure>xbrli:shares</xbrli:measure>'
           '</xbrli:unit>')


def test_a_duplicated_unit_id_is_poisoned_not_last_wins():
    prepared = prepare(_doc(_USD + _SHARES))
    assert prepared["units"]["u1"] is None      # ambiguous evidence, not 'shares'


def test_a_fact_on_a_duplicated_unit_id_abstains():
    bound, why = bind_graph_fact(
        _doc(_USD + _SHARES), inline_element_id="f1",
        concept="us-gaap:Revenues", context_id="c1", unit_ref="u1",
        unit_name="iso4217:USD", is_divide="0", period_type="duration",
        start_date="2024-01-01", end_date="2024-07-01", dims=(),
        entity_cik="320193", raw_value="726000000")
    assert bound is None and "duplicate" in why


# --------------------------------------------------------------------------
# 1. the semantic unit map — the filing's xbrli: prefix vs the graph's name
# --------------------------------------------------------------------------

def _bind(units_xml, unit_name, is_divide, raw="726000000", scale="6"):
    return bind_graph_fact(
        _doc(units_xml, scale=scale), inline_element_id="f1",
        concept="us-gaap:Revenues", context_id="c1", unit_ref="u1",
        unit_name=unit_name, is_divide=is_divide, period_type="duration",
        start_date="2024-01-01", end_date="2024-07-01", dims=(),
        entity_cik="320193", raw_value=raw)


def test_a_shares_fact_binds_although_the_filing_writes_xbrli_shares():
    """THE round-8 headline: the graph drops the `xbrli:` prefix (census
    2026-07-27: 0 of 6,957 Unit nodes carry it). Comparing the two spellings
    directly made every share fact in every real filing abstain."""
    bound, why = _bind(_SHARES, "shares", "0")
    assert bound is not None, why
    assert bound["unit_key"] == ("shares", False)


def test_an_eps_fact_binds_and_reports_usd_per_share():
    divide = ('<xbrli:unit id="u1"><xbrli:divide>'
              '<xbrli:unitNumerator><xbrli:measure>iso4217:USD</xbrli:measure>'
              '</xbrli:unitNumerator><xbrli:unitDenominator>'
              '<xbrli:measure>xbrli:shares</xbrli:measure>'
              '</xbrli:unitDenominator></xbrli:divide></xbrli:unit>')
    bound, why = _bind(divide, "iso4217:USDshares", "1", raw="726000000")
    assert bound is not None, why
    assert bound["unit_key"] == ("iso4217:USDshares", True)


def test_a_usd_fact_reports_usd():
    bound, why = _bind(_USD, "iso4217:USD", "0")
    assert bound is not None, why
    assert bound["unit_key"] == ("iso4217:USD", False)


def test_the_binder_REPORTS_the_unit_and_the_caller_decides():
    """AMENDED TWICE by review (2026-07-27):

    * `pure` moved INTO the candidate table by owner ruling — it backs count /
      the percent family / x (see test_round12_pure_unit_law.py).
    * the BINDER no longer applies ANY candidate policy. It is shared with the
      DORMANT materializer, whose policy differs, so it verifies the unit
      against the FILING and reports it; ONE caller-owned check then decides
      compatibility. Two policy checks in two layers was the defect.
    """
    from driver.relocation.exact_numbers import candidate_units_for
    cny = ('<xbrli:unit id="u1"><xbrli:measure>iso4217:CNY</xbrli:measure>'
           '</xbrli:unit>')
    bound, why = _bind(cny, "iso4217:CNY", "0")
    assert bound is not None, f"the binder must REPORT, not judge: {why}"
    assert bound["unit_key"] == ("iso4217:CNY", False)
    # ...and non-USD money is lawful as `unknown` (FINAL_DESIGN:206), never a
    # blanket refusal — an earlier test of mine asserted the opposite.
    assert candidate_units_for("iso4217:CNY", False) == frozenset({"unknown"})

    pure = ('<xbrli:unit id="u1"><xbrli:measure>xbrli:pure</xbrli:measure>'
            '</xbrli:unit>')
    bound, why = _bind(pure, "pure", "0")
    assert bound is not None, why
    assert bound["unit_key"] == ("pure", False)

    # a unit this route genuinely cannot read still has NO compatible canonical
    # unit — the caller refuses it, and the empty set is how it says so
    assert candidate_units_for("utr:Btu", False) == frozenset()


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
    def __init__(self, rows=None, cik="320193"):
        self._rows = rows if rows is not None else [{
            "period_type": "duration", "start_date": "2024-01-01",
            "end_date": "2024-07-01", "dims": [], "fact_id": "f1",
            "context_id": "c1", "unit_ref": "u1", "unit_name": "iso4217:USD",
            "is_divide": "0", "value": "726,000,000", "decimals": "-6"}]
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
             graph=_Graph(cik="1306830"))


def test_a_missing_cik_parks():
    from driver.core.prepared_fact_v2 import ProductionValidationError
    # THE BRANCH OWNS ITS CODE here — this is the one place in the migrated
    # files where a specific code is pinned at the site rather than derived.
    _refused(ProductionValidationError, "names no single filing company",
             code="SOURCE_COMPANY_AMBIGUOUS", graph=_Graph(cik=None))


def test_the_store_is_never_asked_for_a_document():
    """Option C: the graph store stays graph-only."""
    graph = _Graph()
    assert not hasattr(graph, "get_filing_document")
    assert _one(graph=graph) is not None
    from driver.core.driver_neo4j_adapter import Neo4jStore
    assert not hasattr(Neo4jStore, "get_filing_document")
    assert hasattr(Neo4jStore, "get_source_company_cik")


def test_all_xbrl_items_of_one_event_must_agree_on_the_representation():
    from driver.core.xbrl_attach import _one_representation_for_event
    assert _one_representation_for_event([_SHA, _SHA, _SHA]) == _SHA
    for bad in ([_SHA, "0" * 64], [], [None], [_SHA, None], ["", ""]):
        with pytest.raises(SchemaError):
            _one_representation_for_event(bad)
