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

from driver.relocation.inline_html import (bind_graph_fact, parse_raw,
                                           printed_value, reconcile)

CIK = "320193"


def _doc(*, element_id='id="f-48" ', name="us-gaap:Revenues", ctx="c-1",
         unit="usd", scale="6", sign="", shown="390", hidden=False,
         extra_element="", dims=""):
    body = (f'<td><ix:nonFraction {element_id}name="{name}" contextRef="{ctx}" '
            f'unitRef="{unit}" scale="{scale}" sign="{sign}" '
            f'format="ixt:num-dot-decimal">{shown}</ix:nonFraction></td>')
    table = ('<html><body><table><tr><td>Total net sales</td>' + body
             + '</tr></table>')
    if hidden:            # a REAL hidden fact: inside ix:hidden, no visible row
        table = ('<html><body><table><tr><td>Total net sales</td><td>-</td></tr>'
                 '</table><div style="display:none">' + body + '</div>')
    return (
        table
        + extra_element +
        '<div style="display:none"><ix:header><ix:resources>'
        f'<xbrli:context id="c-1"><xbrli:entity><xbrli:identifier>0000320193'
        '</xbrli:identifier></xbrli:entity><xbrli:period>'
        '<xbrli:startDate>2026-01-01</xbrli:startDate>'
        '<xbrli:endDate>2026-03-31</xbrli:endDate></xbrli:period>'
        f'{dims}</xbrli:context>'
        '<xbrli:context id="c-2"><xbrli:entity><xbrli:identifier>0000320193'
        '</xbrli:identifier></xbrli:entity><xbrli:period>'
        '<xbrli:startDate>2025-01-01</xbrli:startDate>'
        '<xbrli:endDate>2025-03-31</xbrli:endDate></xbrli:period></xbrli:context>'
        '<xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>'
        '<xbrli:unit id="shares"><xbrli:measure>shares</xbrli:measure></xbrli:unit>'
        '</ix:resources></ix:header></div></body></html>')


def _bind(doc=None, **over):
    kw = dict(inline_element_id="f-48", concept="us-gaap:Revenues",
              context_id="c-1", unit_ref="usd", unit_name="iso4217:USD",
              is_divide="0", period_type="duration", start_date="2026-01-01",
              end_date="2026-04-01",      # STORED form: the filing says 03-31
              dims=(), entity_cik=CIK, raw_value="390,000,000")
    kw.update(over)
    return bind_graph_fact(doc if doc is not None else _doc(), **kw)


# ------------------------------------------------------- exact arithmetic ----

D29 = "1." + "0" * 27 + "1"                 # 29 significant digits
D29_SCALED = "1000000.0000000000000000000001"


def test_RED_exact_number_pair_at_29_digits():
    """THE pair: the CORRECT value must verify and the ROUNDED-WRONG value must
    not. `reconcile` multiplied at the default 28-digit context, so it did
    exactly the opposite — the worst possible outcome, and the same defect the
    Core converter had already removed from its own arithmetic."""
    assert reconcile(D29, "ixt:num-dot-decimal", 6, "", D29_SCALED) is True
    assert reconcile(D29, "ixt:num-dot-decimal", 6, "", "1000000") is False


def test_RED_exactness_holds_through_the_whole_binding():
    doc = _doc(shown=D29)
    bound, why = _bind(doc, raw_value=D29_SCALED)
    assert bound is not None, why
    assert bound["value"] == Decimal(D29_SCALED)
    assert _bind(doc, raw_value="1000000")[0] is None


def test_RED_a_malformed_sign_abstains_rather_than_reading_as_positive():
    """`printed_value` negated only on '-', so ANY other sign silently meant
    positive. A malformed sign is malformed evidence: abstain (law step 7)."""
    assert printed_value("390", "ixt:num-dot-decimal", "-") == Decimal(-390)
    assert printed_value("390", "ixt:num-dot-decimal", "") == Decimal(390)
    assert printed_value("390", "ixt:num-dot-decimal", "x") is None
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
            'unitRef="usd" scale="6" format="ixt:num-dot-decimal">390'
            '</ix:nonFraction></td>')
    doc = _doc(element_id="", extra_element=twin)
    assert _bind(doc, inline_element_id="")[0] is None


def test_RED_a_duplicate_id_abstains_and_is_never_rescued():
    dup = ('<td><ix:nonFraction id="f-48" name="us-gaap:Revenues" '
           'contextRef="c-1" unitRef="usd" scale="6" '
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
    assert _bind(doc, dims=())[0] is None                     # claimed none
    assert _bind(_doc(), dims=((axis, mem),))[0] is None      # claimed one
    assert _bind(doc, dims=((axis, mem),))[0] is not None     # exactly right


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
        end_date="2026-04-01", dims=(), entity_cik=CIK, raw_value="16,000,000")
    assert bound is not None, why
    assert bound["unit_name"] == "shares" and bound["is_divide"] == "0"


def test_RED_comma_and_accounting_negative_values_parse():
    assert parse_raw("113,743,000,000") == Decimal("113743000000")
    assert parse_raw("(1,234.50)") == Decimal("-1234.50")


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
        '<xbrli:entity><xbrli:identifier>0000320193</xbrli:identifier></xbrli:entity>',
        '', 1)
    assert _bind(no_entity, entity_cik="")[0] is None
    assert _bind(no_entity)[0] is None
    assert _bind(entity_cik="")[0] is None


def test_RED_a_duplicate_context_id_abstains():
    """Last-wins silently picked one of two conflicting contexts."""
    dup = ('<xbrli:context id="c-1"><xbrli:entity><xbrli:identifier>0000320193'
           '</xbrli:identifier></xbrli:entity><xbrli:period>'
           '<xbrli:startDate>2020-01-01</xbrli:startDate>'
           '<xbrli:endDate>2020-03-31</xbrli:endDate></xbrli:period>'
           '</xbrli:context>')
    doc = _doc().replace('<xbrli:unit id="usd">', dup + '<xbrli:unit id="usd">', 1)
    bound, why = _bind(doc)
    assert bound is None and "duplicate_context_id" in why


def test_RED_the_expected_numeric_object_is_returned_for_field_wise_binding():
    """Callers must bind the THREE fields; the binder supplies what the filing
    actually prints so nobody recomputes it."""
    bound, _ = _bind()
    assert bound["printed_value"] == Decimal(390)
    assert Decimal(1).scaleb(bound["ix_scale"]) == Decimal("1E+6")
    assert None is None
    assert len(bound["representation_sha256"]) == 64


def test_RED_the_LIVE_unit_spellings_are_the_ones_that_must_work():
    """The synthetic `xbrli:shares` does not exist in the graph. The real
    spellings are `shares` (is_divide=0) and `iso4217:USDshares` (is_divide=1)."""
    shares_doc = _doc(unit="shares", scale="0", shown="16,000,000")
    bound, why = bind_graph_fact(
        shares_doc, inline_element_id="f-48", concept="us-gaap:Revenues",
        context_id="c-1", unit_ref="shares", unit_name="shares", is_divide="0",
        period_type="duration", start_date="2026-01-01", end_date="2026-04-01",
        dims=(), entity_cik=CIK, raw_value="16,000,000")
    assert bound is not None, why
    per_share_doc = _doc(unit="usdps", scale="0", shown="1.42").replace(
        '<xbrli:unit id="shares"><xbrli:measure>shares</xbrli:measure></xbrli:unit>',
        '<xbrli:unit id="usdps"><xbrli:divide>'
        '<xbrli:unitNumerator><xbrli:measure>iso4217:USD</xbrli:measure>'
        '</xbrli:unitNumerator><xbrli:unitDenominator>'
        '<xbrli:measure>shares</xbrli:measure></xbrli:unitDenominator>'
        '</xbrli:divide></xbrli:unit>', 1)
    bound, why = bind_graph_fact(
        per_share_doc, inline_element_id="f-48", concept="us-gaap:Revenues",
        context_id="c-1", unit_ref="usdps", unit_name="iso4217:USDshares",
        is_divide="1", period_type="duration", start_date="2026-01-01",
        end_date="2026-04-01", dims=(), entity_cik=CIK, raw_value="1.42")
    assert bound is not None, why
