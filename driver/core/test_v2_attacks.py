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

from driver.core.test_round10_event_boundary import (_FIXTURE_NS, _XMLNS,
                                                     _ns_dim, parts_for)

import pytest

from driver.core import xbrl_attach as xa

from driver.core import fact_match, prepared_fact_v2 as p2
from driver.core.prepared_fact_v2 import (ITEM_FIELDS, PreparedFactV2,
                                          PreparedItemV2, RunInputV2, SchemaError)
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
    """Refused on EVERY constructor, not just the model door. Since W9c the
    refusal comes from the ONE exact-key owner (the source-owned pair is
    derived OUT of ITEM_FIELDS, so it is necessarily unexpected) — and that
    owner deliberately NEVER echoes caller keys (extras by COUNT only, the
    no-echo law), so this node asserts the refusal and its exact-key class,
    not a name echo. As the board put it: this now proves D4; A-D8's route
    is the derivation itself."""
    for field, value in (("xbrl_concept_raw", "MODEL-INVENTED"), ("member_refs", [])):
        payload = {"fact_type": "metric", "part_ref": "p01",
                   "occurrence_in_part": None, "per_x": None,
                   "item": {**item(), field: value}}
        with pytest.raises(SchemaError, match="32 model-owned fields"):
            PreparedFactV2.from_dict(payload)


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
    f'<html {_XMLNS}><body><table><tr>'
    '<td>Total net sales</td>'
    '<td><ix:nonFraction id="f-48" name="us-gaap:Revenues" contextRef="c-1" '
    'unitRef="usd" scale="6" decimals="-6" '
    'format="ixt:num-dot-decimal">390</ix:nonFraction></td>'
    '</tr></table>'
    '<div style="display:none"><ix:header><ix:resources>'
    '<xbrli:context id="c-1"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193'
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
         "value": "390,000,000",                    # COMMAS, as the graph stores
         # the concept identity the real adapter returns, read from the SAME
         # declaration this file's documents are built from
         "concept_namespace": _FIXTURE_NS["us-gaap"],
         "graph_concept_qname": "us-gaap:Revenues"}
    r.update(over)
    return r


CIK = "0000320193"
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
    rejects them. The certified graph-lexical parser is used instead.
    IDENTITY CHANGE (SEQ 265 D): the accounting-paren assert is retired —
    parentheses left the graph grammar (the writer never emits them; census
    zero) and now refuse; the source lane's paren law is pinned at the bind
    door by test_F_a_visible_accounting_negative_still_reconciles."""
    from driver.relocation.inline_html import parse_raw
    assert parse_raw("113,743,000,000") == Decimal("113743000000")
    assert parse_raw("(1,234.50)") is None
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


def test_ATTACK_a_frozen_polarity_proof_does_not_crash_matching():
    from driver.core import fact_match
    proof = {"polarity": "favorable", "basis": "source_framing",
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
    # CLAIM AND ROW NAME THE SAME DECLARED QNAME, so `match_xbrl_fact` selects
    # this row and the refusal comes from the binder's dimension gate — the
    # rule this test is named for — rather than from the earlier
    # no-matching-row gate. The row was a three-key dim before and parked on
    # its own missing namespaces, which made the assertion prove a different
    # law under this test's name; completing it while leaving the two sides
    # spelled differently would only move the refusal to the wrong gate again.
    # The filing context stays dimensionless, so the mismatch is real.
    refs = [{"axis": axis, "member": "us-gaap:m",
             "slice_part": "segment:not_mine"}]
    rows = [_row(dims=[_ns_dim(axis, "us-gaap:m", "M")])]
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
    # C2 (#827, OD-11): the lawful annual TWIN — percent_yoy IS valid on an
    # annual period; the refusal above is percent_sequential-specific. Same
    # node by design (the twin exists to prove the rule's edge, not a new id).
    twin = point(5, unit="percent_yoy", fiscal_year=2026,
                 period_start_date="2026-01-01", period_end_date="2026-12-31",
                 time_type="duration")
    tv = _violations(twin)
    assert not any("invalid on an annual period" in x.message for x in tv), tv


# THE ONE ERROR EACH OF THESE ACTUALLY RAISES (#827 round 6). They accepted
# `(SchemaError, ProductionValidationError)` — an alternation that passes on
# either, so it could not tell which rule fired. Measured: all four raise
# ProductionValidationError, and the two classes are UNRELATED (both derive
# from ValueError, neither from the other), so the SchemaError arm was dead
# and the pair read as "some exception happened".
@pytest.mark.parametrize("bad", ["2026-13-45", "not-a-date", "2026/03/31"])
def test_ATTACK_malformed_dates_are_rejected(bad):
    with pytest.raises(p2.ProductionValidationError):
        _violations(fact(period_end_date=bad, period_start_date="2026-01-01",
                         time_type="duration"))


def test_ATTACK_q5_is_rejected():
    with pytest.raises(p2.ProductionValidationError):
        _violations(fact(fiscal_year=2026, fiscal_quarter=5))


def test_ATTACK_an_invalid_slice_kind_is_rejected():
    with pytest.raises(p2.ProductionValidationError):
        _violations(fact(slice_parts=["planet:mars"]))


def test_ATTACK_two_period_shape_fields_are_rejected_by_the_PRODUCTION_resolver():
    with pytest.raises(p2.ProductionValidationError):
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
    for symbol in ("_check_periods", "_check_shape"):
        assert symbol not in src, (
            f"a second validator is growing back: {symbol!r} belongs to "
            f"driver_validators / driver_period_resolver")
    # T8 reconcile (recorded, not silent): pf2 now lawfully CONSUMES
    # LANE_STATES from its owner, so this leg tightens from "text absent" to
    # "no second binding": the ONLY lawful appearances are the ImportFrom off
    # driver_validators and name loads. Any assignment/def/class re-authoring
    # a lane vocabulary here trips exactly as before.
    import ast
    tree = ast.parse(src)
    owner_import = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == "driver.core.driver_validators" and \
                    any(a.name == "LANE_STATES" for a in node.names):
                owner_import = True
            continue
        binds = []
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            binds = [t.id for t in targets if isinstance(t, ast.Name)]
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            binds = [node.name]
        assert "LANE_STATES" not in binds, (
            "a second lane vocabulary is growing back: LANE_STATES may only "
            "be IMPORTED from driver_validators, never re-bound here")
    assert owner_import, "pf2 must consume LANE_STATES from its one owner (T8)"


# ---------------------------------------------- 5. ordering + per_x exact ----

def test_ATTACK_unmatched_output_is_canonically_ordered():
    g = [point(n) for n in (3, 1, 2)]
    forward = fact_match.match_facts(g, [])
    reverse = fact_match.match_facts(list(reversed(g)), [])
    key = lambda res: [fact_match.record_key(x) for x in res.to_grading_gold]
    assert key(forward) == key(reverse), "unmatched output follows input order"


# S14 (#827): test_ATTACK_xbrl_scaling_is_exact_at_29_digits DELETED with
# the dead helper; surviving owners: test_round12_exact_scale.py::
# test_29_digit_pairs_stay_distinct_through_the_shift and test_bind_graph_fact.py::
# test_RED_exact_number_pair_at_29_digits.


def test_ATTACK_extreme_exponents_park_they_do_not_crash():
    """Raw decimal.Overflow / InvalidOperation escaped as a crash; an
    unrepresentable magnitude is a PARK."""
    # (S14: the dead-helper block that stood here is deleted; the two
    # remaining legs below are the node's living subject.)
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
              "-1234567890.12", "1E+120", "0.5", "1.000",
              # S11 (#827), the missing edge controls (FD §5.1 OD-8: no
              # exponent, no trailing zeros, -0 -> 0):
              "-0",          # signed zero canonicalises to "0" (length 1)
              "-0.00",       # signed zero with trailing zeros -> "0"
              "0E+10",       # zero with a POSITIVE exponent -> "0"
              "0E-10",       # zero with a NEGATIVE exponent -> "0"
              "1E-3",        # non-zero negative exponent -> "0.001"
              "1200E+1"):    # coefficient zeros + exponent -> "12000"
        d = Decimal(v)
        assert stored_char_length(d) == len(dec_canon(d)), v
    # the S11 controls' EXACT canonical forms (the arithmetic, not just parity)
    assert dec_canon(Decimal("-0")) == "0"
    assert dec_canon(Decimal("0E+10")) == "0"
    assert dec_canon(Decimal("1E-3")) == "0.001"
    assert stored_char_length(Decimal("-0.00")) == 1
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
            "proof": {"polarity": "favorable", "basis": "source_framing",
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
    n["proof"]["polarity"] = "unfavorable"


def _assert_untouched(item):
    assert tuple(item.measurement_raw_spans) == ("adjusted",)
    assert tuple(item.slice_parts) == ("segment:a",)
    assert item.level_low["scale_multiplier"] == Decimal(1)
    assert item.polarity_proof["polarity"] == "favorable"


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


# ---------------------------------------------------------------------------
# #827 STEP 2 — THE DERIVED COVERAGE LEDGER.
#
# Not a hand-written checklist: the inventory of public inputs and reachable
# outcomes is READ OUT OF THE LIVE CODE every run — signatures, dataclass and
# namedtuple fields, the event-item/text-part key tuples, and the outcome and
# decision vocabularies. Coverage is then measured against the live test
# corpus. Add a public parameter or a reachable outcome without a test that
# names it and this FAILS; that is the whole point, and it is why nothing here
# may be transcribed.
# ---------------------------------------------------------------------------

_REPO_ROOT = __import__('os').path.dirname(__import__('os').path.dirname(
    __import__('os').path.dirname(__import__('os').path.abspath(__file__))))


def _v2_modules():
    """THE SCOPE, spelled ONCE: the four v2 adapter modules the atomic switch
    turns on. Two spellings of one rule are two rules the day one is edited."""
    from driver.core import fact_match, prepared_fact_v2, slot_convert
    from driver.core import xbrl_attach
    return (prepared_fact_v2, slot_convert, fact_match, xbrl_attach)


def _public_input_inventory():
    """{(owner, input): kind} — OWNER-QUALIFIED PAIRS, never collapsed names.

    The first version keyed by NAME alone, so 102 owner/input pairs became 83
    entries and a parameter covered on one owner counted as covered on every
    other. It also filtered by `__module__`, which silently dropped a public
    function added to the module at runtime.
    """
    import inspect

    inventory = {}
    for mod in _v2_modules():
        for name, obj in vars(mod).items():
            if name.startswith("_") or not callable(obj):
                continue
            # OURS = defined in this repository. A symbol imported from the
            # standard library or a third-party package (`dataclass`,
            # `namedtuple`) is not a public input of ours; a symbol defined in
            # ANOTHER of our modules is a re-export owned by its definer. A
            # runtime-added function still counts, which is what the old
            # `__module__ != mod.__name__` filter wrongly dropped.
            import sys as _sys
            home = getattr(obj, "__module__", None)
            if home:
                home_mod = _sys.modules.get(home)
                home_file = getattr(home_mod, "__file__", "") or ""
                if not home_file.startswith(_REPO_ROOT):
                    continue
                if home != mod.__name__:
                    continue        # a re-export belongs to its DEFINER
            owner = f"{mod.__name__}.{name}"
            if inspect.isclass(obj):
                # CLASS FIELDS ARE NOT COUNTED HERE ANY MORE. A field was
                # credited when its NAME appeared as an attribute access
                # ANYWHERE in the test corpus, on any object — so adding a
                # public field called `label` was invisible, because some
                # unrelated test reads some unrelated `.label`. Owner-
                # qualifying it statically is impossible: measured, 47 of 54
                # fields are constructed through `**kwargs` splat, which no
                # AST can attribute to a field. Fields are proven
                # BEHAVIOURALLY instead — see the field test below.
                continue
            try:
                params = inspect.signature(obj).parameters.values()
            except (TypeError, ValueError):
                continue
            for prm in params:
                if prm.kind in (prm.VAR_POSITIONAL, prm.VAR_KEYWORD):
                    continue
                inventory[(owner, prm.name)] = "param"
    # BOUNDARY KEYS are likewise proven behaviourally (the door must refuse an
    # item that omits one or carries an unknown one), not by spotting the same
    # word in some unrelated dict literal.
    return inventory








def test_827_the_PUBLIC_DECISION_VOCABULARY_is_the_contract_s_five_words():
    """A CONTRACT PIN, not a coverage claim — and the right detector for the
    defect the reviewer injected.

    ChannelContract §6 and BUILD §11.4 fix the channel's outcome vocabulary at
    exactly five words. A sixth word is not "an outcome nobody tested"; it is a
    word the channel cannot interpret, so it is a hard contract failure and
    needs no coverage reasoning at all.

    The gate this replaces asked whether each word appeared as a string literal
    anywhere in the test corpus. `deferred` and `quarantined` both do, in
    unrelated tests — so both passed while being emitted by nothing.
    """
    from driver.core.xbrl_attach import PUBLIC_DECISIONS
    assert PUBLIC_DECISIONS == ("written", "merged", "parked", "skipped",
                                "rejected"), (
        "the public decision vocabulary is ChannelContract §6 law — exactly "
        f"these five words in this order; got {PUBLIC_DECISIONS}")


def test_827_every_DECLARED_outcome_class_really_MAPS_to_its_public_row():
    """BEHAVIOUR, generated from the declaration — never a name scan.

    For every (exception class, code) the module declares, a real instance goes
    through the real `_outcome_row`, and the emitted decision and code are
    asserted. A declared class that maps to nothing, or emits a word outside
    the contract, fails here.

    HONEST LIMIT, stated rather than implied: this proves the MAPPING, not that
    the public door reaches every branch. Branch reachability is what the
    temp-copy mutation battery covers, and no static or in-process check here
    should be read as claiming it.
    """
    from driver.core import xbrl_attach as _xa
    from driver.core.prepared_fact_v2 import OUTCOME_CLASSES
    seen = {}
    for cls, code in _xa._DEFAULT_CODES:
        row = _xa._outcome_row(0, cls("probe"))
        assert row["decision"] == OUTCOME_CLASSES[cls], (
            f"{cls.__name__} emitted {row['decision']!r}, not its declared "
            f"{OUTCOME_CLASSES[cls]!r}")
        assert row["codes"] == (code,), (
            f"{cls.__name__} emitted codes {row['codes']}, not ({code!r},)")
        seen[cls] = row["decision"]
    assert set(seen) == set(OUTCOME_CLASSES), (
        "a declared outcome class has no default code, so nothing can emit it: "
        f"{sorted(c.__name__ for c in set(OUTCOME_CLASSES) - set(seen))}")
    # The adapter emits a SUBSET of the contract — it can never write or merge.
    assert set(OUTCOME_CLASSES.values()) <= set(_xa.PUBLIC_DECISIONS)


def test_827_every_public_INPUT_FIELD_is_REALLY_VALIDATED():
    """GENERATED and BEHAVIOURAL: for every public field of every v2 INPUT
    dataclass, a value that is lawful for no field must be REFUSED.

    This replaces the name-matching field rule, which credited a field whenever
    its name appeared as an attribute access anywhere in any test — so adding a
    public field called `label` was invisible, while `zzz_untested_field` was
    caught. Coverage that depends on the spelling you choose is not coverage.

    Measured before it was built: 34 of 35 `PreparedItemV2` fields already
    refused (the 35th was the since-deleted private machinery field, W9 —
    every remaining field is public surface and refuses).
    """
    import dataclasses
    unlawful = object()          # lawful for no field of any of these classes
    item_kw = _item_kwargs(_nested())
    lawful_item = p2.PreparedItemV2(**item_kw)
    cases = [
        (p2.PreparedItemV2, item_kw),
        (p2.PreparedFactV2, dict(fact_type="metric", part_ref="p01",
                                 occurrence_in_part=None, per_x=None,
                                 item=lawful_item)),
        (p2.RunInputV2, dict(source_id="0000006201-26-000031", facts=[])),
    ]
    unchecked = []
    for cls, base in cases:
        for f in dataclasses.fields(cls):
            # THE FIELD IS ALWAYS SUBSTITUTED, never skipped when it is absent
            # from the lawful kwargs. Skipping absent fields would re-open the
            # exact hole: a NEW field with a default is absent from every
            # existing fixture, which is precisely the case that must fail.
            if f.name.startswith("_") or not f.init:
                continue
            probe = dict(base)
            probe[f.name] = unlawful
            try:
                cls(**probe)
            # ONLY THE DECLARED VALIDATION SIGNAL. `except Exception` credited
            # a field whenever ANY error escaped — including a TypeError or an
            # AttributeError from our own code tripping over the sentinel. A
            # crash is not a refusal: it takes the caller down instead of
            # returning a verdict, and counting it as validation is how a
            # programming defect reads as a working guard.
            except p2.SchemaError:
                continue
            unchecked.append(f"{cls.__name__}.{f.name}")
    assert not unchecked, (
        "public input field(s) accept a value that is lawful for no field, so "
        f"nothing validates them: {unchecked}")


def test_827_slot_name_is_a_PUBLIC_parameter_and_reaches_the_message():
    """`slot_name` was named by NO live test — every caller passed it
    positionally — so the coverage ledger reported it, correctly, the first
    time it ran. It is public: callers may pass it by keyword, and the value
    must reach the refusal so a reader knows WHICH slot failed."""
    from decimal import Decimal

    from driver.core.slot_convert import SlotConversionError, validate_slot
    lawful = {"value": Decimal(1), "scale_multiplier": Decimal("1e6"),
              "unit_scale_evidence": "million"}
    validate_slot(slot_name="level_low", slot=lawful, stated_unit="m_usd",
                  quote="revenue of $1 million")          # positive control
    with pytest.raises(SlotConversionError) as exc:
        validate_slot(slot_name="comparison_high",
                      slot={"value": Decimal(1),
                            "scale_multiplier": Decimal("1e9"),
                            "unit_scale_evidence": "billion"},
                      stated_unit="m_usd", quote="revenue of $1 million")
    assert "comparison_high" in str(exc.value), (
        f"the refusal does not say WHICH slot failed: {exc.value}")




def test_827_produced_DUPLICATES_are_reported_not_silently_collapsed():
    """The coverage gate found this: `MatchResult.produced_duplicates` was a
    public result field that NO live test read. Two identical produced facts
    against one gold fact must be reported as a duplicate, never quietly
    counted once — a silent collapse would credit an emit-once violation."""
    g = point(D29_A)
    r = fact_match.match_facts([g], [point(D29_A), point(D29_A)])
    assert r.produced_duplicates, \
        "two identical produced facts were collapsed without a duplicate report"


def test_827_the_KEYWORD_ONLY_public_parameters_are_really_exercised():
    """The coverage gate, once its blanket fallback was deleted, reported SEVEN
    public keyword-only parameters that no test had ever passed:
    `source_id`, `calendar_override`, `lookups` and `home_facts` on
    `to_stored_fact` / `validate_via_production`.

    They are exercised here as REAL CALLS with real values, and each is
    asserted against the default-call result. What this pins honestly is
    acceptance and default-equivalence — that supplying the documented default
    changes nothing, and that a supplied cache is actually consulted. It does
    not claim to pin every parameter's full semantics.
    """
    f = point(Decimal("726"), unit="count")
    base_kw = _stored_kwargs()

    baseline = p2.validate_via_production(f, **base_kw)
    explicit = p2.validate_via_production(
        f, **base_kw, source_id=None, calendar_override=False,
        home_facts=None, lookups=None)
    assert [v.code for v in explicit] == [v.code for v in baseline], (
        "passing the documented defaults explicitly changed the verdict")

    # a real source_id and a real lookups cache, through the same door
    cache: dict = {}
    with_inputs = p2.validate_via_production(
        f, **base_kw, source_id="0000006201-26-000031", lookups=cache)
    assert [v.code for v in with_inputs] == [v.code for v in baseline]

    # and the STORED path takes them too — a different public owner
    stored_default = p2.to_stored_fact(f, **base_kw)
    stored_explicit = p2.to_stored_fact(
        f, **base_kw, source_id=None, calendar_override=False, lookups=None)
    assert stored_default == stored_explicit


# ---------------------------------------------------------------------------
# #827 ROUND 4 — THE RESOLVER'S OWN GUARANTEES, MUTATION-PROVEN.
#
# The reviewer accepted the AST owner-resolution key only on four conditions.
# Each is checked here against a synthetic corpus file, because a guarantee
# that has never been shown to hold is a guarantee unearned.
#
# HIS CORRECTION, RECORDED: I claimed an explicit owner->test-node mapping
# would not split same-named functions. That was WRONG — each row of such a
# table names its owner, so it splits them by construction. The reason to
# prefer resolution is that the table is transcribed and rots on rename, not
# that it fails to disambiguate.
# ---------------------------------------------------------------------------









# ---------------------------------------------------------------------------
# THE COVERAGE LEDGER, AFTER THE HEURISTIC WAS DELETED (#827 round 6)
#
# What was here scanned every `test_*.py` with `ast.walk` and credited a
# parameter because its NAME appeared in a call — including calls that never
# run, since a call inside `if False:` is harvested exactly like a live one.
# It reported coverage it could not observe: a FALSE GREEN.
#
# It is replaced by an EXPLICIT map, written by hand on purpose, and checked in
# BOTH directions against the DERIVED public surface — so a new public callable
# cannot be silently left out, and an entry cannot outlive the callable it
# names. Whether the named test PASSES is the suite's job; this only says which
# test is the one that covers it.
# ---------------------------------------------------------------------------

#: (owner, PARAMETER) -> the test node that covers it. KEYED ON THE PAIR:
#: an owner-only map collapsed 51 pairs into 17 names, so 34 parameters
#: carried no named test while the ledger read as complete.
COVERED_BY = {
    ("driver.core.slot_convert.family_required_multiplier", "unit"):
        "driver/core/test_round12_pure_unit_law.py::test_the_stored_multiplier_is_ONE_for_the_percent_family_and_x",
    ("driver.core.slot_convert.exact_number", "name"):
        "driver/core/test_prepared_fact_v2.py::test_T9_one_public_exact_number_predicate",
    ("driver.core.slot_convert.exact_number", "v"):
        "driver/core/test_prepared_fact_v2.py::test_T9_one_public_exact_number_predicate",
    ("driver.core.fact_match.match_facts", "gold"):
        "driver/core/test_prepared_fact_v2.py::test_G8_per_x_joins_auto_link_equality",
    ("driver.core.fact_match.match_facts", "produced"):
        "driver/core/test_prepared_fact_v2.py::test_G8_per_x_joins_auto_link_equality",
    ("driver.core.fact_match.record_key", "f"):
        "driver/core/test_v2_attacks.py::test_ATTACK_unmatched_output_is_canonically_ordered",
    ("driver.core.prepared_fact_v2.split_slice_part", "token"):
        "driver/core/test_prepared_fact_v2.py::test_G33_first_colon_only_split_keeps_a_colon_in_the_value",
    ("driver.core.prepared_fact_v2.to_stored_fact", "calendar_override"):
        "driver/core/test_v2_attacks.py::test_827_the_KEYWORD_ONLY_public_parameters_are_really_exercised",
    ("driver.core.prepared_fact_v2.to_stored_fact", "driver"):
        "driver/core/test_round11_outcomes.py::test_slot_conversion_failure_is_a_PARK_not_an_escape",
    ("driver.core.prepared_fact_v2.to_stored_fact", "fact"):
        "driver/core/test_round11_outcomes.py::test_slot_conversion_failure_is_a_PARK_not_an_escape",
    ("driver.core.prepared_fact_v2.to_stored_fact", "fye_month"):
        "driver/core/test_round11_outcomes.py::test_slot_conversion_failure_is_a_PARK_not_an_escape",
    ("driver.core.prepared_fact_v2.to_stored_fact", "lookups"):
        "driver/core/test_v2_attacks.py::test_827_the_KEYWORD_ONLY_public_parameters_are_really_exercised",
    ("driver.core.prepared_fact_v2.to_stored_fact", "source"):
        "driver/core/test_round11_outcomes.py::test_slot_conversion_failure_is_a_PARK_not_an_escape",
    ("driver.core.prepared_fact_v2.to_stored_fact", "source_id"):
        "driver/core/test_v2_attacks.py::test_827_the_KEYWORD_ONLY_public_parameters_are_really_exercised",
    ("driver.core.prepared_fact_v2.validate_via_production", "calendar_override"):
        "driver/core/test_v2_attacks.py::test_827_the_KEYWORD_ONLY_public_parameters_are_really_exercised",
    ("driver.core.prepared_fact_v2.validate_via_production", "driver"):
        "driver/core/test_v2_attacks.py::test_827_the_KEYWORD_ONLY_public_parameters_are_really_exercised",
    ("driver.core.prepared_fact_v2.validate_via_production", "fact"):
        "driver/core/test_v2_attacks.py::test_827_the_KEYWORD_ONLY_public_parameters_are_really_exercised",
    ("driver.core.prepared_fact_v2.validate_via_production", "fye_month"):
        "driver/core/test_v2_attacks.py::test_827_the_KEYWORD_ONLY_public_parameters_are_really_exercised",
    ("driver.core.prepared_fact_v2.validate_via_production", "home_facts"):
        "driver/core/test_v2_attacks.py::test_827_the_KEYWORD_ONLY_public_parameters_are_really_exercised",
    ("driver.core.prepared_fact_v2.validate_via_production", "lookups"):
        "driver/core/test_v2_attacks.py::test_827_the_KEYWORD_ONLY_public_parameters_are_really_exercised",
    ("driver.core.prepared_fact_v2.validate_via_production", "source"):
        "driver/core/test_v2_attacks.py::test_827_the_KEYWORD_ONLY_public_parameters_are_really_exercised",
    ("driver.core.prepared_fact_v2.validate_via_production", "source_id"):
        "driver/core/test_v2_attacks.py::test_827_the_KEYWORD_ONLY_public_parameters_are_really_exercised",
    ("driver.core.prepared_fact_v2.verify_occurrence", "occurrence_in_part"):
        "driver/core/test_prepared_fact_v2.py::test_G11_occurrence_is_verified_against_the_part_text",
    ("driver.core.prepared_fact_v2.verify_occurrence", "part_text"):
        "driver/core/test_prepared_fact_v2.py::test_G11_occurrence_is_verified_against_the_part_text",
    ("driver.core.prepared_fact_v2.verify_occurrence", "quote"):
        "driver/core/test_prepared_fact_v2.py::test_G11_occurrence_is_verified_against_the_part_text",
    ("driver.core.slot_convert.assert_storable", "value"):
        "driver/core/test_round12_exact_scale.py::test_the_storable_bound_matches_the_owner_contract",
    ("driver.core.slot_convert.convert_slot", "slot"):
        "driver/core/test_prepared_fact_v2.py::test_G1_driver_name_changes_nothing",
    ("driver.core.slot_convert.convert_slot", "stated_unit"):
        "driver/core/test_prepared_fact_v2.py::test_G1_driver_name_changes_nothing",
    ("driver.core.slot_convert.exact_mul", "a"):
        "driver/core/test_v2_attacks.py::test_ATTACK_exact_mul_precision_comes_from_the_operands",
    ("driver.core.slot_convert.exact_mul", "b"):
        "driver/core/test_v2_attacks.py::test_ATTACK_exact_mul_precision_comes_from_the_operands",
    # S14: the two exact_scaleb rows repointed — their old owner (the
    # 29-digit xbrl-scaling attack) was deleted with the dead helper.
    ("driver.core.slot_convert.exact_scaleb", "exponent"):
        "driver/core/test_v2_attacks.py::test_ATTACK_a_fractional_scale_is_never_silently_truncated",
    ("driver.core.slot_convert.exact_scaleb", "value"):
        "driver/core/test_v2_attacks.py::test_ATTACK_a_fractional_scale_is_never_silently_truncated",
    ("driver.core.slot_convert.stored_char_length", "value"):
        "driver/core/test_round12_exact_scale.py::test_the_storable_bound_matches_the_owner_contract",
    ("driver.core.slot_convert.validate_slot", "xbrl_backed"):
        "driver/core/test_prepared_fact_v2.py::test_G22_the_xbrl_lane_does_not_require_quote_local_evidence",
    ("driver.core.slot_convert.validate_slot", "quote"):
        "driver/core/test_prepared_fact_v2.py::test_G5_slot_structure_failures",
    ("driver.core.slot_convert.validate_slot", "slot"):
        "driver/core/test_prepared_fact_v2.py::test_G5_slot_structure_failures",
    ("driver.core.slot_convert.validate_slot", "slot_name"):
        "driver/core/test_prepared_fact_v2.py::test_G5_slot_structure_failures",
    ("driver.core.slot_convert.validate_slot", "stated_unit"):
        "driver/core/test_prepared_fact_v2.py::test_G5_slot_structure_failures",
    ("driver.core.xbrl_attach.attach_event_xbrl", "filing_provider"):
        "driver/relocation/test_packet_items_through_the_door.py::test_every_saved_packet_item_attaches_on_its_LITERAL_evidence",
    ("driver.core.xbrl_attach.attach_event_xbrl", "items"):
        "driver/relocation/test_packet_items_through_the_door.py::test_every_saved_packet_item_attaches_on_its_LITERAL_evidence",
    ("driver.core.xbrl_attach.attach_event_xbrl", "menu_tokens"):
        "driver/core/test_round15_audit_evidence.py::test_825_an_empty_frozenset_is_lawful_it_is_not_a_missing_menu",
    ("driver.core.xbrl_attach.attach_event_xbrl", "source_id"):
        "driver/relocation/test_packet_items_through_the_door.py::test_every_saved_packet_item_attaches_on_its_LITERAL_evidence",
    ("driver.core.xbrl_attach.attach_event_xbrl", "store"):
        "driver/relocation/test_packet_items_through_the_door.py::test_every_saved_packet_item_attaches_on_its_LITERAL_evidence",
    ("driver.core.xbrl_attach.attach_event_xbrl", "text_parts"):
        "driver/relocation/test_packet_items_through_the_door.py::test_every_saved_packet_item_attaches_on_its_LITERAL_evidence",
    # THE POLICY NOW TAKES ONLY IDENTITY. Its three old inputs — `unit_name`,
    # `is_divide` and the raw `numerator` — are gone: the first was the graph's
    # prefixed spelling (which decided which alias a filer typed, not which
    # currency they declared), and the divide branch is read from the shape of
    # the verified evidence instead of a flag a caller could contradict.
    ("driver.core.xbrl_attach.candidate_units_for", "measures_expanded"):
        "driver/core/test_unit_identity_expanded.py::test_the_SAME_TEXT_under_a_DIFFERENT_URI_is_not_dollars",
    ("driver.core.xbrl_attach.candidate_units_for", "numerator_expanded"):
        "driver/core/test_unit_identity_expanded.py::test_a_DIVIDE_numerator_under_a_FOREIGN_URI_is_not_dollars",
    ("driver.core.xbrl_attach.expected_multiplier", "ix_scale"):
        "driver/relocation/test_real_726_end_to_end.py::test_real_USD_shares_and_EPS_through_the_COMPLETE_core_path",
    ("driver.core.xbrl_attach.expected_multiplier", "level_unit"):
        "driver/relocation/test_real_726_end_to_end.py::test_real_USD_shares_and_EPS_through_the_COMPLETE_core_path",
}


def test_827R6_every_public_callable_NAMES_the_test_that_covers_it():
    """BOTH DIRECTIONS, against the DERIVED surface — an entry that outlives its
    callable is as wrong as a callable with no entry."""
    public = set(_public_input_inventory())
    uncovered = sorted(public - set(COVERED_BY))
    stale = sorted(set(COVERED_BY) - public)
    assert not uncovered, f"public (owner, parameter) named by no test: {uncovered}"
    assert not stale, f"ledger entries whose pair no longer exists: {stale}"


def test_827R6_every_named_test_node_really_exists():
    """A ledger pointing at a test that is not there is worse than no ledger.
    Checked on disk, so it holds in the clean lane and the live lane alike."""
    import ast as _ast
    import os as _os
    missing = []
    for (owner, param), node in sorted(COVERED_BY.items()):
        path, _, func = node.partition("::")
        full = _os.path.join(_REPO_ROOT, path)
        if not _os.path.exists(full):
            missing.append(f"{owner}({param}) -> missing file {path}")
            continue
        names = {n.name for n in _ast.walk(_ast.parse(open(full, encoding="utf-8").read()))
                 if isinstance(n, _ast.FunctionDef)}
        if func not in names:
            missing.append(f"{owner}({param}) -> {path} has no {func}")
    assert not missing, missing


def test_W9_the_verified_bundle_boundary_is_static_and_singular():
    """W9: the runtime attach sentinel is DELETED; the boundary is proven
    STATICALLY over every non-test module under driver/. Three live facts:
      1. production constructs PreparedItemV2 in exactly ONE place — inside
         PreparedFactV2._build;
      2. exactly ONE production caller hands _build a non-None bundle — the
         verified attach path (xbrl_attach);
      3. from_dict always calls _build with None.
    The matcher resolves ordinary aliases (import X as Y / from M import X
    as Y) before matching, and its own alias-shaped mutant (an in-memory
    module using BOTH alias forms) must report both plants — a matcher that
    cannot see aliases proves nothing."""
    import ast, os

    def scan(source, relname):
        """(constructor-call sites, non-None _build-call sites) with aliases
        resolved for PreparedItemV2 / PreparedFactV2 / their module."""
        tree = ast.parse(source)
        ctor_names, mod_aliases, fact_aliases = set(), set(), set()
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom):
                for a in n.names:
                    if a.name == "PreparedItemV2":
                        ctor_names.add(a.asname or a.name)
                    if a.name == "PreparedFactV2":
                        fact_aliases.add(a.asname or a.name)
                    if n.module and n.module.endswith("prepared_fact_v2") \
                            and a.name == "prepared_fact_v2":
                        mod_aliases.add(a.asname or a.name)
            elif isinstance(n, ast.Import):
                for a in n.names:
                    if a.name.endswith("prepared_fact_v2"):
                        mod_aliases.add(a.asname or a.name.split(".")[0])
        if relname.endswith("prepared_fact_v2.py"):
            ctor_names.add("PreparedItemV2")
            fact_aliases.add("PreparedFactV2")
        ctors, builds = [], []
        for n in ast.walk(tree):
            if not isinstance(n, ast.Call):
                continue
            f = n.func
            if isinstance(f, ast.Name) and f.id in ctor_names:
                ctors.append((relname, n.lineno))
            elif isinstance(f, ast.Attribute):
                v = f.value
                if f.attr == "PreparedItemV2" and isinstance(v, ast.Name) \
                        and v.id in mod_aliases:
                    ctors.append((relname, n.lineno))
                elif f.attr == "_build":
                    owner_ok = (isinstance(v, ast.Name)
                                and (v.id in fact_aliases or v.id == "cls"
                                     or v.id in mod_aliases)) or \
                               (isinstance(v, ast.Attribute)
                                and v.attr == "PreparedFactV2")
                    if owner_ok and not (len(n.args) >= 2
                                         and isinstance(n.args[1], ast.Constant)
                                         and n.args[1].value is None):
                        builds.append((relname, n.lineno))
        return ctors, builds

    # THE MUTANT CONTROL: both alias forms planted; the matcher must see both.
    plant = (
        "from driver.core.prepared_fact_v2 import PreparedItemV2 as Item\n"
        "from driver.core import prepared_fact_v2 as pf2\n"
        "def a():\n    return Item(x=1)\n"
        "def b():\n    return pf2.PreparedFactV2._build({}, {'k': 1})\n")
    pc, pb = scan(plant, "plant.py")
    assert len(pc) == 1 and len(pb) == 1, (pc, pb)

    # THE REAL TREE: every non-test module under driver/, hidden-inclusive.
    root = os.path.join(os.path.dirname(os.path.abspath(p2.__file__)), "..")
    ctors, builds = [], []
    for dirpath, _dirs, files in os.walk(os.path.normpath(root)):
        for fn in files:
            if not fn.endswith(".py") or fn.startswith("test_"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn),
                                  os.path.normpath(root))
            src = open(os.path.join(dirpath, fn), encoding="utf-8").read()
            c, b = scan(src, rel)
            ctors += c
            builds += b
    assert len(ctors) == 1 and ctors[0][0].endswith("prepared_fact_v2.py"), ctors
    assert len(builds) == 1 and builds[0][0].endswith("xbrl_attach.py"), builds
    # fact 3: from_dict's own call passes the literal None (excluded above),
    # so it is absent from `builds` BY the matcher's non-None filter — and the
    # sentinel machinery itself is gone:
    import inspect
    src = inspect.getsource(p2)
    assert "_ATTACH_TOKEN" not in src and "_attach_token" not in src
