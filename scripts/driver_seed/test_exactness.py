"""WP1 Step-1 RED battery — exactness defects pinned at their source (link_lib / xbrl_lane).

Every RED case reproduces a defect verified during the v5.5 design reviews; GREEN guards pin
behavior that must survive the fixes. Shapes mirror REAL graph storage (checked live 2026-07-18):
concept keys are BARE local names; units are filer-local `unitRef` codes (e.g. 'U_USD');
instants are {'instant': date}; values are strings.

    venv/bin/python -m pytest scripts/driver_seed/test_exactness.py -q
"""
import os, sys, json
import pytest
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'relocate_probe'))
import link_lib as L
import xbrl_lane


def blob(concept, facts):
    return json.dumps({concept: facts})


def fact(value, start=None, end=None, instant=None, unit='U_USD', seg=None):
    p = {'instant': instant} if instant else {'startDate': start, 'endDate': end}
    fc = {'value': value, 'period': p, 'unitRef': unit}
    if seg:
        fc['segment'] = seg
    return fc


# ---------------- tier1: Decimal-exact value matching (RED: int-truncation conflates) ----------
# fixtures use a concept that legally passes concept_ok/concept_type_ok ('Revenues' + a 'total
# revenue' name) so the tests isolate EXACTLY the value-comparison logic (tier1 L353/L373).
def test_tier1_decimal_never_matches_a_different_decimal():
    """2.34 must NOT bind a 2.01 fact. Today tier1 truncates both to '2' and matches."""
    b = blob('Revenues', [fact('2.01', '2024-01-01', '2024-12-31')])
    r = L.tier1([b], 'total revenue', 2.34, '2024-12-31')
    assert r is None, f"2.34 bound a 2.01 fact: {r}"


def test_tier1_exact_decimal_still_matches_itself():
    b = blob('Revenues', [fact('2.34', '2024-01-01', '2024-12-31')])
    r = L.tier1([b], 'total revenue', 2.34, '2024-12-31')
    assert r is not None, "exact decimal failed to match itself"


# ---------------- value_ok: % class guard + fractional rounding (RED: both reproduced) ----------
def test_value_ok_number_never_accepts_percent_token():
    assert not L.value_ok(86, 'number', 'utilization was 86% in Q4'), \
        "a plain number bound a %-marked token"


def test_value_ok_number_still_accepts_plain_token():
    assert L.value_ok(86, 'number', 'International Stores 86 at fiscal year end')


def test_value_ok_fractional_never_accepts_integer_rounded_print():
    assert not L.value_ok(2.34, '%', 'gross margin was 2% for the year'), \
        "2.34 accepted the integer-rounded print '2%'"


def test_value_ok_fractional_accepts_one_decimal_and_exact():
    assert L.value_ok(2.34, '%', 'gross margin was 2.3% for the year')
    assert L.value_ok(2.34, '%', 'gross margin was 2.34% for the year')


def test_value_ok_integral_percent_keeps_bare_form():
    assert L.value_ok(2.0, '%', 'gross margin was 2% for the year')


# ---------------- negatives / parentheses: GREEN guards (must survive the fixes) ---------------
def test_sign_guards_survive():
    assert not L.value_ok(123, 'number', 'operating income (123)')     # positive vs printed-negative
    assert L.value_ok(-123, 'number', 'operating income (123)')
    assert L.value_ok(-123, 'number', 'operating income -123')


# ---------------- substring invariant: emitted quotes are RAW source slices (RED: _tidy) -------
def test_row_quote_is_exact_substring_of_source():
    t = 'Segment results\nInternational Stores\n  86   at fiscal year end'
    q = L.row_quote([t], ['International', 'Stores'], 86, 'number')
    assert q is not None
    assert q in t, f"emitted quote is not a raw slice of the source: {q!r}"


def test_scan_text_snips_are_exact_substrings_of_source():
    t = 'Overview\nTotal   revenue was\n $ 6,707 for the year ended December 31, 2024.'
    strict, snips = L.scan_text([t], 'total revenue', 6707, 'number')
    for s in snips:
        assert s in t, f"snippet is not a raw slice of the source: {s!r}"
    if strict is not None:
        assert strict in t, f"strict quote is not a raw slice: {strict!r}"


# ---------------- xbrl_lane: Decimal-exact · instant · exact dates · unit conflicts ------------
def test_resolve_returns_exact_decimal_not_rounded():
    b = blob('Revenues', [fact('2.34', '2024-01-01', '2024-12-31')])
    got = xbrl_lane.resolve([b], 'us-gaap:Revenues', [], '2024-01-01', '2024-12-31')
    assert got == Decimal('2.34'), f"decimal destroyed: {got!r}"


def test_resolve_instant_fact_via_gp_date_date():
    b = blob('CashAndCashEquivalentsAtCarryingValue', [fact('1138000000', instant='2024-12-31')])
    got = xbrl_lane.resolve([b], 'us-gaap:CashAndCashEquivalentsAtCarryingValue', [],
                            '2024-12-31', '2024-12-31')
    assert got == Decimal('1138000000'), f"instant fact not resolved: {got!r}"


def test_resolve_rejects_mixed_convention_dates():
    """inclusive start + exclusive-style end must NOT match an inclusive request (reproduced)."""
    b = blob('Revenues', [fact('5000', '2024-01-01', '2025-01-01')])
    got = xbrl_lane.resolve([b], 'us-gaap:Revenues', [], '2024-01-01', '2024-12-31')
    assert got is None, f"mixed-convention fact accepted: {got!r}"


def test_resolve_rejects_neighboring_period_end():
    """a fact ending one day later is a DIFFERENT period — no ±1-day tolerance."""
    b = blob('Revenues', [fact('5000', '2024-01-01', '2025-01-01')])
    got = xbrl_lane.resolve([b], 'us-gaap:Revenues', [], '2024-01-01', '2025-01-01')
    assert got == Decimal('5000')                      # exact same dates still match…
    got2 = xbrl_lane.resolve([b], 'us-gaap:Revenues', [], '2024-01-02', '2025-01-01')
    assert got2 is None, "start off by one day matched"


def test_resolve_concept_local_name_exact_only():
    """storage is BARE local names (verified live): request prefixes strip deterministically;
    a DIFFERENT local name never matches (green guard on exactness)."""
    b = blob('Revenues', [fact('5000', '2024-01-01', '2024-12-31')])
    assert xbrl_lane.resolve([b], 'us-gaap:Revenues', [], '2024-01-01', '2024-12-31') is not None
    assert xbrl_lane.resolve([b], 'us-gaap:OtherRevenues', [], '2024-01-01', '2024-12-31') is None


def test_resolve_rejects_wrong_prefix_when_stored_prefixed():
    """Round-12: evil:Revenues must NOT satisfy us-gaap:Revenues. Storage is normally BARE
    (verified live) and a bare key still matches by local name; but when the stored key CARRIES a
    prefix, it must match the requested prefix exactly."""
    b = blob('evil:Revenues', [fact('5000', '2024-01-01', '2024-12-31')])
    assert xbrl_lane.resolve([b], 'us-gaap:Revenues', [], '2024-01-01', '2024-12-31') is None
    g = blob('us-gaap:Revenues', [fact('5000', '2024-01-01', '2024-12-31')])
    assert xbrl_lane.resolve([g], 'us-gaap:Revenues', [], '2024-01-01', '2024-12-31') == Decimal('5000')


def test_resolve_expected_unit_class():
    """Round-12: shares must never satisfy a money request (and vice versa)."""
    b = blob('SomeThing', [fact('100', '2024-01-01', '2024-12-31', unit='U_shares')])
    assert xbrl_lane.resolve([b], 'SomeThing', [], '2024-01-01', '2024-12-31',
                             expected_unit='money') is None
    m = blob('SomeThing', [fact('100', '2024-01-01', '2024-12-31', unit='U_USD')])
    assert xbrl_lane.resolve([m], 'SomeThing', [], '2024-01-01', '2024-12-31',
                             expected_unit='money') == Decimal('100')
    assert xbrl_lane.resolve([m], 'SomeThing', [], '2024-01-01', '2024-12-31',
                             expected_unit='nonmoney') is None


def test_tier1_unit_class_guard():
    """Round-12: a currency KPI (is_currency=1) must not bind a shares-tagged fact."""
    sh = blob('Revenues', [fact('5000', '2024-01-01', '2024-12-31', unit='U_shares')])
    assert L.tier1([sh], 'total revenue', 5000, '2024-12-31', is_currency=1) is None
    us = blob('Revenues', [fact('5000', '2024-01-01', '2024-12-31', unit='U_USD')])
    assert L.tier1([us], 'total revenue', 5000, '2024-12-31', is_currency=1) is not None


def test_resolve_unit_conflict_abstains():
    """same identity+value under TWO different unitRefs = ambiguous → abstain (RED: no unit logic)."""
    b = blob('SomeCount', [fact('100', '2024-01-01', '2024-12-31', unit='U_USD'),
                           fact('100', '2024-01-01', '2024-12-31', unit='U_shares')])
    got = xbrl_lane.resolve([b], 'SomeCount', [], '2024-01-01', '2024-12-31')
    assert got is None, f"unitRef conflict silently resolved: {got!r}"


def test_resolve_unit_filter_when_caller_supplies_it():
    b = blob('SomeCount', [fact('100', '2024-01-01', '2024-12-31', unit='U_USD'),
                           fact('200', '2024-01-01', '2024-12-31', unit='U_shares')])
    got = xbrl_lane.resolve([b], 'SomeCount', [], '2024-01-01', '2024-12-31', unit_ref='U_shares')
    assert got == Decimal('200'), f"unit filter missing: {got!r}"


# ---------------- zero: labeled findable, generic abstains (full-locator level exists too) -----
def test_value_forms_zero_exists():
    forms = L.value_forms(0, 'number')
    assert any(f == '0' or f.endswith(' 0') or f == '$0' or f == '$ 0' for f in forms), forms


# ---------------- round-13: rate/percent concepts + scale-evidence gate ----------------
def test_rate_concepts_decided_by_unit_identity_not_name():
    """Round-14 REVERSAL of the round-13 name-token ban (reviewer-confirmed over-reject): the
    certified truth pool carries `awk:PublicUtilitiesGeneralRateCaseAuthorizationsAnnualized
    IncrementalRevenuesApprovedAmount` — a REAL monetary concept with 'Rate' in its name (4 rows).
    Names must not decide; UNIT IDENTITY does: a 'pure'-unitRef fact (rates/ratios/percents) never
    binds in the money/number lane."""
    cert = 'PublicUtilitiesGeneralRateCaseAuthorizationsAnnualizedIncrementalRevenuesApprovedAmount'
    assert L.concept_ok(cert), "the certified Rate-named monetary concept must survive"
    assert L.concept_ok('SalesRevenueGrowthRate'), "names no longer decide"
    usd = blob(cert, [fact('17000000', '2024-01-01', '2024-12-31', unit='U_USD')])
    got = L.tier1([usd], 'Total Revenue', 17000000, '2024-12-31', is_currency=1)
    assert got is not None, "USD fact under a Rate-named concept must bind"
    pure = blob('OperatingIncomeSomething',
                [fact('670', '2024-01-01', '2024-12-31', unit='U_pure')])
    assert L.tier1([pure], 'total operating income units', 670, '2024-12-31',
                   is_currency=0) is None, "a pure-unit (rate/ratio) fact never binds this lane"
    print("[ok] unit identity decides: certified Rate-named USD concept binds; pure-unit never")


def test_row_quote_scale_gate_param():
    """Round-13 gate + round-14 tightening (reviewer-confirmed): scale evidence must match the
    REQUIRED multiplier, and a marker must be the NEAREST one before the hit (52 cohort text
    blocks carry MIXED scale markers). Default (certified callers) stays byte-identical."""
    naked = ['Widget revenues 5,365 for the period']
    marked = ['(in millions) Widget revenues 5,365 for the period']
    toks = ['Widget', 'revenues']
    assert L.row_quote(naked, toks, 5365000000, None) is not None          # legacy default intact
    assert L.row_quote(naked, toks, 5365000000, None, scale_gate=True) is None
    assert L.row_quote(marked, toks, 5365000000, None, scale_gate=True) is not None
    assert L.row_quote(naked, toks, 5365, None, scale_gate=True) is not None   # full magnitude
    tail = ['Widget revenues 5.4 billion for the period']
    assert L.row_quote(tail, toks, 5400000000, None, scale_gate=True) is not None  # tag rides the hit
    pct = ['Widget margin 12.5 % for the period']
    assert L.row_quote(pct, ['Widget', 'margin'], 12.5, '%', scale_gate=True) is not None  # % exempt
    # round-14: the multiplier must MATCH — 'million' can never prove a value needing 'billion'
    wrong_tail = ['Widget revenues 1.2 million for the period']
    assert L.row_quote(wrong_tail, toks, 1200000000, None, scale_gate=True) is None
    right_tail = ['Widget revenues 1.2 billion for the period']
    assert L.row_quote(right_tail, toks, 1200000000, None, scale_gate=True) is not None
    # round-14: a thousands header can never prove a millions-implying form
    k_marked = ['(in thousands) Widget revenues 1,200 for the period']
    assert L.row_quote(k_marked, toks, 1200000000, None, scale_gate=True) is None
    # (1e3-scaled forms are NOT generated by _tableforms — a pre-existing certified-recipe fact,
    # not a round-14 change; the matching-marker positive case uses the millions form instead)
    m_marked = ['(in millions) Widget revenues 1.2 for the period']
    assert L.row_quote(m_marked, toks, 1200000, None, scale_gate=True) is not None
    # round-14 locality: the CURRENT TABLE's declarations rule; an unrelated earlier table's
    # marker never proves this table's scale
    mixed = ['first table (in millions) ... END ##TABLE_START (in thousands) Widget revenues 1,200']
    assert L.row_quote(mixed, toks, 1200000000, None, scale_gate=True) is None
    mixed2 = ['first table (in thousands) ... END ##TABLE_START (in millions) Widget revenues 1,200']
    assert L.row_quote(mixed2, toks, 1200000000, None, scale_gate=True) is not None
    # a REAL table header declares several scales for different columns — '(In millions, except
    # shares in thousands)' (AAPL's standard header; regenerate #1 wrongly dropped 'Products
    # $ 294,866' because the NEAREST single word was 'thousands'). The required multiplier must be
    # AMONG the current table's declarations.
    combined = ['##TABLE_START (In millions, except number of shares, which are reflected in '
                'thousands, and per-share amounts) Products revenues $ 294,866 for the year']
    assert L.row_quote(combined, ['Products', 'revenues'], 294866000000, None,
                       scale_gate=True) is not None
    # a table that declares NOTHING inherits the nearest preceding declaration (AA/Alcoa layout:
    # '(in millions)' is a caption ABOVE the table-start tag; regenerate #2 wrongly dropped 70
    # certified-good binds like 'United States $ 5,365'). A table that DOES declare stays strict.
    caption = ['(in millions) segment detail follows ##TABLE_START United States revenues '
               '$ 5,365 for the year']
    assert L.row_quote(caption, ['United', 'States', 'revenues'], 5365000000, None,
                       scale_gate=True) is not None
    caption_wrong = ['(in thousands) segment detail follows ##TABLE_START United States revenues '
                     '$ 5,365 for the year']
    assert L.row_quote(caption_wrong, ['United', 'States', 'revenues'], 5365000000, None,
                       scale_gate=True) is None
    print("[ok] scale gate: multiplier ∈ the CURRENT table's declared scales; outside tables the "
          "nearest declaration; certified callers intact")


def test_value_ok_rejects_contradicting_scale_tag():
    """Round-14: value_ok's final self-check must reject a quote whose printed scale tag
    CONTRADICTS the claimed value ('1.2 million' can never certify 1.2 BILLION)."""
    assert not L.value_ok(1200000000, None, 'Widget revenues 1.2 million for the period')
    assert L.value_ok(1200000000, None, 'Widget revenues 1.2 billion for the period')
    assert L.value_ok(1200000000, None, 'Widget revenues 1,200 for the period')  # marker proved at collection
    assert not L.value_ok(5365, None, 'Widget revenues 5,365 million for the period')  # tag contradicts full print
    assert L.value_ok(5365, None, 'Widget revenues 5,365 for the period')
    print("[ok] value_ok: printed scale tag can veto a contradicted bind")


def test_scan_text_scale_gate_param():
    """Round-13: the strict (auto-resolve) result honors the gate; candidate snippets stay
    permissive (the LLM tier re-verifies its own output)."""
    naked = ['Widget revenues 5,365 for the period']
    strict, snips = L.scan_text(naked, 'Widget Revenues', 5365000000, None, scale_gate=True)
    assert strict is None, strict
    assert snips, "candidates must still flow to the LLM tier"
    strict2, _ = L.scan_text(['(in millions) Widget revenues 5,365'], 'Widget Revenues',
                             5365000000, None, scale_gate=True)
    assert strict2 is not None
    print("[ok] scan_text: strict result gated, snippets permissive")


# ---------------- round-16: order-free tier1, letter-glued numbers, inheritance unanimity ----
def test_tier1_tie_rule_order_free():
    """Round-17 REVERSAL of the alias pick (reviewer-reproduced: a coincidence-equal
    CostOfRevenue sorts before Revenues and would be CHOSEN for a revenue KPI — the "same
    quantity" alias assumption is false across semantically different concepts that pass the
    loose type filter). ANY difference among top-score candidates — concept, slice, or period —
    ABSTAINS again; order can never decide; identical duplicates still bind."""
    b1 = blob('Revenues', [fact('5000', '2024-01-01', '2024-12-31', unit='U_USD')])
    b2 = blob('RevenuesNet', [fact('5000', '2024-01-01', '2024-12-31', unit='U_USD')])
    assert L.tier1([b1, b2], 'total revenue', 5000, '2024-12-31', is_currency=1) is None
    assert L.tier1([b2, b1], 'total revenue', 5000, '2024-12-31', is_currency=1) is None
    cost = blob('CostOfRevenue', [fact('5000', '2024-01-01', '2024-12-31', unit='U_USD')])
    assert L.tier1([b1, cost], 'total revenue', 5000, '2024-12-31', is_currency=1) is None
    assert L.tier1([cost, b1], 'total revenue', 5000, '2024-12-31', is_currency=1) is None
    q = blob('Revenues', [fact('5000', '2024-10-01', '2024-12-31', unit='U_USD'),
                          fact('5000', '2024-01-01', '2024-12-31', unit='U_USD')])
    assert L.tier1([q], 'total revenue', 5000, '2024-12-31', is_currency=1) is None
    dup = blob('Revenues', [fact('5000', '2024-01-01', '2024-12-31', unit='U_USD'),
                            fact('5000', '2024-01-01', '2024-12-31', unit='U_USD')])
    assert L.tier1([dup], 'total revenue', 5000, '2024-12-31', is_currency=1) is not None
    print("[ok] tier1: ANY tie difference abstains; identical duplicates bind; order-free")


def test_geo_members_match_country_names():
    """Round-18 (reviewer-reproduced ×2 on my round-17 rule): token CONTAINMENT is not geography
    identity — country:GE bound 'South Georgia Revenue', country:US bound 'United States and
    Canada Revenue'. A country member now binds ONLY on EXACT normalized identity: the KPI's
    slice-token set must EQUAL the country name's token set. Fail closed; no fuzzy geography."""
    def geo(code, v='100'):
        return blob('Revenues', [fact(v, '2024-01-01', '2024-12-31', unit='U_USD',
                    seg=[{'dimension': 'srt:StatementGeographicalAxis',
                          'value': f'country:{code}'}])])
    Y, N = (lambda c, k: L.tier1([geo(c)], k, 100, '2024-12-31', is_currency=1) is not None), None
    assert Y('US', 'United States Revenue')
    assert not Y('US', 'United Kingdom Revenue')
    assert not Y('US', 'United States and Canada Revenue')      # combined region ≠ US alone
    assert Y('GE', 'Georgia Revenue')
    assert not Y('GE', 'South Georgia Revenue')                 # the island, not the country
    assert Y('PG', 'Papua New Guinea Revenue')
    assert not Y('GN', 'Papua New Guinea Revenue')              # Guinea ≠ Papua New Guinea
    assert Y('WS', 'Samoa Revenue')
    assert not Y('WS', 'American Samoa Revenue')
    assert Y('KR', 'South Korea Revenue')
    assert not Y('KR', 'North Korea Revenue')
    assert Y('BA', 'Bosnia and Herzegovina Revenue')            # exact long names still bind
    assert Y('CG', 'Congo Revenue')
    assert not Y('CD', 'Congo Revenue')                         # DR Congo name ≠ plain Congo
    print("[ok] country members: EXACT geography identity; all reviewer pin pairs hold")


def test_country_plus_product_multi_axis():
    """Round-19 (reviewer-reproduced, both directions): a [country:US, IPhoneMember] fact is a
    US-iPhone SLICE — plain 'United States Revenue' must NOT bind it, and 'United States iPhone
    Revenue' MUST. The identity check covers ALL meaningful members, not only the country."""
    mixed = blob('Revenues', [fact('100', '2024-01-01', '2024-12-31', unit='U_USD', seg=[
        {'dimension': 'srt:StatementGeographicalAxis', 'value': 'country:US'},
        {'dimension': 'us-gaap:ProductOrServiceAxis', 'value': 'aapl:IPhoneMember'}])])
    assert L.tier1([mixed], 'United States Revenue', 100, '2024-12-31', is_currency=1) is None
    assert L.tier1([mixed], 'United States iPhone Revenue', 100, '2024-12-31',
                   is_currency=1) is not None
    # a country + STRUCTURAL co-member (fully generic-filtered) still equals the plain country KPI
    struct = blob('Revenues', [fact('200', '2024-01-01', '2024-12-31', unit='U_USD', seg=[
        {'dimension': 'srt:StatementGeographicalAxis', 'value': 'country:US'},
        {'dimension': 'us-gaap:StatementBusinessSegmentsAxis',
         'value': 'us-gaap:OperatingSegmentsMember'}])])
    assert L.tier1([struct], 'United States Revenue', 200, '2024-12-31', is_currency=1) is not None
    print("[ok] multi-axis country: the KPI must name the WHOLE slice")


def test_allcaps_camel_members_tokenize():
    """Round-17: acronym splitting is restricted to runs of >=2 capitals so 'IPhoneMember' stays
    EXACTLY {'iphone'} (round-16's union leaked 'phone' — a 'Phone Revenue' KPI could bind it);
    'EMEASegmentMember' still yields 'emea'."""
    t = L.member_tokens(['aapl:IPhoneMember'])
    assert 'iphone' in t and 'phone' not in t, t
    t2 = L.member_tokens(['acn:EMEASegmentMember'])
    assert 'emea' in t2, t2                 # ('segment' is filtered as a GENERIC member word)
    ip = blob('Revenues', [fact('200000000', '2024-01-01', '2024-12-31', unit='U_USD',
              seg=[{'dimension': 'us-gaap:ProductOrServiceAxis', 'value': 'aapl:IPhoneMember'}])])
    assert L.tier1([ip], 'Phone Revenue', 200000000, '2024-12-31', is_currency=1) is None
    print("[ok] IPhone tokens unchanged; EMEA splits; Phone never binds IPhone")


def test_reversed_dimension_order_canonical():
    """Round-18 (reviewer: axis list was sorted but member text and quote were NOT): reversing a
    fact's dimension list must produce a FULLY identical record — every field."""
    segs = [{'dimension': 'us-gaap:StatementBusinessSegmentsAxis', 'value': 'x:AlphaMember'},
            {'dimension': 'srt:StatementGeographicalAxis', 'value': 'x:BetalandMember'}]
    a = blob('Revenues', [fact('5000', '2024-01-01', '2024-12-31', unit='U_USD', seg=segs)])
    b = blob('Revenues', [fact('5000', '2024-01-01', '2024-12-31', unit='U_USD', seg=list(reversed(segs)))])
    ra = L.tier1([a], 'alpha betaland revenue', 5000, '2024-12-31', is_currency=1)
    rb = L.tier1([b], 'alpha betaland revenue', 5000, '2024-12-31', is_currency=1)
    assert ra is not None and rb is not None
    assert ra == rb, {k: (ra[k], rb[k]) for k in ra if ra[k] != rb[k]}
    print("[ok] reversed dimensions -> byte-identical record (member, quote, axes, all fields)")


def test_reversed_text_input_deterministic():
    """Round-18 upgrade (reviewer: the old fixture had only 3 matches, below the 20-hit cutoff):
    25 REAL matching occurrences — past the bound — and reversing the text order must still give
    identical output; snips stay bounded by keep."""
    texts = [f'section {i}: total widget revenue 5,432 reported in unit {i}' for i in range(25)]
    f1 = L.scan_text(texts, 'total widget revenue', 5432, 'number')
    f2 = L.scan_text(list(reversed(texts)), 'total widget revenue', 5432, 'number')
    assert f1 == f2, (f1[1][:2], f2[1][:2])
    assert len(f1[1]) <= 6
    print("[ok] 25-match reversed input identical; candidates bounded")



# ---- round-18: the four round-16 safety tests RESTORED UNCHANGED (my round-17 test-file
# surgery sliced to EOF and silently deleted them — reviewer catch; battery 107->105 explained) --
def test_boundary_rejects_letter_glued_numbers():
    """Round-16 (reviewer-confirmed live): '86' inside 'modelX86' or 'FY86' is NOT a value print.
    The numeric boundary now rejects ALPHANUMERIC neighbors, not just digit-gluing."""
    assert not L.bounded_hit('the modelX86 line', '86')
    assert not L.bounded_hit('in FY86 we grew', '86')
    assert L.bounded_hit('stores grew to 86 units', '86')
    assert L.bounded_hit('a total of $86 in fees', '86')
    assert L.bounded_hit('(86)', '86')
    assert L.bounded_hit('margin was 86% overall', '86')
    print("[ok] boundary: letter-glued digits never bind")


def test_label_tokens_match_whole_words_only():
    """Round-16: label adjacency must match WHOLE WORDS — 'Net' never matches inside 'Internet',
    'Car' never inside 'Oscar'. All-tokens-present still required."""
    assert L.row_quote(['Internet division revenues 5,432 for the year'],
                       ['Net', 'revenues'], 5432, None) is None
    assert L.row_quote(['Net revenues 5,432 for the year'], ['Net', 'revenues'], 5432, None) is not None
    assert L.row_quote(['Oscar brand sales 1,200 in total'], ['Car', 'sales'], 1200, None) is None
    print("[ok] label tokens are whole words, never substrings")


def test_scale_inheritance_requires_unanimity():
    """Round-16 (reviewer-confirmed hazard): an UNDECLARED table inherits a preceding declaration
    ONLY when the text declares exactly ONE scale overall (reading convention); any mixed-scale
    text never lends to undeclared tables. Declared tables stay strict either way."""
    toks = ['Widget', 'revenues']
    mixed_borrow = ['(in millions) ##TABLE_START a END (in thousands) ##TABLE_START b END '
                    '##TABLE_START Widget revenues 1,200 more']
    assert L.row_quote(mixed_borrow, toks, 1200000000, None, scale_gate=True) is None
    mixed_near = ['(in thousands) ##TABLE_START a END (in millions) intro '
                  '##TABLE_START Widget revenues 1,200 more']
    assert L.row_quote(mixed_near, toks, 1200000000, None, scale_gate=True) is None
    single = ['(in millions) intro ##TABLE_START alpha END ##TABLE_START Widget revenues 1,200']
    assert L.row_quote(single, toks, 1200000000, None, scale_gate=True) is not None
    print("[ok] scale inheritance: unanimous document convention only")


def test_thousand_and_trillion_scaled_forms():
    """Round-16: exact thousand- and trillion-scaled table forms exist and are marker-gated like
    the rest ('(in thousands) 1,200' can finally prove 1.2 million; wrong marker still rejects)."""
    toks = ['Widget', 'revenues']
    k = ['(in thousands) Widget revenues 1,200 for the period']
    assert L.row_quote(k, toks, 1200000, None, scale_gate=True) is not None
    assert L.row_quote(k, toks, 1200000000, None, scale_gate=True) is None   # thousands ≠ billions
    assert L.row_quote(['Widget revenues 1,200 no marker'], toks, 1200000, None,
                       scale_gate=True) is None
    print("[ok] thousand/trillion scale forms, marker-gated")



def test_strong_match_at_position_21_survives():
    """Round-19 (reviewer): bounded collection must keep the BEST evidence, not the first-N in
    canonical order — 20 weak matches in 'a...' texts must not evict a strong labeled table match
    living in a 'z...' text."""
    weak = [f'a{i:02d} filler mentions 5,432 without context' for i in range(20)]
    strong = ['z ##TABLE_START total widget revenue 5,432 in the annual table']
    strict, snips = L.scan_text(weak + strong, 'total widget revenue', 5432, 'number')
    assert snips and 'z ' [0] in snips[0][:1] or '##TABLE_START' in snips[0], snips[:1]
    assert any('##TABLE_START' in sn for sn in snips), "strong table match evicted by weak fill"
    print("[ok] rank-based retention: position-21 strong evidence survives")


def test_full_slice_proof_for_all_dimensions():
    """Round-20 (reviewer-reproduced): slice completeness must hold for EVERY meaningful member,
    not only country: — [Alpha, Beta] must not bind plain 'Alpha Revenue' (Beta unproven);
    'Alpha Beta Revenue' binds; identical member names under DIFFERENT axes stay bindable;
    structural members (already-proven exact ∅-token class) change nothing."""
    ab = blob('Revenues', [fact('100', '2024-01-01', '2024-12-31', unit='U_USD', seg=[
        {'dimension': 'x:AxisOne', 'value': 'x:AlphaMember'},
        {'dimension': 'x:AxisTwo', 'value': 'x:BetaMember'}])])
    assert L.tier1([ab], 'Alpha Revenue', 100, '2024-12-31', is_currency=1) is None
    assert L.tier1([ab], 'Alpha Beta Revenue', 100, '2024-12-31', is_currency=1) is not None
    dup = blob('Revenues', [fact('200', '2024-01-01', '2024-12-31', unit='U_USD', seg=[
        {'dimension': 'x:AxisOne', 'value': 'x:AlphaMember'},
        {'dimension': 'x:AxisTwo', 'value': 'y:AlphaMember'}])])
    assert L.tier1([dup], 'Alpha Revenue', 200, '2024-12-31', is_currency=1) is not None
    st = blob('Revenues', [fact('300', '2024-01-01', '2024-12-31', unit='U_USD', seg=[
        {'dimension': 'x:AxisOne', 'value': 'x:AlphaMember'},
        {'dimension': 'us-gaap:StatementBusinessSegmentsAxis',
         'value': 'us-gaap:OperatingSegmentsMember'}])])
    assert L.tier1([st], 'Alpha Revenue', 300, '2024-12-31', is_currency=1) is not None
    print("[ok] full-slice proof for every dimension; structural members exempt")


def test_ranking_whole_words_before_value_and_cap():
    """Round-20: rank candidates by WHOLE-WORD label tokens in the text BEFORE the value —
    'Internet' lines score zero for a 'Net' KPI; the exact 'Net Revenue' line ranks first.
    max_hits is an honored return cap (5 in -> never more than 5 out) and pruning actually
    triggers past 4x max_hits."""
    texts = [f'a{i:02d} Internet Revenue was 5,432 in region {i}' for i in range(30)]
    texts += ['z Net Revenue totalled 5,432 for the year']
    strict, snips = L.scan_text(texts, 'Net Revenue', 5432, 'number', max_hits=5)
    assert len(snips) <= 5, len(snips)
    assert 'Net Revenue totalled' in snips[0], snips[0]     # the true whole-word line ranks FIRST
    print("[ok] whole-word pre-value ranking; max_hits honored; pruning exercised")



def test_slice_gate_shared_normalization():
    """Round-20b: ONE normalization on BOTH sides of the slice equality — member-name furniture
    ('...RevenueMember', '...SegmentMember' with a stopped word, 'Sector', 'Company') must not
    fail certified binds; a REAL unproven member (NonUs) still rejects."""
    c = blob('Revenues', [fact('100', '2024-01-01', '2024-12-31', unit='U_USD', seg=[
        {'dimension': 'x:A', 'value': 'x:ConsultingRevenueMember'}])])
    assert L.tier1([c], 'Consulting Revenue', 100, '2024-12-31', is_currency=1) is not None
    g = blob('Revenues', [fact('200', '2024-01-01', '2024-12-31', unit='U_USD', seg=[
        {'dimension': 'x:A', 'value': 'x:GrowthMarketsSegmentMember'}])])
    assert L.tier1([g], 'Growth Markets Revenue', 200, '2024-12-31', is_currency=1) is not None
    f = blob('Revenues', [fact('300', '2024-01-01', '2024-12-31', unit='U_USD', seg=[
        {'dimension': 'x:A', 'value': 'x:FinancialServicesSectorMember'}])])
    assert L.tier1([f], 'Financial Services Revenue', 300, '2024-12-31', is_currency=1) is not None
    nonus = blob('Revenues', [fact('400', '2024-01-01', '2024-12-31', unit='U_USD', seg=[
        {'dimension': 'x:A', 'value': 'x:EstablishedPharmaceuticalProductsMember'},
        {'dimension': 'x:B', 'value': 'us-gaap:NonUsMember'}])])
    assert L.tier1([nonus], 'Established Pharmaceutical Products Revenue', 400,
                   '2024-12-31', is_currency=1) is None      # non-US slice stays unproven
    print("[ok] shared normalization recovers furniture-only misses; NonUs still rejects")
