"""RED-first proofs for PreparedFact v2 — the G-suite's code half (G1-G11,
G20-G35). Written BEFORE the modules exist; every test names its G-number.

Scope fence: these pin the NEW contract/converter/matcher, which land BESIDE
the live v1 contract. Nothing here flips the live path — the atomic switch
waits on the owner's remaining sign-offs.
"""
import inspect
import json
import os
from decimal import Decimal

import pytest

from driver.core import prepared_fact_v2, slot_convert
from driver.core.driver_ids import dec_canon
from driver.core.fact_match import match_facts
from driver.core.prepared_fact_v2 import (ITEM_FIELDS, RETIRED_FIELDS,
                                          PreparedFactV2, SchemaError,
                                          check_per_x_against_name,
                                          split_slice_part, verify_occurrence)
from driver.core.slot_convert import (CANONICAL_UNITS, SlotConversionError,
                                      check_xbrl_consistency, convert_slot,
                                      validate_slot)

_EVENTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                       ".claude", "plans", "Drivers", "experiments", "fixtures",
                       "events")

# A REAL part from the frozen corpus carrying BOTH scale words (33 of the 134
# parts do — census reproduced). The wrong-word-in-the-same-part attack is
# therefore fixtured from real filings, not invented.
AAL_EVENT = "0000006201-26-000031"
QUOTE_BILLION = "Record first-quarter revenue of $13.9 billion"
QUOTE_MILLION = "First-quarter GAAP net loss of $382 million"
# One quote carrying BOTH scale words — the ordinary shape of a results
# sentence, and the case membership alone cannot adjudicate (G24).
QUOTE_BOTH = "revenue of $13.9 billion versus expectations of $363 million"


def _part_text(source_id, part_name):
    with open(os.path.join(_EVENTS, f"{source_id}.json"), encoding="utf-8") as f:
        ev = json.load(f)
    return next(p["content"] for p in ev["text_parts"] if p["part"] == part_name)


def slot(value, multiplier=1, evidence=None):
    return {"value": Decimal(str(value)),
            "scale_multiplier": Decimal(str(multiplier)),
            "unit_scale_evidence": evidence}


def item(**over):
    """A minimal LAWFUL item: every one of the 32 keys present, null-filled."""
    base = {k: None for k in ITEM_FIELDS}
    base.update(driver_name="revenue", driver_state="reported",
                quote=QUOTE_BILLION, measurement_raw_spans=[], slice_parts=[])
    base.update(over)
    return base


def fact(**over):
    base = {"fact_type": "metric", "part_ref": "exhibit_99_1",
            "occurrence_in_part": None, "per_x": None, "item": item()}
    for k in ("fact_type", "part_ref", "occurrence_in_part", "per_x"):
        if k in over:
            base[k] = over.pop(k)
    if over:
        base["item"] = item(**over)
    return PreparedFactV2.from_dict(base)


def money_fact(value, multiplier="1e6", evidence="million", *, unit="m_usd",
               quote=QUOTE_BOTH, **over):
    """A lawful POINT-shaped money fact: both bands equal, shape hint present
    (law requires the hint whenever numbers are), evidence inside the quote."""
    s = slot(value, multiplier, evidence)
    return fact(quote=quote, level_low=s, level_high=s, level_unit=unit,
                level_shape_hint="point", **over)




# --- the PRODUCTION rule path (these rules are NOT the schema's to enforce) ---
_PROD = dict(driver={"name": "revenue", "fact_type": "metric"},
             source={"date": "2026-04-23T08:30:00-04:00", "source_type": "8k",
                     "ticker": "AAL", "source_id": "0000006201-26-000031"},
             fye_month=12)


def violations(f, **over):
    kw = dict(_PROD)
    kw.update(over)
    return prepared_fact_v2.validate_via_production(f, **kw)


# ---------------------------------------------------------------- G1 / G2 ----

def test_G1_converter_api_fence_by_reflection():
    """The converter may not even ACCEPT a name, quote, qname, or raw text —
    it cannot read meaning it never receives."""
    params = list(inspect.signature(convert_slot).parameters)
    assert params == ["stated_unit", "slot"], params
    banned = ("name", "quote", "qname", "concept", "label", "text", "raw")
    assert not [p for p in params for b in banned if b in p.lower()]


def test_G1_driver_name_changes_nothing():
    """`eps_guidance` vs `revenue_guidance` — a lawful pair (NAME-17). The same
    slot converts identically; the name is not an input."""
    s = slot("1.3", "1e9", "billion")
    assert convert_slot("m_usd", s) == Decimal(1300)
    for name in ("eps_guidance", "revenue_guidance", "revenue_per_region"):
        # revenue_per_region is a LABELLED invalid-name attack (NAME-10): even
        # an unlawful name cannot reach the converter, so it cannot change a value.
        f = money_fact("1.3", "1e9", "billion", driver_name=name)
        assert convert_slot(f.item.level_unit, f.item.level_low) == Decimal(1300)


def test_G2_quote_and_concept_name_cannot_alter_a_value():
    s = slot("363", "1e6", "million")
    values = {convert_slot("m_usd", s)}
    for quote in (QUOTE_MILLION.replace("382", "363"), QUOTE_BOTH,
                  "unrelated prose stating 363 million"):
        f = money_fact("363", "1e6", "million", quote=quote)
        values.add(convert_slot(f.item.level_unit, f.item.level_low))
    assert values == {Decimal(363)}


# --------------------------------------------------------------------- G3 ----

def test_G3_percent_family_units_are_distinct():
    fam = ["percent", "percent_yoy", "percent_sequential", "percent_points",
           "basis_points"]
    assert len(set(fam)) == 5
    assert set(fam) <= set(CANONICAL_UNITS)
    assert len(CANONICAL_UNITS) == 10


@pytest.mark.parametrize("unit", ["percent", "percent_yoy", "percent_sequential",
                                  "percent_points", "basis_points", "x"])
def test_G3_multiplier_not_one_on_a_ratio_slot_parks(unit):
    assert convert_slot(unit, slot("5", 1)) == Decimal(5)
    with pytest.raises(SlotConversionError):
        convert_slot(unit, slot("5", "1e6", "million"))


# --------------------------------------------------------------------- G4 ----

@pytest.mark.parametrize("unit,value,mult,expected", [
    ("m_usd", "1.3", "1e9", "1300"),          # billions stated, canonical millions
    ("m_usd", "363", "1e6", "363"),           # millions stated
    ("m_usd", "800", "1e6", "800"),           # mixed-scale range: the low
    ("m_usd", "1.2", "1e9", "1200"),          # mixed-scale range: the high
    ("m_usd", "850000", "1", "0.85"),         # plain dollars
    ("usd", "85", "0.01", "0.85"),            # cents
    ("m_usd", "1.2", "1e12", "1200000"),      # trillions
    ("usd", "-0.10", "1", "-0.10"),           # signed loss round-trips
])
def test_G4_scale_via_model_stated_multiplier(unit, value, mult, expected):
    assert convert_slot(unit, slot(value, mult)) == Decimal(expected)


def test_G4_mixed_scale_comparison_inside_ONE_fact():
    """$1.3 billion actual vs $363 million expectation — one fact, two scales."""
    f = money_fact("13.9", "1e9", "billion",
                   comparison_low=slot("363", "1e6", "million"),
                   comparison_high=slot("363", "1e6", "million"),
                   comparison_shape_hint="point")
    conv = {k: convert_slot("m_usd", getattr(f.item, k))
            for k in ("level_low", "comparison_low")}
    assert conv == {"level_low": Decimal(13900), "comparison_low": Decimal(363)}


# --------------------------------------------------------------------- G5 ----

@pytest.mark.parametrize("bad", [
    {"value": Decimal(1)},                                     # missing keys
    {"value": Decimal(1), "scale_multiplier": Decimal(1)},     # missing evidence
    {"value": None, "scale_multiplier": Decimal(1), "unit_scale_evidence": None},
    {"value": Decimal(1), "scale_multiplier": None, "unit_scale_evidence": None},
    {"value": Decimal(1), "scale_multiplier": Decimal(0), "unit_scale_evidence": None},
    {"value": Decimal(1), "scale_multiplier": Decimal(-1), "unit_scale_evidence": None},
    {"value": Decimal("NaN"), "scale_multiplier": Decimal(1), "unit_scale_evidence": None},
    {"value": Decimal(1), "scale_multiplier": Decimal("Infinity"), "unit_scale_evidence": None},
    {"value": 1.5, "scale_multiplier": Decimal(1), "unit_scale_evidence": None},
    {"value": Decimal(1), "scale_multiplier": Decimal(1), "unit_scale_evidence": None,
     "extra": "x"},                                            # unknown key
    {"value": None, "scale_multiplier": None, "unit_scale_evidence": None},
])
def test_G5_slot_structure_failures(bad):
    with pytest.raises((SlotConversionError, SchemaError)):
        validate_slot("level_low", bad, stated_unit="m_usd", quote=QUOTE_BILLION)


def test_G5_a_numberless_slot_is_null_not_an_empty_object():
    validate_slot("level_low", None, stated_unit=None, quote=QUOTE_BILLION)
    assert convert_slot("m_usd", None) is None


# --------------------------------------------------------------------- G6 ----

def test_G6_evidence_must_sit_inside_the_quote():
    validate_slot("level_low", slot("13.9", "1e9", "billion"),
                  stated_unit="m_usd", quote=QUOTE_BILLION)
    with pytest.raises(SlotConversionError):
        validate_slot("level_low", slot("13.9", "1e9", "billion"),
                      stated_unit="m_usd", quote=QUOTE_MILLION)


def test_G6_wrong_scale_word_elsewhere_in_the_SAME_part_still_fails():
    """The real corpus fixture: this part contains BOTH words, so a part-wide
    search would wrongly accept 'billion' for the $382 MILLION fact. Membership
    is quote-local, so it fails — as it must."""
    part = _part_text(AAL_EVENT, "exhibit_99_1")
    assert "billion" in part and "million" in part
    assert QUOTE_MILLION in part and "billion" not in QUOTE_MILLION
    with pytest.raises(SlotConversionError):
        validate_slot("level_low", slot("382", "1e9", "billion"),
                      stated_unit="m_usd", quote=QUOTE_MILLION)


def test_G6_evidence_null_only_at_multiplier_one():
    validate_slot("level_low", slot("14", 1), stated_unit="count",
                  quote="opened 14 stores")
    with pytest.raises(SlotConversionError):
        validate_slot("level_low", slot("14", "1e6"), stated_unit="m_usd",
                      quote="opened 14 stores")


def test_G6_extended_quote_carries_a_table_header_scale():
    """The header lives outside the row, so the reader EXTENDS the quote to
    include it (quotes have no length limit) — then membership passes."""
    quote = "(in millions) Total revenue 4,828"
    validate_slot("level_low", slot("4828", "1e6", "in millions"),
                  stated_unit="m_usd", quote=quote)


def test_G6_word_number_evidence_passes():
    quote = "a charge of forty-two million dollars"
    validate_slot("level_low", slot("42", "1e6", "million"),
                  stated_unit="m_usd", quote=quote)
    assert convert_slot("m_usd", slot("42", "1e6", "million")) == Decimal(42)


def test_G6_cents_multiplier_is_usd_only():
    validate_slot("level_low", slot("85", "0.01", "cents"), stated_unit="usd",
                  quote="85 cents per share")
    with pytest.raises(SlotConversionError):
        validate_slot("level_low", slot("85", "0.01", "cents"),
                      stated_unit="m_usd", quote="85 cents per share")


# --------------------------------------------------------------------- G7 ----

def test_G7_unknown_units_still_multiply():
    """Magnitude is preserved; only the UNIT stays unknown. EUR 1.3 billion and
    EUR 363 million must never collapse to 1.3 vs 363."""
    big = convert_slot("unknown", slot("1.3", "1e9", "billion"))
    small = convert_slot("unknown", slot("363", "1e6", "million"))
    assert big == Decimal("1300000000") and small == Decimal("363000000")
    assert big > small


SCALE_WORDS = ("million", "billion", "thousand", "trillion", "lakh", "crore",
               "milliard", "hundred", "cent")


def test_G7_no_tokenizer_exists_to_invent_a_multiplier():
    """An unfamiliar scale word cannot produce a number, because no word->number
    table and no scale-word COMPARISON exist. Proven on the AST, not by grepping
    the text: a docstring explaining the ban is legal; executable code that
    reads scale words is not."""
    import ast
    tree = ast.parse(inspect.getsource(slot_convert))
    # (a) no mapping literal from string keys to numbers — that IS a scale table
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict) and node.keys:
            str_keys = all(isinstance(k, ast.Constant) and isinstance(k.value, str)
                           for k in node.keys if k is not None)
            num_vals = any(isinstance(v, ast.Constant)
                           and isinstance(v.value, (int, float)) for v in node.values)
            assert not (str_keys and num_vals), "a scale-word -> number table exists"
    # (b) no scale word appears in any comparison, container literal, or
    #     subscript — i.e. nowhere code could TEST for one
    import re
    suspects = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Compare, ast.Tuple, ast.List, ast.Set, ast.Subscript)):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                    low = sub.value.lower()
                    # whole words only: `percent` is a UNIT name and must not
                    # register as the scale word `cent`
                    suspects += [w for w in SCALE_WORDS
                                 if re.search(rf"\b{w}s?\b", low)]
    assert not suspects, f"scale words reachable by code: {sorted(set(suspects))}"


# --------------------------------------------------------------------- G8 ----

def test_G8_per_x_rides_once_at_fact_level():
    f = fact(per_x="share")
    assert f.per_x == "share"
    assert "per_x" not in ITEM_FIELDS


def test_G8_per_x_joins_auto_link_equality():
    a = fact(per_x="share", driver_name="eps")
    b = fact(per_x=None, driver_name="eps")
    assert match_facts([a], [b]).links == []


def test_G8_eps_with_per_x_share_is_lawful():
    assert check_per_x_against_name("eps", "share") is None
    assert check_per_x_against_name("eps_guidance", "share") is None
    assert check_per_x_against_name("oil_price_per_barrel", "barrel") is None


def test_G8_name_vs_per_x_disagreement_parks():
    assert check_per_x_against_name("oil_price_per_barrel", "tonne") is not None
    assert check_per_x_against_name("revenue", "share") is not None


def test_G8_the_deferred_acronym_class_PARKS_and_is_never_ruled():
    """`dps` + per_x=share sits in the owner's OPEN acronym question. Code must
    neither admit it (that would decide the question) nor call it unlawful — it
    PARKS, fail-closed, until the owner rules."""
    reason = check_per_x_against_name("dps", "share")
    assert reason is not None and "unverified" in reason.lower()


# --------------------------------------------------------------------- G9 ----

def test_G9_one_canonicalizer_shared_with_run_event():
    assert slot_convert.canonical is dec_canon
    assert slot_convert.canonical(convert_slot("m_usd", slot("1.30", "1e9"))) == "1300"


# -------------------------------------------------------------------- G10 ----

def _pair():
    return money_fact("363"), money_fact("363")


def test_G10_exact_record_and_locator_auto_links():
    g, p = _pair()
    r = match_facts([g], [p])
    assert len(r.links) == 1 and not r.to_grading_gold and not r.to_grading_produced


def test_G10_duplicate_gold_is_INCONCLUSIVE_before_anything_else():
    g, p = _pair()
    r = match_facts([g, money_fact("363")], [p])
    assert r.gold_inconclusive and not r.links


def test_G10_produced_duplicates_collapse_AND_flag_emit_once():
    g, p = _pair()
    r = match_facts([g], [p, money_fact("363")])
    assert len(r.links) == 1, "a duplicate must not double-credit"
    assert r.emit_once_violation is True, "the duplication must be VISIBLE"


def test_G10_same_span_different_fact_never_auto_links():
    g, p = money_fact("363"), money_fact("364")
    r = match_facts([g], [p])
    assert not r.links and r.to_grading_gold and r.to_grading_produced


def test_G10_everything_unmatched_reaches_grading_no_filter():
    g = [money_fact(str(n)) for n in (1, 2, 3)]
    p = [money_fact(str(n)) for n in (2, 9)]
    r = match_facts(g, p)
    assert len(r.links) == 1
    assert len(r.to_grading_gold) == 2 and len(r.to_grading_produced) == 1


def test_G10_order_free_under_full_permutation():
    import itertools
    g = [money_fact(str(n)) for n in (1, 2, 3)]
    p = [money_fact(str(n)) for n in (3, 1, 7)]
    want = None
    for gp in itertools.permutations(g):
        for pp in itertools.permutations(p):
            r = match_facts(list(gp), list(pp))
            got = (sorted(r.link_keys), len(r.to_grading_gold),
                   len(r.to_grading_produced))
            want = want or got
            assert got == want, "matching is order-dependent"


def test_G10_a_missing_locator_is_a_validation_failure():
    with pytest.raises(SchemaError):
        PreparedFactV2.from_dict({"fact_type": "metric", "part_ref": None,
                                  "occurrence_in_part": None, "per_x": None,
                                  "item": item()})


# -------------------------------------------------------------------- G11 ----

def test_G11_occurrence_is_verified_against_the_part_text():
    part = "alpha beta alpha gamma"
    assert verify_occurrence(part, "beta", None) is None
    assert verify_occurrence(part, "alpha", 2) is None
    assert verify_occurrence(part, "alpha", None) is not None    # repeats: needs k
    assert verify_occurrence(part, "beta", 1) is not None        # unique: must be null
    assert verify_occurrence(part, "alpha", 3) is not None       # k > count
    assert verify_occurrence(part, "delta", None) is not None    # fabricated


def test_G11_a_fabricated_locator_fails_on_real_corpus_text():
    part = _part_text(AAL_EVENT, "exhibit_99_1")
    assert verify_occurrence(part, QUOTE_BILLION, None) is None
    assert verify_occurrence(part, "Record first-quarter revenue of $99.9 billion",
                             None) is not None


# ------------------------------------------------------------- G20/G21/G30 ----

def test_G20_table_wide_scale_applied_once():
    quote = "(in millions) Total revenue 4,828"
    validate_slot("level_low", slot("4828", "1e6", "in millions"),
                  stated_unit="m_usd", quote=quote)
    assert convert_slot("m_usd", slot("4828", "1e6", "in millions")) == Decimal(4828)


def test_G21_xbrl_declared_scale_is_never_double_scaled():
    check_xbrl_consistency(displayed=Decimal(390), ix_scale=6,
                           full_value=Decimal("390000000"))
    assert convert_slot("m_usd", slot("390", "1e6")) == Decimal(390)
    with pytest.raises(SlotConversionError):
        check_xbrl_consistency(displayed=Decimal(390), ix_scale=6,
                               full_value=Decimal("390000"))


def test_G30_the_live_fiscal_packet_row():
    """The real packet: displayed 726, ix.scale=6, graph 726,000,000."""
    check_xbrl_consistency(displayed=Decimal(726), ix_scale=6,
                           full_value=Decimal("726000000"))
    assert convert_slot("m_usd", slot("726", "1e6")) == Decimal(726)
    with pytest.raises(SlotConversionError):
        check_xbrl_consistency(displayed=Decimal(726), ix_scale=6,
                               full_value=Decimal("726000000000"))


def test_G22_the_xbrl_lane_does_not_require_quote_local_evidence():
    validate_slot("level_low", slot("726", "1e6"), stated_unit="m_usd",
                  quote="North America 390 361 778 726", lane="xbrl")
    with pytest.raises(SlotConversionError):
        validate_slot("level_low", slot("726", "1e6"), stated_unit="m_usd",
                      quote="North America 390 361 778 726", lane="text")


# -------------------------------------------------------------------- G23 ----

@pytest.mark.parametrize("retired", sorted(RETIRED_FIELDS))
def test_G23_old_payload_fields_are_rejected_atomically(retired):
    d = {"fact_type": "metric", "part_ref": "p01", "occurrence_in_part": None,
         "per_x": None, "item": item(**{retired: "anything"})}
    with pytest.raises(SchemaError) as e:
        PreparedFactV2.from_dict(d)
    assert retired in str(e.value)


def test_G23_a_scalar_numeric_slot_is_rejected():
    with pytest.raises(SchemaError):
        PreparedFactV2.from_dict({"fact_type": "metric", "part_ref": "p01",
                                  "occurrence_in_part": None, "per_x": None,
                                  "item": item(level_low=Decimal(363),
                                               level_shape_hint="floor",
                                               level_unit="m_usd")})


# ---------------------------------------------------------------- G24/G31 ----

def test_G24_membership_alone_cannot_catch_a_wrong_slot_assignment():
    """Both words sit inside ONE quote, so a swapped assignment passes STRUCTURE
    by design. This is a GRADING attack, and the test states that plainly rather
    than pretending code catches it."""
    quote = "revenue of $13.9 billion and a net loss of $382 million"
    validate_slot("level_low", slot("382", "1e9", "billion"),
                  stated_unit="m_usd", quote=quote)          # structurally valid
    assert convert_slot("m_usd", slot("382", "1e9", "billion")) == Decimal(382000)


def test_G31_compensated_misread_can_never_grade_correct():
    gold = money_fact("1.3", "1e9", "billion")
    bad = money_fact("1300", "1e6", "billion")
    assert (convert_slot("m_usd", gold.item.level_low)
            == convert_slot("m_usd", bad.item.level_low) == Decimal(1300))
    assert match_facts([gold], [bad]).links == [], \
        "converted scalars must never be a scoring representation"


# -------------------------------------------------------------------- G25 ----

def test_G25_emit_once_violation_blocks_a_silent_pass():
    g, p = _pair()
    clean = match_facts([g], [p])
    dirty = match_facts([g], [p, money_fact("363")])
    assert clean.emit_once_violation is False
    assert dirty.emit_once_violation is True
    assert dirty.can_pass is False and clean.can_pass is True


# ---------------------------------------------------------------- G26/G29 ----

def test_G26_duration_and_instant_are_meaning_not_date_count():
    """A balance with a stated window still grades instant; a flow with one date
    still grades duration. The ILLEGAL combination (a duration whose window has
    no width) is caught by the PRODUCTION resolver, not by a second copy of the
    rule in the schema."""
    fact(time_type="instant", period_end_date="2026-03-31")           # balance
    fact(time_type="duration", period_start_date="2026-01-01",
         period_end_date="2026-03-31")
    with pytest.raises(prepared_fact_v2.ProductionValidationError) as e:
        violations(fact(time_type="duration", period_start_date="2026-03-31",
                        period_end_date="2026-03-31"))
    assert "start == end is illegal" in str(e.value)


def test_G29_exact_dates_may_coexist_with_fiscal_framing():
    f = fact(period_start_date="2025-07-01", period_end_date="2025-09-30",
             fiscal_year=2025, fiscal_quarter=3, time_type="duration")
    assert f.item.fiscal_quarter == 3


def test_G29_two_shape_fields_together_park():
    with pytest.raises(prepared_fact_v2.ProductionValidationError) as e:
        violations(fact(fiscal_year=2025, fiscal_quarter=3, half=2,
                        time_type="duration"))
    assert "conflicting period fields" in str(e.value)


def test_G29_a_sentinel_excludes_every_other_period_field():
    fact(sentinel_class="long_term")
    with pytest.raises(prepared_fact_v2.ProductionValidationError) as e:
        violations(fact(sentinel_class="long_term", fiscal_year=2026,
                        time_type="duration"))
    assert "sentinel_class excludes" in str(e.value)


# -------------------------------------------------------------------- G27 ----

@pytest.mark.parametrize("shape,low,high", [
    ("point", "5", "5"), ("range", "5", "7"), ("floor", "5", None),
    ("ceiling", None, "7"),
])
def test_G27_shapes_round_trip_from_their_definition(shape, low, high):
    fact(quote=QUOTE_BOTH, level_shape_hint=shape, level_unit="m_usd",
         level_low=slot(low, "1e6", "million") if low else None,
         level_high=slot(high, "1e6", "million") if high else None)


def test_G27_a_point_is_not_a_floor():
    for hint, low, high in (("floor", "5", "5"), ("point", "5", None)):
        f = fact(quote=QUOTE_BOTH, level_shape_hint=hint, level_unit="m_usd",
                 level_low=slot(low, "1e6", "million"),
                 level_high=slot(high, "1e6", "million") if high else None)
        v = violations(f)
        assert any(x.code == "SHAPE" for x in v), (hint, v)


# ---------------------------------------------------------------- G33/G34 ----

def test_G33_slice_parts_are_kind_colon_value_strings():
    f = fact(slice_parts=["product:iphone", "geography:china"])
    # stored as an immutable tuple — the deep-freeze at the boundary
    assert f.item.slice_parts == ("product:iphone", "geography:china")
    with pytest.raises(SchemaError):
        fact(slice_parts=[["product", "iphone"]])       # the v1 tuple form


def test_G33_first_colon_only_split_keeps_a_colon_in_the_value():
    assert split_slice_part("unknown:legacy: brands") == ("unknown", "legacy: brands")
    assert split_slice_part("product:iphone") == ("product", "iphone")


def test_G34_company_confirmed_never_stores_a_guessed_false():
    guidance = dict(driver={"name": "revenue", "fact_type": "guidance"})
    f = fact(fact_type="guidance", driver_state="introduced",
             value_text="roughly flat", company_confirmed=False,
             period_start_date="2026-01-01", period_end_date="2026-12-31",
             fiscal_year=2026, time_type="duration")
    v = violations(f, **guidance)
    assert any(x.code == "LANE" and "RESERVED" in x.message for x in v), v


def test_G34_value_text_and_numeric_slots_are_mutually_exclusive():
    f = fact(fact_type="guidance", driver_state="introduced",
             value_text="roughly flat", quote=QUOTE_BOTH, company_confirmed=True,
             level_unit="m_usd", level_shape_hint="floor",
             level_low=slot("5", "1e6", "million"),
             period_start_date="2026-01-01", period_end_date="2026-12-31",
             fiscal_year=2026, time_type="duration")
    v = violations(f, driver={"name": "revenue", "fact_type": "guidance"})
    assert any(x.code == "VALUE_TEXT" for x in v), v


# -------------------------------------------------------------------- G35 ----

def test_G35_per_share_cell_lawfully_keeps_multiplier_one():
    """Under '(in millions, except per-share amounts)' the per-share cell is
    multiplier 1 with a bare marker — lawful. The AGGREGATE mistake (bare '$'
    justifying multiplier 1) is a MEANING error: code checks membership, hidden
    grading attacks the reading. Recognising '$' as 'bare' in code would be the
    banned word-list class."""
    quote = "(in millions, except per-share amounts) Diluted EPS $ 1.42"
    validate_slot("level_low", slot("1.42", 1, "$"), stated_unit="usd", quote=quote)
    assert convert_slot("usd", slot("1.42", 1, "$")) == Decimal("1.42")


# ----------------------------------------------------- contract arithmetic ----

def test_the_contract_is_32_model_owned_plus_2_source_owned():
    assert len(ITEM_FIELDS) == 32
    assert len(prepared_fact_v2.SOURCE_OWNED_FIELDS) == 2
    assert len(set(ITEM_FIELDS) | set(prepared_fact_v2.SOURCE_OWNED_FIELDS)) == 34


def test_the_field_list_matches_the_packages_A3_skeleton():
    """One schema, derived from BOTH sides — never two hand-written lists."""
    pkg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                       ".claude", "plans", "Drivers", "experiments", "harness",
                       "exp5_rev4_package.md")
    with open(pkg, encoding="utf-8") as f:
        text = f.read()
    import re
    a3 = text.split("### A3")[1].split("### A4")[0]
    skeleton = re.search(r"```\n(.*?)```", a3, re.S).group(1)
    keys = set(json.loads(skeleton)["facts"][0]["item"])
    assert keys == set(ITEM_FIELDS), keys.symmetric_difference(set(ITEM_FIELDS))


def test_G16_production_never_imports_exam_code():
    """One-way import fence: exam code may import production; production may
    never import answer keys, graders, fixtures, or probe heuristics."""
    import ast
    here = os.path.dirname(os.path.abspath(__file__))
    exam_names = ("kf_lint", "score_exp5", "raw_transport", "fact16_checks",
                  "grade_batch", "harness")
    for mod in ("slot_convert.py", "prepared_fact_v2.py", "fact_match.py",
                "xbrl_attach.py"):
        tree = ast.parse(open(os.path.join(here, mod), encoding="utf-8").read())
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            for n in names:
                assert not any(x in n for x in exam_names), f"{mod} imports {n}"


def test_G18_the_new_modules_reach_no_graph_write():
    """AST, not text — prose may legitimately mention a transaction."""
    import ast
    here = os.path.dirname(os.path.abspath(__file__))
    for mod in ("slot_convert.py", "prepared_fact_v2.py", "fact_match.py",
                "xbrl_attach.py"):
        tree = ast.parse(open(os.path.join(here, mod), encoding="utf-8").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                assert node.id != "ENABLE_DRIVER_WRITES", mod
            if isinstance(node, ast.Attribute):
                assert node.attr not in ("transaction", "execute_write"), mod
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names] + [getattr(node, "module", "") or ""]
                assert not any("neo4j" in n for n in names), mod
