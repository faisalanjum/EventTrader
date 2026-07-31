"""The reviewer's direct attacks on the rev-4 build, saved as regressions.

Every test here reproduced a REAL defect in the first implementation. They are
kept forever because each one passed the original suite: green tests proved the
code did what I told it to, not what the law requires.

The eight defects, all confirmed live before any fix:
  1. two DIFFERENT 29-digit values auto-linked (Decimal.normalize() rounds at
     the context precision, so distinct numbers collapsed to one key)
  2. a 65-digit value silently rounded to 60 (a fixed precision cap is not
     exactness)
  3. two UNEQUAL 29-digit endpoints passed as a "point" (shape arithmetic ran
     at the DEFAULT 28-digit context)
  4. the XBRL bundle lost its all-or-nothing rule; model input could supply the
     two code-owned XBRL fields; and a legitimate structured-XBRL slot was
     REJECTED because every slot was judged as text evidence
  5. the contract accepted an invented driver_state, Q5, guidance without
     confirmation, confirmation on a metric, annual percent_sequential,
     malformed dates, invalid slice kinds, and conditions absent from the quote
     — because it never reached production's validator
  6. unmatched output order followed input order
  7. per_x matched by SUBSTRING (`barrel` accepted `..._per_barrels`)
  8. G-claims asserted more than the tests proved
"""
from decimal import Decimal

from driver.core.test_round10_event_boundary import parts_for

import pytest

from driver.core import xbrl_attach as xa

from driver.core import fact_match, prepared_fact_v2 as p2
from driver.core.prepared_fact_v2 import (ITEM_FIELDS, PreparedFactV2,
                                          PreparedItemV2, RunInputV2, SchemaError,
                                          check_per_x_against_name)
from driver.core.slot_convert import (SlotConversionError, convert_slot,
                                      exact_mul)
from driver.core.test_round10_event_boundary import filing_evidence
from driver.core.prepared_fact_v2 import ProductionValidationError
from driver.core.driver_neo4j_adapter import GraphFactRows

QUOTE = "revenue of $363 million"

D29_A = Decimal("1." + "0" * 27 + "1")     # 29 significant digits, differ only
D29_B = Decimal("1." + "0" * 27 + "2")     # in the 29th — beyond the default 28


def slot(v, m=1, ev=None):
    return {"value": Decimal(str(v)), "scale_multiplier": Decimal(str(m)),
            "unit_scale_evidence": ev}


def item(**over):
    base = {k: None for k in ITEM_FIELDS}
    base.update(driver_name="revenue", driver_state="reported", quote=QUOTE,
                measurement_raw_spans=[], slice_parts=[])
    base.update(over)
    return base


def fact(**over):
    d = {"fact_type": over.pop("fact_type", "metric"),
         "part_ref": over.pop("part_ref", "p01"),
         "occurrence_in_part": over.pop("occurrence_in_part", None),
         "per_x": over.pop("per_x", None), "item": item(**over)}
    return PreparedFactV2.from_dict(d)


def point(value, mult=1, ev=None, unit="count", **over):
    s = slot(value, mult, ev)
    return fact(level_low=s, level_high=s, level_unit=unit,
                level_shape_hint="point", **over)


# ------------------------------------------------------- 1. wrong credit ----

def test_ATTACK_two_different_29_digit_values_must_not_auto_link():
    """The sharpest finding: normalize() rounded both to the same 28-digit key,
    so a WRONG answer was credited as an exact match."""
    assert D29_A != D29_B
    r = fact_match.match_facts([point(D29_A)], [point(D29_B)])
    assert r.links == [], "different values auto-linked — wrong credit"
    assert len(r.to_grading_gold) == 1 and len(r.to_grading_produced) == 1


def test_ATTACK_equal_values_written_differently_still_link():
    """The flip side that normalize() was there for: 1.30 and 1.3 ARE the same
    stated number and must still match. Decimal already compares and hashes
    them equally, so no normalization step is needed at all."""
    assert Decimal("1.30") == Decimal("1.3")
    assert hash(Decimal("1.30")) == hash(Decimal("1.3"))
    r = fact_match.match_facts([point("1.30")], [point("1.3")])
    assert len(r.links) == 1


# ---------------------------------------------------------- 2. exactness ----

def test_ATTACK_a_65_digit_value_is_not_rounded():
    big = Decimal("1." + "1" * 64)
    assert len(big.as_tuple().digits) == 65
    out = convert_slot("count", slot(big, 1))
    assert out == big, "a fixed precision cap silently truncated the value"
    assert len(out.as_tuple().digits) == 65


def test_ATTACK_exact_mul_precision_comes_from_the_operands():
    a, b = Decimal("1." + "1" * 40), Decimal("1." + "1" * 40)
    product = exact_mul(a, b)
    # EXACT: reconstruct the product by hand from the integer coefficients, so
    # the assertion cannot be satisfied by a rounded result. (The previous
    # version ended in `or True` and asserted nothing at all.)
    from decimal import localcontext
    with localcontext() as ctx:                 # an INDEPENDENT high-precision
        ctx.prec = 200                          # computation, not the same helper
        expected = a * b
    assert product == expected
    # the exact product of m-digit and n-digit decimals needs at most m+n digits
    assert len(product.as_tuple().digits) <= 81
    # and it must be EXACT: multiplying back out recovers the operand
    assert exact_mul(Decimal("2"), Decimal("0.5")) == Decimal("1")
    assert exact_mul(Decimal("1e9"), Decimal("1.3")) == Decimal("1300000000")


def test_ATTACK_unequal_29_digit_endpoints_are_not_a_point():
    """My duplicate shape check ran at the default 28-digit context, so two
    different numbers satisfied 'low == high'. The duplicate is DELETED;
    production's `_shape` compares exact Decimals and catches it."""
    f = fact(level_low=slot(D29_A), level_high=slot(D29_B),
             level_unit="count", level_shape_hint="point")
    v = _violations(f)
    assert any(x.code == "SHAPE" for x in v), v


# ------------------------------------------------------- 3. XBRL boundary ----

def test_ATTACK_model_input_cannot_supply_the_code_owned_xbrl_fields():
    """Refused on EVERY constructor, not just the model door: an earlier version
    let `from_verified_source` accept model-supplied XBRL fields silently."""
    for field, value in (("xbrl_concept_raw", "MODEL-INVENTED"), ("member_refs", [])):
        payload = {"fact_type": "metric", "part_ref": "p01",
                   "occurrence_in_part": None, "per_x": None,
                   "item": {**item(), field: value}}
        with pytest.raises(SchemaError) as e:
            PreparedFactV2.from_dict(payload)
        assert field in str(e.value)
        _refused(SchemaError, field, payload)        # and through the trusted door


def test_ATTACK_every_fact_level_key_must_be_present_explicitly():
    """An OMITTED key is a different claim from a stated null; the prompt
    requires every field explicitly present."""
    full = {"fact_type": "metric", "part_ref": "p01", "occurrence_in_part": None,
            "per_x": None, "item": item()}
    PreparedFactV2.from_dict(full)
    for drop in ("per_x", "occurrence_in_part", "part_ref"):
        payload = {k: v for k, v in full.items() if k != drop}
        with pytest.raises(SchemaError) as e:
            PreparedFactV2.from_dict(payload)
        assert drop in str(e.value)
    short = {**full, "item": {k: v for k, v in item().items() if k != "conditions"}}
    with pytest.raises(SchemaError) as e:
        PreparedFactV2.from_dict(short)
    assert "conditions" in str(e.value)


def _xbrl_item(**over):
    s390 = slot(390, "1e6")
    base = dict(level_low=s390, level_high=s390, level_unit="m_usd",
                level_shape_hint="point", time_type="duration",
                period_start_date="2026-01-01", period_end_date="2026-03-31",
                quote="North America 390 361 778 726")
    base.update(over)
    return {"fact_type": "metric", "part_ref": "p01", "occurrence_in_part": None,
            "per_x": None, "item": item(**base)}


# ---------------------------------------------------------------------------
# REAL-SHAPED FIXTURES. The graph row carries the shapes the live database
# actually returns (probed read-only): a COMMA-FORMATTED value string — 807,132
# of 1,000,000 numeric facts carry commas — a bare `unit_ref` pointer plus the
# semantic Unit node behind it, and the SHORT inline element id that is the
# join key to the filing's own rendering. The inline document is a real
# ix:nonFraction fragment, so evidence and scale come from the certified
# Route-A binder rather than from anything this test asserts.
# ---------------------------------------------------------------------------
ELEMENT_ID = "f-48"
INLINE_HTML = (
    '<html><body><table><tr>'
    '<td>Total net sales</td>'
    '<td><ix:nonFraction id="f-48" name="us-gaap:Revenues" contextRef="c-1" '
    'unitRef="usd" scale="6" decimals="-6" '
    'format="ixt:num-dot-decimal">390</ix:nonFraction></td>'
    '</tr></table>'
    '<div style="display:none"><ix:header><ix:resources>'
    '<xbrli:context id="c-1"><xbrli:entity><xbrli:identifier>0000320193'
    '</xbrli:identifier></xbrli:entity><xbrli:period>'
    '<xbrli:startDate>2026-01-01</xbrli:startDate>'
    '<xbrli:endDate>2026-03-31</xbrli:endDate></xbrli:period></xbrli:context>'
    '<xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>'
    '<xbrli:unit id="shares"><xbrli:measure>xbrli:shares</xbrli:measure>'
    '</xbrli:unit>'
    '</ix:resources></ix:header></div></body></html>')


class FakeStore:
    """CORE's GRAPH — rows and the filing company, nothing else.

    Under the injected-provider design (round 8) the graph store stays
    graph-only: it never serves a document, so it cannot supply both a claim
    and the evidence for it."""

    def __init__(self, rows, expect_source="0000006201-26-000031", doc=None,
                 cik=None):
        self._rows, self._expect = rows, expect_source
        self._doc = INLINE_HTML if doc is None else doc   # kept for FakeProvider
        self._cik = CIK if cik is None else cik
        self.calls = []

    def get_xbrl_representation_count(self, source_id):
        return 1

    def get_xbrl_fact_dimensions(self, source_id, concept):
        self.calls.append((source_id, concept))
        if source_id != self._expect:
            return GraphFactRows(rows=[], exclusions=())
        return GraphFactRows(rows=[r for r in self._rows if r["concept"] == concept], exclusions=())

    def get_source_company_cik(self, source_id):
        return self._cik if source_id == self._expect else None


class FakeProvider:
    """FISCAL's injected filing provider: the DOCUMENT for a source id, and
    nothing else. It cannot state a hash, so the check can never be circular."""

    def __init__(self, doc=None, expect_source="0000006201-26-000031"):
        self._doc = INLINE_HTML if doc is None else doc
        self._expect = expect_source

    def get_filing_document(self, source_id):
        return self._doc if source_id == self._expect else None




def _row(**over):
    r = {"concept": "us-gaap:Revenues", "period_type": "duration",
         "start_date": "2026-01-01", "end_date": "2026-04-01",   # end EXCLUSIVE
         "dims": [], "fact_id": ELEMENT_ID, "context_id": "c-1",
         "unit_ref": "usd", "unit_name": "iso4217:USD", "is_divide": "0",
         "value": "390,000,000"}                     # COMMAS, as the graph stores
    r.update(over)
    return r


CIK = "320193"
_REQUIRED_KEYS = ("fact_id", "value", "unit_ref", "unit_name",
                  "is_divide", "context_id")


def _attach(payload=None, *, source_id="0000006201-26-000031",
            concept="us-gaap:Revenues", member_refs=(), rows=None,
            inline_doc=None, evidence_doc=None, store=None, provider=None):
    # MIGRATED (#821): through the ONE public event door.
    #
    # #824: the evidence is LAWFUL against the very document THIS call serves
    # and the fact carries that filing's own quote, so each attack below reaches
    # the rule it names instead of dying at the evidence gate. Only the quote is
    # set here; whatever field a test attacks is left alone.
    import copy as _copy
    payload = _copy.deepcopy(payload if payload is not None else _xbrl_item())
    # `evidence_doc` exists for ONE case: a test that strips the element's id to
    # exercise the identity fallback. That document RENDERS IDENTICALLY —
    # verified: same visible text, same text_sha — so the evidence is the same
    # rendering's, and the id is the attacked field.
    evidence, filing_quote = filing_evidence(
        evidence_doc if evidence_doc is not None
        else (INLINE_HTML if inline_doc is None else inline_doc),
        ELEMENT_ID)
    payload["item"]["quote"] = filing_quote
    entry = {"fact": payload, "concept": concept,
             "member_refs": list(member_refs), "source_evidence": evidence}
    return xa.attach_event_xbrl(
        [entry], source_id=source_id,
        store=store if store is not None
        else FakeStore(rows if rows is not None else [_row()], doc=inline_doc),
        filing_provider=provider if provider is not None
        else FakeProvider(doc=inline_doc),
        text_parts=parts_for([entry]))


def _one(payload=None, **kw):
    """The ONE verified fact, for a test whose subject is a SUCCESS."""
    res = _attach(payload, **kw)
    assert res.preflight_outcomes == (), [dict(o) for o in res.preflight_outcomes]
    assert [i for i, _f in res.facts] == [0]
    return res.facts[0][1]


def _refused(exc_class, needle, payload=None, **kw):
    """An item-local refusal, as the outcome row the door now returns (#825).

    THE EXPECTED DECISION AND CODE COME FROM THE EXCEPTION CLASS THIS TEST
    ALREADY NAMED, looked up through the one outcome owner — never from what
    the run happens to produce, so a migrated assertion cannot quietly become a
    mirror of the implementation. Exactly one row, and the reason is mandatory:
    without it a test proves that A refusal happened, not that the RIGHT rule
    refused.
    """
    want_decision, want_code = xa._default_outcome(exc_class("probe"))
    res = _attach(payload, **kw)
    assert res.facts == (), "a refused item must attach nothing"
    assert len(res.preflight_outcomes) == 1, \
        [dict(o) for o in res.preflight_outcomes]
    row = res.preflight_outcomes[0]
    assert (row["index"], row["decision"], row["codes"]) == \
        (0, want_decision, (want_code,))
    assert needle in row["detail"], row["detail"]
    return row


def test_ATTACK_the_happy_path_verifies_against_a_real_shaped_row():
    """The positive case must genuinely pass — otherwise every negative below
    could be passing for the wrong reason."""
    f = _one()
    assert f.item.xbrl_concept_raw == "us-gaap:Revenues"
    assert convert_slot("m_usd", f.item.level_low) == Decimal(390)


def test_ATTACK_comma_formatted_graph_values_are_parsed_not_rejected():
    """807,132 of 1,000,000 live numeric facts carry commas; a bare Decimal()
    rejects them. The certified accounting-number parser is used instead."""
    from driver.relocation.inline_html import parse_raw
    assert parse_raw("113,743,000,000") == Decimal("113743000000")
    assert parse_raw("(1,234.50)") == Decimal("-1234.50")       # accounting negative
    _one(rows=[_row(value="390,000,000")])                      # end to end


def test_ATTACK_the_verifier_fetches_its_own_evidence():
    import inspect
    params = inspect.signature(xa.attach_event_xbrl).parameters
    assert "fact_rows" not in params and "slot" not in params
    assert "fact_tokens" not in params and "bundle" not in params
    store = FakeStore([_row()])
    _one(store=store)
    assert store.calls == [("0000006201-26-000031", "us-gaap:Revenues")]


def test_ATTACK_a_forged_filing_row_can_no_longer_be_supplied():
    # round 11: an unbacked concept PARKS rather than rejecting — the graph
    # runs about a quarter behind the channel, so "no fact yet" is corpus lag
    # far more often than invention, and a park drains where a reject loses it.
    from driver.core.prepared_fact_v2 import ProductionValidationError
    _refused(ProductionValidationError, "NO fact", concept="totally:Fabricated")


def test_ATTACK_a_bundle_cannot_be_carried_into_another_source():
    # round 11: PARK-RETRY, not a rejection — a document the provider does not
    # have YET is ChannelContract 3's hold case, not a channel mistake.
    from driver.core.prepared_fact_v2 import SourceUnavailable
    _refused(SourceUnavailable, "no document for source",
             source_id="SOME-OTHER-FILING")


# WHY THE FOUR ATTACKS BELOW EXPECT A PARK, stated once (#824).
# Each of them breaks something the BINDER checks — the unit the graph names,
# the element id, whether the rendering reconciles, the dimension set — so the
# graph and the filing disagree and `bind_graph_fact` returns None. Execution
# reaches the `bound is None` branch, which is a GRAPH/FILING binding failure
# and therefore an ordinary park, not a contract rejection. This is decided by
# WHERE the failure arises (that branch), never by reading the reason text.
# A contradiction submitted AFTER a successful bind — a wrong slot, a wrong
# unit for a bound fact, wrong evidence — still REJECTS, and those tests below
# keep `SchemaError` unchanged.


def test_ATTACK_the_semantic_Unit_node_is_the_authority_not_the_unit_ref():
    """`unit_ref` is a bare pointer; the meaning lives on the linked Unit node.
    A share unit could pass as m_usd because nothing consulted it."""
    # unit_ref says shares, fact is m_usd
    _refused(ProductionValidationError, "unit_ref_mismatch",
             rows=[_row(unit_ref="shares", unit_name="xbrli:shares")])
    # the claimed name is not the filing's
    _refused(ProductionValidationError, "unit_name_not_the_filings_measure",
             rows=[_row(unit_name="xbrli:shares")])
    # a per-something (divide) unit
    _refused(ProductionValidationError, "is_divide_disagrees",
             rows=[_row(is_divide="1")])


def test_ATTACK_evidence_and_scale_come_from_the_filings_own_rendering():
    """Invented evidence and an empty evidence list were both accepted. Evidence
    is no longer an argument at all: it is resolved from the inline document by
    the fact's own short element id."""
    import inspect
    assert "evidence_pieces" not in inspect.signature(xa.attach_event_xbrl).parameters
    # THE LAW, corrected: a NON-BLANK short id must resolve EXACTLY. The
    # fallback is permitted only when the id is null/blank — an earlier version
    # fell back on ANY id failure, rescuing wrong and duplicate ids.
    row = _refused(ProductionValidationError, "exact_id_id_not_found",
                   rows=[_row(fact_id="f-does-not-exist")])
    assert "fallback" not in row["detail"]


def test_ATTACK_a_wrong_declared_scale_fails_the_certified_reconcile():
    """displayed composed with format, scale and sign must equal the stored
    value — checked by the binder's own `reconcile`, not by arithmetic here."""
    _refused(ProductionValidationError, "value_does_not_reconcile",
             rows=[_row(value="390,000")])      # rendering says 390 x 10^6


def test_ATTACK_the_facts_OWN_slot_is_the_one_verified():
    from driver.core.slot_convert import convert_slot as cs
    assert cs("m_usd", slot(390, 1)) == Decimal("0.000390")
    _refused(SchemaError, "level_low describes the source as value=390 x 1",
             _xbrl_item(level_low=slot(390, 1), level_high=slot(390, 1)))


def test_ATTACK_every_numeric_slot_is_checked_not_just_level_low():
    """A filing reports ONE value, so a claimed 390-391 RANGE must fail — only
    level_low used to be compared."""
    _refused(SchemaError, "level_high describes the source as",
             _xbrl_item(level_low=slot(390, "1e6"), level_high=slot(391, "1e6"),
                        level_shape_hint="range"))
    for extra in ("change_value", "comparison_low", "comparison_high"):
        kw = {extra: slot(1, "1e6")}
        if extra == "change_value":
            kw["change_unit"] = "m_usd"
        # The reason must NAME the offending slot, so a check that fired on the
        # wrong field could not pass this loop.
        _refused(SchemaError,
                 f"{extra} must be null on an XBRL-backed fact",
                 _xbrl_item(**kw))


def test_ATTACK_missing_row_metadata_parks_it_does_not_trust_the_caller():
    """Every required field parks when blank — EXCEPT `fact_id`, which may
    # blank (None/''/whitespace) is LAWFUL and means "this element has no
    # id", which routes to the identity fallback. The dated, scoped counts
    # of such facts have ONE owner, in `xbrl_attach`.

    #819: this asserted `SchemaError`, which DECIDES REJECTED, while its own
    name and message said PARK. A broken filing row is not something a channel
    can fix by resubmitting, so a rejection meant the item never drained."""
    from driver.core.prepared_fact_v2 import ProductionValidationError
    for field in ("value", "unit_ref", "unit_name", "is_divide", "context_id"):
        row = _refused(ProductionValidationError, field,
                       rows=[_row(**{field: None})])
        # case-insensitive: this asserts INTENT, not the message's formatting
        assert "park" in row["detail"].lower(), \
            "the message must name the field and say it parks"
    for field in _REQUIRED_KEYS:                 # a missing COLUMN is different
        row = {k: v for k, v in _row().items() if k != field}
        got = _refused(ProductionValidationError, field, rows=[row])
        assert "no" in got["detail"]


def test_ATTACK_a_lawful_BLANK_fact_id_reaches_the_fallback():
    """Core rejected every blank short id before the fallback it had just built
    could run — and the three blank forms behaved differently from each other."""
    doc = INLINE_HTML.replace('id="f-48" ', "")      # the element has no id
    # The stripped document renders IDENTICALLY (same visible text, same
    # text_sha), so its evidence is the untouched rendering's; only the id —
    # the field under attack — differs.
    for blank in (None, "", "   "):
        f = _one(rows=[_row(fact_id=blank)], inline_doc=doc,
                 evidence_doc=INLINE_HTML)
        assert f.item.xbrl_concept_raw == "us-gaap:Revenues", blank


def test_ATTACK_a_compensated_numeric_description_is_rejected():
    """The filing prints 390 with declared scale 6. Descriptions that convert to
    the same total but describe a DIFFERENT source reading must all fail."""
    from driver.core.slot_convert import convert_slot as cs
    for value, mult in ((390000000, 1), ("0.39", "1e9"), ("3.9", "1e8")):
        s390 = slot(value, mult)
        assert cs("m_usd", s390) == Decimal(390)      # same total...
        # ...different description
        _refused(SchemaError, "describes the source as",
                 _xbrl_item(level_low=s390, level_high=s390))
    _one()                                             # the true one still binds


def test_ATTACK_invented_scale_evidence_on_an_xbrl_slot_is_rejected():
    s390 = dict(slot(390, "1e6"), unit_scale_evidence="I invented this")
    _refused(SchemaError,
             "level_low.unit_scale_evidence must be null on an XBRL-backed fact",
             _xbrl_item(level_low=s390, level_high=s390))


def test_ATTACK_the_document_is_tied_to_the_source_id():
    """An AAL source id could be paired with an AAPL document because nothing
    tied them. The document is now FETCHED for the source, not handed in."""
    import inspect
    # the EVENT DOOR is the boundary now: it must accept neither a document
    # nor a company from its caller (the private binder receives both, but
    # only from the door, which fetched them itself).
    assert "inline_doc" not in inspect.signature(xa.attach_event_xbrl).parameters
    assert "entity_cik" not in inspect.signature(xa.attach_event_xbrl).parameters
    from driver.core.prepared_fact_v2 import SourceUnavailable
    _refused(SourceUnavailable, "no document for source",   # a different filing
             source_id="0000320193-26-000999")


def test_ATTACK_a_document_that_does_not_hash_to_its_source_is_refused():
    """Round 8: the expected hash comes from the channel's HARVESTED packet and
    the document from the provider — two hands, so a provider serving another
    document is caught. (Before, the provider supplied both and the check only
    caught it contradicting itself.)"""
    other = INLINE_HTML.replace("390", "999")
    _refused(SchemaError, "does not hash to the representation",
             provider=FakeProvider(doc=other))          # harvested sha unchanged


def test_ATTACK_the_attach_token_is_not_reachable_from_outside():
    assert not hasattr(p2.PreparedItemV2, "_ATTACH_TOKEN")
    assert not any(n.endswith("ATTACH_TOKEN") for n in dir(p2.PreparedItemV2))


def test_ATTACK_a_frozen_polarity_proof_does_not_crash_matching():
    from driver.core import fact_match
    proof = {"polarity": "higher_favorable", "basis": "source_framing",
             "evidence": "e", "sentence": "s"}
    f = fact(polarity_proof=proof)
    r = fact_match.match_facts([f], [f])
    assert len(r.links) == 1


def test_ATTACK_conflicting_duplicate_rows_park_regardless_of_order():
    # #819: was `SchemaError` (= rejected) while the name and the message both
    # said park. Two conflicting facts in someone else's filing are ours to
    # park, never a contract violation to hand back to the channel.
    from driver.core.prepared_fact_v2 import ProductionValidationError
    a, b = _row(), _row(value="111,000,000")
    for rows in ([a, b], [b, a]):
        _refused(ProductionValidationError, "CONFLICTING", rows=rows)


def test_ATTACK_the_returned_fact_is_DEEPLY_immutable():
    """The frozen dataclass froze only its own attributes: mutating the caller's
    input after verification changed what the fact stored — 390 million became
    0.000390 for the THIRD time, by a third route."""
    d = _xbrl_item()
    f = _one(d)
    assert convert_slot("m_usd", f.item.level_low) == Decimal(390)
    d["item"]["level_low"]["scale_multiplier"] = Decimal(1)     # mutate the input
    assert convert_slot("m_usd", f.item.level_low) == Decimal(390), \
        "the attached fact aliased the caller's slot"
    with pytest.raises(TypeError):
        f.item.level_low["scale_multiplier"] = Decimal(1)
    assert isinstance(f.item.slice_parts, tuple)
    assert isinstance(f.item.member_refs, tuple)


def test_ATTACK_model_built_facts_are_deeply_immutable_too():
    """Same defect, same class, the OTHER door."""
    d = {"fact_type": "metric", "part_ref": "p01", "occurrence_in_part": None,
         "per_x": None, "item": item(slice_parts=["segment:a"])}
    f = PreparedFactV2.from_dict(d)
    d["item"]["slice_parts"].append("segment:INJECTED")
    assert f.item.slice_parts == ("segment:a",)
    with pytest.raises(AttributeError):
        f.item.slice_parts.append("x")


def test_ATTACK_member_slices_must_be_the_facts_own_slices():
    axis = "us-gaap:StatementBusinessSegmentsAxis"
    refs = [{"axis": axis, "member": "m", "slice_part": "segment:not_mine"}]
    rows = [_row(dims=[{"axis": axis, "member": "m", "label": "M"}])]
    # The claimed pair is not the matched fact's, so the BINDER abstains before
    # the member law is reached — the reason names that gate, not the ref rule.
    _refused(ProductionValidationError, "dimension_set_mismatch",
             _xbrl_item(slice_parts=["segment:mine"]), member_refs=refs,
             rows=rows)


def test_ATTACK_a_wrong_context_finds_no_matching_fact():
    """#819 class (reviewer, audit :451): this asserted `SchemaError` and so
    CEMENTED the wrong outcome. Evidence the graph cannot bind YET is the
    ordinary PARK — the third time a test of mine has pinned a defect as
    though it were intended behaviour."""
    from driver.core.prepared_fact_v2 import ProductionValidationError
    _refused(ProductionValidationError, "exact context",
             _xbrl_item(period_end_date="2026-06-30"))


def test_ATTACK_the_text_lane_still_demands_quote_local_evidence():
    with pytest.raises(SchemaError):
        fact(level_low=slot(390, "1e6"), level_high=slot(390, "1e6"),
             level_unit="m_usd", level_shape_hint="point")


# --------------------------------------- 4. production validation is wired ----

def _stored_kwargs():
    return dict(driver={"name": "revenue", "fact_type": "metric"},
                source={"date": "2026-04-23T08:30:00-04:00", "source_type": "8k",
                        "ticker": "AAL", "source_id": "0000006201-26-000031"},
                fye_month=12)


def _violations(f, **over):
    kw = _stored_kwargs()
    kw.update(over)
    return p2.validate_via_production(f, **kw)


@pytest.mark.parametrize("label,over,code", [
    ("invented driver_state", dict(driver_state="exploded"), "STATE"),
    ("company_confirmed on a metric", dict(company_confirmed=True), "LANE"),
    ("conditions on a metric", dict(conditions="if the moon is full"), "CONDITIONS"),
])
def test_ATTACK_production_rules_now_reject_what_v2_used_to_accept(label, over, code):
    v = _violations(fact(**over))
    assert any(x.code == code for x in v), f"{label} was accepted: {v}"


def test_ATTACK_guidance_without_confirmation_is_rejected():
    v = _violations(fact(fact_type="guidance", driver_state="introduced",
                         value_text="roughly flat", period_end_date="2026-12-31",
                         fiscal_year=2026, time_type="duration",
                         period_start_date="2026-01-01"),
                    driver={"name": "revenue", "fact_type": "guidance"})
    assert any(x.code == "LANE" for x in v)


def test_ATTACK_annual_percent_sequential_is_rejected():
    f = point(5, unit="percent_sequential", fiscal_year=2026,
              period_start_date="2026-01-01", period_end_date="2026-12-31",
              time_type="duration")
    v = _violations(f)
    assert any("percent_sequential" in x.message for x in v), v


@pytest.mark.parametrize("bad", ["2026-13-45", "not-a-date", "2026/03/31"])
def test_ATTACK_malformed_dates_are_rejected(bad):
    with pytest.raises((SchemaError, p2.ProductionValidationError)):
        _violations(fact(period_end_date=bad, period_start_date="2026-01-01",
                         time_type="duration"))


def test_ATTACK_q5_is_rejected():
    with pytest.raises((SchemaError, p2.ProductionValidationError)):
        _violations(fact(fiscal_year=2026, fiscal_quarter=5))


def test_ATTACK_an_invalid_slice_kind_is_rejected():
    with pytest.raises((SchemaError, p2.ProductionValidationError)):
        _violations(fact(slice_parts=["planet:mars"]))


def test_ATTACK_two_period_shape_fields_are_rejected_by_the_PRODUCTION_resolver():
    with pytest.raises((SchemaError, p2.ProductionValidationError)):
        _violations(fact(fiscal_year=2026, fiscal_quarter=3, half=2))


def test_the_contract_does_not_reimplement_THREE_NAMED_production_symbols():
    """A LIMITED SYMBOL TRIPWIRE, named for exactly what it is.

    It watches three identifiers owned by `driver_validators` /
    `driver_period_resolver` for reappearing inside the v2 contract. An
    identifier cannot be reworded, so formatting cannot alter the property.

    IT IS NOT A PROOF OF NO DUPLICATION, and the old name implied it was. Two
    PROSE needles sat in the same list — one a sentence about the period-shape
    field limit, the other a sentence about the value_text character bound —
    which tested a COMMENT'S WORDING: reflowing a sentence broke them, while
    re-implementing the rule under a different sentence did not. Both are
    DELETED, and deliberately not replaced by a longer banned-phrase list.

    They are DESCRIBED here rather than QUOTED. Quoting them left the retired
    needles as the only literal copies in the tree, so every audit grep for
    "are they gone?" kept finding them inside the note recording their removal —
    the same false positive three rounds running.
    """
    import inspect
    src = inspect.getsource(p2)
    for symbol in ("_check_periods", "_check_shape", "LANE_STATES"):
        assert symbol not in src, (
            f"a second validator is growing back: {symbol!r} belongs to "
            f"driver_validators / driver_period_resolver")


# ---------------------------------------------- 5. ordering + per_x exact ----

def test_ATTACK_unmatched_output_is_canonically_ordered():
    g = [point(n) for n in (3, 1, 2)]
    forward = fact_match.match_facts(g, [])
    reverse = fact_match.match_facts(list(reversed(g)), [])
    key = lambda res: [fact_match.record_key(x) for x in res.to_grading_gold]
    assert key(forward) == key(reverse), "unmatched output follows input order"


def test_ATTACK_per_x_uses_exact_denominator_matching_not_substring():
    assert check_per_x_against_name("oil_price_per_barrel", "barrel") is None
    assert check_per_x_against_name("cost_per_available_seat_mile",
                                    "available_seat_mile") is None
    # a terminal family suffix may follow the denominator
    assert check_per_x_against_name("oil_price_per_barrel_guidance", "barrel") is None
    # ...but a DIFFERENT denominator must never pass by substring
    for wrong in ("oil_price_per_barrels", "oil_price_per_barrel_of_oil",
                  "revenue_per_barrelling"):
        assert check_per_x_against_name(wrong, "barrel") is not None, wrong


def test_ATTACK_the_deferred_acronym_class_still_parks():
    reason = check_per_x_against_name("dps", "share")
    assert reason is not None and "unverified" in reason.lower()
    assert check_per_x_against_name("eps", "share") is None


def test_ATTACK_xbrl_scaling_is_exact_at_29_digits():
    """The declared-scale check ran at the DEFAULT 28-digit context: it REJECTED
    the exact 29-digit value and ACCEPTED the rounded-wrong one."""
    from driver.core.slot_convert import check_xbrl_consistency
    from driver.core.slot_convert import exact_scaleb
    d29 = Decimal("1." + "0" * 27 + "1")
    exact_full = exact_scaleb(d29, 6)
    assert len(exact_full.as_tuple().digits) == 29     # nothing was rounded away
    check_xbrl_consistency(displayed=d29, ix_scale=6, full_value=exact_full)
    with pytest.raises(SlotConversionError):
        check_xbrl_consistency(displayed=d29, ix_scale=6,
                               full_value=Decimal("1000000"))


def test_ATTACK_extreme_exponents_park_they_do_not_crash():
    """Raw decimal.Overflow / InvalidOperation escaped as a crash; an
    unrepresentable magnitude is a PARK."""
    from driver.core.slot_convert import check_xbrl_consistency
    with pytest.raises(SlotConversionError):
        check_xbrl_consistency(displayed=Decimal(1), ix_scale=10 ** 9,
                               full_value=Decimal(1))
    # a magnitude beyond the decimal exponent range must PARK, not crash
    with pytest.raises(SlotConversionError):
        convert_slot("m_usd", slot(Decimal("1E+999999999999999999"), "1e9"))
    # ...and a magnitude that is arithmetically representable but NOT storable
    # now parks at the representation bound rather than surviving conversion to
    # die later inside the canonicalizer.
    with pytest.raises(SlotConversionError) as e:
        convert_slot("m_usd", slot(Decimal("1E+999999999"), "1e9"))
    assert "not storable" in str(e.value)


def test_ATTACK_an_unstorable_magnitude_parks_before_it_can_exhaust_memory():
    """`Decimal("1E+999999999")` passed conversion and then died with
    MemoryError inside the canonicalizer. The guard is a REPRESENTATION bound
    checked from the exponent — the expanded string is never built, because
    building it is the failure being prevented."""
    from driver.core.slot_convert import assert_storable
    with pytest.raises(SlotConversionError) as e:
        convert_slot("count", slot(Decimal("1E+999999999"), 1))
    assert "not storable" in str(e.value)
    # ...and the value that killed the canonicalizer never reaches it
    from driver.core.driver_ids import dec_canon
    assert dec_canon(assert_storable(Decimal("1.30"))) == "1.3"
    # a real filing figure is nowhere near the bound
    for ok in ("390", "-0.10", "1E+120", "1.000000000000000000000000001"):
        assert_storable(Decimal(ok))




def test_ATTACK_the_representation_length_is_exact_not_approximate():
    """SUPERSEDED IN PLACE: the bound is now the length of the CANONICAL stored
    form, so it is checked against `dec_canon` (see
    test_ATTACK_the_canonical_length_matches_the_real_canonicalizer). Comparing
    against raw `format(d,"f")` would re-assert the defect — `1.30` formats to
    four characters but is stored as `1.3`."""
    from driver.core.driver_ids import dec_canon
    from driver.core.slot_convert import stored_char_length
    assert stored_char_length(Decimal("1.30")) == len(dec_canon(Decimal("1.30")))


def test_ATTACK_a_fractional_scale_is_never_silently_truncated():
    """`ix_scale=6.5` was silently treated as 6. The scale exponent must be an
    exact integer; the certified binder's own `int(el.get('scale'))` raises on
    a malformed one, and our shift refuses a non-int outright."""
    from driver.core.slot_convert import exact_scaleb
    for bad in (6.5, "6", True, None):
        with pytest.raises(SlotConversionError):
            exact_scaleb(Decimal(390), bad)
    assert exact_scaleb(Decimal(390), 6) == Decimal("390000000")


def test_ATTACK_the_canonical_length_matches_the_real_canonicalizer():
    """The guard rejected `1.000…` although its canonical stored form is `1`."""
    from driver.core.driver_ids import dec_canon
    from driver.core.slot_convert import assert_storable, stored_char_length
    for v in ("1." + "0" * 1100, "1.30", "-0.10", "390", "0.000390", "0",
              "-1234567890.12", "1E+120", "0.5", "1.000"):
        d = Decimal(v)
        assert stored_char_length(d) == len(dec_canon(d)), v
    assert_storable(Decimal("1." + "0" * 1100))      # canonical form is just "1"


# ---------------------------------------------------------------------------
# #823 — DEEP IMMUTABILITY AT EVERY CONSTRUCTOR. The two doors froze; the
# dataclasses themselves did not, so a direct construction kept the caller's
# objects and the "frozen" fact changed underneath it.
# ---------------------------------------------------------------------------

def _nested():
    """One of every nested shape the item can hold, all caller-owned."""
    return {"spans": ["adjusted"], "parts": ["segment:a"],
            "slot": {"value": Decimal("1"), "scale_multiplier": Decimal(1),
                     "unit_scale_evidence": None},
            "proof": {"polarity": "higher_favorable", "basis": "source_framing",
                      "evidence": "e", "sentence": "s"}}


def _item_kwargs(n):
    d = {k: None for k in ITEM_FIELDS}
    d.update(driver_name="revenue", driver_state="reported", quote=QUOTE,
             measurement_raw_spans=n["spans"], slice_parts=n["parts"],
             level_unit="count", level_low=n["slot"], level_high=n["slot"],
             level_shape_hint="point", polarity_proof=n["proof"])
    return d


def _mutate_everything(n):
    n["spans"].append("MUTATED")
    n["parts"].clear()
    n["slot"]["scale_multiplier"] = Decimal(999)
    n["proof"]["polarity"] = "lower_favorable"


def _assert_untouched(item):
    assert tuple(item.measurement_raw_spans) == ("adjusted",)
    assert tuple(item.slice_parts) == ("segment:a",)
    assert item.level_low["scale_multiplier"] == Decimal(1)
    assert item.polarity_proof["polarity"] == "higher_favorable"


def test_ATTACK_823_the_DIRECT_item_constructor_freezes_too():
    """`PreparedItemV2(...)` kept the caller's lists and dicts: appending to the
    spans, clearing the parts or editing the slot changed the frozen fact."""
    n = _nested()
    item = PreparedItemV2(**_item_kwargs(n))
    _mutate_everything(n)
    _assert_untouched(item)


def test_ATTACK_823_the_DIRECT_fact_constructor_freezes_too():
    n = _nested()
    f = PreparedFactV2(fact_type="metric", part_ref="p01",
                       occurrence_in_part=None, per_x=None,
                       item=PreparedItemV2(**_item_kwargs(n)))
    _mutate_everything(n)
    _assert_untouched(f.item)


def test_ATTACK_823_the_MODEL_door_still_freezes():
    n = _nested()
    f = PreparedFactV2.from_dict({"fact_type": "metric", "part_ref": "p01",
                                  "occurrence_in_part": None, "per_x": None,
                                  "item": _item_kwargs(n)})
    _mutate_everything(n)
    _assert_untouched(f.item)


@pytest.mark.parametrize("route", ["direct", "from_dict"])
def test_ATTACK_823_the_run_input_holds_its_facts_as_a_TUPLE(route):
    """`RunInputV2(source_id=..., facts=[])` VALIDATED an empty list, then the
    caller appended a non-fact — so the invariant the constructor had just
    checked was false on a supposedly frozen object."""
    facts = []
    ri = (RunInputV2(source_id="acc-1", facts=facts) if route == "direct"
          else RunInputV2.from_dict({"source_id": "acc-1", "facts": facts}))
    facts.append("not-a-fact")
    assert isinstance(ri.facts, tuple)
    assert ri.facts == (), f"the validated fact list changed: {ri.facts}"


def test_ATTACK_823_nothing_is_mutable_THROUGH_the_returned_object():
    n = _nested()
    item = PreparedItemV2(**_item_kwargs(n))
    for attempt in (lambda: item.measurement_raw_spans.append("x"),
                    lambda: item.slice_parts.append("x"),
                    lambda: item.level_low.__setitem__("value", Decimal(2)),
                    lambda: item.polarity_proof.__setitem__("basis", "x")):
        with pytest.raises((AttributeError, TypeError)):
            attempt()


def test_ATTACK_823_matching_and_HASHING_are_unchanged_by_freezing():
    """The required proof: freezing must not alter identity or grading."""
    n1, n2 = _nested(), _nested()
    a = PreparedFactV2(fact_type="metric", part_ref="p01",
                       occurrence_in_part=None, per_x=None,
                       item=PreparedItemV2(**_item_kwargs(n1)))
    b = PreparedFactV2(fact_type="metric", part_ref="p01",
                       occurrence_in_part=None, per_x=None,
                       item=PreparedItemV2(**_item_kwargs(n2)))
    assert fact_match.record_key(a) == fact_match.record_key(b)
    assert hash(fact_match.record_key(a)) == hash(fact_match.record_key(b))
    assert len(fact_match.match_facts([a], [b]).links) == 1
