"""R12-1 (#817) — the CANDIDATE-FACT unit law, proved through the attachment
path on real filings, INCLUDING the filing-side locator.

SCOPE, STATED ONCE AND EXACTLY. These proofs cover the NUMBER, the UNIT and the
FILING-SIDE LOCATOR against real graph rows and real cached filings: the quote
is the filing's own text at the bound element's span, and the submitted
evidence is checked against the fetched document. #824 wired that verification,
so the older note here — that quote verification was unwired and a fabricated
quote still attached — is retired.

WHAT THESE STILL DO NOT PROVE: the EVENT PART is test scaffolding. It is
derived from the fact's own quote so the occurrence check has something lawful
to read, which means it cannot prove the historical text view the AI actually
received. That leg has no durable source today and stays for switch preflight;
no fixture stands in for it.

OWNER RULING 2026-07-27: `pure` means DIMENSIONLESS and does not itself choose
the unit. pure may back count, the percent family and x; `unknown` is the
existing fail-safe; pure may NEVER back usd/m_usd. The AI picks the unit from
the source text/table, code checks only COMPATIBILITY, and never infers the
unit from the concept name. ix.scale is not copied blindly: percent family / x
store multiplier 1, money / count store the source's real magnitude. The
dormant no-AI materializer keeps its whitelist unchanged.

FOUR REPAIRS after the first attempt was reviewed:
  1  non-USD money was made to ABSTAIN; the locked plan (FINAL_DESIGN:206,
     "non-USD gaps may stay `unknown`") allows it to be STORED as unknown, and
     my own test had cemented the block as if it were intended.
  2  the SHARED binder applied the candidate whitelist itself AND the caller
     applied it again — two policy checks, one inside a module the dormant
     materializer also uses. The binder now reports the verified unit; ONE
     caller-owned check decides compatibility.
  3  the text-lane "0.01 means cents" rule ran on structured XBRL metadata, so
     an `unknown` fact at ix.scale -2 was rejected out of hand.
  4  these tests overclaimed: they never ran the complete attachment path, the
     source wording lived only in comments, `except Exception` could turn any
     bug into a skip, and rows[0] picked a fact by unstable order.

EVERY FIXTURE IS PINNED BY EXACT fact_id, and its expected unit is justified by
DISPLAYED SOURCE WORDING that this file ASSERTS against the bound evidence —
never by the concept name, which cannot be trusted: the concept
`RestructuringAndRelatedCostNumberOfPositionsEliminatedPeriodPercent` carries
both "NumberOf" and "Percent".
"""
import os
from decimal import Decimal

from driver.core.test_round10_event_boundary import (_FIXTURE_NS, _XMLNS,
                                                     parts_for)

#: The fixtures below state units the way a FILING writes them. The policy now
#: consumes expanded names, so the raw spelling is resolved HERE — in the
#: fixture, where the reader can see which namespace each one means — rather
#: than by the code under test, which is the whole point of the change.
_ISO4217_NS = 'http://www.xbrl.org/2003/iso4217'
_XBRLI_NS = 'http://www.xbrl.org/2003/instance'
_UTR_NS = 'http://www.xbrl.org/2009/utr'
_FIXTURE_MEASURE_NS = {'iso4217': _ISO4217_NS, 'xbrli': _XBRLI_NS,
                       'utr': _UTR_NS}


def _exp(*raw_measures):
    """Fixture spellings -> (namespace URI, local name). An unprefixed measure
    is an XBRL 2.1 instance-namespace one, exactly as a filing's default
    binding would make it."""
    out = []
    for raw in raw_measures:
        prefix, _sep, local = raw.partition(':')
        out.append((_FIXTURE_MEASURE_NS[prefix], local) if local
                   else (_XBRLI_NS, prefix))
    return tuple(out)


import pytest
from driver.core.xbrl_attach import (
    candidate_units_for as xa_candidate_units_for,
    _CANDIDATE_EXACT as xa_CANDIDATE_EXACT)

from driver.core.xbrl_attach import attach_event_xbrl
from driver.core.test_round10_event_boundary import filing_evidence

CACHE = "scripts/driver_seed/relocate_probe/inline_html_cache"

_IP_30 = ("id3VybDovL2RvY3MudjEvZG9jOjAzOWNmN2E0NjMyNTQ1ZmNhM2M1ZWZmMDI0MzRjYmE5"
          "L3NlYzowMzljZjdhNDYzMjU0NWZjYTNjNWVmZjAyNDM0Y2JhOV83Ni9mcmFnOmNhNDkw"
          "MmFhYWExNzQyOTE5ZDQ4YjRjNmE2MTI4YzM4L3RleHRyZWdpb246Y2E0OTAyYWFhYTE3"
          "NDI5MTlkNDhiNGM2YTYxMjhjMzhfMTQyMDY_7b4a942a-ab9a-4d81-a167-6c1afd4fe744")

# label · accession · fact_id · concept · graph value · level_unit ·
# displayed · ix.scale · WORDING THAT DECIDES THE UNIT (asserted, not narrated)
REAL = [
    ("percent", "0001306830-24-000155", "f-711",
     "us-gaap:LongtermDebtWeightedAverageInterestRate", "0.026", "percent",
     "2.6", -2, "weighted average interest rate"),
    ("count", "0000051434-23-000022", _IP_30,
     "ip:PotentiallyResponsibleParties", "30", "count", "30", 0, "producers"),
    ("scaled count", "0000002488-24-000123", "f-747",
     "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding", "1,637,000,000",
     "count", "1,637", 6, "shares"),
    ("x", "0000817720-25-000011", "f-647",
     "syna:DebtInstrumentCovenantMinimumInterestCoverageRatio", "3", "x",
     "3.0", 0, "to 1.0"),
    ("unknown (non-USD)", "0001306830-24-000155", "f-722",
     "us-gaap:LineOfCreditFacilityMaximumBorrowingCapacity", "750,000,000",
     "unknown", "750", 6, "CNY 750 million"),
]


def _neo4j_or_skip():
    """Skip ONLY for a genuine Neo4j outage. Every other failure must FAIL — a
    blanket `except Exception` turned a renamed reader into a green skip."""
    if not os.environ.get("NEO4J_URI"):
        pytest.skip("NEO4J_URI unset — genuine outage, not a silent pass")
    from driver.core.xbrl_attach import RETRYABLE_SOURCE_ERRORS
    from driver.core.driver_neo4j_adapter import Neo4jStore
    try:
        return Neo4jStore()
    except RETRYABLE_SOURCE_ERRORS:                        # pragma: no cover
        pytest.skip("Neo4j unreachable — genuine outage")


def _text(acc):
    with open(os.path.join(CACHE, f"{acc}.htm"), encoding="utf-8",
              errors="replace") as f:
        return f.read()


def _the_row(store, acc, qname, fact_id):
    """THE pinned fact — never rows[0], which picks by unstable order."""
    rows = [r for r in store.get_xbrl_fact_dimensions(acc, qname).rows
            if r["fact_id"] == fact_id]
    assert len(rows) == 1, f"pinned id matched {len(rows)} rows, expected 1"
    return rows[0]


def _refs_and_parts(row):
    """Build the fact's member_refs and slice tokens with PRODUCTION's own
    functions — `check_member_refs` recomputes the token from the filing's
    label and trusts nothing supplied, so re-deriving that rule here would be a
    second implementation of it."""
    from driver.core.driver_ids import encode_unknown_axis
    from driver.core.driver_member_fold import member_token
    from driver.core.slice_menu import classify_axis
    refs, parts = [], []
    for d in row["dims"]:
        status, kind = classify_axis(d["axis"])
        token = (member_token(kind, d["label"]) if status == "slice"
                 else encode_unknown_axis(d["axis"], d["label"]))
        refs.append({"axis": d["axis"], "member": d["member"],
                     "slice_part": token})
        parts.append(token)
    return refs, parts


@pytest.mark.live
@pytest.mark.parametrize(
    "label,acc,fact_id,qname,graph_value,level_unit,displayed,scale,wording", REAL)
def test_a_real_fact_attaches_through_the_candidate_path_INCLUDING_the_locator(
        label, acc, fact_id, qname, graph_value, level_unit, displayed, scale,
        wording):
    """The event door end to end — injected provider, graph-owned CIK, harvested
    representation — not the low-level binder.

    SCOPE: this proves the NUMBER, the UNIT and the FILING-SIDE LOCATOR on real
    data — the quote is the filing's own text at the bound element's span, and
    the submitted evidence is verified against the fetched document. The event
    part is scaffolding derived from that quote, so it does not prove the
    historical text view the AI actually received.
    """
    from datetime import date, timedelta
    from driver.core.prepared_fact_v2 import ITEM_FIELDS

    store = _neo4j_or_skip()
    try:
        row = _the_row(store, acc, qname, fact_id)
        assert row["value"] == graph_value
        text = _text(acc)

        class Provider:
            def get_filing_document(self, source_id):
                return text if source_id == acc else None

        stored_end = (row["start_date"] if row["period_type"] == "instant"
                      else row["end_date"])
        incl = (date.fromisoformat(stored_end) - timedelta(days=1)).isoformat()
        mult = Decimal(1) if level_unit in ("percent", "x") else Decimal(10) ** scale
        slot = {"value": Decimal(displayed.replace(",", "")),
                "scale_multiplier": mult, "unit_scale_evidence": None}
        it = {k: None for k in ITEM_FIELDS}
        refs, parts = _refs_and_parts(row)
        evidence, filing_quote = filing_evidence(text, fact_id)
        it.update(driver_name="thing", driver_state="reported",
                  quote=filing_quote,
                  measurement_raw_spans=[], slice_parts=parts,
                  level_unit=level_unit, level_low=dict(slot),
                  level_high=dict(slot), time_type=row["period_type"],
                  period_end_date=incl,
                  period_start_date=(row["start_date"]
                                     if row["period_type"] == "duration" else None))
        entry = {"fact": {"fact_type": "metric", "part_ref": "p1",
                          "occurrence_in_part": None, "per_x": None,
                          "item": it},
                 "concept": qname, "member_refs": refs,
                 "source_evidence": evidence}
        res = attach_event_xbrl([entry], source_id=acc, store=store,
                                filing_provider=Provider(),
                                text_parts=parts_for([entry]))
        assert res.preflight_outcomes == (), \
            [dict(o) for o in res.preflight_outcomes]
        assert [i for i, _f in res.facts] == [0]
        fact = res.facts[0][1]
        assert fact.item.xbrl_concept_raw == qname
        assert fact.item.level_unit == level_unit
    finally:
        store.close()


@pytest.mark.parametrize(
    "label,acc,fact_id,qname,graph_value,level_unit,displayed,scale,wording", REAL)
def test_the_SOURCE_WORDING_that_justifies_the_unit_is_really_there(
        label, acc, fact_id, qname, graph_value, level_unit, displayed, scale,
        wording):
    """The wording is the whole evidential basis for the expected unit, so it is
    ASSERTED against the bound element's own evidence — not left in a comment
    where a changed filing or a mis-transcribed sentence goes unnoticed."""
    from driver.relocation.inline_html import element_evidence, prepare
    ev, why = element_evidence(prepare(_text(acc)), fact_id)
    assert ev is not None, why
    seen = " ".join([ev.get("row_label") or "", ev.get("row_text") or "",
                     ev.get("block") or ""])
    assert wording.lower() in seen.lower(), \
        f"{label}: the wording justifying unit {level_unit!r} is not in the filing"


@pytest.mark.live
def test_a_wrong_unit_for_a_real_fact_is_REFUSED():
    """The percentage fact, claimed as money — the one thing `pure` may never
    back. Without this the permissive tests above could pass vacuously."""
    from datetime import date, timedelta
    from driver.core.prepared_fact_v2 import ITEM_FIELDS
    from driver.core.xbrl_attach import attach_event_xbrl
    acc, fact_id = "0001306830-24-000155", "f-711"
    qname = "us-gaap:LongtermDebtWeightedAverageInterestRate"
    store = _neo4j_or_skip()
    try:
        row = _the_row(store, acc, qname, fact_id)
        text = _text(acc)

        class Provider:
            def get_filing_document(self, source_id):
                return text

        stored_end = (row["start_date"] if row["period_type"] == "instant"
                      else row["end_date"])
        incl = (date.fromisoformat(stored_end) - timedelta(days=1)).isoformat()
        slot = {"value": Decimal("2.6"), "scale_multiplier": Decimal("1E-2"),
                "unit_scale_evidence": None}
        it = {k: None for k in ITEM_FIELDS}
        refs, parts = _refs_and_parts(row)
        evidence, filing_quote = filing_evidence(text, fact_id)
        it.update(driver_name="thing", driver_state="reported",
                  quote=filing_quote,
                  measurement_raw_spans=[], slice_parts=parts, level_unit="m_usd",
                  level_low=dict(slot), level_high=dict(slot),
                  time_type=row["period_type"], period_end_date=incl,
                  period_start_date=(row["start_date"]
                                     if row["period_type"] == "duration" else None))
        entry = {"fact": {"fact_type": "metric", "part_ref": "p1",
                          "occurrence_in_part": None, "per_x": None,
                          "item": it},
                 "concept": qname, "member_refs": refs,
                 "source_evidence": evidence}
        res = attach_event_xbrl([entry], source_id=acc, store=store,
                                filing_provider=Provider(),
                                text_parts=parts_for([entry]))
        assert res.facts == ()
        assert len(res.preflight_outcomes) == 1
        row = res.preflight_outcomes[0]
        assert (row["index"], row["decision"], row["codes"]) == \
            (0, "rejected", ("XBRL_CONTRACT_INVALID",))
        # `match="pure"` was matching the GRAPH'S UNIT NAME, not a rule word.
        # Both halves are named now: which unit the filing records, and which
        # level_unit was claimed against it.
        assert "records unit 'pure'" in row["detail"], row["detail"]
        assert "not level_unit='m_usd'" in row["detail"], row["detail"]
    finally:
        store.close()


# ---- the compatibility law -------------------------------------------------

def test_pure_backs_count_the_percent_family_and_x_but_never_money():
    from driver.core.xbrl_attach import candidate_units_for
    allowed = candidate_units_for(_exp("pure"), ())
    for u in ("count", "x", "percent", "percent_yoy", "percent_sequential",
              "percent_points", "basis_points"):
        assert u in allowed, u
    assert "usd" not in allowed and "m_usd" not in allowed


def test_pure_may_back_unknown_as_the_failsafe():
    """RULE-LEVEL and labelled: no decisively-worded genuinely-undecidable
    `pure` fact was found in the cached corpus, and one was NOT manufactured."""
    from driver.core.xbrl_attach import candidate_units_for
    assert "unknown" in candidate_units_for(_exp("pure"), ())


@pytest.mark.parametrize("currency", ["iso4217:CNY", "iso4217:EUR",
                                      "iso4217:GBP", "iso4217:JPY"])
def test_non_USD_money_may_be_stored_as_unknown_not_abstained(currency):
    """FINAL_DESIGN:206 — "non-USD gaps may stay `unknown` (monitored)". Adding
    real `eur`/`cny` units stays open; using the EXISTING fail-safe is locked
    law, and the first version of this file asserted the opposite."""
    from driver.core.xbrl_attach import candidate_units_for
    assert candidate_units_for(_exp(currency), ()) == frozenset({"unknown"}), currency


def test_the_money_and_share_units_are_unchanged():
    from driver.core.xbrl_attach import candidate_units_for as C
    assert C(_exp("iso4217:USD"), ()) == frozenset({"usd", "m_usd"})
    assert C(_exp("shares"), ()) == frozenset({"count"})
    # a divide unit is judged by its STRUCTURE now, so the numerator must be
    # supplied — see test_EPS_is_the_SAME_rule_not_a_special_case
    # A DIVIDE UNIT IS RECOGNISED BY ITS STRUCTURE, not by a concatenated name:
    # the numerator is passed and the plain measures are empty.
    assert C((), _exp("iso4217:USD")) == frozenset({"usd"})
    for u in ("percent", "x", "count"):
        assert u not in C(_exp("iso4217:USD"), ())


def test_a_unit_this_route_cannot_read_at_all_has_no_compatible_unit():
    from driver.core.xbrl_attach import candidate_units_for
    assert candidate_units_for(_exp("utr:Btu"), ()) == frozenset()


def test_the_DORMANT_materializer_whitelist_is_untouched():
    """THE SCOPE IS PINNED, NOT THE SPELLING. This pinned
    `ROUTE_A_SEM_UNIT`, a map from the GRAPH's prefixed text to a reading; #827
    Stage 3 retired it because a prefix is an alias and it therefore both
    refused lawful aliases and accepted rebound ones.

    What the pin was FOR survives exactly: the whitelist admits three readings
    and no more, so this asserts the same three against the identity-keyed
    tables that replaced it. Growth by drive-by is still caught."""
    from driver.relocation.exact_numbers import (ROUTE_A_SEM_UNIT_DIVIDE,
                                                 ROUTE_A_SEM_UNIT_SIMPLE)
    ISO = "http://www.xbrl.org/2003/iso4217"
    XBRLI = "http://www.xbrl.org/2003/instance"
    assert ROUTE_A_SEM_UNIT_SIMPLE == {((ISO, "USD"),): "usd",
                                       ((XBRLI, "shares"),): "count"}
    assert ROUTE_A_SEM_UNIT_DIVIDE == {
        (((ISO, "USD"),), ((XBRLI, "shares"),)): "usd_per_share"}


# ---- repair 2: ONE policy check, and it is the caller's --------------------

def test_the_shared_binder_applies_no_candidate_policy():
    """The binder is shared with the DORMANT materializer, whose policy differs.
    It verifies the unit against the FILING and reports it — it must never gate
    on the candidate route's own table."""
    import inspect
    from driver.relocation import inline_html
    src = inspect.getsource(inline_html)
    assert "CANDIDATE_XBRL_UNIT_COMPAT" not in src
    assert "candidate_units_for" not in src


# ---- repair 3: the cents rule is TEXT-lane only ----------------------------

@pytest.mark.parametrize("unit", ["unknown", "count", "percent", "x"])
def test_the_cents_rule_does_not_judge_structured_xbrl_metadata(unit):
    """"a 0.01 multiplier means cents" reads a TEXT quote. On the XBRL lane the
    0.01 IS `ix.scale = -2`, declared by the filing — an `unknown` fact at
    scale -2 was rejected out of hand."""
    from driver.core.slot_convert import validate_slot
    slot = {"value": Decimal("21.3"), "scale_multiplier": Decimal("0.01"),
            "unit_scale_evidence": None}
    validate_slot("level_low", slot, stated_unit=unit, quote="q", xbrl_backed=True)


def test_the_cents_rule_STILL_guards_the_text_lane():
    from driver.core.slot_convert import validate_slot, SlotConversionError
    slot = {"value": Decimal("21.3"), "scale_multiplier": Decimal("0.01"),
            "unit_scale_evidence": "in cents"}
    with pytest.raises(SlotConversionError):
        validate_slot("level_low", slot, stated_unit="count",
                      quote="21.3 in cents", xbrl_backed=False)


# ---- ix.scale is not the stored multiplier ---------------------------------

def test_the_stored_multiplier_is_ONE_for_the_percent_family_and_x():
    from driver.core.xbrl_attach import expected_multiplier
    for u in ("percent", "percent_yoy", "percent_sequential", "percent_points",
              "basis_points", "x"):
        assert expected_multiplier(u, -2) == Decimal(1), u
    # C3 (#827 F-UNITS): the ONE owner of membership AND the required value —
    # every family unit answers Decimal(1); every other enum unit answers None
    # (the caller's own arithmetic governs). The three doors consume this owner.
    from driver.core.slot_convert import family_required_multiplier
    for u in ("percent", "percent_yoy", "percent_sequential", "percent_points",
              "basis_points", "x"):
        assert family_required_multiplier(u) == Decimal(1), u
    for u in ("usd", "m_usd", "count", "unknown"):
        assert family_required_multiplier(u) is None, u


def test_money_count_and_unknown_use_the_sources_real_magnitude():
    from driver.core.xbrl_attach import expected_multiplier
    assert expected_multiplier("usd", 6) == Decimal(10) ** 6
    assert expected_multiplier("count", 6) == Decimal(10) ** 6   # 1,637 x 10^6
    assert expected_multiplier("count", 0) == Decimal(1)
    assert expected_multiplier("unknown", 6) == Decimal(10) ** 6


# ---------------------------------------------------------------------------
# REOPENED #817 — physical/business per-X divide units (review 2026-07-27)
#
# NAME-13 (FINAL_DESIGN:94): "A stated business/physical per-X denominator
# stays in the name (`oil_price_per_barrel`) ... store the BASE unit". So a
# USD-per-barrel fact is `level_unit="usd"` with `per_x="barrel"` — and the
# rule rejected it as "may back nothing", losing a large real population:
# (all counts are NUMERIC, NON-NULL facts: is_numeric='1', is_nil='0')
#   327,005 iso4217:USDshares · 2,302 USDutr:bbl · 1,169 USDutr:MWh
#   1,147 USDutr:MMBTU · 620 CADshares · 347 USDutr:kWh · 183 USDutr:Mcf
#
# WHY THE STRUCTURE, NEVER THE NAME: the graph name is the measures
# CONCATENATED, and `utr:galutr:M` (140 live facts) cannot be split back
# reliably — `utr:gal`+`utr:M` or `utr:galutr`+`M`? The binder already holds the
# filing's VERIFIED numerator/denominator; that is what must travel.
# ---------------------------------------------------------------------------

PER_X_REAL = ("0000717423-24-000038", "f-830",
              "us-gaap:DerivativeSwapTypeAverageFixedPrice", "3.2",
              "3.20", 0, "Price per MCF")


@pytest.mark.live
def test_a_real_USD_per_physical_unit_fact_attaches_with_the_BASE_unit():
    """Real filing, wording "Price per MCF:" — a USD price per thousand cubic
    feet. The denominator belongs in the NAME (per_x, model-owned, validated
    later at admission); the value keeps its base unit.

    SAME SCOPE AS ABOVE: number, unit and filing-side locator on real data;
    the event part remains scaffolding."""
    from datetime import date, timedelta
    from driver.core.prepared_fact_v2 import ITEM_FIELDS
    acc, fid, qname, graph_v, displayed, scale, wording = PER_X_REAL
    store = _neo4j_or_skip()
    try:
        row = _the_row(store, acc, qname, fid)
        assert row["value"] == graph_v and row["unit_name"] == "iso4217:USDutr:Mcf"
        text = _text(acc)

        class Provider:
            def get_filing_document(self, source_id):
                return text

        stored_end = (row["start_date"] if row["period_type"] == "instant"
                      else row["end_date"])
        incl = (date.fromisoformat(stored_end) - timedelta(days=1)).isoformat()
        slot = {"value": Decimal(displayed), "scale_multiplier": Decimal(10) ** scale,
                "unit_scale_evidence": None}
        refs, parts = _refs_and_parts(row)
        evidence, filing_quote = filing_evidence(text, fid)
        it = {k: None for k in ITEM_FIELDS}
        it.update(driver_name="gas_price_per_mcf", driver_state="reported",
                  quote=filing_quote, measurement_raw_spans=[],
                  slice_parts=parts,
                  level_unit="usd", level_low=dict(slot), level_high=dict(slot),
                  time_type=row["period_type"], period_end_date=incl,
                  period_start_date=(row["start_date"]
                                     if row["period_type"] == "duration" else None))
        entry = {"fact": {"fact_type": "metric", "part_ref": "p1",
                          "occurrence_in_part": None, "per_x": "mcf",
                          "item": it},
                 "concept": qname, "member_refs": refs,
                 "source_evidence": evidence}
        res = attach_event_xbrl([entry], source_id=acc, store=store,
                                filing_provider=Provider(),
                                text_parts=parts_for([entry]))
        assert res.preflight_outcomes == (), \
            [dict(o) for o in res.preflight_outcomes]
        assert [i for i, _f in res.facts] == [0]
        fact = res.facts[0][1]
        assert fact.item.level_unit == "usd"
        assert fact.per_x == "mcf"
    finally:
        store.close()


def test_the_per_x_wording_is_really_in_the_filing():
    from driver.relocation.inline_html import element_evidence, prepare
    acc, fid, _q, _v, _d, _s, wording = PER_X_REAL
    ev, why = element_evidence(prepare(_text(acc)), fid)
    assert ev is not None, why
    seen = " ".join([ev.get("row_label") or "", ev.get("row_text") or "",
                     ev.get("block") or ""])
    assert wording.lower() in seen.lower()


@pytest.mark.parametrize("numerator,expected", [
    (("iso4217:USD",), {"usd"}),            # USD per anything -> base unit usd
    (("iso4217:CAD",), {"unknown"}),        # 620 live CADshares facts
    (("iso4217:EUR",), {"unknown"}),
    (("utr:gal",), set()),                  # utr:galutr:M — not money at all
    (("utr:bbl",), set()),                  # utr:bblutr:D
    ((), set()),                            # unreadable shape -> park
    (("iso4217:USD", "utr:bbl"), set()),    # two numerators -> park, never guess
])
def test_a_divide_unit_is_judged_by_its_STRUCTURED_numerator(numerator, expected):
    """The numerator decides the base unit; the denominator is the per-X and is
    the model's to state. Judged from the filing's verified structure — the
    concatenated graph name is never parsed."""
    from driver.core.xbrl_attach import candidate_units_for
    got = candidate_units_for((), _exp(*numerator))
    assert got == frozenset(expected), f"{numerator} -> {sorted(got)}"


def test_EPS_is_the_SAME_rule_not_a_special_case_FOR_UNIT_BINDING():
    """`iso4217:USDshares` had its own hard-coded row; USD-over-anything covers
    it, so the special case is gone rather than sitting beside the general one.

    SCOPED DELIBERATELY: this is about UNIT BINDING only. The separate `eps`
    NAMING exception (NAME-13, still an open owner item) is untouched — its
    check left Core with W3 and moves to the POST per-X naming feature; an
    approved naming change will arrive on its own, never inferred from this."""
    assert (_ISO4217_NS, "USDshares") not in xa_CANDIDATE_EXACT
    assert xa_candidate_units_for((), _exp("iso4217:USD")) == frozenset({"usd"})


def test_the_binder_reports_the_structured_measures():
    from driver.relocation.inline_html import bind_graph_fact
    divide = ('<ix:header><ix:resources><xbrli:unit id="u1"><xbrli:divide>'
              '<xbrli:unitNumerator><xbrli:measure>iso4217:USD</xbrli:measure>'
              '</xbrli:unitNumerator><xbrli:unitDenominator>'
              '<xbrli:measure>utr:bbl</xbrli:measure>'
              '</xbrli:unitDenominator></xbrli:divide></xbrli:unit></ix:resources></ix:header>')
    doc = (f'<html {_XMLNS}><body><ix:header><ix:resources><xbrli:context id="c1"><xbrli:entity>'
           '<xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193</xbrli:identifier></xbrli:entity>'
           '<xbrli:period><xbrli:startDate>2024-01-01</xbrli:startDate>'
           '<xbrli:endDate>2024-06-30</xbrli:endDate></xbrli:period>'
           '</xbrli:context></ix:resources></ix:header>' + divide +
           '<p><ix:nonFraction id="f1" name="us-gaap:X" contextRef="c1" '
           'unitRef="u1" scale="0" decimals="2">44.02</ix:nonFraction></p>'
           '</body></html>')
    bound, why = bind_graph_fact(
        doc, inline_element_id="f1", concept="us-gaap:X", context_id="c1",
        unit_ref="u1", unit_name="iso4217:USDutr:bbl", is_divide="1",
        period_type="duration", start_date="2024-01-01", end_date="2024-07-01",
        dims=(), entity_cik="0000320193", raw_value="44.02",
        **_IDENTITY)
    assert bound is not None, why
    assert bound["unit_numerator_expanded"] == \
        (("http://www.xbrl.org/2003/iso4217", "USD"),)
    assert bound["unit_measures_expanded"] == ()   # divide: no plain measures


def test_the_outcome_map_has_no_duplicate_keys():
    """A dict literal with a repeated key silently keeps the last one, so the
    runtime map can never reveal it — this reads the SOURCE."""
    import ast
    import inspect
    from driver.core import prepared_fact_v2 as p2
    src = inspect.getsource(p2._outcome_classes)
    for node in ast.walk(ast.parse(src.strip())):
        if isinstance(node, ast.Dict):
            names = [getattr(k, "id", None) for k in node.keys]
            assert len(names) == len(set(names)), f"duplicate key(s): {names}"


# ---------------------------------------------------------------------------
# XBRL 2.1 requires BOTH sides of a <xbrli:divide> to carry at least one
# measure. The binder accepted a USD numerator with an empty denominator (and,
# found while reproducing, an empty NUMERATOR and a blank measure too), so a
# malformed declaration could bind.
#
# STRUCTURAL VALIDITY, so the check belongs in the SHARED binder — not in
# candidate policy, which is the caller's. Cache census 2026-07-27: 1,769
# filings, 2,086 divide declarations, every one 1x1 with no blank measure — so
# this guard changes no current fact and exists for the malformed filing we
# have not met.
# ---------------------------------------------------------------------------

def _divide_doc(num_measures, den_measures):
    m = lambda vals: "".join(f"<xbrli:measure>{v}</xbrli:measure>" for v in vals)
    return (f'<html {_XMLNS}><body><ix:header><ix:resources><xbrli:context id="c1"><xbrli:entity>'
            '<xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193</xbrli:identifier></xbrli:entity>'
            '<xbrli:period><xbrli:startDate>2024-01-01</xbrli:startDate>'
            '<xbrli:endDate>2024-06-30</xbrli:endDate></xbrli:period>'
            '</xbrli:context></ix:resources></ix:header><ix:header><ix:resources><xbrli:unit id="u1"><xbrli:divide>'
            f'<xbrli:unitNumerator>{m(num_measures)}</xbrli:unitNumerator>'
            f'<xbrli:unitDenominator>{m(den_measures)}</xbrli:unitDenominator>'
            '</xbrli:divide></xbrli:unit></ix:resources></ix:header>'
            '<p><ix:nonFraction id="f1" name="us-gaap:X" contextRef="c1" '
            'unitRef="u1" scale="0" decimals="2">44.02</ix:nonFraction></p>'
           '</body></html>')


#: the concept identity these binder calls state, read from the SAME
#: declaration the documents are built from
_IDENTITY = {"concept_namespace": _FIXTURE_NS["us-gaap"],
             "graph_concept_qname": "us-gaap:X"}


def _bind_divide(num, den, unit_name):
    from driver.relocation.inline_html import bind_graph_fact
    return bind_graph_fact(
        _divide_doc(num, den), inline_element_id="f1", concept="us-gaap:X",
        context_id="c1", unit_ref="u1", unit_name=unit_name, is_divide="1",
        period_type="duration", start_date="2024-01-01", end_date="2024-07-01",
        dims=(), entity_cik="0000320193", raw_value="44.02",
        **_IDENTITY)


#: TWO FAULTS, TWO NAMES (#827 round 5). A side carrying NO measure element is
#: a STRUCTURE fault and is refused at parse; a measure that is present but
#: says nothing is a VALUE fault and is refused at bind. `"divide" in why` was
#: a substring check loose enough to accept either, so it could not tell the
#: two apart — and an abstention whose stated cause is wrong is not a correct
#: abstention.
_STRUCTURE = "malformed_unit_structure"
_VALUE = "malformed_divide_unit_measure"


@pytest.mark.parametrize("num,den,unit_name,expected", [
    (["iso4217:USD"], [], "iso4217:USD", _STRUCTURE),      # no denominator
    ([], ["utr:bbl"], "utr:bbl", _STRUCTURE),              # no numerator
    ([], [], "", _STRUCTURE),                              # both sides empty
    # ROUND 7 MOVED THESE EARLIER, and the reason moved with them. A measure
    # is a QNAME; blank and whitespace-only text is not one, so it is refused
    # at PARSE as structure rather than reaching the bind-time value check.
    # `malformed_divide_unit_measure` still owns a measure that IS a QName but
    # names a side the graph cannot use.
    (["iso4217:USD"], [""], "iso4217:USD", _STRUCTURE),     # blank denominator
    ([""], ["utr:bbl"], "utr:bbl", _STRUCTURE),             # blank numerator
    ([" "], ["utr:bbl"], "utr:bbl", _STRUCTURE),            # whitespace only
])
def test_a_malformed_divide_unit_ABSTAINS_in_the_shared_binder(num, den,
                                                               unit_name,
                                                               expected):
    bound, why = _bind_divide(num, den, unit_name)
    assert bound is None, "a malformed divide unit bound"
    assert why.endswith(expected), f"expected {expected}, said {why!r}"


def test_a_MULTI_MEASURE_divide_is_still_structurally_valid():
    """XBRL permits more than one measure per side. Structural validity must not
    reject that — whether we can READ a compound numerator is candidate POLICY,
    decided by the caller, and it parks there instead."""
    from driver.core.xbrl_attach import candidate_units_for
    bound, why = _bind_divide(["iso4217:USD", "utr:bbl"], ["utr:D"],
                              "iso4217:USDutr:bblutr:D")
    assert bound is not None, f"a lawful multi-measure unit was refused: {why}"
    assert bound["unit_numerator_expanded"] == (
        ("http://www.xbrl.org/2003/iso4217", "USD"),
        ("http://example.org/utr", "bbl"))    # the FIXTURE binds utr: here
    # ...and the CALLER parks it, because a compound numerator has no base unit
    assert candidate_units_for(bound["unit_measures_expanded"],
                               bound["unit_numerator_expanded"]) == frozenset()


def test_the_lawful_one_by_one_divide_still_binds():
    """The guard must not touch the 2,086 real declarations."""
    bound, why = _bind_divide(["iso4217:USD"], ["utr:bbl"], "iso4217:USDutr:bbl")
    assert bound is not None, why
    assert bound["unit_numerator_expanded"] == \
        (("http://www.xbrl.org/2003/iso4217", "USD"),)
    assert bound["unit_measures_expanded"] == ()


# --- every measure must be a non-blank QName, in EVERY position -------------
# The first guard only required at least ONE non-blank measure per side, so a
# lawful measure paired with a blank one still bound. XBRL 2.1 4.8.2: every
# measure is a QName; multiple VALID measures per side remain lawful.

@pytest.mark.parametrize("num,den", [
    (["iso4217:USD", ""], ["utr:bbl"]),          # blank second in numerator
    (["", "iso4217:USD"], ["utr:bbl"]),          # blank first in numerator
    (["iso4217:USD"], ["utr:bbl", ""]),          # blank second in denominator
    (["iso4217:USD"], ["", "utr:bbl"]),          # blank first in denominator
    (["iso4217:USD", "  "], ["utr:bbl"]),        # whitespace-only counts as blank
    (["iso4217:USD", ""], ["utr:bbl", ""]),      # blank on both sides
    (["iso4217:USD", "utr:D", ""], ["utr:bbl"]),  # blank last of three
])
def test_a_BLANK_measure_anywhere_makes_the_divide_unit_malformed(num, den):
    """ROUND 7: the refusal moved EARLIER and its reason moved with it. A
    measure is a QName, so a blank one is refused at parse as structure — the
    substring check `"divide" in why` was loose enough to hide which rule
    fired, and now names the one that does."""
    bound, why = _bind_divide(num, den, "iso4217:USDutr:bbl")
    assert bound is None, "a blank measure bound alongside a valid one"
    assert why.endswith(_STRUCTURE), f"expected {_STRUCTURE}, said {why!r}"


def test_multiple_VALID_measures_remain_lawful_on_both_sides():
    """The guard rejects blanks, never plurality."""
    bound, why = _bind_divide(["iso4217:USD", "utr:D"], ["utr:bbl", "utr:M"],
                              "iso4217:USDutr:Dutr:bblutr:M")
    assert bound is not None, f"a lawful multi-measure unit was refused: {why}"
    assert bound["unit_numerator_expanded"] == (
        ("http://www.xbrl.org/2003/iso4217", "USD"),
        ("http://example.org/utr", "D"))      # the FIXTURE binds utr: here
    assert bound["unit_measures_expanded"] == ()   # plurality lawful, still a divide


def test_attach_REFUSES_a_family_fact_stating_a_multiplier():
    """C3 (#827 F-UNITS): the family multiplier law THROUGH the public attach
    door, all six units, on this suite's synthetic ix document. Assertions
    read AttachResult.preflight_outcomes — the door CATCHES the internal
    SchemaError (xbrl_attach:1214-1216) and returns an outcome row, so a
    pytest.raises attach test would be FALSE PROOF. Multiplier 1 attaches;
    a stated non-1 multiplier is refused with the complete pinned outcome
    (no fact · decision "rejected" · the XBRL_CONTRACT_INVALID code · the
    "must state multiplier 1" detail), via round8's _refused checker."""
    from driver.core.prepared_fact_v2 import SchemaError
    from driver.core.test_round8_xbrl_binding import (ACC, _Graph, _Provider,
                                                      _default_outcome, _doc,
                                                      _fact)
    # a PURE-unit world: the one candidate map backs the whole multiplier-one
    # family from xbrli pure, so document, graph row and provider all declare
    # it — the same synthetic apparatus as round8's _attach, doc swapped.
    doc = _doc('<ix:header><ix:resources><xbrli:unit id="u1">'
               '<xbrli:measure>xbrli:pure</xbrli:measure></xbrli:unit>'
               '</ix:resources></ix:header>')
    pure_row = dict(_Graph()._rows[0], unit_name="pure")

    def attach_pure(fact):
        evidence, filing_quote = filing_evidence(doc, "f1")
        fact["item"]["quote"] = filing_quote
        item = {"fact": fact, "concept": "us-gaap:Revenues", "member_refs": [],
                "source_evidence": evidence}
        return attach_event_xbrl([item], source_id=ACC,
                                 store=_Graph(rows=[dict(pure_row)]),
                                 filing_provider=_Provider(doc),
                                 text_parts=parts_for([item]))

    want_decision, want_code = _default_outcome(SchemaError("probe"))
    for unit in ("percent", "percent_yoy", "percent_sequential",
                 "percent_points", "basis_points", "x"):
        ok = attach_pure(_fact(level_unit=unit, value="726", mult=1))
        assert ok.preflight_outcomes == (), \
            (unit, [dict(o) for o in ok.preflight_outcomes])
        assert [i for i, _f in ok.facts] == [0], unit
        bad = attach_pure(_fact(level_unit=unit, value="726", mult=10 ** 6))
        assert bad.facts == (), (unit, "a refused item must attach nothing")
        assert len(bad.preflight_outcomes) == 1, \
            (unit, [dict(o) for o in bad.preflight_outcomes])
        row = bad.preflight_outcomes[0]
        assert (row["index"], row["decision"], row["codes"]) == \
            (0, want_decision, (want_code,)), (unit, dict(row))
        assert "must state multiplier 1" in row["detail"], (unit, dict(row))
