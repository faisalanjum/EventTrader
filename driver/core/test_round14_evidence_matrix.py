"""#824 — the filing-evidence attack matrix.

The audit's required RED-first battery for the four-key `source_evidence`: the
pure structural boundary (zero I/O), then the prepared-document attacks, then
lawful synthetic positive controls.

DISCIPLINE FOR THIS FILE. Lawful evidence is built once from the fixture owner
and then EXACTLY ONE field is perturbed, so every refusal below is attributable
to the thing named in the test and not to some earlier gate. Where the subject
under test IS the evidence builder or the canonical comparison, the expected
value is stated as an independent literal — never recomputed from the builder,
which would let the builder vouch for itself.
"""
from decimal import Decimal

import pytest

from driver.core.prepared_fact_v2 import SchemaError
from driver.core.test_round10_event_boundary import (_ACC, _DOOR_DOC, _Counting,
                                                     _CountingProvider,
                                                     _XMLNS, _door_item,
                                                     _door_row,
                                                     parts_for)
from driver.core.xbrl_attach import _default_outcome, attach_event_xbrl
from driver.relocation.inline_html import SOURCE_EVIDENCE_KEYS, prepare
from driver.core.driver_neo4j_adapter import GraphFactRows

# The document's own text, stated independently of any evidence the builder
# produces. Every expectation below is anchored to these literals.
_TEXT = prepare(_DOOR_DOC)["text"]
assert _TEXT[45:52] == "726 726", _TEXT
assert len(_TEXT) == 52, len(_TEXT)


# THE bad-span data, defined ONCE. Every span in the contract obeys the same
# exact-span law, so the quote span, the label span and a piece span are all
# tested with this same list rather than three drifting copies.


# THE SPAN FORMS, SPLIT BY THE RULE EACH ONE BREAKS. These replaced a single
# `_BAD_SPANS` list that lumped three separate laws together, so a test over it
# could only assert "something refused it" and a wrong-reason mutation passed.
# Each family carries the fragment of the message that names ITS law.
_SPAN_NOT_A_PAIR = [None, [], [1], [1, 2, 3], (1,), "45,52",
                    {"start": 45, "end": 52}]
_SPAN_NOT_EXACT_INTS = [[45.0, 52], [45, 52.0], [True, 52], [45, True],
                        [Decimal(45), 52], [45, Decimal(52)], ["45", "52"],
                        [None, 52], [45, None]]
_SPAN_OUT_OF_RANGE = [[52, 45], [45, 45], [-1, 52], [45, -2]]


def _span_cases(field):
    """(form, reason-fragment) for every malformed span form, for one field."""
    return ([(b, f"{field} must be exactly [start, end]")
             for b in _SPAN_NOT_A_PAIR] +
            [(b, f"{field} endpoints must be exact integers")
             for b in _SPAN_NOT_EXACT_INTS] +
            [(b, f"{field} must satisfy 0 <= start < end")
             for b in _SPAN_OUT_OF_RANGE])


def _run(item, store=None, provider=None):
    return attach_event_xbrl([item], source_id=_ACC,
                             store=store if store is not None else _Counting(),
                             filing_provider=(provider if provider is not None
                                              else _CountingProvider()),
                             text_parts=parts_for([item]))


def _perturbed(**evidence_fields):
    """A lawful door item with EXACTLY the named evidence fields replaced."""
    return _door_item("us-gaap:A", "fA", **evidence_fields)


# ---- the TWO local checkers every test below uses --------------------------
#
# ONE for success, ONE for refusal, so every assertion in this file states the
# same complete set of facts and none can quietly check less than its neighbour.

def _attached(res):
    """A SUCCESS: exactly one fact, at its ORIGINAL index, and NO outcome row.
    The old bare list could not say the second part — a silently parked item and
    an empty list were the same value."""
    assert res.preflight_outcomes == (), [dict(o) for o in res.preflight_outcomes]
    assert [i for i, _f in res.facts] == [0]
    return res.facts[0][1]


def _refused_purely(item, why):
    """A PURE refusal: the item is refused AND the event reads nothing at all.

    ALL FOUR reads the door can make are counted — representation count, filing
    fetch, company CIK, concept rows. Only the first two were checked, on 30 of
    the 52 structural cases, so an injected CIK read or concept-row read stayed
    green on every one of them and was invisible on the other 22.
    """
    store, provider = _Counting(), _CountingProvider()
    row = _refused(_run(item, store, provider), SchemaError, why)
    assert (store.representation, store.cik, store.row_reads,
            provider.fetches) == (0, 0, [], 0), \
        "a structural refusal must cost NO I/O of any kind"
    return row


def _refused(res, exc_class, needle):
    """An ITEM-LOCAL refusal: exactly ONE indexed row, whose decision and code
    are derived from the exception class the ORIGINAL test named, through the
    same production owner the door uses. That is NOT self-proving on its own —
    it reads production to decide what production should say. What makes it
    sound is that the class-to-decision-and-code mapping is pinned INDEPENDENTLY
    in the round-15 matrix, against the contract's five words and the registered
    CLI codes; this helper then only has to agree with it.

    The reason must contain the fragment belonging to THE RULE UNDER TEST: a
    bare `SchemaError` check passes for any of forty other reasons."""
    want_decision, want_code = _default_outcome(exc_class("probe"))
    assert res.facts == (), "a refused item must attach nothing"
    assert len(res.preflight_outcomes) == 1, \
        [dict(o) for o in res.preflight_outcomes]
    row = res.preflight_outcomes[0]
    assert (row["index"], row["decision"], row["codes"]) == \
        (0, want_decision, (want_code,))
    assert needle in row["detail"], row["detail"]
    return row


# ---- 1. THE PURE STRUCTURAL BOUNDARY — refused with ZERO I/O ---------------

@pytest.mark.parametrize("bad", [
    "a" * 63, "a" * 65, "A" * 64, " " + "a" * 63, "a" * 63 + " ",
    "g" * 64, None, 64, b"a" * 64, "",
])
def test_matrix_a_malformed_representation_hash_is_refused(bad):
    _refused_purely(_perturbed(representation_sha256=bad),
                    "expected a 64-character lowercase hex sha256")


@pytest.mark.parametrize("bad,why", _span_cases("quote_span"))
def test_matrix_b_malformed_quote_span_is_refused(bad, why):
    _refused_purely(_perturbed(quote_span=bad), why)


def test_matrix_b_a_custom_int_SUBCLASS_endpoint_is_refused():
    """RESTORED after I wrongly cut it as redundant.

    My argument was that `bool` is already parametrized and both forms take the
    same `type(v) is not int` branch, so a second subclass proved nothing. That
    does not survive mutation: a guard rewritten to reject `bool` EXPLICITLY and
    fall back to `isinstance` for everything else leaves all the other tests
    green — verified. One guard line does not mean one input class, and reading
    the source is not a substitute for breaking it.

    An int subclass may carry any behaviour it likes; a character offset is an
    `int` and nothing else.
    """
    class Sneaky(int):
        pass

    _refused_purely(_perturbed(quote_span=[Sneaky(45), 52]),
                    "quote_span endpoints must be exact integers")


@pytest.mark.parametrize("bad", [
    [0, 100], [44, 52], [45, 53], [0, 1],
])
def test_matrix_b_a_label_span_outside_its_quote_is_refused(bad):
    """A label that does not lie inside its own quote describes a different
    place in the filing, whatever else is true of it."""
    _refused_purely(_perturbed(raw_label_span=bad),
                    "raw_label_span must lie INSIDE quote_span")


@pytest.mark.parametrize("bad", [
    "pieces", {"kind": "header"}, 5, None,
])
def test_matrix_c_a_non_container_pieces_value_is_refused(bad):
    _refused_purely(_perturbed(pieces=bad),
                    "source_evidence pieces must be a list or tuple")


_PIECE_KEYS_MSG = ("each evidence piece carries EXACTLY the keys "
                   "('kind', 'text', 'span')")


@pytest.mark.parametrize("bad,why", [
    ([{"kind": "header", "text": "x"}], _PIECE_KEYS_MSG),          # no span
    ([{"kind": "header", "span": [45, 52]}], _PIECE_KEYS_MSG),     # no text
    ([{"text": "x", "span": [45, 52]}], _PIECE_KEYS_MSG),          # no kind
    ([{"kind": "header", "text": "x", "span": [45, 52], "z": 1}],
     _PIECE_KEYS_MSG),                                             # extra key
    ([{"kind": "footer", "text": "x", "span": [45, 52]}],     # kind off the enum
     "evidence piece kind is one of"),
    ([{"kind": "HEADER", "text": "x", "span": [45, 52]}],     # case is not it
     "evidence piece kind is one of"),
    ([{"kind": "header", "text": "", "span": [45, 52]}],      # blank text
     "each evidence piece needs non-blank string text"),
    ([{"kind": "header", "text": "   ", "span": [45, 52]}],   # whitespace text
     "each evidence piece needs non-blank string text"),
    ([{"kind": "header", "text": 5, "span": [45, 52]}],       # non-string text
     "each evidence piece needs non-blank string text"),
    ([{"kind": "header", "text": "x", "span": [52, 45]}],     # reversed span
     "an evidence piece span must satisfy 0 <= start < end, got [52, 45]"),
    (["not-a-mapping"], _PIECE_KEYS_MSG),
])
def test_matrix_c_a_malformed_evidence_piece_is_refused(bad, why):
    _refused_purely(_perturbed(pieces=bad), why)


def test_matrix_c_duplicate_identical_pieces_are_REFUSED_not_collapsed():
    """Collapsing would make the claim and the filing agree by editing the
    claim, which is the one repair a verifier may never perform."""
    piece = {"kind": "header", "text": "726 726", "span": [45, 52]}
    _refused_purely(_perturbed(pieces=[piece, dict(piece)]),
                    "duplicate identical evidence pieces are refused")


def test_matrix_d_the_caller_cannot_mutate_evidence_after_entry():
    """The filing provider is caller-supplied code that runs AFTER the pure
    checks — the #823 time-of-check/time-of-use lesson, on the new input."""
    item = _door_item("us-gaap:A", "fA")

    class Hostile(_CountingProvider):
        def get_filing_document(self, s):
            item["source_evidence"]["quote_span"] = [0, 1]
            item["source_evidence"]["pieces"].append(
                {"kind": "section", "text": "invented", "span": [0, 1]})
            return super().get_filing_document(s)

    _attached(_run(item, provider=Hostile()))


# ---- 2. THE PREPARED-DOCUMENT ATTACKS -------------------------------------

@pytest.mark.parametrize("span,why", [
    ([44, 52], "does not describe the bound element"),
    ([46, 52], "does not describe the bound element"),
    ([45, 51], "does not describe the bound element"),
    # THIS ONE IS A DIFFERENT LAW, and lumping it hid that: the lawful quote ends
    # at the last character of the representation, so +1 at the end runs off the
    # document and the earlier bounds check fires instead of the element match.
    ([45, 53], "the submitted quote_span ends beyond the representation"),
])
def test_matrix_e_a_quote_span_shifted_by_one_either_way_is_refused(span, why):
    """Off by a single character in either direction, at either end."""
    _refused(_run(_perturbed(quote_span=span)), SchemaError, why)


def test_matrix_e_a_stale_but_WELL_FORMED_hash_is_refused():
    """64 lowercase hex, structurally perfect, and not this document's."""
    _refused(_run(_perturbed(representation_sha256="b" * 64)), SchemaError,
             "does not hash to the representation")


def test_matrix_e_a_piece_whose_text_is_not_at_its_span_is_refused():
    _refused(_run(_perturbed(pieces=[{"kind": "header", "text": "Not there",
                                      "span": [45, 52]}])), SchemaError,
             "is not the text at its own span")


def test_matrix_e_an_ADDED_piece_the_element_does_not_have_is_refused():
    """The canonical evidence for this element has no pieces; an extra one is
    a claim the filing does not make."""
    _refused(_run(_perturbed(pieces=[{"kind": "section", "text": "726 726",
                                      "span": [45, 52]}])), SchemaError,
             "the submitted evidence pieces differ from the bound element's own")


def test_matrix_e_a_correct_looking_span_at_the_WRONG_place_is_refused():
    """`726` appears twice; citing the second occurrence as the quote is
    well-formed, reproduces real text, and is still not this element's row."""
    assert _TEXT[49:52] == "726"
    _refused(_run(_perturbed(quote_span=[49, 52])), SchemaError,
             "does not describe the bound element")


# ---- 3. POSITIVE CONTROLS — the gate must not refuse everything ------------

def test_matrix_f_the_lawful_item_attaches_and_carries_its_evidence():
    """Also carries the LAWFUL-NULL label case, which was a separate test.

    Null is the approved form when no structural label exists, and this prose
    block genuinely has none — so the lawful item ALREADY submits
    `raw_label_span: None`. The separate test "overrode" it to None, producing
    byte-identical evidence: a no-op that proved nothing this test did not.
    It is an assertion on the submitted item, which is what it always was.

    The other half of that distinction — null is NOT lawful on an element that
    HAS a structural label — is pinned on the table cell in section 5, so a
    malformed span still cannot pass as an approved null.
    """
    item = _door_item("us-gaap:A", "fA")
    assert item["source_evidence"]["raw_label_span"] is None, \
        "the prose block has no structural label, so null is the lawful form"
    fact = _attached(_run(item))
    assert fact.item.quote == _TEXT[45:52] == "726 726"


def test_matrix_f_a_second_element_on_the_same_row_also_attaches():
    """Two facts lawfully share one row text and one span — the CE control's
    shape in miniature. Neither may be refused for sharing."""
    _attached(_run(_door_item("us-gaap:B", "fB")))


# THE SAME DOOR DOCUMENT with its one block tag swapped for an inline `span`.
# Nothing else changes, so anything this fixture reaches that `_DOOR_DOC` does
# not is attributable to the OWNER of the fact and to nothing else.
_SPAN_DOC = _DOOR_DOC.replace("<p>", "<span>").replace("</p>", "</span>")
# THE PREMISE, asserted on the fixture itself rather than on the rule under
# test: the document contains no table or block tag ANYWHERE, so the bound
# element cannot have a `td`/`th` or `p`/`li`/`div` ancestor and its owner can
# only be the inline `span` holding it.
assert "<span>" in _SPAN_DOC and not any(
    t in _SPAN_DOC for t in ("<p>", "<li", "<div", "<td", "<th", "<tr")), _SPAN_DOC


def test_matrix_f_a_fact_owned_only_by_a_SPAN_attaches_through_the_door():
    """THE MUST-ALLOW twin of matrix-k, through the real Core door.

    Filings do not all wrap their facts in a table cell or a `p`/`li`/`div`.
    When the nearest owner is an inline `span` the element is still perfectly
    visible and perfectly locatable, so the door must ATTACH it. Until the
    direct-parent owner existed, the walker recorded no span for that parent,
    the evidence builder returned None, and this lawful fact parked exactly like
    matrix-k's genuinely undescribable one — the door losing a real fact over a
    formatting choice. Matrix-k pins the refusal; this pins the permission, and
    neither is sound without the other.
    """
    class P(_CountingProvider):
        def get_filing_document(self, s):
            return _SPAN_DOC

    item = _door_item("us-gaap:A", "fA", doc=_SPAN_DOC)
    fact = _attached(attach_event_xbrl([item], source_id=_ACC, store=_Counting(),
                                       filing_provider=P(),
                                       text_parts=parts_for([item])))
    # the SAME quote the block-owned fixture yields, stated as a literal
    assert fact.item.quote == "726 726"


def test_matrix_g_character_offsets_not_byte_offsets():
    """A multi-byte character before the quote moves the BYTE offset but not
    the CHARACTER offset. Spans are Python string indices; if any of this were
    computed on UTF-8 bytes, the lawful span below would miss."""
    doc = _DOOR_DOC.replace("<p>", "<p>€ éé ")
    text = prepare(doc)["text"]
    # The quote is the whole BLOCK, multi-byte characters and all — stated as a
    # literal, not recomputed from the builder.
    item = _door_item("us-gaap:A", "fA", doc=doc)
    q0, q1 = item["source_evidence"]["quote_span"]
    assert text[q0:q1] == "€ éé 726 726"
    # THE POINT: the end offset counts CHARACTERS. On UTF-8 bytes the same
    # prefix is longer, so a byte-based span would slice somewhere else.
    assert len(text[:q1].encode("utf-8")) > q1, "no multi-byte content in range"

    class P(_CountingProvider):
        def get_filing_document(self, s):
            return doc

    fact = _attached(attach_event_xbrl(
        [item], source_id=_ACC, store=_Counting(), filing_provider=P(),
        text_parts=parts_for([item])))
    assert fact.item.quote == "€ éé 726 726"


# ---- 4. THE NORMALISED RESULT IS ITSELF IMMUTABLE -------------------------

def test_matrix_h_the_normalised_evidence_is_a_READ_ONLY_mapping():
    """The door's normalised evidence claimed to be an immutable copy. Its
    CONTENTS were isolated from the caller — which is why the mutation test
    passed — but the outer object was a plain `dict`, writable by anything
    holding it during the I/O phase. Isolation and immutability are two
    different properties and this file now pins both."""
    from types import MappingProxyType

    from driver.core.test_round10_event_boundary import filing_evidence
    from driver.core.xbrl_attach import _checked_source_evidence
    submitted, _quote = filing_evidence(_DOOR_DOC, "fA")
    normalised = _checked_source_evidence(submitted)
    assert isinstance(normalised, MappingProxyType)
    for key, value in (("representation_sha256", "a" * 64),
                       ("quote_span", (0, 1)), ("pieces", ()),
                       ("raw_label_span", None), ("invented", 1)):
        with pytest.raises(TypeError):
            normalised[key] = value


def test_matrix_h_the_caller_object_is_not_the_one_carried_forward():
    """Isolation, proved separately from immutability: editing what the caller
    still holds cannot reach the normalised value."""
    from driver.core.test_round10_event_boundary import filing_evidence
    from driver.core.xbrl_attach import _checked_source_evidence
    submitted, _quote = filing_evidence(_DOOR_DOC, "fA")
    normalised = _checked_source_evidence(submitted)
    submitted["quote_span"] = [0, 1]
    submitted["pieces"] = [{"kind": "section", "text": "x", "span": [0, 1]}]
    assert tuple(normalised["quote_span"]) == (45, 52)
    assert normalised["pieces"] == ()


# THE TWO REASONS THE PIECE ROUTE CAN GIVE, named once. The first fires when the
# submitted piece SET is not the element's own; the second when the set matches
# but a piece's text is not the text at its own span. They are different rules.
_DIFFER = "the submitted evidence pieces differ from the bound element's own"
_NOT_AT_SPAN = "is not the text at its own span"


# ---- 5. A LAWFUL MULTI-PIECE TABLE, and the mutations it makes reachable ---
#
# The synthetic door document is a prose block with ZERO pieces, so it could
# not reach piece deletion, reordering, rewording, re-kinding, re-spanning, a
# sibling-column swap, a whole-evidence swap between elements, or two identical
# quote strings at different structural spans. This table supplies all of them:
# two elements share one row and one section but have DIFFERENT column headers,
# and the row below repeats the same text at a different span.

_TABLE_DOC = (
    f'<html {_XMLNS}><body><ix:header><ix:resources><xbrli:context id="c1"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">'
    '0000320193</xbrli:identifier></xbrli:entity><xbrli:period>'
    '<xbrli:startDate>2024-01-01</xbrli:startDate><xbrli:endDate>'
    '2024-06-30</xbrli:endDate></xbrli:period></xbrli:context></ix:resources></ix:header>'
    '<ix:header><ix:resources><xbrli:unit id="u1"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit></ix:resources></ix:header>'
    '<table>'
    '<tr><td>Segment detail</td></tr>'
    '<tr><td></td><td>Three months</td><td>Six months</td></tr>'
    '<tr><td>North America</td>'
    '<td><ix:nonFraction id="t1" name="us-gaap:A" contextRef="c1" unitRef="u1"'
    ' scale="6" decimals="-6">726</ix:nonFraction></td>'
    '<td><ix:nonFraction id="t2" name="us-gaap:A" contextRef="c1" unitRef="u1"'
    ' scale="6" decimals="-6">726</ix:nonFraction></td></tr>'
    '<tr><td>North America</td>'
    '<td><ix:nonFraction id="t3" name="us-gaap:A" contextRef="c1" unitRef="u1"'
    ' scale="6" decimals="-6">726</ix:nonFraction></td>'
    '<td><ix:nonFraction id="t4" name="us-gaap:A" contextRef="c1" unitRef="u1"'
    ' scale="6" decimals="-6">726</ix:nonFraction></td></tr>'
    '</table></body></html>')
_TABLE_TEXT = prepare(_TABLE_DOC)["text"]


class _TableStore:
    def __init__(self, fact_id):
        self._id = fact_id

    def get_xbrl_representation_count(self, s):
        return 1

    def get_source_company_cik(self, s):
        return "0000320193"

    def get_xbrl_fact_dimensions(self, s, c):
        # THE SHARED ROW OWNER, not a second hand-written copy. This dict had
        # drifted into a duplicate of `_door_row`, so a new required column had
        # to be added in two places — which is exactly how one of them goes
        # stale. `_door_row` also carries the concept identity the binder needs.
        return GraphFactRows(rows=[_door_row(self._id, concept=c)],
                             exclusions=())


class _TableProvider:
    def get_filing_document(self, s):
        return _TABLE_DOC


def _table_item(fact_id="t1", **evidence_fields):
    from decimal import Decimal

    from driver.core.prepared_fact_v2 import ITEM_FIELDS
    from driver.core.test_round10_event_boundary import filing_evidence
    evidence, quote = filing_evidence(_TABLE_DOC, fact_id, **evidence_fields)
    slot = {"value": Decimal("726"), "scale_multiplier": Decimal(10) ** 6,
            "unit_scale_evidence": None}
    it = {k: None for k in ITEM_FIELDS}
    it.update(driver_name="thing", driver_state="reported", quote=quote,
              measurement_raw_spans=[], slice_parts=[], level_unit="usd",
              level_low=dict(slot), level_high=dict(slot), time_type="duration",
              period_start_date="2024-01-01", period_end_date="2024-06-30")
    return {"fact": {"fact_type": "metric", "part_ref": fact_id,
                     "occurrence_in_part": None, "per_x": None, "item": it},
            "concept": "us-gaap:A", "member_refs": [],
            "source_evidence": evidence}


def _run_table(item, fact_id="t1"):
    return attach_event_xbrl([item], source_id=_ACC, store=_TableStore(fact_id),
                             filing_provider=_TableProvider(),
                             text_parts=parts_for([item]))


def _pieces_of(fact_id):
    """The element's OWN pieces, read once so a mutation can start from them."""
    from driver.core.test_round10_event_boundary import filing_evidence
    return [dict(p) for p in filing_evidence(_TABLE_DOC, fact_id)[0]["pieces"]]


def test_matrix_i_the_table_fixture_is_lawful_and_MULTI_piece():
    """The premise every mutation below rests on, asserted against independent
    literals rather than against the builder's own output."""
    item = _table_item("t1")
    ev = item["source_evidence"]
    assert _TABLE_TEXT[ev["quote_span"][0]:ev["quote_span"][1]] \
        == "North America 726 726"
    assert _TABLE_TEXT[ev["raw_label_span"][0]:ev["raw_label_span"][1]] \
        == "North America"
    assert [(p["kind"], p["text"]) for p in ev["pieces"]] == \
        [("header", "Three months"), ("section", "Segment detail")]
    _attached(_run_table(item))


@pytest.mark.parametrize("mutate,label,why", [
    (lambda p: p[:1], "a piece DELETED", _DIFFER),
    (lambda p: list(reversed(p)), "the pieces REORDERED", _DIFFER),
    (lambda p: [{**p[0], "kind": "section"}] + p[1:], "a piece RE-KINDED", _DIFFER),
    (lambda p: p + [{"kind": "header", "text": "Six months", "span": [73, 83]}],
     "a sibling column's header ADDED", _DIFFER),
    # These two keep the piece SET intact, so the set comparison passes and the
    # text-at-its-own-span rule is what catches them. One fragment for all six
    # would have let either rule stand in for the other.
    (lambda p: [{**p[0], "text": "Three Months"}] + p[1:], "a piece REWORDED",
     _NOT_AT_SPAN),
    (lambda p: [{**p[0], "span": [p[1]["span"][0], p[1]["span"][1]]}] + p[1:],
     "a piece RE-SPANNED to another piece's offsets", _NOT_AT_SPAN),
])
def test_matrix_i_every_piece_mutation_is_refused(mutate, label, why):
    _refused(_run_table(_table_item("t1", pieces=mutate(_pieces_of("t1")))),
             SchemaError, why)


def test_matrix_i_a_SIBLING_COLUMNS_header_cannot_stand_for_this_fact():
    """t1 and t2 share the row, the label and the section; only the period
    header separates them. Swapping it is well-formed, reproduces real filing
    text at real offsets, and describes the OTHER column's fact."""
    theirs = _pieces_of("t2")
    assert [(p["kind"], p["text"]) for p in theirs] == \
        [("header", "Six months"), ("section", "Segment detail")]
    _refused(_run_table(_table_item("t1", pieces=theirs)), SchemaError, _DIFFER)


def test_matrix_i_a_COMPLETE_evidence_swap_between_elements_is_refused():
    """SWAPPED FROM t3, NOT t2. t1 and t2 differ ONLY in `pieces` — verified
    field by field — so a "complete" swap with t2 submitted exactly what the
    sibling-header test already submits, and proved the same rule twice under
    two names. t3 differs in `quote_span` AND `raw_label_span`, so this is a
    genuinely whole-evidence swap and the element match is what refuses it."""
    from driver.core.test_round10_event_boundary import filing_evidence
    other, _q = filing_evidence(_TABLE_DOC, "t3")
    _refused(_run_table(_table_item("t1", **{k: other[k] for k in other})),
             SchemaError, "does not describe the bound element")


def test_matrix_i_identical_quote_TEXT_at_a_DIFFERENT_span_is_refused():
    """The row below repeats the same characters. Citing its span for this
    element is a perfect-looking claim about the wrong row."""
    from driver.core.test_round10_event_boundary import filing_evidence
    lower, _q = filing_evidence(_TABLE_DOC, "t3")
    upper = _table_item("t1")["source_evidence"]
    a, b = lower["quote_span"]
    c, d = upper["quote_span"]
    assert _TABLE_TEXT[a:b] == _TABLE_TEXT[c:d] and (a, b) != (c, d)
    # The lower row's quote sits BELOW this element's own label, so the earliest
    # rule to notice is that the label no longer lies inside the quote. That is
    # the gate that fires, and naming it keeps the test honest about which one.
    _refused(_run_table(_table_item("t1", quote_span=lower["quote_span"])),
             SchemaError, "raw_label_span must lie INSIDE quote_span")


def test_matrix_i_the_lower_row_binds_on_ITS_OWN_evidence():
    """The positive control for the case above: identical text is lawful, and
    the element that owns those offsets still attaches."""
    _attached(_run_table(_table_item("t3"), fact_id="t3"))


@pytest.mark.parametrize("bad,why", _span_cases("an evidence piece span"))
def test_matrix_i_the_same_span_law_governs_a_PIECE_span(bad, why):
    """The exact-span law is one rule; this proves the piece route uses it,
    reusing the very forms the quote-span route is tested with — and now the
    same three sub-rules, each named."""
    pieces = _pieces_of("t1")
    _refused(_run_table(_table_item("t1", pieces=[{**pieces[0], "span": bad}])),
             SchemaError, why)


@pytest.mark.parametrize("bad,why", [
    # A NULL label span is lawful on an element that HAS no structural label
    # (section 3 proves it on the prose block). This element is a table cell with
    # "North America" as its row label, so claiming null contradicts the filing
    # and is caught by the element match, not by the span shape law.
    (None, "does not describe the bound element"),
] + [c for c in _span_cases("raw_label_span") if c[0] is not None])
def test_matrix_i_the_same_span_law_governs_the_LABEL_span(bad, why):
    _refused(_run_table(_table_item("t1", raw_label_span=bad)), SchemaError, why)


@pytest.mark.parametrize("drop", list(SOURCE_EVIDENCE_KEYS))
def test_matrix_i_a_MISSING_inner_evidence_key_is_refused(drop):
    ev = dict(_table_item("t1")["source_evidence"])
    ev.pop(drop)
    item = _table_item("t1")
    item["source_evidence"] = ev
    _refused(_run_table(item), SchemaError,
             "source_evidence carries EXACTLY the keys")


def test_matrix_i_an_EXTRA_inner_evidence_key_is_refused():
    item = _table_item("t1")
    item["source_evidence"] = dict(item["source_evidence"], sneaky=1)
    _refused(_run_table(item), SchemaError,
             "source_evidence carries EXACTLY the keys")


def test_matrix_i_a_MIXED_KEY_TYPE_evidence_mapping_is_refused():
    """A mapping whose keys are not all strings must be refused without the
    guard itself crashing while formatting the message — the #819 lesson."""
    item = _table_item("t1")
    item["source_evidence"] = {**dict(item["source_evidence"]), 5: "x"}
    _refused(_run_table(item), SchemaError,
             "source_evidence carries EXACTLY the keys")


# ---- 6. THE ONE-CHARACTER SHIFT, on EVERY span the contract carries --------
#
# The quote span already has all four controls. The exact-span law is one rule,
# so the label and the piece spans must show the same four — otherwise "the
# same law governs all three" is an assertion rather than a demonstration.

def _shift(span, which, delta):
    a, b = span
    return [a + delta, b] if which == "start" else [a, b + delta]


@pytest.mark.parametrize("which,delta,why", [
    # Moving the START back puts the label OUTSIDE its own quote, so the
    # containment rule fires first. The other three stay inside the quote and
    # are caught by the element match. Two different laws, named separately —
    # one shared fragment would let either cover for the other.
    ("start", -1, "raw_label_span must lie INSIDE quote_span"),
    ("start", 1, "does not describe the bound element"),
    ("end", -1, "does not describe the bound element"),
    ("end", 1, "does not describe the bound element"),
])
def test_matrix_j_a_one_character_shift_of_the_LABEL_span_is_refused(
        which, delta, why):
    lawful = _table_item("t1")["source_evidence"]["raw_label_span"]
    _refused(_run_table(_table_item("t1",
                                    raw_label_span=_shift(lawful, which, delta))),
             SchemaError, why)


@pytest.mark.parametrize("which,delta", [("start", -1), ("start", 1),
                                         ("end", -1), ("end", 1)])
def test_matrix_j_a_one_character_shift_of_a_PIECE_span_is_refused(which, delta):
    pieces = _pieces_of("t1")
    moved = {**pieces[0], "span": _shift(pieces[0]["span"], which, delta)}
    _refused(_run_table(_table_item("t1", pieces=[moved] + pieces[1:])),
             SchemaError, "is not the text at its own span")


# ---- 7. NO REPRODUCIBLE LOCATION -> PARK, never an invented locator --------
#
# THE FIXTURE CHANGED, THE RULE DID NOT. It used to place the fact directly in
# `<body>`, which had no reproducible location only because the walker was never
# asked to record that parent — a defect, now fixed, not a property of the
# filing. The case that genuinely has no visible location is a CSS-HIDDEN owner:
# the walker deliberately skips hidden subtrees, so no span exists to report.
# That is also the only kind the frozen manifest actually contains, all 6,091 of
# them.

_NO_BLOCK_DOC = (
    f'<html {_XMLNS}><body><ix:header><ix:resources><xbrli:context id="c1"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">'
    '0000320193</xbrli:identifier></xbrli:entity><xbrli:period>'
    '<xbrli:startDate>2024-01-01</xbrli:startDate><xbrli:endDate>'
    '2024-06-30</xbrli:endDate></xbrli:period></xbrli:context></ix:resources></ix:header>'
    '<ix:header><ix:resources><xbrli:unit id="u1"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit></ix:resources></ix:header>'
    # `nb` is VISIBLE and lawful — whitespace-only content under the official
    # `ixt:fixed-zero` transform, which returns 0 for any input — so it binds,
    # `hidden` is False and the hidden guard cannot pre-empt this test. It
    # displays nothing, so its own span is empty and `source_evidence` returns
    # None: exactly the later branch under test. (Truly EMPTY content is
    # refused earlier as `malformed_fact_content_model`, Inline XBRL 1.1
    # §10.1.1, so whitespace is the lawful way to reach this.) The first div
    # supplies representation text so the submitted evidence still reproduces
    # real characters and no earlier envelope check fires. That text is the
    # single character `0` — the SAME number `ixt:fixed-zero` yields — so the
    # submitted quote, the slot and the graph row all agree, and no future
    # quote-versus-value check can pre-empt the canonical-evidence branch this
    # test exists for.
    '<div>0</div>'
    '<div><ix:nonFraction id="nb" name="us-gaap:A" contextRef="c1" '
    'unitRef="u1" scale="6" decimals="-6" format="ixt:fixed-zero"> '
    '</ix:nonFraction></div></body></html>')


def test_matrix_k_an_element_with_no_reproducible_location_PARKS():
    """The canonical builder returns None rather than inventing coordinates,
    and the door must turn that into an ordinary PARK — the filing simply
    cannot support a location for this element today. A reject would tell the
    channel to 'fix and resubmit' something it did not get wrong."""
    from decimal import Decimal

    from driver.core.prepared_fact_v2 import (ITEM_FIELDS,
                                              ProductionValidationError)
    from driver.relocation.inline_html import (element_evidence, prepare,
                                               source_evidence)
    prep = prepare(_NO_BLOCK_DOC)
    ev, why = element_evidence(prep, "nb")
    # THE PREMISE, ASSERTED. The element resolves and is NOT hidden, so the
    # earlier hidden guard cannot fire; it simply displays nothing, so the
    # canonical builder can produce no evidence for it. Its block span exists
    # but is EMPTY — which is the honest shape here, and why the trigger being
    # asserted is the builder's own None rather than a missing span.
    assert ev is not None, why
    assert ev["hidden"] is False, "a hidden fact would park for another reason"
    assert ev["displayed"] == "", ev["displayed"]
    assert source_evidence(prep, ev) is None

    # THE LAWFUL ZERO RESULT, consistently: `ixt:fixed-zero` yields 0, so the
    # submitted slot and the graph row both say 0. Any other number parks at the
    # RECONCILE step and this test would never reach the branch it exists for.
    slot = {"value": Decimal("0"), "scale_multiplier": Decimal(10) ** 6,
            "unit_scale_evidence": None}
    it = {k: None for k in ITEM_FIELDS}
    it.update(driver_name="thing", driver_state="reported", quote="0",
              measurement_raw_spans=[], slice_parts=[], level_unit="usd",
              level_low=dict(slot), level_high=dict(slot), time_type="duration",
              period_start_date="2024-01-01", period_end_date="2024-06-30")
    # A well-formed claim: the submitted evidence is structurally lawful and
    # its spans DO reproduce real text, so nothing earlier can fire.
    text = prep["text"]
    # THE EXACT ONE-CHARACTER SPAN of the visible `0`. The header's own text
    # (the CIK, the dates) also carries zeros, so the character is addressed
    # from the END, where the only displayed div sits — and that is asserted,
    # not assumed, so a fixture change can never silently move the span.
    start = text.rindex("0")
    assert start == len(text) - 1 and text[start:start + 1] == "0", repr(text)
    item = {"fact": {"fact_type": "metric", "part_ref": "p1",
                     "occurrence_in_part": None, "per_x": None, "item": it},
            "concept": "us-gaap:A", "member_refs": [],
            "source_evidence": {"representation_sha256": prep["text_sha"],
                                "quote_span": [start, start + 1],
                                "raw_label_span": None, "pieces": []}}

    class _Store(_TableStore):
        def get_xbrl_fact_dimensions(self, s, c):
            base = super().get_xbrl_fact_dimensions(s, c)
            # THE GRAPH AGREES WITH THE FACT, deliberately. `ixt:fixed-zero`
            # yields 0, so a row holding any other number would park at the
            # RECONCILE step and this test would pass without ever reaching the
            # location branch it exists for.
            return GraphFactRows(
                rows=[dict(r, fact_id="nb", value="0") for r in base.rows],
                exclusions=base.exclusions)

    class _P:
        def get_filing_document(self, s):
            return _NO_BLOCK_DOC

    # the UNIQUE reason, so an EARLIER park can never satisfy this test
    _refused(attach_event_xbrl([item], source_id=_ACC, store=_Store("nb"),
                               filing_provider=_P(),
                               text_parts=parts_for([item])),
             ProductionValidationError,
             "no reproducible visible row/block evidence")


# --- #827 E3: rendered-text truth THROUGH THE DOOR (SEQ 234/235) ------------
# Comments, script/style text and template contents are not displayed
# evidence; a UA-hidden `rp` revealed by an author inline display is. Each
# case binds (or not) through `attach_event_xbrl` itself. Ordering deviation
# recorded in the bridge: these door pins were written AFTER the walk fix and
# proven RED against an exact reconstructed pre-fix module state.

def _ghost_door(fragment):
    """_DOOR_DOC with `fragment` injected at the head of the fact block."""
    return _DOOR_DOC.replace("<p>", "<p>" + fragment, 1)


def test_E3_door_ghost_text_never_reaches_the_attached_quote():
    """THE DOOR RUNS FIRST (SEQ 236): `_door_item` builds evidence that is
    self-consistent with whatever representation the CURRENT code produces,
    the public door ATTACHES it either way, and the independent expected
    quote is what bites — against the pre-fix state the door returns a fact
    whose quote CONTAINS the ghosts, which is the defect stated as evidence.
    No setup assertion, hash mismatch or earlier refusal may stand in."""
    doc = _ghost_door('<!--COMMENT--><script>GHOST</script>'
                      '<style>.secret{display:none}</style>'
                      '<template style="display:block">SPOOK</template>')

    class P(_CountingProvider):
        def get_filing_document(self, s):
            return doc

    item = _door_item("us-gaap:A", "fA", doc=doc)
    fact = _attached(attach_event_xbrl([item], source_id=_ACC,
                                       store=_Counting(), filing_provider=P(),
                                       text_parts=parts_for([item])))
    # THE INDEPENDENT LITERAL — the whole bite. Pre-fix the attached quote was
    # 'COMMENT GHOST .secret{display:none} SPOOK 726 726'.
    assert fact.item.quote == "726 726", fact.item.quote
    # only now, the optional representation corollary
    text = prepare(doc)["text"]
    for ghost in ("COMMENT", "GHOST", ".secret", "SPOOK"):
        assert ghost not in text, ghost


def test_E3_door_an_author_revealed_rp_binds_as_ordinary_text():
    doc = _ghost_door('<rp style="display:inline">SHOWN RP </rp>')
    assert "SHOWN RP" in prepare(doc)["text"]

    class P(_CountingProvider):
        def get_filing_document(self, s):
            return doc

    item = _door_item("us-gaap:A", "fA", doc=doc)
    fact = _attached(attach_event_xbrl([item], source_id=_ACC,
                                       store=_Counting(), filing_provider=P(),
                                       text_parts=parts_for([item])))
    assert fact.item.quote == "SHOWN RP 726 726"
