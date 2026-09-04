"""RED-first proofs for the ONE complete Route-A binding operation.

Every test here reproduced a real bypass in the Core verifier that was calling
the binder's pieces by hand. The lesson driving this file: reusing CERTIFIED
code is not the same as reusing CORRECT code — the Core verifier delegated its
arithmetic to `reconcile()` and thereby re-imported the exact 28-digit rounding
defect it had removed from its own code two rounds earlier.

THE LOCKED LAW being pinned (FinalPlan §5A Route A, steps 2-7):
  2. join by the SHORT `Fact.fact_id` to the display element's `id=`
  3. the `(name, contextRef, unitRef)` fallback is permitted ONLY when the short
     id is null/blank, and only when unique
  4. reconcile displayed/format/scale/sign against the graph value with EXACT
     Decimal arithmetic
  7. missing, duplicate, hidden-without-local-evidence, malformed, or
     conflicting evidence ABSTAINS
"""
from decimal import Decimal

import pytest

from driver.relocation.inline_html import (NOT_WELL_FORMED, bind_graph_fact,
                                           find_by_identity, one_concept_target,
                                           parse_raw, prepare, printed_value,
                                           reconcile)

CIK = "0000320193"

#: THE FIXTURE'S OWN NAMESPACE DECLARATION — one owner for both the markup
#: below and the expanded identity a test asserts, so the document and the
#: assertion cannot drift apart. This is this fixture's constant; it is not a
#: global mapping and it is not a rule that infers a namespace from a prefix.
_FIXTURE_NS = {
    'xbrli': 'http://www.xbrl.org/2003/instance',
    'xbrldi': 'http://xbrl.org/2006/xbrldi',
    'ix': 'http://www.xbrl.org/2013/inlineXBRL',
    # THE OFFICIAL XBRL CURRENCY NAMESPACE, because these tests assert that a
    # LAWFUL USD unit binds. Binding the familiar `iso4217:` prefix to an
    # invented URI would make the fixture certify the very defect this round
    # removes — a prefix trusted over the namespace it actually names.
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
    # ...and the SAME registry as the EXPANDED identity the semantic functions
    # take. `printed_value`/`reconcile` were being handed the raw text
    # `"ixt:num-dot-decimal"` here — a prefix, which is exactly what #827
    # Stage 3 removed from every semantic decision. A raw string cannot state
    # which registry it means, so these calls were asserting nothing about
    # identity even while they passed.
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

#: THE TRANSFORM IDENTITIES, derived from the SAME map the fixture documents
#: declare — so a test can never assert a transform the fixture does not bind.
_NUM_DOT_DECIMAL = (_FIXTURE_NS['ixt'], 'num-dot-decimal')
_FIXED_ZERO = (_FIXTURE_NS['ixt'], 'fixed-zero')


def _graph_dims(*pairs, ns=None):
    """A dimension set AS THE GRAPH SUPPLIES IT — (namespace URI, local name),
    resolved through the map the fixture's own document declares.

    The adapter decodes each dimension's namespace from its composite id, so
    the binder never receives a prefix from the graph side; these fixtures used
    to hand it prefixed spellings, which only ever tested whether two documents
    happened to pick the same alias. Every URI is LOOKED UP, never typed: a
    fixture that writes its own URI can claim a member its document does not
    contain, and an undeclared prefix must raise here rather than quietly
    become an unbindable claim.
    """
    ns = _FIXTURE_NS if ns is None else ns
    return tuple(tuple((ns[q.partition(':')[0]], q.partition(':')[2])
                       for q in pair) for pair in pairs)


def _identity_kw(concept):
    """The identity kwargs THIS fixture's document states for `concept`.

    The graph supplies both halves in production; here the document the test
    just built is the equivalent authority, read from the SAME declaration the
    markup is generated from — so the assertion and the document cannot drift.
    """
    prefix = str(concept).partition(":")[0]
    return {"concept_namespace": _FIXTURE_NS.get(prefix),
            "graph_concept_qname": concept}



def _xa(value):
    """A value written into an ATTRIBUTE, escaped as XML requires.

    A raw `<` or `&` in an attribute value is not well-formed XML, so a fixture
    that interpolated one was not testing the id or QName rule at all — it was
    testing the parser's refusal of its own markup. Escaping puts the EXACT
    intended character into the attribute (`a&lt;b` IS the value `a<b`), so the
    rule under test is genuinely reached.
    """
    return (str(value).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


def _doc(*, element_id='id="f-48" ', name="us-gaap:Revenues", ctx="c-1",
         unit="usd", scale="6", sign="", shown="390", hidden=False,
         extra_element="", dims=""):
    name = _xa(name)
    # AN OPTIONAL ATTRIBUTE IS ABSENT OR LAWFUL. The schema declares `sign` as a
    # restriction of xs:string whose pattern is exactly `-`, so `sign=""` is
    # neither the positive case (absent) nor the negative one — it is invalid
    # markup, and a fixture emitting it was an invalid control asserting a sign
    # it did not have.
    signed = f' sign="{sign}"' if sign else ''
    body = (f'<td><ix:nonFraction {element_id}name="{name}" contextRef="{ctx}" '
            f'unitRef="{unit}" scale="{scale}" decimals="-6"{signed} '
            f'format="ixt:num-dot-decimal">{shown}</ix:nonFraction></td>')
    table = (f'<html {_XMLNS}><body><table><tr><td>Total net sales</td>' + body
             + '</tr></table>')
    if hidden:            # a REAL hidden fact: inside ix:hidden, no visible row
        table = (f'<html {_XMLNS}><body><table><tr><td>Total net sales</td><td>-</td></tr>'
                 '</table><div style="display:none">' + body + '</div>')
    return (
        table
        + extra_element +
        '<div style="display:none"><ix:header><ix:resources>'
        '<xbrli:context id="c-1"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193'
        '</xbrli:identifier></xbrli:entity><xbrli:period>'
        '<xbrli:startDate>2026-01-01</xbrli:startDate>'
        '<xbrli:endDate>2026-03-31</xbrli:endDate></xbrli:period>'
        # DIMENSIONS LIVE IN A SCENARIO (XBRL 2.1 §4.7.4). They used to be
        # dropped bare into the context — a second fixture of exactly the class
        # round 5 is repairing: an invalid document standing in as the LAWFUL
        # control, which would have argued the new rule was over-strict.
        + (f'<xbrli:scenario>{dims}</xbrli:scenario>' if dims else '')
        + '</xbrli:context>'
        '<xbrli:context id="c-2"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193'
        '</xbrli:identifier></xbrli:entity><xbrli:period>'
        '<xbrli:startDate>2025-01-01</xbrli:startDate>'
        '<xbrli:endDate>2025-03-31</xbrli:endDate></xbrli:period></xbrli:context>'
        '<xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>'
        '<xbrli:unit id="shares"><xbrli:measure>xbrli:shares</xbrli:measure></xbrli:unit>'
        '</ix:resources></ix:header></div></body></html>')


def _bind(doc=None, **over):
    kw = dict(inline_element_id="f-48", concept="us-gaap:Revenues",
              context_id="c-1", unit_ref="usd", unit_name="iso4217:USD",
              is_divide="0", period_type="duration", start_date="2026-01-01",
              end_date="2026-04-01",      # STORED form: the filing says 03-31
              dims=(), entity_cik=CIK, raw_value="390,000,000")
    kw.update(over)
    # THE CONCEPT'S IDENTITY IS REQUIRED, so the helper supplies it once for
    # every test in this file rather than each call repeating it. It is read
    # from THIS fixture's own declaration, and it tracks whatever `concept` the
    # caller passed, so a test that overrides the concept still asserts against
    # the identity its own document states.
    for key, value in _identity_kw(kw["concept"]).items():
        kw.setdefault(key, value)
    return bind_graph_fact(doc if doc is not None else _doc(), **kw)


# ------------------------------------------------------- exact arithmetic ----

# IDENTITY CHANGE (SEQ 265 C, corrected by SEQ 266 §1): the old pair used a
# raw with a 22-digit fraction the writer provably never stores; my first
# replacement used a fractional raw that the FLOAT formatter cannot reach
# either (binary floats hold no .001 at 1e25 — grammar shape is not
# formatter reachability). The 29-significant-digit exactness LAW is
# unchanged and now rides the INTEGER writer lane, whose f"{v:,}" output is
# exact at THIS fixture's 35-digit length (no any-length claim: CPython
# refuses int→str past its ~4,300-digit conversion gate — SEQ 271):
D29 = "10000000000000000000000000001"                   # 29 significant digits
D29_RAW = "10,000,000,000,000,000,000,000,000,001,000,000"   # ×10^6, int lane
D29_RAW_WRONG = "10,000,000,000,000,000,000,000,000,000,000,000"


def test_RED_exact_number_pair_at_29_digits():
    """THE pair: the CORRECT value must verify and the ROUNDED-WRONG value must
    not. `reconcile` multiplied at the default 28-digit context, so it did
    exactly the opposite — the worst possible outcome, and the same defect the
    Core converter had already removed from its own arithmetic."""
    assert reconcile(D29, _NUM_DOT_DECIMAL, 6, "", D29_RAW) is True
    assert reconcile(D29, _NUM_DOT_DECIMAL, 6, "", D29_RAW_WRONG) is False


def test_RED_exactness_holds_through_the_whole_binding():
    doc = _doc(shown=D29)
    bound, why = _bind(doc, raw_value=D29_RAW)
    assert bound is not None, why
    # the exactness proof IS the successful bind: reconcile gates it at 29
    # digits (pinned directly above); the record reports the printed fields
    assert bound["printed_value"] == Decimal(D29)
    assert bound["evidence"]["scale"] == 6
    assert _bind(doc, raw_value=D29_RAW_WRONG)[0] is None


def test_RED_a_malformed_sign_abstains_rather_than_reading_as_positive():
    """`printed_value` negated only on '-', so ANY other sign silently meant
    positive. A malformed sign is malformed evidence: abstain (law step 7)."""
    assert printed_value("390", _NUM_DOT_DECIMAL, "-") == Decimal(-390)
    assert printed_value("390", _NUM_DOT_DECIMAL, "") == Decimal(390)
    assert printed_value("390", _NUM_DOT_DECIMAL, "x") is None
    assert _bind(_doc(sign="x"))[0] is None


# ------------------------------------------------ the identity law, step 3 ----

def test_RED_fallback_is_permitted_ONLY_when_the_short_id_is_blank():
    """The behaviour was INVERTED: any id failure fell through to the fallback,
    so wrong, padded, numeric and duplicate ids were all rescued."""
    for wrong in ("f-99", " f-48", "48", "F-48"):
        bound, why = _bind(inline_element_id=wrong)
        assert bound is None, f"a non-blank WRONG id was rescued: {wrong}"
        assert "fallback" not in (why or ""), why


def test_RED_a_blank_short_id_uses_the_unique_identity_fallback():
    doc = _doc(element_id="")                       # element genuinely has no id
    for blank in ("", None, "   "):
        bound, why = _bind(doc, inline_element_id=blank)
        assert bound is not None, why


def test_RED_the_fallback_abstains_when_it_is_not_unique():
    twin = ('<td><ix:nonFraction name="us-gaap:Revenues" contextRef="c-1" '
            'unitRef="usd" scale="6" decimals="-6" format="ixt:num-dot-decimal">390'
            '</ix:nonFraction></td>')
    doc = _doc(element_id="", extra_element=twin)
    assert _bind(doc, inline_element_id="")[0] is None


def test_RED_a_duplicate_id_abstains_and_is_never_rescued():
    dup = ('<td><ix:nonFraction id="f-48" name="us-gaap:Revenues" '
           'contextRef="c-1" unitRef="usd" scale="6" decimals="-6" '
           'format="ixt:num-dot-decimal">390</ix:nonFraction></td>')
    assert _bind(_doc(extra_element=dup))[0] is None


# ------------------------------------- the identity law, steps 5-7 (checks) ----

@pytest.mark.parametrize("field,value", [
    ("concept", "us-gaap:CostOfRevenue"),          # wrong concept
    ("context_id", "c-2"),                          # wrong context
    ("unit_ref", "shares"),                         # wrong unit reference
    ("entity_cik", "1018724"),                      # a DIFFERENT company
    ("start_date", "2025-01-01"),                   # wrong period
    ("end_date", "2026-07-01"),
])
def test_RED_a_mismatched_identity_component_abstains(field, value):
    assert _bind(**{field: value})[0] is None, f"{field}={value} was accepted"


def test_RED_a_dimension_set_mismatch_abstains():
    """A complete dimension set is a CLAIM: extra, missing or different members
    all abstain — a member elsewhere in the filing proves nothing."""
    axis, mem = "us-gaap:StatementBusinessSegmentsAxis", "aapl:IPhoneMember"
    dims = (f'<xbrldi:explicitMember dimension="{axis}">{mem}'
            f'</xbrldi:explicitMember>')
    doc = _doc(dims=dims)
    claim = _graph_dims((axis, mem))
    assert _bind(doc, dims=())[0] is None                  # claimed none
    assert _bind(_doc(), dims=claim)[0] is None            # claimed one
    assert _bind(doc, dims=claim)[0] is not None           # exactly right


def test_RED_a_hidden_element_without_local_evidence_abstains():
    assert _bind(_doc(hidden=True))[0] is None


def test_RED_the_semantic_unit_must_agree_with_the_filings_Unit_node():
    """`unit_ref` is a bare pointer; the Unit node carries the meaning."""
    assert _bind(unit_name="xbrli:shares")[0] is None
    assert _bind(is_divide="1")[0] is None


def test_RED_shares_and_per_share_units_are_lawful_not_rejected():
    """Only plain USD was supported, so lawful share counts and USD-per-share
    facts could never bind at all."""
    doc = _doc(unit="shares", scale="0", shown="16,000,000")
    bound, why = bind_graph_fact(
        doc, inline_element_id="f-48", concept="us-gaap:Revenues",
        context_id="c-1", unit_ref="shares", unit_name="shares",
        is_divide="0", period_type="duration", start_date="2026-01-01",
        end_date="2026-04-01", dims=(), entity_cik=CIK, raw_value="16,000,000",
        **_identity_kw("us-gaap:Revenues"))
    assert bound is not None, why
    assert bound["unit_measures_expanded"] == \
        (("http://www.xbrl.org/2003/instance", "shares"),)


def test_RED_comma_values_parse_and_graph_parens_now_refuse():
    """IDENTITY CHANGE (SEQ 265 D): this test was
    `test_RED_comma_and_accounting_negative_values_parse` and asserted
    `parse_raw("(1,234.50)") == Decimal("-1234.50")`. A parenthesised
    string is NEITHER an XSD decimal NOR an exact canonical grouped
    transport form, so it refuses on that authority alone — not because
    the writer happens not to emit one. The SOURCE lane's
    accounting-negative law is pinned separately at the bind door."""
    assert parse_raw("113,743,000,000") == Decimal("113743000000")
    assert parse_raw("(1,234.50)") is None


# ------------------------------------------- crashes and fail-open closures ----

def test_RED_a_non_string_element_id_is_malformed_not_a_crash():
    """A numeric id crashed on .strip(). It is malformed input, not a typo."""
    for bad in (48, 3.5, [], {}):
        bound, why = _bind(inline_element_id=bad)
        assert bound is None and why == "malformed_element_id", bad


def test_RED_a_malformed_is_divide_flag_is_malformed_not_a_crash():
    """`is_divide='yes'` crashed on int(); '2' passed by accident. It is a flag."""
    for bad in ("yes", "2", "", None, "true"):
        bound, why = _bind(is_divide=bad)
        assert bound is None and why == "malformed_is_divide", bad


def test_RED_an_absent_entity_identifier_abstains():
    """'' == '' was fail-open: an ABSENT identifier proves nothing."""
    no_entity = _doc().replace(
        '<xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193</xbrli:identifier></xbrli:entity>',
        '', 1)
    assert _bind(no_entity, entity_cik="")[0] is None
    assert _bind(no_entity)[0] is None
    assert _bind(entity_cik="")[0] is None


def test_RED_a_duplicate_context_id_abstains():
    """Last-wins silently picked one of two conflicting contexts."""
    dup = ('<xbrli:context id="c-1"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193'
           '</xbrli:identifier></xbrli:entity><xbrli:period>'
           '<xbrli:startDate>2020-01-01</xbrli:startDate>'
           '<xbrli:endDate>2020-03-31</xbrli:endDate></xbrli:period>'
           '</xbrli:context>')
    doc = _doc().replace('<xbrli:unit id="usd">', dup + '<xbrli:unit id="usd">', 1)
    bound, why = _bind(doc, concept_namespace=_NS_GAAP_VARIANT)
    assert bound is None and "duplicate_context_id" in why


def test_RED_the_expected_numeric_object_is_returned_for_field_wise_binding():
    """Callers must bind the THREE fields; the binder supplies what the filing
    actually prints so nobody recomputes it."""
    bound, _ = _bind()
    assert bound["printed_value"] == Decimal(390)
    assert Decimal(1).scaleb(bound["evidence"]["scale"]) == Decimal("1E+6")


def test_RED_the_LIVE_unit_spellings_are_the_ones_that_must_work():
    """The synthetic `xbrli:shares` does not exist in the graph. The real
    spellings are `shares` (is_divide=0) and `iso4217:USDshares` (is_divide=1)."""
    shares_doc = _doc(unit="shares", scale="0", shown="16,000,000")
    bound, why = bind_graph_fact(
        shares_doc, inline_element_id="f-48", concept="us-gaap:Revenues",
        context_id="c-1", unit_ref="shares", unit_name="shares", is_divide="0",
        period_type="duration", start_date="2026-01-01", end_date="2026-04-01",
        dims=(), entity_cik=CIK, raw_value="16,000,000",
        **_identity_kw("us-gaap:Revenues"))
    assert bound is not None, why
    per_share_doc = _doc(unit="usdps", scale="0", shown="1.42").replace(
        '<xbrli:unit id="shares"><xbrli:measure>xbrli:shares</xbrli:measure></xbrli:unit>',
        '<xbrli:unit id="usdps"><xbrli:divide>'
        '<xbrli:unitNumerator><xbrli:measure>iso4217:USD</xbrli:measure>'
        '</xbrli:unitNumerator><xbrli:unitDenominator>'
        '<xbrli:measure>xbrli:shares</xbrli:measure></xbrli:unitDenominator>'
        '</xbrli:divide></xbrli:unit>', 1)
    bound, why = bind_graph_fact(
        per_share_doc, inline_element_id="f-48", concept="us-gaap:Revenues",
        context_id="c-1", unit_ref="usdps", unit_name="iso4217:USDshares",
        is_divide="1", period_type="duration", start_date="2026-01-01",
        end_date="2026-04-01", dims=(), entity_cik=CIK, raw_value="1.42",
        **_identity_kw("us-gaap:Revenues"))
    assert bound is not None, why


# --------------------------------------------------------------------------
# #827 ROUND 4 — THE BINDER ACCEPTED MALFORMED XBRL STRUCTURE, AND ACCEPTED A
# LAWFUL DOCUMENT UNDER THE WRONG PERIOD KIND.
#
# The parser reads each context/unit child with `find()`, which returns the
# FIRST match and drops contradictory extras in silence. Ten shapes were driven
# through the PUBLIC door (`attach_event_xbrl`) and every one ATTACHED while the
# whole suite stayed green.
#
# Two different severities, deliberately kept apart:
#   * (a)-(e) need a MALFORMED filing. Real-corpus cost of refusing them: ZERO
#     Superseded by the round-5 measurement, which is a RUNNABLE receipt rather
#     than a number copied into prose: receipts_827/structure_census.py over
#     the full cache, with its own must-catch/must-allow self-test.
#   * (f) needs NO malformed markup at all — a lawful DURATION context binds a
#     graph row typed `instant`, because the binder never compares the period
#     KIND it was asked for against the kind the document declares.
#
# Each rule below carries its lawful MUST-ALLOW control: a checker is only
# correct if it is correct in BOTH directions.
# --------------------------------------------------------------------------

_LAWFUL_PERIOD = ('<xbrli:period><xbrli:startDate>2026-01-01</xbrli:startDate>'
                  '<xbrli:endDate>2026-03-31</xbrli:endDate></xbrli:period>')
_LAWFUL_UNIT = ('<xbrli:unit id="usd"><xbrli:measure>iso4217:USD'
                '</xbrli:measure></xbrli:unit>')
_DIVIDE = ('<xbrli:divide><xbrli:unitNumerator><xbrli:measure>iso4217:USD'
           '</xbrli:measure></xbrli:unitNumerator><xbrli:unitDenominator>'
           '<xbrli:measure>xbrli:shares</xbrli:measure></xbrli:unitDenominator>'
           '</xbrli:divide>')


def _period(markup):
    """The lawful c-1 period replaced by `markup` — one exact substitution."""
    doc = _doc()
    assert doc.count(_LAWFUL_PERIOD) == 1, "the period anchor is not unique"
    return doc.replace(_LAWFUL_PERIOD, markup)


def _unit(markup):
    doc = _doc()
    assert doc.count(_LAWFUL_UNIT) == 1, "the unit anchor is not unique"
    return doc.replace(_LAWFUL_UNIT, markup)


def test_827_MUST_ALLOW_the_lawful_control_still_binds():
    """The control that makes every refusal below meaningful."""
    bound, why = _bind()
    assert bound is not None, why


@pytest.mark.parametrize("label,markup", [
    ("instant AND duration in one period",
     '<xbrli:period><xbrli:startDate>2026-01-01</xbrli:startDate>'
     '<xbrli:endDate>2026-03-31</xbrli:endDate>'
     '<xbrli:instant>2026-03-31</xbrli:instant></xbrli:period>'),
    ("forever AND duration in one period",
     '<xbrli:period><xbrli:forever/><xbrli:startDate>2026-01-01</xbrli:startDate>'
     '<xbrli:endDate>2026-03-31</xbrli:endDate></xbrli:period>'),
    ("two period containers",
     '<xbrli:period><xbrli:startDate>2026-01-01</xbrli:startDate>'
     '<xbrli:endDate>2026-03-31</xbrli:endDate></xbrli:period>'
     '<xbrli:period><xbrli:startDate>2019-01-01</xbrli:startDate>'
     '<xbrli:endDate>2019-03-31</xbrli:endDate></xbrli:period>'),
    # THE WORST SHAPE: start and end are two independent `find()` calls, so a
    # start/end pair DECLARED NOWHERE in the filing is synthesized across two
    # containers. That is fabricated evidence, not merely mis-selected evidence.
    ("a period pair SYNTHESIZED across two containers",
     '<xbrli:period><xbrli:startDate>2026-01-01</xbrli:startDate></xbrli:period>'
     '<xbrli:period><xbrli:endDate>2026-03-31</xbrli:endDate></xbrli:period>'),
    ("duplicate startDate",
     '<xbrli:period><xbrli:startDate>2026-01-01</xbrli:startDate>'
     '<xbrli:startDate>2019-01-01</xbrli:startDate>'
     '<xbrli:endDate>2026-03-31</xbrli:endDate></xbrli:period>'),
])
def test_827_a_MALFORMED_period_structure_never_binds(label, markup):
    bound, why = _bind(_period(markup))
    assert bound is None, f"{label}: bound instead of abstaining"


def test_827_two_entity_identifiers_never_bind():
    """A context naming two different filers cannot identify one. The first was
    silently taken, so facts bound for filer #1 while the markup claimed both."""
    doc = _doc().replace(
        '<xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193</xbrli:identifier></xbrli:entity>'
        '<xbrli:period><xbrli:startDate>2026-01-01</xbrli:startDate>',
        '<xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193</xbrli:identifier>'
        '<xbrli:identifier scheme="http://www.sec.gov/CIK">0000789019</xbrli:identifier></xbrli:entity>'
        '<xbrli:period><xbrli:startDate>2026-01-01</xbrli:startDate>', 1)
    bound, why = bind_graph_fact(
        doc, inline_element_id="f-48", concept="us-gaap:Revenues",
        context_id="c-1", unit_ref="usd", unit_name="iso4217:USD",
        is_divide="0", period_type="duration", start_date="2026-01-01",
        end_date="2026-04-01", dims=(), entity_cik=CIK,
        raw_value="390,000,000", **_identity_kw("us-gaap:Revenues"))
    assert bound is None, "a two-filer context bound as one filer"


@pytest.mark.parametrize("label,markup,unit_name,is_divide", [
    ("a plain measure AND a divide in one unit",
     f'<xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure>'
     f'{_DIVIDE}</xbrli:unit>', "iso4217:USDshares", "1"),
    ("two divide containers",
     f'<xbrli:unit id="usd">{_DIVIDE}{_DIVIDE}</xbrli:unit>',
     "iso4217:USDshares", "1"),
    ("two unitNumerator containers",
     '<xbrli:unit id="usd"><xbrli:divide>'
     '<xbrli:unitNumerator><xbrli:measure>iso4217:USD</xbrli:measure>'
     '</xbrli:unitNumerator>'
     '<xbrli:unitNumerator><xbrli:measure>iso4217:EUR</xbrli:measure>'
     '</xbrli:unitNumerator><xbrli:unitDenominator>'
     '<xbrli:measure>xbrli:shares</xbrli:measure></xbrli:unitDenominator>'
     '</xbrli:divide></xbrli:unit>', "iso4217:USDshares", "1"),
])
def test_827_a_MALFORMED_unit_structure_never_binds(label, markup, unit_name,
                                                    is_divide):
    """The two-numerator case is the sharpest: a unit declaring BOTH USD and
    EUR numerators bound as USD — a second currency vanished in silence."""
    bound, why = _bind(_unit(markup), unit_name=unit_name, is_divide=is_divide)
    assert bound is None, f"{label}: bound instead of abstaining"


def test_827_MUST_ALLOW_a_lawful_divide_unit_with_ONE_container_still_binds():
    """COMPOUND UNITS STAY LAWFUL. The rule counts CONTAINERS, never measures:
    one numerator and one denominator, each free to carry several measures.
    Requiring one measure per container would reject lawful filings — the
    over-catching mistake, which is as bad as under-catching."""
    bound, why = _bind(_unit(f'<xbrli:unit id="usd">{_DIVIDE}</xbrli:unit>'),
                       unit_name="iso4217:USDshares", is_divide="1")
    assert bound is not None, why


def test_827_a_lawful_DURATION_document_never_binds_an_INSTANT_row():
    """NO MALFORMED MARKUP IS INVOLVED. The document is a lawful duration; the
    graph row merely asks for an instant. The binder set `stored_start=None`
    whenever an instant was requested and compared only the end, so the
    document's own period KIND was never read. This is the one shape that needs
    nothing wrong in the filing."""
    bound, why = _bind(period_type="instant", start_date="2026-04-01",
                       end_date="2026-04-01")
    assert bound is None, "a duration context bound as an instant"


def test_827_a_lawful_INSTANT_document_never_binds_a_DURATION_row():
    """The mirror. It was refused only by accident — a blank start reading as
    'malformed_period' — so it is pinned deliberately here."""
    bound, why = _bind(_period('<xbrli:period><xbrli:instant>2026-03-31'
                               '</xbrli:instant></xbrli:period>'))
    assert bound is None, "an instant context bound as a duration"


def test_827_MUST_ALLOW_a_lawful_INSTANT_document_binds_an_INSTANT_row():
    """The control for the two rules above: matching kinds must still bind."""
    bound, why = _bind(_period('<xbrli:period><xbrli:instant>2026-03-31'
                               '</xbrli:instant></xbrli:period>'),
                       period_type="instant", start_date="2026-04-01",
                       end_date="2026-04-01")
    assert bound is not None, why


# --------------------------------------------------------------------------
# #827 ROUND 4, blocker 2 — the fixed-zero branch returned BEFORE the sign was
# validated, so malformed markup produced a VALUE instead of an abstention.
# Reachable through the public event door, not a helper curiosity.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("bad", ["x", " - ", "+", "--", " ", "−"])
def test_827_a_malformed_sign_abstains_even_on_FIXED_ZERO(bad):
    from driver.relocation.inline_html import printed_value
    assert printed_value("0", _FIXED_ZERO, bad) is None, \
        f"sign={bad!r} produced a value from malformed markup"


@pytest.mark.parametrize("ok", [None, "", "-"])
def test_827_MUST_ALLOW_lawful_fixed_zero_signs_still_return_zero(ok):
    """The control. 193,026 fixed-zero tags in the cache carry no sign and 936
    carry '-'; both must keep returning zero, or the fix costs real facts."""
    from decimal import Decimal
    from driver.relocation.inline_html import printed_value
    assert printed_value("0", _FIXED_ZERO, ok) == Decimal(0)


@pytest.mark.parametrize("label,entity", [
    ("no entity element at all", ''),
    ("an entity carrying no identifier", '<xbrli:entity></xbrli:entity>'),
])
def test_827_a_context_without_ONE_identifier_refuses_as_MALFORMED(label, entity):
    """XBRL 2.1 §4.7 requires one entity with one identifier; typed dimensions
    live in segment/scenario and never substitute for them.

    ROUND 5 CORRECTED THE OWNER OF THIS RULE. It used to assert `entity_missing`,
    on the recorded belief that absence was 'already refused, more precisely,
    by a smaller existing path'. THAT BELIEF WAS FALSE: the identifier was read
    with a subtree-wide `find()`, so one sitting outside any entity — even
    inside `period` — satisfied it, and a context with no entity at all still
    bound. Absence of the CONTAINER is a structure fault and says so; absence
    of the VALUE keeps `entity_missing` (proven in the blank-identifier test).
    A rule relied upon must be a rule proven, or the reliance is an assumption."""
    doc = _doc().replace(
        '<xbrli:context id="c-1"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193'
        '</xbrli:identifier></xbrli:entity>',
        f'<xbrli:context id="c-1">{entity}', 1)
    bound, why = _bind(doc, concept_namespace=_NS_GAAP_VARIANT)
    assert bound is None and why == 'exact_id_malformed_context_structure', why


# --------------------------------------------------------------------------
# #827 ROUND 5 — CONTAINMENT. Every value was read with `find()`, which searches
# EVERY DESCENDANT: the parser checked that a value EXISTS, never that it sits
# where XBRL 2.1 puts it. Seven shapes attached with reason `ok`, the worst
# being a context carrying NEITHER an entity NOR a period — a filer id and two
# dates simply floating loose inside it.
#
# XBRL 2.1 §4.7/§4.8 fix the containment exactly:
#   context -> ONE entity  (-> ONE identifier, at most one segment)
#           -> ONE period  (-> instant | startDate+endDate | forever)
#           -> at most one scenario
#   unit    -> direct measures  XOR  ONE divide (-> ONE numerator and ONE
#              denominator, each carrying one or more measures)
#
# COMPOUND UNITS STAY LAWFUL: a container may hold several measures. The rule
# counts CONTAINERS and their PLACE, never the number of measures.
#
# THE REASON IS PART OF THE CONTRACT. The round-4 tests asserted only that
# nothing attached, so malformed structure could be — and was — reported as
# `duplicate_context_id`. A refusal that lies about why is not a correct
# refusal, and an outcome-only test can never see the lie. These pin the EXACT
# reason, and each MUST-CATCH is paired with a lawful MUST-ALLOW.
# --------------------------------------------------------------------------

_LAWFUL_ENTITY = ('<xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193'
                  '</xbrli:identifier></xbrli:entity>')
_LAWFUL_BODY = _LAWFUL_ENTITY + _LAWFUL_PERIOD
_DATES = ('<xbrli:startDate>2026-01-01</xbrli:startDate>'
          '<xbrli:endDate>2026-03-31</xbrli:endDate>')
_IDENT = '<xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193</xbrli:identifier>'


def _context(markup):
    """The whole lawful c-1 body (entity + period) replaced by `markup`."""
    doc = _doc()
    assert doc.count(_LAWFUL_BODY) == 1, "the context body anchor is not unique"
    return doc.replace(_LAWFUL_BODY, markup)


@pytest.mark.parametrize("label,body", [
    # ---- the identifier, and where it is allowed to live -------------------
    ("a bare identifier with no entity at all", _IDENT + _LAWFUL_PERIOD),
    ("an identifier sitting OUTSIDE its entity",
     '<xbrli:entity></xbrli:entity>' + _IDENT + _LAWFUL_PERIOD),
    ("an identifier buried in the PERIOD",
     '<xbrli:entity></xbrli:entity><xbrli:period>' + _IDENT + _DATES
     + '</xbrli:period>'),
    ("two entity containers", _LAWFUL_ENTITY + _LAWFUL_ENTITY + _LAWFUL_PERIOD),
    # ISOLATES THE ENTITY COUNT. With an identifier in BOTH entities the stray
    # guard catches it first, so the count rule is never the one under test —
    # a mutation battery proved exactly that by escaping. Here the second
    # entity is EMPTY: every other check passes and only "exactly one entity"
    # can refuse it.
    ("two entities, only the first carrying an identifier",
     _LAWFUL_ENTITY + '<xbrli:entity></xbrli:entity>' + _LAWFUL_PERIOD),
    ("two periods, only the first carrying dates",
     _LAWFUL_ENTITY + _LAWFUL_PERIOD + '<xbrli:period></xbrli:period>'),
    ("two identifiers in one entity",
     '<xbrli:entity>' + _IDENT
     + '<xbrli:identifier scheme="http://www.sec.gov/CIK">0000789019</xbrli:identifier></xbrli:entity>'
     + _LAWFUL_PERIOD),
    # ---- the dates, and where they are allowed to live ---------------------
    ("dates with no period element at all", _LAWFUL_ENTITY + _DATES),
    ("dates OUTSIDE an empty period",
     _LAWFUL_ENTITY + '<xbrli:period></xbrli:period>' + _DATES),
    ("dates buried in the ENTITY",
     '<xbrli:entity>' + _IDENT + _DATES + '</xbrli:entity>'
     '<xbrli:period></xbrli:period>'),
    ("dates under an arbitrary wrapper inside the period",
     _LAWFUL_ENTITY + '<xbrli:period><div>' + _DATES + '</div></xbrli:period>'),
    ("two period containers", _LAWFUL_ENTITY + _LAWFUL_PERIOD + _LAWFUL_PERIOD),
    # ---- the period form itself --------------------------------------------
    ("duplicate forever",
     _LAWFUL_ENTITY + '<xbrli:period><xbrli:forever/><xbrli:forever/>'
     '</xbrli:period>'),
    ("forever beside dates",
     _LAWFUL_ENTITY + '<xbrli:period><xbrli:forever/>' + _DATES
     + '</xbrli:period>'),
    ("a start with no end",
     _LAWFUL_ENTITY + '<xbrli:period><xbrli:startDate>2026-01-01'
     '</xbrli:startDate></xbrli:period>'),
    ("duplicate instant",
     _LAWFUL_ENTITY + '<xbrli:period><xbrli:instant>2026-03-31</xbrli:instant>'
     '<xbrli:instant>2019-01-01</xbrli:instant></xbrli:period>'),
    ("an empty period declaring no form at all",
     _LAWFUL_ENTITY + '<xbrli:period></xbrli:period>'),
    # ---- the dimension containers ------------------------------------------
    ("two segments — dimensions SYNTHESIZED across containers",
     '<xbrli:entity>' + _IDENT
     + '<xbrli:segment><xbrldi:explicitMember dimension="us-gaap:A1">'
       'us-gaap:M1</xbrldi:explicitMember></xbrli:segment>'
       '<xbrli:segment><xbrldi:explicitMember dimension="us-gaap:A2">'
       'us-gaap:M2</xbrldi:explicitMember></xbrli:segment></xbrli:entity>'
     + _LAWFUL_PERIOD),
    ("an explicitMember in NEITHER segment nor scenario",
     '<xbrli:entity>' + _IDENT
     + '<xbrldi:explicitMember dimension="us-gaap:A1">us-gaap:M1'
       '</xbrldi:explicitMember></xbrli:entity>' + _LAWFUL_PERIOD),
])
def test_827R5_a_MISPLACED_context_element_refuses_with_ITS_OWN_reason(label,
                                                                       body):
    """`exact_id_` is the LANE that looked the element up (the short id, never
    the fallback); the reason itself is the rest. Both are asserted, so neither
    the lane nor the cause can drift unnoticed."""
    bound, why = _bind(_context(body))
    assert bound is None, f"{label}: ATTACHED"
    assert why == 'exact_id_malformed_context_structure', f"{label}: {why!r}"


@pytest.mark.parametrize("label,body,dims", [
    ("the lawful duration control", _LAWFUL_BODY, ()),
    ("a lawful instant",
     _LAWFUL_ENTITY + '<xbrli:period><xbrli:instant>2026-03-31'
     '</xbrli:instant></xbrli:period>', ()),
    ("a lawful segment carrying one explicitMember",
     '<xbrli:entity>' + _IDENT
     + '<xbrli:segment><xbrldi:explicitMember dimension="us-gaap:A1">'
       'us-gaap:M1</xbrldi:explicitMember></xbrli:segment></xbrli:entity>'
     + _LAWFUL_PERIOD, _graph_dims(("us-gaap:A1", "us-gaap:M1"))),
    ("a lawful scenario carrying one explicitMember",
     _LAWFUL_ENTITY + _LAWFUL_PERIOD
     + '<xbrli:scenario><xbrldi:explicitMember dimension="us-gaap:A1">'
       'us-gaap:M1</xbrldi:explicitMember></xbrli:scenario>',
     _graph_dims(("us-gaap:A1", "us-gaap:M1"))),
    ("a lawful segment AND a lawful scenario — one of each is allowed",
     '<xbrli:entity>' + _IDENT
     + '<xbrli:segment><xbrldi:explicitMember dimension="us-gaap:A1">'
       'us-gaap:M1</xbrldi:explicitMember></xbrli:segment></xbrli:entity>'
     + _LAWFUL_PERIOD
     + '<xbrli:scenario><xbrldi:explicitMember dimension="us-gaap:A2">'
       'us-gaap:M2</xbrldi:explicitMember></xbrli:scenario>',
     _graph_dims(("us-gaap:A1", "us-gaap:M1"), ("us-gaap:A2", "us-gaap:M2"))),
])
def test_827R5_MUST_ALLOW_lawful_context_shapes_still_bind(label, body, dims):
    """Without these the structure rule could refuse everything and look right."""
    over = dict(dims=dims)
    if 'instant' in body:
        over.update(period_type='instant', start_date='2026-04-01')
    bound, why = _bind(_context(body), **over)
    assert bound is not None, f"{label}: refused as {why!r}"


@pytest.mark.parametrize("label,markup,unit_name,is_divide", [
    ("an orphan unitNumerator with no divide at all",
     '<xbrli:unit id="usd"><xbrli:unitNumerator><xbrli:measure>iso4217:USD'
     '</xbrli:measure></xbrli:unitNumerator></xbrli:unit>', "iso4217:USD", "0"),
    ("an orphan unitDenominator with no divide at all",
     '<xbrli:unit id="usd"><xbrli:unitDenominator><xbrli:measure>iso4217:USD'
     '</xbrli:measure></xbrli:unitDenominator></xbrli:unit>', "iso4217:USD", "0"),
    ("a plain measure beside an orphan container",
     '<xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure>'
     '<xbrli:unitNumerator><xbrli:measure>xbrli:shares</xbrli:measure>'
     '</xbrli:unitNumerator></xbrli:unit>', "iso4217:USD", "0"),
    ("a measure OUTSIDE both divide containers",
     '<xbrli:unit id="usd"><xbrli:divide><xbrli:unitNumerator>'
     '<xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unitNumerator>'
     '<xbrli:measure>xbrli:shares</xbrli:measure><xbrli:unitDenominator>'
     '<xbrli:measure>xbrli:shares</xbrli:measure></xbrli:unitDenominator>'
     '</xbrli:divide></xbrli:unit>', "iso4217:USDshares", "1"),
    # ISOLATES THE CONTAINER COUNT, for the same reason as the entity case: a
    # second numerator carrying MEASURES is caught by the stray-measure guard,
    # so the count rule escaped its mutation. An EMPTY second container leaves
    # every measure count correct, and only "exactly one numerator" refuses it.
    ("a second, EMPTY unitNumerator beside a lawful one",
     '<xbrli:unit id="usd"><xbrli:divide><xbrli:unitNumerator>'
     '<xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unitNumerator>'
     '<xbrli:unitNumerator></xbrli:unitNumerator><xbrli:unitDenominator>'
     '<xbrli:measure>xbrli:shares</xbrli:measure></xbrli:unitDenominator>'
     '</xbrli:divide></xbrli:unit>', "iso4217:USDshares", "1"),
    ("a second, EMPTY unitDenominator beside a lawful one",
     '<xbrli:unit id="usd"><xbrli:divide><xbrli:unitNumerator>'
     '<xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unitNumerator>'
     '<xbrli:unitDenominator><xbrli:measure>xbrli:shares</xbrli:measure>'
     '</xbrli:unitDenominator><xbrli:unitDenominator></xbrli:unitDenominator>'
     '</xbrli:divide></xbrli:unit>', "iso4217:USDshares", "1"),
    # ISOLATES "a side must carry a measure". The denominator used the BARE
    # word `shares`, so once round 7 required measures to be QNames that rule
    # refused the fixture first and the empty-numerator rule was never
    # exercised — its mutation escaped. Every OTHER part of this unit is now
    # lawful, so only the empty side can refuse it.
    ("a numerator carrying no measure at all",
     '<xbrli:unit id="usd"><xbrli:divide><xbrli:unitNumerator>'
     '</xbrli:unitNumerator><xbrli:unitDenominator><xbrli:measure>xbrli:shares'
     '</xbrli:measure></xbrli:unitDenominator></xbrli:divide></xbrli:unit>',
     "iso4217:USDshares", "1"),
    ("a divide under an arbitrary wrapper",
     f'<xbrli:unit id="usd"><div>{_DIVIDE}</div></xbrli:unit>',
     "iso4217:USDshares", "1"),
    ("a unit declaring nothing at all",
     '<xbrli:unit id="usd"></xbrli:unit>', "iso4217:USD", "0"),
])
def test_827R5_a_MISPLACED_unit_element_refuses_with_ITS_OWN_reason(
        label, markup, unit_name, is_divide):
    bound, why = _bind(_unit(markup), unit_name=unit_name, is_divide=is_divide)
    assert bound is None, f"{label}: ATTACHED"
    assert why == 'exact_id_malformed_unit_structure', f"{label}: {why!r}"


def test_827R6_a_NESTED_context_never_binds():
    """A context inside a context is not a shape XBRL 2.1 has: the inner one's
    children are the outer one's descendants, so a second filer or period could
    ride inside the first. Corpus cost of refusing it: 0 of 733,172."""
    bound, why = _bind(_context(
        _ident() + _LAWFUL_PERIOD
        + '<xbrli:context id="inner"><xbrli:entity><xbrli:identifier '
          'scheme="http://www.sec.gov/CIK">0000789019</xbrli:identifier>'
          '</xbrli:entity></xbrli:context>'))
    assert bound is None and why == 'exact_id_malformed_context_structure', why


@pytest.mark.parametrize("label,markup,unit_name,is_divide", [
    ("a unit nested inside a unit",
     '<xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure>'
     '<xbrli:unit id="inner"><xbrli:measure>iso4217:EUR</xbrli:measure>'
     '</xbrli:unit></xbrli:unit>', "iso4217:USD", "0"),
    # A ratio of a thing to ITSELF measures nothing — it is the number 1 wearing
    # a unit. Corpus cost of refusing it: 0 of 15,210.
    ("a divide whose numerator and denominator are the SAME measure",
     '<xbrli:unit id="usd"><xbrli:divide><xbrli:unitNumerator>'
     '<xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unitNumerator>'
     '<xbrli:unitDenominator><xbrli:measure>iso4217:USD</xbrli:measure>'
     '</xbrli:unitDenominator></xbrli:divide></xbrli:unit>',
     "iso4217:USDiso4217:USD", "1"),
])
def test_827R6_a_NESTED_or_SELF_RATIO_unit_never_binds(label, markup, unit_name,
                                                        is_divide):
    bound, why = _bind(_unit(markup), unit_name=unit_name, is_divide=is_divide)
    assert bound is None, f"{label}: ATTACHED"
    assert why == 'exact_id_malformed_unit_structure', f"{label}: {why!r}"


@pytest.mark.parametrize("label,markup,unit_name,is_divide", [
    ("a lawful plain unit", _LAWFUL_UNIT, "iso4217:USD", "0"),
    ("a lawful divide unit",
     f'<xbrli:unit id="usd">{_DIVIDE}</xbrli:unit>', "iso4217:USDshares", "1"),
    # THE over-catching guard: several measures in ONE container is a COMPOUND
    # unit and is lawful. The binder must carry it; refusing it is the
    # classifier's job downstream, not the parser's.
    ("a lawful divide with a COMPOUND numerator",
     '<xbrli:unit id="usd"><xbrli:divide><xbrli:unitNumerator>'
     '<xbrli:measure>iso4217:USD</xbrli:measure>'
     '<xbrli:measure>xbrli:shares</xbrli:measure></xbrli:unitNumerator>'
     '<xbrli:unitDenominator><xbrli:measure>utr:MWh</xbrli:measure>'
     '</xbrli:unitDenominator></xbrli:divide></xbrli:unit>',
     "iso4217:USDsharesutr:MWh", "1"),
    ("a lawful divide with a COMPOUND denominator",
     '<xbrli:unit id="usd"><xbrli:divide><xbrli:unitNumerator>'
     '<xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unitNumerator>'
     '<xbrli:unitDenominator><xbrli:measure>xbrli:shares</xbrli:measure>'
     '<xbrli:measure>utr:MWh</xbrli:measure></xbrli:unitDenominator>'
     '</xbrli:divide></xbrli:unit>', "iso4217:USDsharesutr:MWh", "1"),
])
def test_827R5_MUST_ALLOW_lawful_unit_shapes_still_bind(label, markup,
                                                        unit_name, is_divide):
    bound, why = _bind(_unit(markup), unit_name=unit_name, is_divide=is_divide)
    assert bound is not None, f"{label}: refused as {why!r}"


# ---- the reason must name what is actually wrong --------------------------

def test_827R5_a_GENUINE_duplicate_context_id_still_says_duplicate():
    """The truthful reason cuts BOTH ways: renaming malformed structure must not
    cost the duplicate-id diagnosis its own name."""
    doc = _doc()
    twin = ('<xbrli:context id="c-1"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193'
            '</xbrli:identifier></xbrli:entity><xbrli:period>'
            '<xbrli:startDate>2019-01-01</xbrli:startDate>'
            '<xbrli:endDate>2019-03-31</xbrli:endDate>'
            '</xbrli:period></xbrli:context>')
    bound, why = _bind(doc.replace('<xbrli:unit id="usd">', twin
                                   + '<xbrli:unit id="usd">', 1))
    assert bound is None and why == 'exact_id_duplicate_context_id', why


def test_827R5_a_GENUINE_duplicate_unit_id_still_says_duplicate():
    doc = _doc()
    twin = ('<xbrli:unit id="usd"><xbrli:measure>iso4217:EUR</xbrli:measure>'
            '</xbrli:unit>')
    bound, why = _bind(doc.replace('<xbrli:unit id="shares">',
                                   twin + '<xbrli:unit id="shares">', 1))
    assert bound is None and why == 'exact_id_duplicate_unit_id', why


def test_827R5_MALFORMED_structure_is_NEVER_called_a_duplicate_id():
    """THE round-4 defect: both poisons were the same `None`, so the consumer
    reported every malformed context as a repeated id. The abstention was safe;
    the stated cause was false, and no test could see it."""
    ctx_bound, ctx_why = _bind(_context(_IDENT + _LAWFUL_PERIOD))
    unit_bound, unit_why = _bind(_unit(
        '<xbrli:unit id="usd"><xbrli:unitNumerator><xbrli:measure>iso4217:USD'
        '</xbrli:measure></xbrli:unitNumerator></xbrli:unit>'))
    # BOTH halves, or the test passes for the wrong reason: before the fix these
    # markups ATTACHED, so "no duplicate in the reason" was true of `ok`.
    assert ctx_bound is None and unit_bound is None, "malformed markup ATTACHED"
    assert 'duplicate' not in ctx_why, ctx_why
    assert 'duplicate' not in unit_why, unit_why


# ---- ROUND 5b: a CRASH, and the sequence the schema fixes -----------------
# The dimension set was built by sorting `(dimension, member)` pairs straight
# out of the markup. An `<explicitMember>` with no `dimension=` contributed
# `None`, and sorting `None` against a string raises TypeError — so a filing
# with one good dimension and one nameless one CRASHED the public door instead
# of refusing the fact. Validate, THEN sort.
#
# XBRL 2.1 also fixes the ORDER of these children (xs:sequence), and order was
# not checked at all: a context stating its period before its entity, or a
# divide stating denominator before numerator, is not lawful markup.

@pytest.mark.parametrize("label,members", [
    ("a member with NO dimension= at all",
     '<xbrldi:explicitMember>a:M</xbrldi:explicitMember>'),
    ("a member with a BLANK dimension=",
     '<xbrldi:explicitMember dimension="">a:M</xbrldi:explicitMember>'),
    ("a member with a WHITESPACE dimension=",
     '<xbrldi:explicitMember dimension="   ">a:M</xbrldi:explicitMember>'),
    ("a member with no VALUE",
     '<xbrldi:explicitMember dimension="a:Ax"></xbrldi:explicitMember>'),
    ("a member whose value is whitespace",
     '<xbrldi:explicitMember dimension="a:Ax">   </xbrldi:explicitMember>'),
    # THE CRASH AS REPORTED: one lawful dimension beside one nameless one.
    ("ONE VALID DIMENSION PLUS ONE NAMELESS ONE — the reported crash",
     '<xbrldi:explicitMember dimension="a:Ax">a:M</xbrldi:explicitMember>'
     '<xbrldi:explicitMember>a:M2</xbrldi:explicitMember>'),
    ("valid plus blank-valued",
     '<xbrldi:explicitMember dimension="a:Ax">a:M</xbrldi:explicitMember>'
     '<xbrldi:explicitMember dimension="a:Ax2"></xbrldi:explicitMember>'),
])
def test_827R5_a_NAMELESS_dimension_REFUSES_and_never_crashes(label, members):
    """It must not raise. A crash is not a refusal: it takes down the whole
    event instead of parking one fact."""
    bound, why = _bind(_context(
        '<xbrli:entity>' + _IDENT + f'<xbrli:segment>{members}</xbrli:segment>'
        '</xbrli:entity>' + _LAWFUL_PERIOD))
    assert bound is None, f"{label}: ATTACHED"
    assert why == 'exact_id_malformed_context_structure', f"{label}: {why!r}"


@pytest.mark.parametrize("label,body", [
    ("period BEFORE entity", _LAWFUL_PERIOD + _LAWFUL_ENTITY),
    ("scenario BEFORE period",
     _LAWFUL_ENTITY + '<xbrli:scenario><xbrldi:explicitMember dimension="a:Ax">'
     'a:M</xbrldi:explicitMember></xbrli:scenario>' + _LAWFUL_PERIOD),
    ("segment BEFORE identifier",
     '<xbrli:entity><xbrli:segment><xbrldi:explicitMember dimension="a:Ax">'
     'a:M</xbrldi:explicitMember></xbrli:segment>' + _IDENT + '</xbrli:entity>'
     + _LAWFUL_PERIOD),
    ("endDate BEFORE startDate",
     _LAWFUL_ENTITY + '<xbrli:period>'
     '<xbrli:endDate>2026-03-31</xbrli:endDate>'
     '<xbrli:startDate>2026-01-01</xbrli:startDate></xbrli:period>'),
])
def test_827R5_a_context_out_of_SCHEMA_ORDER_refuses(label, body):
    bound, why = _bind(_context(body), dims=())
    assert bound is None, f"{label}: ATTACHED"
    assert why == 'exact_id_malformed_context_structure', f"{label}: {why!r}"


def test_827R5_a_divide_out_of_SCHEMA_ORDER_refuses():
    """XBRL 2.1 sequences the divide as numerator THEN denominator. Reversed,
    the two sides would be read the wrong way round — USD/share becomes
    share/USD, which is a different unit wearing the same name."""
    bound, why = _bind(_unit(
        '<xbrli:unit id="usd"><xbrli:divide>'
        '<xbrli:unitDenominator><xbrli:measure>xbrli:shares</xbrli:measure>'
        '</xbrli:unitDenominator><xbrli:unitNumerator>'
        '<xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unitNumerator>'
        '</xbrli:divide></xbrli:unit>'), unit_name="iso4217:USDshares",
        is_divide="1")
    assert bound is None
    assert why == 'exact_id_malformed_unit_structure', why


def test_827R5_MUST_ALLOW_the_lawful_SCHEMA_ORDER_still_binds():
    """The control for all five order rules at once — entity before period
    before scenario, identifier before segment, start before end."""
    bound, why = _bind(_context(
        '<xbrli:entity>' + _IDENT
        + '<xbrli:segment><xbrldi:explicitMember dimension="a:Ax">a:M'
          '</xbrldi:explicitMember></xbrli:segment></xbrli:entity>'
        + _LAWFUL_PERIOD
        + '<xbrli:scenario><xbrldi:explicitMember dimension="a:Ax2">a:M2'
          '</xbrldi:explicitMember></xbrli:scenario>'),
        dims=_graph_dims(("a:Ax", "a:M"), ("a:Ax2", "a:M2")))
    assert bound is not None, why


# ---- ROUND 6: WHO the filer is, and WHAT the graph row may say -------------
# The identifier's DIGITS mean a CIK only under the SEC's own scheme, and
# `scheme` is required by XBRL 2.1 §4.7.3. Nothing read it: a filing declaring
# the same ten digits under any other scheme — or none — bound as that filer.
# Measured over the frozen cache: 733,172 identifiers, every one carrying
# exactly `http://www.sec.gov/CIK` and exactly ten ASCII digits, none padded
# with non-XML whitespace. Enforcing all three costs zero real evidence.

_SEC = 'http://www.sec.gov/CIK'


def _ident(value="0000320193", scheme=_SEC):
    attr = "" if scheme is None else f' scheme="{scheme}"'
    return (f'<xbrli:entity><xbrli:identifier{attr}>{value}'
            '</xbrli:identifier></xbrli:entity>')


@pytest.mark.parametrize("label,entity", [
    ("no scheme= at all", _ident(scheme=None)),
    ("blank scheme=", _ident(scheme="")),
    ("whitespace-only scheme=", _ident(scheme="   ")),
    ("a DIFFERENT scheme carrying the same digits",
     _ident(scheme="http://example.com/CIK")),
    ("the SEC scheme misspelt", _ident(scheme="http://www.sec.gov/cik")),
    # ---- the value itself: exactly ten ASCII digits ----------------------
    ("nine digits", _ident("000032019")),
    ("eleven digits", _ident("00003201930")),
    ("digits with an inner space", _ident("00003 20193")),
    ("NON-ASCII digits that look like the CIK",
     _ident("００００３２０１ｙ３")),
    # ---- XML whitespace ONLY (#x20 #x9 #xD #xA) --------------------------
    ("padded with a NO-BREAK SPACE", _ident(" 0000320193")),
    ("padded with a ZERO-WIDTH SPACE", _ident("0000320193​")),
    ("padded with an IDEOGRAPHIC SPACE", _ident("　0000320193")),
])
def test_827R6_a_MALFORMED_filer_identity_never_binds(label, entity):
    bound, why = _bind(_context(entity + _LAWFUL_PERIOD))
    assert bound is None, f"{label}: ATTACHED"
    assert why == 'exact_id_malformed_context_structure', f"{label}: {why!r}"


@pytest.mark.parametrize("label,entity,cik", [
    ("the lawful SEC identity", _ident(), "0000320193"),
    ("XML-lawful padding around the digits", _ident(" \t0000320193\n "),
     "0000320193"),
])
def test_827R6_MUST_ALLOW_the_lawful_filer_identity_still_binds(label, entity,
                                                                cik):
    """LEADING ZEROS ARE PRESERVED, not stripped off both sides: the filing
    states ten digits and the graph's CIK is padded up to meet it."""
    bound, why = _bind(_context(entity + _LAWFUL_PERIOD), entity_cik=cik)
    assert bound is not None, f"{label}: refused as {why!r}"


@pytest.mark.parametrize("label,graph_cik", [
    ("one digit", "1"),
    ("the CIK without its padding", "320193"),
    ("eleven digits", "00003201930"),
    ("Unicode digits that look like a CIK", "００００３２０１９３"),
    ("digits with an inner space", "00003 20193"),
    ("not a string at all", 320193),
    ("None", None),
])
def test_827R6_a_GRAPH_cik_outside_the_stored_form_never_binds(label,
                                                               graph_cik):
    """THE ASYMMETRY, PINNED BY MEASUREMENT. The filing must STATE ten ASCII
    digits and is never padded or stripped. The graph is not normalised either
    — census 2026-08-01, read-only: all 796 `Company` nodes store `id` and
    `cik` as exactly ten ASCII digits, so there is nothing to normalise and
    padding `1` up to `0000000001` would invent a filer the graph never named.
    """
    bound, why = _bind(_context(_ident() + _LAWFUL_PERIOD),
                       entity_cik=graph_cik)
    assert bound is None, f"{label}: ATTACHED"
    assert why == 'malformed_entity_cik', f"{label}: {why!r}"


def test_827R6_a_filing_CIK_of_ONE_DIGIT_fails_while_the_ten_digit_form_binds():
    """The reviewer's exact pair. `1` in the FILING is malformed markup — the
    document must commit to ten digits — while the same registrant stated
    lawfully binds against the graph's proven storage form."""
    short, why = _bind(_context(_ident("1") + _LAWFUL_PERIOD),
                       entity_cik="0000000001")
    assert short is None and why == 'exact_id_malformed_context_structure', why
    ok, why = _bind(_context(_ident("0000000001") + _LAWFUL_PERIOD),
                    entity_cik="0000000001")
    assert ok is not None, why


@pytest.mark.parametrize("bad", [None, "", "  ", "quarterly", "DURATION",
                                 "Instant", 0, 1, True, ["duration"]])
def test_827R6_a_period_type_outside_the_TWO_words_never_binds(bad):
    """Every use asked `== 'instant'` or `!= 'instant'`, so ANY other value —
    `None` included — silently meant DURATION. The graph's own vocabulary is
    exactly two words (measured: duration 8,358, instant 3,058)."""
    bound, why = _bind(_context(_ident() + _LAWFUL_PERIOD), period_type=bad)
    assert bound is None, f"period_type={bad!r} ATTACHED"
    assert why == 'malformed_period_type', f"period_type={bad!r}: {why!r}"


@pytest.mark.parametrize("kind,start,end", [
    ("duration", "2026-01-01", "2026-04-01"),
    ("instant", "2026-04-01", "2026-04-01"),
])
def test_827R6_MUST_ALLOW_both_lawful_period_types_still_bind(kind, start, end):
    doc = _context(_ident() + (
        _LAWFUL_PERIOD if kind == "duration" else
        '<xbrli:period><xbrli:instant>2026-03-31</xbrli:instant></xbrli:period>'))
    bound, why = _bind(doc, period_type=kind, start_date=start, end_date=end)
    assert bound is not None, f"{kind}: refused as {why!r}"


def test_827R6_a_BLANK_identifier_is_a_STRUCTURE_fault_not_a_missing_entity():
    """ROUND 6 MOVED THIS BOUNDARY, and the reason moved with it. A blank
    identifier used to reach `entity_missing`, because the value was read and
    only then found empty. The identifier must now BE exactly ten ASCII digits
    under the SEC scheme, so a blank one is markup that never states a filer at
    all — a structure fault, refused at parse.

    `entity_missing` is consequently unreachable from a parsed context: it is
    kept as a fail-closed backstop and FLAGGED for the reviewer rather than
    deleted on my own derivation, which is exactly the reasoning that was wrong
    one round ago."""
    bound, why = _bind(_context(
        '<xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">'
        '</xbrli:identifier></xbrli:entity>' + _LAWFUL_PERIOD))
    assert bound is None and why == 'exact_id_malformed_context_structure', why




# ---- ROUND 6 ITEM 3: NAMESPACE, NOT PREFIX --------------------------------
# XBRL gives an element its identity by NAMESPACE. The parser compared the
# literal string `xbrli:`, so a filing that lawfully binds the INSTANCE
# namespace to `i:` produced ZERO contexts and ZERO units, and every one of its
# facts refused as `undefined_context` — a whole valid filing lost in silence.
#
# `i:` is an alternate for the INSTANCE namespace (normally `xbrli:`). Inline
# XBRL facts are a DIFFERENT namespace and keep `ix:`; the two are tested apart.
# Measured: all 1,769 cached filings declare all three namespaces, so requiring
# the declaration costs no real evidence — and there is NO prefix fallback,
# because a prefix nobody declared is not a qualified name at all.

_NS_INSTANCE = "http://www.xbrl.org/2003/instance"
_NS_DIMENSION = "http://xbrl.org/2006/xbrldi"
_NS_INLINE = "http://www.xbrl.org/2013/inlineXBRL"
#: `_ns_doc` is its OWN fixture with its OWN taxonomy binding —
#: deliberately different from `_FIXTURE_NS` above, so a test cannot
#: pass by accidentally sharing one fake namespace across fixtures.
_NS_GAAP_VARIANT = "http://fasb.org/us-gaap/2026"


def _ns_doc(*, inst="xbrli", dim="xbrldi", ix="ix", declare=None, dims=""):
    """One lawful filing, spelled with whatever prefixes the caller declares."""
    d = ({inst: _NS_INSTANCE, dim: _NS_DIMENSION, ix: _NS_INLINE}
         if declare is None else dict(declare))
    # the measure and axis QNames below name these, and a consumed QName whose
    # prefix nobody declared is not a qualified name — real filings declare
    # every prefix they use (measured: all 1,769 do).
    d.setdefault("iso4217", "http://www.xbrl.org/2003/iso4217")
    d.setdefault("us-gaap", _NS_GAAP_VARIANT)
    # `format` is xs:QName too, so the transformation-registry prefix must be
    # declared here for the same reason: a fixture asserting a transform by an
    # unbound name is not a lawful control. Real filings all declare it.
    d.setdefault("ixt", _FIXTURE_NS["ixt"])
    xmlns = " ".join(f'xmlns:{p}="{u}"' for p, u in d.items())
    return (
        f'<html {xmlns}><body><table><tr><td>Total net sales</td>'
        f'<td><{ix}:nonFraction id="f-48" name="us-gaap:Revenues" '
        f'contextRef="c-1" unitRef="usd" scale="6" decimals="-6" '
        f'format="ixt:num-dot-decimal">390</{ix}:nonFraction></td></tr></table>'
        f'<div style="display:none"><{ix}:header><{ix}:resources>'
        f'<{inst}:context id="c-1"><{inst}:entity><{inst}:identifier '
        f'scheme="http://www.sec.gov/CIK">0000320193</{inst}:identifier>'
        f'{dims}</{inst}:entity><{inst}:period>'
        f'<{inst}:startDate>2026-01-01</{inst}:startDate>'
        f'<{inst}:endDate>2026-03-31</{inst}:endDate></{inst}:period>'
        f'</{inst}:context><{inst}:unit id="usd">'
        f'<{inst}:measure>iso4217:USD</{inst}:measure></{inst}:unit>'
        f'</{ix}:resources></{ix}:header></div></body></html>')


@pytest.mark.parametrize("label,prefix", [
    ("the conventional xbrli: binding", "xbrli"),
    ("the lawful alternate i: binding", "i"),
    ("any other lawfully declared prefix", "inst"),
])
def test_827R6_a_lawful_INSTANCE_binding_binds_whatever_its_prefix(label,
                                                                   prefix):
    """MUST-ALLOW. `i:` produced 0 contexts and 0 units before this rule."""
    bound, why = _bind(_ns_doc(inst=prefix), concept_namespace=_NS_GAAP_VARIANT)
    assert bound is not None, f"{label}: refused as {why!r}"


def test_827R6_MUST_ALLOW_inline_facts_keep_their_own_namespace():
    """The inline namespace is NOT the instance namespace: facts stay `ix:`
    even when the instance elements are spelled `i:`."""
    bound, why = _bind(_ns_doc(inst="i", ix="ix"), concept_namespace=_NS_GAAP_VARIANT)
    assert bound is not None, why


def test_827R6_an_UNDECLARED_instance_prefix_is_not_a_qualified_name():
    """Markup under a prefix nobody declared is not seen — and it is now caught
    at the strongest possible gate, the parser itself.

    An undeclared prefix on an ELEMENT NAME is a namespace well-formedness
    error (Namespaces in XML §3), so the document is not a conforming Inline
    XBRL report at all and no part of it may be read. The previous reader
    RECOVERED from it and reported the downstream symptom — a context that
    could not be found — which was true but understated: the whole document was
    unreadable, not one reference inside it.

    The guarantee is unchanged and strictly stronger: nothing binds. Contrast
    `test_827R9_a_bare_concept_name...`, where an undeclared prefix appears in
    an attribute VALUE — well-formedness says nothing about values, so there the
    document stays readable and only that one fact is refused."""
    doc = _ns_doc(inst="xbrli", declare={"ix": _NS_INLINE,
                                         "xbrldi": _NS_DIMENSION})
    bound, why = _bind(doc, concept_namespace=_NS_GAAP_VARIANT)
    assert bound is None and why == NOT_WELL_FORMED, why


def test_827R6_a_prefix_declared_to_the_WRONG_namespace_is_not_the_element():
    """`xbrli:` bound to something that is not the instance namespace names a
    different element entirely, however familiar the spelling looks."""
    doc = _ns_doc(declare={"xbrli": "http://example.com/not-xbrl",
                           "xbrldi": _NS_DIMENSION, "ix": _NS_INLINE})
    bound, why = _bind(doc, concept_namespace=_NS_GAAP_VARIANT)
    assert bound is None and why == 'exact_id_undefined_context', why


def test_827R6_a_lawful_DIMENSION_binding_is_read_whatever_its_prefix():
    """MUST-ALLOW + MUST-CATCH for the consumed dimension QName: the member is
    read under any declared binding of the dimension namespace, and an
    UNDECLARED one is not a member at all — so its dimension set is empty and
    a fact claiming one abstains."""
    member = ('<{d}:segment_placeholder/>')          # replaced below
    seg = ('<{i}:segment><{d}:explicitMember dimension="us-gaap:A1">us-gaap:M1'
           '</{d}:explicitMember></{i}:segment>')
    # `_ns_doc` binds `us-gaap` to ITS OWN variant, not the shared fixture map,
    # so the claim is resolved through that document's declaration.
    claim = _graph_dims(("us-gaap:A1", "us-gaap:M1"),
                        ns={"us-gaap": _NS_GAAP_VARIANT})
    lawful = _ns_doc(dim="dimns", dims=seg.format(i="xbrli", d="dimns"))
    bound, why = _bind(lawful, concept_namespace=_NS_GAAP_VARIANT, dims=claim)
    assert bound is not None, f"lawful dimension binding refused: {why!r}"
    undeclared = _ns_doc(dims=seg.format(i="xbrli", d="nope"))
    bound, why = _bind(undeclared, concept_namespace=_NS_GAAP_VARIANT, dims=claim)
    assert bound is None, "an undeclared dimension prefix was read as a member"
    assert member  # keeps the local referenced; the shape above is the fixture


# ---- ROUND 6 ITEM 4: the exact public-door attacks -------------------------
# Measured on DIRECT children only (a descendant scan counted 2,112 lawful
# typedMember VALUES and would have argued for refusing real contexts):
#   context -> entity, period          unit -> measure, divide
#   segment/scenario -> explicitMember, typedMember
# So every rule below costs zero real evidence.

@pytest.mark.parametrize("label,body", [
    ("markup nested inside the identifier",
     '<xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">'
     '<b>0000320193</b></xbrli:identifier></xbrli:entity>' + _LAWFUL_PERIOD),
    ("markup nested inside startDate",
     _ident() + '<xbrli:period><xbrli:startDate><b>2026-01-01</b>'
     '</xbrli:startDate><xbrli:endDate>2026-03-31</xbrli:endDate>'
     '</xbrli:period>'),
    ("an UNKNOWN direct child of the context",
     _ident() + _LAWFUL_PERIOD + '<xbrli:somethingElse/>'),
    ("unsupported content inside a segment",
     '<xbrli:entity>' + _IDENT.replace(
         '<xbrli:identifier>',
         '<xbrli:identifier scheme="http://www.sec.gov/CIK">')
     + '<xbrli:segment><xbrli:notAMember>x</xbrli:notAMember></xbrli:segment>'
       '</xbrli:entity>' + _LAWFUL_PERIOD),
])
def test_827R6_item4_context_attacks(label, body):
    bound, why = _bind(_context(body))
    assert bound is None, f"{label}: ATTACHED"
    assert why == 'exact_id_malformed_context_structure', f"{label}: {why!r}"


def test_827R6_item4_markup_nested_inside_a_measure():
    bound, why = _bind(_unit(
        '<xbrli:unit id="usd"><xbrli:measure><b>iso4217:USD</b>'
        '</xbrli:measure></xbrli:unit>'))
    assert bound is None and why == 'exact_id_malformed_unit_structure', why


def test_827R6_item4_an_unknown_direct_child_of_a_unit():
    bound, why = _bind(_unit(
        '<xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure>'
        '<xbrli:somethingElse/></xbrli:unit>'))
    assert bound is None and why == 'exact_id_malformed_unit_structure', why


def test_827R6_item4_MUST_ALLOW_a_lawful_typed_dimension_still_parks_truthfully():
    """THE CONTROL FOR THE TRAP. A typed dimension's VALUE element is lawful
    content inside `typedMember` — 2,112 of them exist in the frozen cache —
    and must never be read as an unknown context child. It parks under its own
    name, exactly as before."""
    bound, why = _bind(_context(
        '<xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">'
        '0000320193</xbrli:identifier><xbrli:segment>'
        '<xbrldi:typedMember dimension="us-gaap:Ax">'
        '<us-gaap:AxDomain>whatever</us-gaap:AxDomain>'
        '</xbrldi:typedMember></xbrli:segment></xbrli:entity>' + _LAWFUL_PERIOD))
    assert bound is None
    assert why == 'exact_id_typed_dimensions_unsupported', why


# ---- ROUND 6 ITEM 6: reading a graph number -------------------------------
# THE RULE (GRAPH-DECIMAL, #827). A graph value READS when it is either:
#   · an XSD decimal — Arelle's pinned `decimalPattern`, a reused standards
#     owner; there is no project-authored production regex here; or
#   · an exact canonical grouped TRANSPORT form — comma-bearing text that
#     round-trips exactly through the runtime's own grouped formatting at the
#     input's stated precision.
# A value that is NEITHER refuses. That is the entire authority. Note the two
# are independent: canonical grouped text is not an XSD decimal, yet reads.
#
# CORPUS (read-only, 12,402,201 numeric non-nil facts, 2026-08-01):
#   plain integer 1,385,166 · plain decimal 896,155 · thousands commas
#   10,120,880 · underscores 0 · exponents 0 · NaN letters 0 · parens 0.
# This is COMPATIBILITY evidence about what the graph happens to hold. It is
# never a legality argument, and the writer's absence of a spelling is never a
# reason to refuse one.
#
# `Decimal()` is NOT a lexical gate: it accepts Python underscore separators,
# full-width and Arabic-Indic digits, exponents, Infinity — and sNaN, a
# SIGNALLING NaN that raises the moment anything touches it. That is exactly
# why `decimalPattern` must run BEFORE the exact finite-number owner.

@pytest.mark.parametrize("bad", [
    "1_0",            # Python underscore separator -> Decimal says 10
    "１２",            # FULL-WIDTH digits
    "٦",              # ARABIC-INDIC digit
    "६",              # DEVANAGARI digit
    "sNaN", "NaN", "-NaN",            # not finite, and sNaN SIGNALS
    "Infinity", "-Infinity", "Inf",
    "nan", "inf", "-inf",             # the writer CAN spell these; the
                                      # exact-number domain refuses them
    "1e3", "1E3",                     # exponent notation
    "1,23,4", "1,,234", ",123", "1,234,",   # malformed comma grouping
    # GRAPH-DECIMAL (#827): "1234"/"-1234"/"12345.6", "01"/"001",
    # "1.0"/"1.20"/"-0.00"/"0.10" and "1,234.5678" LEFT this battery. Each is
    # a lawful XSD decimal, and the writer's grouping habit is a fact about
    # the WRITER, never a reader-side refusal authority. They are MUST-ALLOW
    # cases below.
    "(98)", "(1,234.50)",             # neither an XSD decimal nor a
                                      # canonical grouped transport form
                                      # (SEQ 265 D); source lane keeps its
                                      # own accounting-negative law
    "", "   ", "-", "--1", "1.2.3", "0x10",
])
def test_827R6_a_value_NEITHER_XSD_decimal_NOR_grouped_transport_is_refused(bad):
    assert parse_raw(bad) is None, f"{bad!r} was read as a number"


@pytest.mark.parametrize("good,want", [
    ("1,234", "1234"),
    ("10,120,880", "10120880"), ("896.155", "896.155"),
    ("-1,385,166.25", "-1385166.25"), ("0", "0"),
    ("-0", "0"),                                  # lawful signed zero (7,887
                                                  # live in the graph)
    ("1,000,000,000,000,000,007",
     "1000000000000000007"),                      # unbounded grouped length
    ("0.001", "0.001"),                           # rounding-carry writer form
    # GRAPH-DECIMAL (#827) — arrived here FROM the refused battery. XSD
    # decimal is the lexical owner (Arelle's pinned decimalPattern), so these
    # READ; refusing them was presentation-filtering, not correctness.
    ("1234", "1234"), ("-1234", "-1234"),         # ungrouped 4+ digit runs
    ("12345.6", "12345.6"),
    ("+1234", "1234"),                            # lawful XSD leading plus
    ("01", "1"), ("001", "1"), ("01234", "1234"), # leading zeros: no repair
    ("1.0", "1.0"), ("1.20", "1.20"),             # trailing fraction zeros
    ("-0.00", "-0.00"), ("0.10", "0.10"),         # (`==` is numeric here, so
                                                  # this pins readability, not
                                                  # retained scale)
    ("1,234.5678", "1234.5678"),                  # grouped, >3 fraction digits
    # "(98)" is NOT here: accounting parentheses are not XSD decimals and
    # stay refused; the SOURCE lane's own law is pinned by
    # test_F_a_visible_accounting_negative_still_reconciles.
])



def test_827R6_MUST_ALLOW_every_lawful_graph_number_input(good, want):
    assert parse_raw(good) == Decimal(want), good


@pytest.mark.parametrize("padded", [" 1,234 ", "\t1234\n", "1234 "])
def test_827R6_a_PADDED_graph_value_is_not_the_value(padded):
    """EXACT LEXICAL, both sides. The graph writes no padding, so a padded
    string is a value it never stored — stripping it invented one."""
    assert parse_raw(padded) is None


def test_827R6_accounting_parens_may_not_carry_a_SECOND_sign():
    """IDENTITY CHANGE (SEQ 265 D): historically `(-390,000,000)` came back
    POSITIVE (double negation — corruption). A parenthesised spelling is
    neither an XSD decimal nor a canonical grouped transport form, so EVERY
    one of them refuses on that authority — not on the writer's habits — and
    all three forms are None; the old `(390)` == -390 expectation is retired
    with the paren branch."""
    assert parse_raw("(-390,000,000)") is None
    assert parse_raw("(+390)") is None
    assert parse_raw("(390)") is None


def test_F_a_visible_accounting_negative_still_reconciles_to_graph_minus():
    """SEQ 265 F — the SOURCE lane's accounting-negative law survives the
    graph-parser cleanup: a fact DISPLAYED inside visible parentheses,
    carrying the schema's own sign="-", still binds against the graph's
    plain negative. Deleting dead graph compatibility removed no lawful
    source evidence."""
    doc = _doc(sign="-", shown="98")
    doc = doc.replace('<td><ix:nonFraction', '<td>(<ix:nonFraction')
    doc = doc.replace('</ix:nonFraction></td>', '</ix:nonFraction>)</td>')
    bound, why = _bind(doc, raw_value="-98,000,000")
    assert bound is not None, why
    assert bound["printed_value"] == Decimal("-98")   # printed = pre-scale


# SEQ 270 — THE PUBLIC DOOR refuses UNREADABLE raw spellings AS
# non-reconciling. Each bad raw is the SAME number its source markup displays,
# written in a form that is NEITHER an XSD decimal NOR a canonical grouped
# transport form; unreadable at the door, it cannot reconcile, and the lawful
# twin must bind. Refusal rests on that rule, never on the writer's habits.
# This is the door-level face of the `parse_raw` battery above — one table,
# no wider duplication.
_DOOR_UNREADABLE_SPELLINGS = [
    # (source shown, sign, wrap in visible parens, BAD raw, LAWFUL raw)
    ("12",    "",  False, "１２", "12"),     # full-width digits
    ("98",    "-", True,  "(98)",         "-98"),    # parens as a GRAPH spelling
]

# GRAPH-DECIMAL (#827) — the counterpart table. These raws were "alien" above
# until the XSD-decimal ruling: each is a DIFFERENT SPELLING OF THE SAME
# NUMBER the markup displays, so the door must BIND it. Refusing them was
# presentation-matching wearing reconciliation's name.
_DOOR_LAWFUL_RESPELLINGS = [
    # (source shown, sign, wrap, raw spelled differently but numerically equal)
    ("1,234", "", False, "1234"),      # ungrouped where the writer groups
    ("1.2",   "", False, "1.20"),      # trailing-zero fraction
]


@pytest.mark.parametrize("shown,sign,wrap,raw", _DOOR_LAWFUL_RESPELLINGS)
def test_GRAPHDECIMAL_the_DOOR_binds_a_lawful_respelling_of_the_same_number(
        shown, sign, wrap, raw):
    bound, why = _bind(_door_doc(shown, sign, wrap), raw_value=raw)
    assert bound is not None, why


@pytest.mark.parametrize("shown,sign,wrap,raw", _DOOR_LAWFUL_RESPELLINGS)
def test_GRAPHDECIMAL_the_DOOR_still_refuses_a_DIFFERENT_number(
        shown, sign, wrap, raw):
    """The lawful control's twin: widening the LEXICAL gate must not widen the
    ARITHMETIC one. Same lawful spelling shape, genuinely different value."""
    bound, why = _bind(_door_doc(shown, sign, wrap), raw_value="9999")
    assert bound is None
    assert why == 'value_does_not_reconcile', why


def _door_doc(shown, sign, wrap_parens):
    doc = _doc(shown=shown, sign=sign, scale="0")
    if wrap_parens:                     # the F-test's visible accounting form
        doc = doc.replace('<td><ix:nonFraction', '<td>(<ix:nonFraction')
        doc = doc.replace('</ix:nonFraction></td>', '</ix:nonFraction>)</td>')
    return doc


@pytest.mark.parametrize("shown,sign,wrap,bad,lawful", _DOOR_UNREADABLE_SPELLINGS)
def test_827R6_the_DOOR_refuses_an_UNREADABLE_raw_as_non_reconciling(
        shown, sign, wrap, bad, lawful):
    bound, why = _bind(_door_doc(shown, sign, wrap), raw_value=bad)
    assert bound is None
    assert why == 'value_does_not_reconcile', why


@pytest.mark.parametrize("shown,sign,wrap,bad,lawful", _DOOR_UNREADABLE_SPELLINGS)
def test_827R6_the_DOOR_binds_every_lawful_twin(shown, sign, wrap, bad, lawful):
    bound, why = _bind(_door_doc(shown, sign, wrap), raw_value=lawful)
    assert bound is not None, why


# ---------------------------------------------------------------------------
# #827 ROUND 7b — THE THREE HOLES THE REVIEWER REPRODUCED THROUGH THE PUBLIC
# DOOR. Every one attached with reason 'ok'.
#
# Each is a PAIR: the malformed form must refuse UNDER ITS OWN NAME, and the
# lawful control beside it must still bind. A refusal that lies about its cause
# is not a correct refusal, and a rule proven in one direction is half a rule.
# ---------------------------------------------------------------------------

#: XML 1.0 S — the ONLY whitespace an XML document may pad a value with.
#: Python's bare `.strip()` ALSO eats U+000B, U+000C, U+00A0 and U+3000, so
#: every site that asked "is this id blank?" with it answered YES for
#: characters XML does not call space at all — and a fact whose id is one of
#: them was routed to the identity fallback, a law that applies only when the
#: element genuinely carries NO id.
NBSP, VT, FF, IDEO = " ", "\x0b", "\x0c", "　"


@pytest.mark.parametrize("label,bad", [
    ("two names", "1 2"), ("angle bracket", "a<b"), ("leading digit", "1f"),
    ("colon", "a:b"), ("empty-ish dot", "."),
    # VT and FF are NOT here, and their absence is proven, not assumed — see
    # `test_827R9_VT_and_FF_cannot_occur_in_an_XML_document_at_all` below.
    ("NBSP only", NBSP), ("ideographic only", IDEO),
    ("trailing space", "f-48 "), ("leading space", " f-48"),
])
def test_827R7_an_UNLAWFUL_element_id_is_MALFORMED_under_its_own_name(label,
                                                                     bad):
    """An XML ID is an NCName. `id="1 2"` is not a name at all, and a
    whitespace-only id is not the same claim as NO id.

    THE DOCUMENT DECLARES THE SAME UNLAWFUL ID, so this is a genuine exact
    match and not a lookup that misses by luck — the first fixture asked for
    `f-48` while the document declared the junk, so every row refused as
    `id_not_found` and proved nothing about the rule.
    """
    bound, why = _bind(_doc(element_id=f'id="{_xa(bad)}" '),
                       inline_element_id=bad)
    assert bound is None, f"{label}: an unlawful id bound"
    # `exact_id_` is the path prefix; `malformed_id` is `element_evidence`'s
    # own reason. The rule lives at that ONE door so the locator — the other
    # caller, which had the same hole — is covered by the same line.
    assert why == "exact_id_malformed_id", f"{label}: refused as {why!r}"


@pytest.mark.parametrize("blank", [None, "", " ", "  \t\r\n "])
def test_827R7_MUST_ALLOW_an_XML_blank_id_still_uses_the_identity_fallback(
        blank):
    """The other direction. XML 1.0 S padding around an absent id IS blank, and
    those facts must keep binding through the fallback — 0 of the pinned 1,769
    filings carry an unlawful id, so the rule costs no real evidence, but this
    lane is the one that would silently empty if blankness were tightened."""
    bound, why = _bind(inline_element_id=blank)
    assert bound is not None, f"a lawful blank id stopped binding: {why}"


def test_827R7_MUST_ALLOW_a_lawful_element_id_still_binds_exactly():
    assert _bind()[0] is not None


@pytest.mark.parametrize("label,bad", [
    # "bare word" is NOT here: an unprefixed value is a LAWFUL QName wherever a
    # default namespace is in scope, and one always is inside an XHTML report.
    # Its own law is the test directly below this one.
    ("undeclared prefix", "zz:Revenues"),
    ("empty local", "us-gaap:"),
    ("empty prefix", ":Revenues"),
    ("two colons", "a:b:c"),
    ("space inside the local", "us-gaap:Rev enues"),
    ("angle bracket", "us-gaap:Rev<enues"),
])
def test_827R7_an_UNLAWFUL_concept_QName_never_binds(label, bad):
    """A concept is a QName: its meaning comes from the namespace its prefix is
    bound to. Nothing validated it, so `Revenues` and `zz:Revenues` bound as
    readily as the real name — the graph and the document merely had to agree
    on the same junk, which is exactly what a corrupted ingest produces."""
    # THE JUNK IS IN THE DOCUMENT, and the graph identity is LAWFUL — which is
    # the only shape that can occur: measured read-only, 12,402,201 of
    # 12,402,201 graph facts carry a Concept namespace and none is blank, so
    # the graph cannot be the source of an unlawful QName. Passing the junk as
    # the graph concept too (the earlier fixture) made this refuse on the
    # graph-identity gate instead of the document rule it names.
    bound, why = _bind(_doc(name=bad))
    assert bound is None, f"{label}: an unlawful concept name bound"
    # THE PATH IS PART OF THE REASON. The check lives in the one evidence
    # funnel, so the door reports it under whichever path reached it —
    # `exact_id_` here, `fallback_` when the graph states no id. Pinning the
    # bare name would have passed against a refusal from a different rule.
    assert why == "exact_id_malformed_concept_name", \
        f"{label}: refused as {why!r}"


def test_827R9_a_bare_concept_name_takes_the_DEFAULT_namespace_and_then_mismatches():
    """An unprefixed QName is not malformed — it is a DIFFERENT concept.

    XBRL 2.1 §4.8.2 as corrected by Erratum 62 makes these values plain
    `xsd:QName`, and XML Schema QName resolution gives an unprefixed one the
    in-scope DEFAULT namespace — or, when there is none, the ABSENT namespace,
    which is itself a lawful value. THIS fixture declares prefixes only and no
    default, so `Revenues` resolves to (absent, Revenues): a perfectly
    well-formed name that simply is not the us-gaap concept the graph asked for.
    A document that did declare a default would resolve it to that URI instead,
    and would mismatch for exactly the same reason.

    So it must NOT bind, and it must not be called malformed either: the
    refusal belongs at the identity COMPARISON, where the truthful reason is
    that the two concepts differ. Calling a lawful name malformed would be a
    false statement about the filing."""
    bound, why = _bind(_doc(name="Revenues"))
    assert bound is None, "a bare word must never bind to a namespaced concept"
    assert why == "concept_mismatch", why


@pytest.mark.parametrize("good", [
    "us-gaap:Revenues", "dei:EntityCommonStockSharesOutstanding",
    "aapl:CustomConcept", "srt:SegmentMember",
])
def test_827R7_MUST_ALLOW_real_concept_QNames_still_bind(good):
    """The controls come from the shapes real filings use: a standard taxonomy
    prefix, an entity-specific extension, and a declared third-party prefix.
    Census over the pinned corpus: 0 concept names that this rule refuses."""
    bound, why = _bind(_doc(name=good), concept=good)
    assert bound is not None, f"{good} stopped binding: {why}"


def test_827R7_the_concept_rule_covers_the_FALLBACK_path_too():
    """One funnel, both doors. When the graph states NO id the binder resolves
    by identity instead, and that path reaches the same evidence builder — so
    the rule must hold there too, under the fallback's own prefix. A check
    written on only one path is a rule with a second, unguarded entrance."""
    # Same shape as its exact-id twin above: the DOCUMENT carries the unlawful
    # name while the graph identity stays lawful.
    bound, why = _bind(_doc(name="zz:Revenues"), inline_element_id=None)
    assert bound is None
    assert why == "fallback_no_identity_match", why


@pytest.mark.parametrize("bad,expected", [
    ("1 2", "malformed_id"), ("a<b", "malformed_id"),
    ("1f", "malformed_id"), ("a:b", "malformed_id"),
    # XML 1.0 S IS blank; U+000B, U+000C, U+00A0 and U+3000 are NOT, and
    # calling them blank is what routed a fact to the wrong law. The two
    # reasons are pinned SEPARATELY on purpose: accepting either would let a
    # mutation swap `.strip(XML_S)` back to `.strip()` and stay green.
    (" ", "blank_id"), ("\t\r\n", "blank_id"),
    # THE NAMED CONSTANTS, never a literal invisible character: an NBSP typed
    # directly into this list arrived as a PLAIN SPACE, silently duplicating
    # the blank case and asserting the opposite reason for it.
    (NBSP, "malformed_id"), (IDEO, "malformed_id"),
])
def test_827R7_the_PUBLIC_id_door_refuses_an_unlawful_id_for_EVERY_caller(
        bad, expected):
    """`element_evidence` is the one door the binder AND the locator go
    through, so the XML-name rule is stated there once instead of twice.

    THE LOCATOR HAD THE SAME HOLE and it is not hypothetical: it rejects a
    PADDED id and a non-string id, but `1 2` is neither padded nor non-string,
    so it went straight to this lookup. Fixing the shared door closed both
    callers with one line — two copies of a rule are two rules the day one of
    them is edited."""
    from driver.relocation.inline_html import element_evidence, prepare
    prepared = prepare(_doc(element_id=f'id="{_xa(bad)}" '))
    ev, why = element_evidence(prepared, bad)
    assert ev is None, f"{bad!r} resolved through the public door"
    assert why == expected, f"{bad!r} refused as {why!r}, expected {expected!r}"


@pytest.mark.parametrize("label,ch", [("VT", VT), ("FF", FF)])
def test_827R9_VT_and_FF_cannot_occur_in_an_XML_document_at_all(label, ch):
    """These two are refused EARLIER and HARDER than `malformed_id`, and the
    reason is the standard, not our choice.

    XML 1.0 5e §2.2 Char is `#x9 | #xA | #xD | [#x20-#xD7FF] | ...` — U+000B and
    U+000C are in NO production. They cannot appear literally, and `&#11;` /
    `&#12;` are refused too (xmlParseCharRef rejects the value), so no
    well-formed XML document can carry an id made of them. The id rule is
    therefore UNREACHABLE for these characters, and asserting `malformed_id`
    would assert a path that cannot be walked.

    The guarantee that matters is unchanged and is what is pinned here: such a
    document NEVER yields evidence, under a truthful reason of its own."""
    from driver.relocation.inline_html import (NOT_WELL_FORMED,
                                               element_evidence, prepare,
                                               refused as refused_reason)
    prepared = prepare(_doc(element_id=f'id="{ch}" '))
    assert refused_reason(prepared) == NOT_WELL_FORMED, label
    assert element_evidence(prepared, ch) == (None, NOT_WELL_FORMED), label
    # ...and the character is refused as a REFERENCE too, so this is a property
    # of XML itself rather than of how this fixture happens to spell it.
    ref = prepare(_doc(element_id=f'id="&#{ord(ch)};" '))
    assert refused_reason(ref) == NOT_WELL_FORMED, label


def test_827R7_MUST_ALLOW_the_public_id_door_still_resolves_a_real_id():
    from driver.relocation.inline_html import element_evidence, prepare
    ev, why = element_evidence(prepare(_doc()), "f-48")
    assert ev is not None, why
    assert ev["name"] == "us-gaap:Revenues"


# ---------------------------------------------------------------------------
# #827 round 8 — THE TWO JOINS, PROVED SEPARATELY.
#
# Everything downstream — the concept identity, the unit, the value — is only
# meaningful once the graph fact and the filing element are proven to be the
# SAME fact. There are exactly two ways that join is made, and each is proved
# here on its own, with an exact reason per attack and a lawful twin.
#
# Each RED asserts its EXACT reason rather than "some refusal", because the
# gates run in order and a neighbour's rule would otherwise take the credit.
# The twins are what show no earlier gate is firing at all.
# ---------------------------------------------------------------------------

_SECOND = ('<td><ix:nonFraction id="f-99" name="us-gaap:Revenues" '
           'contextRef="c-1" unitRef="usd" scale="6" decimals="-6" '
           'format="ixt:num-dot-decimal">390</ix:nonFraction></td>')


@pytest.mark.parametrize("label,kw,reason", [
    ("the id names an element carrying a DIFFERENT concept",
     dict(doc=_doc(name="us-gaap:Other")), "concept_mismatch"),
    ("the id names an element in a DIFFERENT context",
     dict(doc=_doc(ctx="c-2")), "context_mismatch"),
    ("the id names an element with a DIFFERENT unitRef",
     dict(doc=_doc(unit="shares")), "unit_ref_mismatch"),
    ("the id is not in the document at all",
     dict(inline_element_id="f-nope"), "exact_id_id_not_found"),
    ("the id is carried by TWO elements, so it names neither",
     dict(doc=_doc(extra_element=_SECOND.replace("f-99", "f-48"))),
     "exact_id_duplicate_id"),
])
def test_827R8_JOIN_exact_id_refuses_for_its_OWN_reason(label, kw, reason):
    """EXACT-ID PATH. The graph names an element; that element must BE the
    graph's fact. Each attack states the exact reason, so no attack can pass on
    a neighbouring rule's refusal."""
    bound, why = _bind(**kw)
    assert bound is None, f"{label}: the join was not proved but it bound"
    assert why == reason, f"{label}: refused as {why!r}, not {reason!r}"


def test_827R8_JOIN_MUST_ALLOW_the_lawful_exact_id_still_binds():
    """The twin for every case above: with nothing perturbed, the id resolves
    and the element matches, so the join IS proved and the fact binds. Without
    this, each refusal above could be an earlier gate firing."""
    bound, why = _bind()
    assert bound is not None, f"the lawful exact-id join stopped binding: {why}"


def test_827R8_JOIN_a_NON_BLANK_id_never_falls_back_to_identity():
    """THE LAW THAT SEPARATES THE TWO PATHS. When the graph states an id, that
    id is the join — a failure there must NEVER be retried as an identity
    match. Here the stated id is absent while a DIFFERENT element would match
    the (name, contextRef, unitRef) triple uniquely, so a fallback would bind
    the wrong element and call it proved."""
    doc = _doc(element_id='id="f-01" ')
    bound, why = _bind(doc, inline_element_id="f-48")
    assert bound is None, "a non-blank id fell back to an identity match"
    assert why == "exact_id_id_not_found", why


@pytest.mark.parametrize("label,kw,reason", [
    ("no element carries that identity",
     dict(concept="us-gaap:Nothing"), "fallback_no_identity_match"),
    ("TWO elements carry it, so it names neither",
     dict(doc=_doc(extra_element=_SECOND)), "fallback_ambiguous_identity"),
])
def test_827R8_JOIN_identity_fallback_refuses_for_its_OWN_reason(label, kw,
                                                                 reason):
    """FALLBACK PATH, used ONLY when the graph states no id. It joins on the
    complete (name, contextRef, unitRef) identity and only when that is
    UNIQUE — anything else cannot prove which element the fact is."""
    bound, why = _bind(inline_element_id="", **kw)
    assert bound is None, f"{label}: the join was not proved but it bound"
    assert why == reason, f"{label}: refused as {why!r}, not {reason!r}"


@pytest.mark.parametrize("blank", [None, "", "   ", "\t\r\n"])
def test_827R8_JOIN_MUST_ALLOW_a_unique_identity_binds_for_every_blank(blank):
    """The twin: every XML-blank id form routes to the fallback, and a UNIQUE
    identity proves the join. Blankness is XML 1.0 S, so these four forms are
    the same statement — the graph has no id for this fact."""
    bound, why = _bind(inline_element_id=blank)
    assert bound is not None, f"a unique identity stopped binding: {why}"


# ---------------------------------------------------------------------------
# #827 round 8b — THE FALLBACK'S CONCEPT HALF IS AN EXPANDED NAME.
#
# The reviewer reproduced the hole: `identity_fallback` compared the raw `name`
# attribute, so a document lawfully binding TWO prefixes to one taxonomy made
# the "complete identity" incomplete — the exact-id twin bound while the
# blank-id fact refused as `no_identity_match`. A prefix is an alias; only the
# expanded (namespace URI, local name) says which concept an element carries.
# ---------------------------------------------------------------------------

#: ONE taxonomy, TWO lawful prefixes — the shape that exposed the defect.
_ALIAS_NS = dict(_FIXTURE_NS, gaap=_FIXTURE_NS["us-gaap"])
_ALIAS_XMLNS = " ".join(f'xmlns:{p}="{u}"' for p, u in _ALIAS_NS.items())


def _alias_doc(*, name="gaap:Revenues", element_id='id="f-48" ', extra=""):
    """A lawful filing whose fact is written under the ALIAS prefix."""
    return (
        f'<html {_ALIAS_XMLNS}><body><table><tr><td>Total net sales</td>'
        f'<td><ix:nonFraction {element_id}name="{name}" contextRef="c-1" '
        f'unitRef="usd" scale="6" decimals="-6" format="ixt:num-dot-decimal">390'
        f'</ix:nonFraction></td>{extra}</tr></table>'
        '<div style="display:none"><ix:header><ix:resources>'
        '<xbrli:context id="c-1"><xbrli:entity>'
        '<xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193'
        '</xbrli:identifier></xbrli:entity><xbrli:period>'
        '<xbrli:startDate>2026-01-01</xbrli:startDate>'
        '<xbrli:endDate>2026-03-31</xbrli:endDate>'
        '</xbrli:period></xbrli:context>'
        '<xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure>'
        '</xbrli:unit></ix:resources></ix:header></div></body></html>')


def test_827R8b_JOIN_MUST_ALLOW_a_blank_id_fact_under_a_LAWFUL_ALIAS_prefix():
    """(1) The reviewer's exact case. The graph stores `us-gaap:Revenues`; the
    filing writes `gaap:Revenues` under a second prefix bound to the SAME
    taxonomy URI. Same concept, so the blank-id fallback must find it."""
    bound, why = _bind(_alias_doc(element_id=""), inline_element_id="")
    assert bound is not None, f"a lawful alias prefix refused the join: {why}"


def test_827R8b_JOIN_the_exact_id_twin_under_the_alias_also_binds():
    """(4) The exact-id path was already sound and must stay sound — this is
    the twin whose success made the fallback's refusal a provable defect."""
    bound, why = _bind(_alias_doc())
    assert bound is not None, why


def test_827R8b_JOIN_the_SAME_local_name_under_a_DIFFERENT_URI_refuses():
    """(2) Alias-tolerance must not become name-tolerance: the same local part
    under another taxonomy is a DIFFERENT concept, and the fallback must refuse
    with its own reason rather than some later gate's."""
    other = dict(_FIXTURE_NS, gaap="http://example.org/OTHER-taxonomy")
    xmlns = " ".join(f'xmlns:{p}="{u}"' for p, u in other.items())
    doc = _alias_doc(element_id="").replace(_ALIAS_XMLNS, xmlns, 1)
    bound, why = _bind(doc, inline_element_id="")
    assert bound is None, "a different taxonomy bound as the same concept"
    assert why == "fallback_no_identity_match", why


def test_827R8b_JOIN_two_prefixes_resolving_to_ONE_identity_are_AMBIGUOUS():
    """(3) Two elements written under different prefixes that expand to the SAME
    identity are two candidates for one fact — the join cannot say which, so it
    refuses. Raw-text matching saw two different names and would have bound."""
    twin = ('<td><ix:nonFraction name="us-gaap:Revenues" contextRef="c-1" '
            'unitRef="usd" scale="6" decimals="-6" format="ixt:num-dot-decimal">390'
            '</ix:nonFraction></td>')
    bound, why = _bind(_alias_doc(element_id="", extra=twin),
                       inline_element_id="")
    assert bound is None, "two candidates for one fact bound anyway"
    assert why == "fallback_ambiguous_identity", why


# ---------------------------------------------------------------------------
# 827B16 — THE NEW UNIT-TYPE REASON, PROVED AT THE REAL BINDER DOOR.
# `unsupported_unit_type` is minted for a RESOLVED non-standard type on one of
# the three NAMED unit elements: the declaration resolves, so the filing may be
# perfectly valid and we simply cannot prove the derivation without the foreign
# schema. Calling it malformed would be a false finding; letting it bind would
# attach a unit we never checked. It must therefore travel intact to BOTH
# public attachment paths — the exact-id one and the blank-id fallback — and
# the lawful declared-type twin must still bind.
# ---------------------------------------------------------------------------

#: Declared ON THE UNIT, which is lawful anywhere, so the shared filing fixture
#: this whole file depends on is left byte-identical.
_B16_NS = (' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
           ' xmlns:cust="http://example.org/cust"')


def _b16_unit(numerator_type):
    """The lawful divide unit with ONE xsi:type asserted on its numerator."""
    t = '' if numerator_type is None else ' xsi:type="%s"' % numerator_type
    return ('<xbrli:unit id="usd"%s><xbrli:divide>'
            '<xbrli:unitNumerator%s><xbrli:measure>iso4217:USD</xbrli:measure>'
            '</xbrli:unitNumerator><xbrli:unitDenominator>'
            '<xbrli:measure>xbrli:shares</xbrli:measure>'
            '</xbrli:unitDenominator></xbrli:divide></xbrli:unit>'
            % (_B16_NS, t))


_B16_DIVIDE = dict(unit_name="iso4217:USDshares", is_divide="1")


def test_827B16_a_RESOLVED_custom_unit_type_reaches_the_EXACT_ID_door():
    bound, why = _bind(_unit(_b16_unit('cust:MyMeasures')), **_B16_DIVIDE)
    assert bound is None, "a unit we could not check ATTACHED"
    assert why == 'exact_id_unsupported_unit_type', why


def test_827B16_the_DECLARED_type_twin_still_binds():
    """The control that makes the refusal above mean something: the SAME markup
    asserting the type the schema actually declares is lawful and binds."""
    bound, why = _bind(_unit(_b16_unit('xbrli:measuresType')), **_B16_DIVIDE)
    assert bound is not None, why


def test_827B16_the_UNTYPED_twin_still_binds():
    bound, why = _bind(_unit(_b16_unit(None)), **_B16_DIVIDE)
    assert bound is not None, why


def test_827B16_the_same_poison_reaches_the_NULL_ID_FALLBACK_truthfully():
    """The prepared unit is shared by both doors, so the blank-id path must
    report the SAME reason under its own prefix — not fall through, and not
    quietly become a different verdict."""
    bound, why = _bind(_unit(_b16_unit('cust:MyMeasures')),
                       inline_element_id="", **_B16_DIVIDE)
    assert bound is None, "a unit we could not check ATTACHED via the fallback"
    assert why == 'fallback_unsupported_unit_type', why


def test_EU151_a_blank_concept_namespace_refuses_at_the_one_owner():
    """EU-151 (#827, fail-closed): a missing or WHITESPACE namespace must
    refuse as missing_graph_concept_namespace at graph_concept_target — an
    empty-string default participating in the expanded-name compare was the
    recorded review-disproof. Measured 2026-08-08: no suite reddened when
    the blank gate was weakened to type-only."""
    from driver.relocation.inline_html import graph_concept_target
    assert graph_concept_target("us-gaap:Revenues", None,
                                "us-gaap:Revenues") is None
    assert graph_concept_target("us-gaap:Revenues", "",
                                "us-gaap:Revenues") is None
    assert graph_concept_target("us-gaap:Revenues", "   ",
                                "us-gaap:Revenues") is None
    bound, why = _bind(concept_namespace="   ")
    assert bound is None
    assert why == "missing_graph_concept_namespace"


def test_EU152_an_INDETERMINATE_duration_refuses_not_binds():
    """EU-152 (#827, fail-closed): the forward-period compare is THREE-STATE
    — filing_duration_ordered answers None at the calendar edge, and None
    must refuse exactly like False (`is not True`). Measured 2026-08-08: a
    weaken to `is False` reddened nothing, and the graph could never even
    store this filing's exclusive end (the day after 9999-12-31), so the
    DOCUMENT itself must declare the edge for the compare to be reached."""
    from driver.relocation.exact_numbers import filing_duration_ordered
    assert filing_duration_ordered("9999-12-30", "9999-12-31") is None
    edge_doc = _doc().replace(
        "<xbrli:startDate>2026-01-01</xbrli:startDate>"
        "<xbrli:endDate>2026-03-31</xbrli:endDate>",
        "<xbrli:startDate>9999-12-30</xbrli:startDate>"
        "<xbrli:endDate>9999-12-31</xbrli:endDate>")
    assert edge_doc != _doc(), "the context substitution must land"
    bound, why = _bind(edge_doc, start_date="9999-12-30",
                       end_date="9999-12-31")
    assert bound is None
    # MEASURED 2026-08-08: representability refuses FIRST — the graph can
    # never store this filing's exclusive end, so the forward compare's
    # None arm is door-unreachable and the `is not True` form is the
    # RETAINED fail-closed safety net (the EU-016 precedent); the direct
    # three-state answer above is the arm's own pin.
    assert why == "unbindable_period", why


def test_EU171_an_absent_unitRef_is_the_no_unit_identity_in_the_pool():
    """find_by_identity (PROOF-ONLY reach lane, g2_fevid_call_trace_v5): an
    element carrying NO unitRef attribute compares as the no-unit identity
    '' — the same normalization the binder's unit_ref_mismatch arm applies —
    so a no-unit query finds exactly it, and the unit-carrying control is
    still found only by its exact document-local IDREF."""
    extra = ('<div style="display:none"><ix:nonFraction id="nu-1" '
             'name="us-gaap:Revenues" contextRef="c-2" scale="0" decimals="0" '
             'format="ixt:num-dot-decimal">7</ix:nonFraction></div>')
    prepared = prepare(_doc(extra_element=extra))
    target = (_FIXTURE_NS['us-gaap'], 'Revenues')
    assert find_by_identity(prepared, target, '') == ['nu-1']
    assert find_by_identity(prepared, target, 'usd') == ['f-48']


def test_EU172_a_malformed_graph_qname_refuses_as_its_own_missing_identity():
    """graph_concept_target: a stored qname that is not a QName at all
    (a:b:c — an NCName may not contain a colon, Namespaces in XML 1.0 3e
    section 4) refuses under the identity's OWN reason, never flowing on as
    an empty local name for the equality ladder to call a concept mismatch.
    Measured over the whole graph population: 0 of 13,775,616 stored qnames
    are refused (the contract-sheet census), so the guard costs nothing and
    only ever catches corruption."""
    assert _bind(concept="us-gaap:Rev:enues") == (
        None, 'missing_graph_concept_namespace')
    ok, why = _bind()
    assert why == 'ok' and ok is not None      # the lawful control binds


def test_EU174_disagreeing_concept_records_park_never_pick():
    """one_concept_target (PROOF-ONLY reach lane, g2_fevid_call_trace_v5):
    identical records collapse to the ONE target they agree on; records
    disagreeing on the namespace refuse as None — silently taking the first
    would let row order decide what a fact means (the refuse-never-repair
    law, the EU-154 block)."""
    ns = _FIXTURE_NS['us-gaap']
    agree = [(ns, "us-gaap:Revenues"), (ns, "us-gaap:Revenues")]
    assert one_concept_target("us-gaap:Revenues", agree) == (ns, "Revenues")
    clash = agree + [(ns + "X", "us-gaap:Revenues")]
    assert one_concept_target("us-gaap:Revenues", clash) is None


def test_EU184_a_bool_scale_is_not_an_int_and_fails_to_reconcile():
    """reconcile: the four False arms are the refusal side of the frozen
    value-reconciliation law (comparison only — an unresolved raw, printed
    value, scale, or magnitude simply fails to reconcile, never guesses).
    The scale must be a REAL int: isinstance(True, int) is True in Python,
    so only the exact type check is strict enough — a bool scale fails to
    reconcile while the true int-1 control reconciles the same pair. (Two
    owners refuse the bool: this gate and exact_scaleb's own real-int rule —
    the gate is the retained safety net, recorded at the site.)"""
    assert reconcile('390', _NUM_DOT_DECIMAL, 1, '', '3,900') is True
    assert reconcile('390', _NUM_DOT_DECIMAL, True, '', '3,900') is False


def test_EU156_a_forever_period_PARKS_under_its_own_named_reason():
    """EU-156 (#827) — PARK-NAMED-REASON for the forever/undated scope refusal.

    `<xbrli:forever/>` is LAWFUL XBRL 2.1 (§4.7.2): a context whose period has
    no dated boundary at all. This reader binds DATED graph facts, so a forever
    context can never back one — but the owner's E-SUPPORTED-SCOPE ruling
    (2026-08-07) is that refusing lawful input is a scope DECISION, so it must
    park under its own NAMED reason and be counted as its own pile by the
    first-production census. Two things therefore matter and are asserted
    separately: that it refuses, and that it refuses under the name
    `forever_or_undated_period` rather than being swept into the malformed
    pile — a lawful document reported as malformed would blame the filer for
    our scope choice.

    The mutation for this rule survived the whole suite before this node
    existed, which is why it is added here rather than recorded as reused.
    """
    doc = _doc().replace(
        '<xbrli:startDate>2026-01-01</xbrli:startDate>'
        '<xbrli:endDate>2026-03-31</xbrli:endDate>', '<xbrli:forever/>')
    bound, why = _bind(doc)
    assert bound is None
    assert 'forever_or_undated_period' in why, why
    # NOT the malformed pile — the document is lawful, the refusal is ours
    assert 'malformed' not in why, why
    # CONTROL: the same fixture with its dated period still binds
    ok, why_ok = _bind(_doc())
    assert ok is not None, why_ok


def test_EU163_an_unreadable_ix_element_kind_PARKS_under_its_own_named_reason():
    """EU-163 (#827) — PARK-NAMED-REASON for the element-kind scope refusal.

    `ix:nonNumeric` is a lawful Inline XBRL 1.1 element (§12.1.2). This reader's
    readable target is `ix:nonFraction` alone, so pointing a graph fact at any
    other lawful ix kind is refused — again a scope choice, not a defect in the
    filing, so it parks under the named reason `unsupported_element_kind`.

    The element id used here is REAL and present in the document, so the
    refusal cannot be "no such element": it is specifically about the KIND.
    """
    nn = ('<div style="display:none"><ix:nonNumeric id="f-99" '
          'name="dei:DocumentType" contextRef="c-1">10-Q</ix:nonNumeric></div>')
    bound, why = _bind(_doc(extra_element=nn), inline_element_id='f-99')
    assert bound is None
    assert 'unsupported_element_kind' in why, why
    assert 'malformed' not in why, why
    # CONTROL: the nonFraction in the SAME document still binds
    ok, why_ok = _bind(_doc(extra_element=nn))
    assert ok is not None, why_ok
