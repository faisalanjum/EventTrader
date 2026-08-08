"""#818 — ONE exact power-of-ten operation, and an extreme scale must PARK.

OBSERVED DEFECT (audit 2026-07-27): `expected_multiplier("usd", 1000000)` raises
a raw `decimal.Overflow`, and the same shift is implemented THREE times:

    slot_convert.exact_scaleb           the careful one (traps Inexact, widens
                                        Emax/Emin, derives precision)
    inline_html expected_slot           Decimal(1).scaleb(int(...))  — unguarded
    inline_html reconcile               base.scaleb(scale)           — its own
                                        localcontext and except clause
    prepared_fact_v2 expected_multiplier Decimal(1).scaleb(int(...)) — unguarded

THE FIX IS A MOVE, NOT A NEW LAYER: the one implementation lives in
`exact_numbers` (dependency-free, importable from BOTH relocation and core);
every caller uses it and none copies its arithmetic. Each boundary converts a
failure into ITS OWN normal park result — the binder abstains, Core raises the
already-declared park outcome.


`ix.scale` is a legal XBRL integer of any size, so an extreme one is a fact we
cannot represent — a PARK — never a crash.
"""
from decimal import Decimal

import pytest

from driver.core.xbrl_attach import attach_event_xbrl

from driver.relocation import exact_numbers as XN
from driver.core.test_round10_event_boundary import (_FIXTURE_NS, _XMLNS,
                                                     parts_for)
from driver.core.test_round10_event_boundary import filing_evidence
from driver.core.driver_neo4j_adapter import GraphFactRows


# --- ONE implementation ----------------------------------------------------

def test_the_shared_operation_is_exact_and_traps_rounding():
    """A power-of-ten shift never changes the coefficient, so nothing rounds.

    The expected value is computed under an INDEPENDENT high-precision context:
    the obvious `big * Decimal(10) ** 6` runs at the DEFAULT 28-digit context
    and rounds — the exact defect this function exists to prevent, and the first
    version of this test asserted against it."""
    from decimal import localcontext
    big = Decimal("1." + "1" * 64)                    # 65 significant digits
    out = XN.exact_scaleb(big, 6)
    assert len(out.as_tuple().digits) == 65, "the coefficient was truncated"
    with localcontext() as ctx:
        ctx.prec = 200
        expected = big * Decimal(10) ** 6
    assert out == expected


def test_29_digit_pairs_stay_distinct_through_the_shift():
    """The defect class this programme keeps hitting: two values that differ
    only beyond the default 28-digit context must not collapse."""
    a = Decimal("1." + "0" * 27 + "1")
    b = Decimal("1." + "0" * 27 + "2")
    assert a != b
    assert XN.exact_scaleb(a, 3) != XN.exact_scaleb(b, 3)


@pytest.mark.parametrize("exponent", [10 ** 19, -(10 ** 19), 10 ** 30])
def test_an_exponent_BEYOND_EMAX_parks_in_the_arithmetic(exponent):
    with pytest.raises(XN.ExactError):
        XN.exact_scaleb(Decimal("1"), exponent)


@pytest.mark.parametrize("digits", [4300, 4301, 5001, 20000])
def test_the_PARK_survives_an_exponent_too_long_to_PRINT(digits):
    """The guard must not crash inside itself.

    `exact_scaleb` reports an unrepresentable magnitude as `ExactError` — the
    park R12-2 built. Its message interpolated the exponent, and `f"{n}"` on an
    integer past CPython's 4,300-digit gate raises a raw `ValueError`. So for
    exactly the values the park exists to catch, the park raised the crash it
    was written to prevent.

    The exponent is built with `int(Decimal(...))`, which performs no string
    conversion, and is never printed here for the same reason."""
    exponent = int(Decimal("9" * digits))
    with pytest.raises(XN.ExactError):
        XN.exact_scaleb(Decimal("1"), exponent)


@pytest.mark.parametrize("exponent", [True, False, 6.0, "6", None, Decimal(6)])
def test_a_non_INTEGER_exponent_is_refused_at_the_arithmetic_boundary(exponent):
    """bool is an int subclass, so `isinstance` is not enough."""
    with pytest.raises(XN.ExactError):
        XN.exact_scaleb(Decimal("1"), exponent)


@pytest.mark.parametrize("exponent,expected", [
    (0, "1"), (6, "1E+6"), (-2, "0.01"), (9, "1E+9"), (-6, "0.000001"),
])
def test_ordinary_exponents_still_work(exponent, expected):
    assert XN.exact_scaleb(Decimal(1), exponent) == Decimal(expected)


# --- Core's boundary: a park, not a crash ----------------------------------

@pytest.mark.parametrize("unit", ["usd", "m_usd", "count", "unknown"])
@pytest.mark.parametrize("scale,boundary", [
    (1000000, "representable but 1,000,001 characters — UNSTORABLE"),
    (10 ** 19, "beyond Emax — not representable at all"),
])
def test_expected_multiplier_PARKS_on_an_extreme_scale(unit, scale, boundary):
    """The audit's case was `("usd", 1000000)` raising a raw decimal.Overflow.
    Routing through the shared exact shift widens Emax, so that magnitude is now
    representable — and must still PARK, because it cannot be STORED. Both
    boundaries land on the same already-declared outcome."""
    from driver.core.xbrl_attach import expected_multiplier
    from driver.core.slot_convert import SlotConversionError
    with pytest.raises(SlotConversionError):
        expected_multiplier(unit, scale)


@pytest.mark.parametrize("unit", ["percent", "percent_yoy", "basis_points", "x"])
def test_the_multiplier_one_family_never_touches_the_arithmetic(unit):
    """They store multiplier 1 whatever the filing declares, so an extreme
    scale cannot reach the shift at all."""
    from driver.core.xbrl_attach import expected_multiplier
    assert expected_multiplier(unit, 1000000) == Decimal(1)
    assert expected_multiplier(unit, -1000000) == Decimal(1)


def test_money_and_count_still_carry_the_real_magnitude():
    from driver.core.xbrl_attach import expected_multiplier
    assert expected_multiplier("usd", 6) == Decimal(10) ** 6
    assert expected_multiplier("count", 3) == Decimal(10) ** 3
    assert expected_multiplier("unknown", 6) == Decimal(10) ** 6


def test_the_park_outcome_is_a_DECLARED_one():
    from driver.core.prepared_fact_v2 import OUTCOME_CLASSES
    from driver.core.slot_convert import SlotConversionError
    assert OUTCOME_CLASSES[SlotConversionError] == "parked"


# --- the binder's boundary: abstain ----------------------------------------

def _doc(scale):
    return (f'<html {_XMLNS}><body><ix:header><ix:resources><xbrli:context id="c1"><xbrli:entity>'
            '<xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193</xbrli:identifier></xbrli:entity>'
            '<xbrli:period><xbrli:startDate>2024-01-01</xbrli:startDate>'
            '<xbrli:endDate>2024-06-30</xbrli:endDate></xbrli:period>'
            '</xbrli:context></ix:resources></ix:header><ix:header><ix:resources><xbrli:unit id="u1">'
            '<xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit></ix:resources></ix:header>'
            f'<p><ix:nonFraction id="f1" name="us-gaap:X" contextRef="c1" '
            f'unitRef="u1" scale="{scale}" decimals="-6">726</ix:nonFraction>'
            '</p></body></html>')


def test_an_ordinary_scale_still_binds():
    from driver.relocation.inline_html import bind_graph_fact
    bound, why = bind_graph_fact(
        _doc(6), inline_element_id="f1", concept="us-gaap:X", context_id="c1",
        unit_ref="u1", unit_name="iso4217:USD", is_divide="0",
        period_type="duration", start_date="2024-01-01", end_date="2024-07-01",
        dims=(), entity_cik="0000320193", raw_value="726,000,000",
        concept_namespace=_FIXTURE_NS["us-gaap"],
        graph_concept_qname="us-gaap:X")
    assert bound is not None, why
    assert bound["evidence"]["scale"] == 6
    assert bound["printed_value"] == Decimal("726")


# ---------------------------------------------------------------------------
# #818 REOPENED — five narrow corrections (review 2026-07-27)
# ---------------------------------------------------------------------------

def test_the_binder_returns_the_PRINTED_VALUE_and_SCALE_only():
    """CORE owns the stored multiplier. The binder was computing one too, so the
    same decision had two authors — and the binder's copy was not even the one
    Core used. It reports what the filing PRINTS and DECLARES; nothing more."""
    from driver.relocation.inline_html import bind_graph_fact
    bound, why = bind_graph_fact(
        _doc(6), inline_element_id="f1", concept="us-gaap:X", context_id="c1",
        unit_ref="u1", unit_name="iso4217:USD", is_divide="0",
        period_type="duration", start_date="2024-01-01", end_date="2024-07-01",
        dims=(), entity_cik="0000320193", raw_value="726,000,000",
        concept_namespace=_FIXTURE_NS["us-gaap"],
        graph_concept_qname="us-gaap:X")
    assert bound is not None, why
    assert bound["printed_value"] == Decimal("726")
    assert bound["evidence"]["scale"] == 6
    assert "expected_slot" not in bound, "the binder still decides the multiplier"


#: THE SAME TWO VALUES, SPELLED UNDER THE FROZEN CANONICAL GRAPH LEXICAL
#: CONTRACT derived from the two writer formatters (corpus evidence shows
#: compatibility, not legality or complete formatter reachability). The
#: exponent spelling `726E+1000000` was convenient but the graph holds none:
#: census 2026-08-01 over 12,402,201 numeric non-nil facts found ZERO
#: exponents, so a value in that spelling could never arrive from Core's
#: graph. These are the identical numbers in the contract's grouped spelling
#: (premise asserted equal below), which keeps this test's purpose exactly:
#: the value RECONCILES, so execution reaches the storable bound instead of
#: parking early at the binder.
# IDENTITY CHANGE (SEQ 265 C): the positive-scale raw is now written in
# the writer's own GROUPED form. The frozen canonical graph lexical
# contract has NO ARTIFICIAL SIZE LIMIT, so this spelling is lawful under
# the contract — but it is NOT a demonstrated current-writer output: the
# runtime's own `f"{huge_int:,}"` refuses at this length (SEQ 269), so
# the test constructs the canonical grouped string directly by STRING
# arithmetic and Core does not inherit CPython's hidden int→str ceiling
# (the same 4,300-digit gate the scale reader already learned about). The
# NEGATIVE-scale param is RETIRED: its raw needed a 999,997-digit
# fraction, and the frozen lexical contract caps fractions at 3 digits
# (census: frac>3 is ZERO across 12,402,201 values) — no lawful graph
# value can demand that path; the arithmetic-side park it exercised
# remains pinned by test_an_exponent_BEYOND_EMAX_parks_in_the_arithmetic.
def _grouped(digits):
    head = len(digits) % 3 or 3
    return ','.join([digits[:head]] + [digits[i:i + 3]
                                       for i in range(head, len(digits), 3)])


@pytest.mark.parametrize("scale,raw", [
    (1000000, _grouped("726" + "0" * 1000000)),
])
def test_the_FULL_DOOR_reaches_the_storage_park_not_a_value_mismatch(scale, raw):
    """The previous full-path proof was false: its value could never reconcile,
    so it parked at the BINDER and never exercised the multiplier at all. These
    values match exactly (726 x 10^scale), so reconciliation SUCCEEDS and
    execution reaches the storable bound — which is what #818 is about."""
    from driver.core.prepared_fact_v2 import ITEM_FIELDS
    from driver.relocation.inline_html import reconcile
    doc = _doc(scale)
    # the premise this test rests on: the value DOES reconcile — and it is the
    # same number the exponent spelling named, in the graph's own form
    from decimal import Decimal as _D
    assert _D(raw.replace(",", "")) == _D(f"726E{scale:+d}")
    assert reconcile("726", None, scale, "", raw) is True

    row = {"period_type": "duration", "start_date": "2024-01-01",
           "end_date": "2024-07-01", "dims": [], "fact_id": "f1",
           "context_id": "c1", "unit_ref": "u1", "unit_name": "iso4217:USD",
           "is_divide": "0", "value": raw, "decimals": "0",
           # the concept identity the real adapter returns
           "concept_namespace": _FIXTURE_NS["us-gaap"],
           "graph_concept_qname": "us-gaap:X"}

    class Graph:
        def get_xbrl_representation_count(self, s): return 1
        def get_xbrl_fact_dimensions(self, s, c): return GraphFactRows(rows=[row], exclusions=())
        def get_source_company_cik(self, s): return "0000320193"

    class Provider:
        def get_filing_document(self, s): return doc

    # build the multiplier with the SHARED operation: `Decimal(10) ** scale`
    # overflows at the default context, so the first version of this test
    # crashed in its own fixture before reaching the code under test.
    slot = {"value": Decimal("726"),
            "scale_multiplier": XN.exact_scaleb(Decimal(1), scale),
            "unit_scale_evidence": None}
    # ITEM 4: every EARLIER input must be lawful, or this test proves nothing
    # about the storage park it names. The evidence and the quote come from the
    # element this fixture's own graph row points at.
    evidence, filing_quote = filing_evidence(doc, "f1")
    it = {k: None for k in ITEM_FIELDS}
    it.update(driver_name="thing", driver_state="reported", quote=filing_quote,
              measurement_raw_spans=[], slice_parts=[], level_unit="usd",
              level_low=dict(slot), level_high=dict(slot), time_type="duration",
              period_start_date="2024-01-01", period_end_date="2024-06-30")
    entry = {"fact": {"fact_type": "metric", "part_ref": "p1",
                      "occurrence_in_part": None, "per_x": None, "item": it},
             "concept": "us-gaap:X", "member_refs": [],
             "source_evidence": evidence}
    res = attach_event_xbrl([entry], source_id="x", store=Graph(),
                            filing_provider=Provider(),
                            text_parts=parts_for([entry]))
    # A value the store cannot MATERIALISE is not a contract violation — the
    # filing is lawful and the scale is legal XBRL. It is the declared
    # NOT_STORABLE park, which is exactly the outcome `SlotConversionError`
    # already mapped to; only the reporting channel changed.
    assert res.facts == ()
    assert len(res.preflight_outcomes) == 1
    row = res.preflight_outcomes[0]
    assert (row["index"], row["decision"], row["codes"]) == \
        (0, "parked", ("NOT_STORABLE",))
    assert "characters in canonical stored form" in row["detail"], row["detail"]


@pytest.mark.parametrize("value", ["NaN", "-NaN", "sNaN", "Infinity", "-Infinity"])
def test_a_NON_FINITE_decimal_is_refused_by_the_shared_operation(value):
    """NaN and +/-Infinity were shifted happily and returned as-is. A non-finite
    is never a source number (`exact_numbers.dec` has always said so); the shift
    must agree."""
    with pytest.raises(XN.ExactError):
        XN.exact_scaleb(Decimal(value), 6)


def test_the_scaleb_scan_is_DERIVED_from_the_production_tree():
    """The first version hand-listed three modules, so a new module using
    `.scaleb` would have been invisible — the same 'pin the instances, miss the
    property' mistake this arc keeps finding. Walk the tree instead."""
    import ast
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[2] / "driver"
    owner = root / "relocation" / "exact_numbers.py"
    scanned, offenders = 0, []
    for path in sorted(root.rglob("*.py")):
        if path.name.startswith("test_") or path == owner:
            continue
        scanned += 1
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Attribute) and node.attr == "scaleb":
                offenders.append(f"{path.relative_to(root)}:{node.lineno}")
    assert scanned >= 15, f"the scan covered only {scanned} modules — too narrow"
    assert not offenders, f"direct .scaleb outside the shared owner: {offenders}"


def test_the_storable_bound_is_exact_at_1024_characters():
    """THE LIMIT IS THE LAW, not the comment describing it. The previous version
    read the source text and matched a phrase, so it measured formatting: a
    lawful reflow of the very comment it policed turned it RED.

    `1E+1023` expands to one digit plus 1,023 zeros — exactly 1,024 characters,
    the widest storable number; one character more parks. Both lengths are
    asserted FIRST, and against the ACTUAL canonical string as well as our own
    counter, so the test cannot pass because something unrelated failed."""
    from driver.core.slot_convert import (SlotConversionError, assert_storable,
                                          stored_char_length)
    widest, over = Decimal("1E+1023"), Decimal("1E+1024")
    assert stored_char_length(widest) == len(format(widest, "f")) == 1024
    assert stored_char_length(over) == len(format(over, "f")) == 1025
    assert assert_storable(widest) is widest          # accepted, unchanged
    with pytest.raises(SlotConversionError):
        assert_storable(over)


def test_scaleb_preserves_the_COEFFICIENT_verbatim():
    """The equivalence pin for the precision simplification (#827 bundle A).

    `exact_scaleb`'s precision is `len(value.as_tuple().digits)` — the value's
    own digit count, nothing added and no floor. A power-of-ten shift moves
    only the exponent, so at exactly that precision the coefficient survives
    VERBATIM — asserted at representation level (`as_tuple()`), because `==`
    on Decimals is numeric and would bless a silently shortened coefficient:
    `...7890E-6 == ...789E-5` is True while only one of them is what the
    filing stated. The trailing-zero case below is the one a one-lower
    precision would silently shorten (Rounded, untrapped) — the measured
    minimality edge from the #827 proof, pinned at the exact boundary.
    """
    from driver.relocation.exact_numbers import exact_scaleb
    cases = [
        (Decimal("12345678901234567890"), -6,
         Decimal("12345678901234.567890")),          # trailing zero SURVIVES
        (Decimal("726"), 6, Decimal("7.26E+8")),
        (Decimal("9" * 40), 1, Decimal("9" * 40 + "E+1")),
        (Decimal("-3.14159"), 3, Decimal("-3141.59")),
        (Decimal("0.026"), 2, Decimal("2.6")),
    ]
    for value, exponent, want in cases:
        got = exact_scaleb(value, exponent)
        assert got.as_tuple() == want.as_tuple(), (value, exponent, got, want)
