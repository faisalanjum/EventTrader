"""#824 — a fabricated quote must not attach.

REPRODUCED LIVE BEFORE ANY CHANGE: an item whose quote was
`THIS QUOTE DOES NOT EXIST IN THE FILING` attached successfully through the
public event door and was stored verbatim, because `verify_occurrence` had been
built and left in `DEFERRED_HELPERS` — dead code standing in for a guard.

These tests pin the wiring. The door receives the event's `text_parts` ONCE, in
the ordered packet shape the model saw, and every fact's quote must occur in the
part it names, at the occurrence it claims. The arithmetic stays in its existing
owner, `prepared_fact_v2.verify_occurrence`; the door calls it and never counts.

SCOPE, stated so a later reader is not misled: this closes fabrication against
THE EVENT VIEW THE DOOR IS GIVEN — whatever `text_parts` the caller supplies,
every quote must occur in the part it names, at the occurrence it claims.
Verifying the same quote against the FILING's own certified spans is DONE; it
was the other half of #824 and is no longer outstanding.

The remaining limit is narrower, and it is about these TESTS, not the rule: the
event view they supply is SCAFFOLDING built from each item's own quote, because
the historical text a reader was actually shown was never archived. So the rule
is proved; what any past model saw is not, and this file never claimed to.
"""
import copy
from decimal import Decimal

import pytest

from driver.core.prepared_fact_v2 import SchemaError
from driver.core.test_round10_event_boundary import (_ACC, _DOOR_DOC, _Counting,
                                                     _CountingProvider,
                                                     _door_item)
from driver.core.xbrl_attach import attach_event_xbrl
from driver.relocation.inline_html import prepare

FABRICATED = "THIS QUOTE DOES NOT EXIST IN THE FILING"
# THE FILING'S OWN QUOTE, stated INDEPENDENTLY of the evidence builder.
# These tests are about the OCCURRENCE rule, so the filing evidence is only
# lawful INPUT here — but the input may not be vouched for by the very builder
# whose output another test checks. So the span is written as a literal and the
# text it must slice is asserted outright: if the fixture document ever changes,
# this fails here rather than quietly re-deriving a new "truth".
_PREPARED = prepare(_DOOR_DOC)
_QUOTE = _PREPARED["text"][45:52]
assert _QUOTE == "726 726", _PREPARED["text"]
_PARTS = [{"part": "fA", "content": _QUOTE}]
# The repeated-part text, defined ONCE and proved to hold the quote exactly
# twice — the occurrence rule turns on that count, so it is measured here
# rather than assumed by five separate constructions.
_TWICE = _QUOTE + " " + _QUOTE
assert _TWICE.count(_QUOTE) == 2, _TWICE


def _item(quote=None, part_ref="fA", occurrence=None):
    """Lawful by default; `quote` overrides exactly the one attacked field."""
    i = copy.deepcopy(_door_item("us-gaap:A", "fA"))
    i["fact"]["item"]["quote"] = _QUOTE if quote is None else quote
    i["fact"]["part_ref"] = part_ref
    i["fact"]["occurrence_in_part"] = occurrence
    return i


def _door(items, parts=None, *, store=None, provider=None):
    return attach_event_xbrl(items, source_id=_ACC,
                             store=store if store is not None else _Counting(),
                             filing_provider=(provider if provider is not None
                                              else _CountingProvider()),
                             text_parts=_PARTS if parts is None else parts)


# ITEM-LOCAL REFUSAL, asserted as the row the door now returns (#825). This is
# strictly MORE than the old `pytest.raises` + substring: it pins the item's
# index, its public decision word, its exact code, AND the reason text.
def _refused(res, needle):
    assert res.facts == (), "a refused item must attach nothing"
    # EXACTLY ONE ROW. Reading `[0]` alone let a duplicated outcome pass, which
    # is the same set-vs-sequence blindness that hid duplicates elsewhere.
    assert len(res.preflight_outcomes) == 1, \
        [dict(o) for o in res.preflight_outcomes]
    row = res.preflight_outcomes[0]
    assert (row["index"], row["decision"], row["codes"]) == \
        (0, "rejected", ("XBRL_CONTRACT_INVALID",))
    # THE REASON IS MANDATORY, and every fragment below is copied from the
    # message production actually emits. Without it, replacing one locator
    # sub-rule's reason with another's left these tests green — they proved a
    # refusal happened, not that the RIGHT rule refused.
    assert needle in row["detail"], row["detail"]
    return row


# ---- A. THE BLOCKER --------------------------------------------------------

def test_824_a_FABRICATED_quote_is_refused_and_costs_ZERO_io():
    store, provider = _Counting(), _CountingProvider()
    _refused(_door([_item(quote=FABRICATED)], store=store, provider=provider),
             "fabricated locator")
    # The refusal is a PURE check. #820's law is that every pure check runs
    # before any I/O, so a fabricated locator must cost nothing at all.
    assert (store.representation, store.cik, store.row_reads,
            provider.fetches) == (0, 0, [], 0)


def test_824_a_a_real_quote_at_a_lawful_locator_still_attaches():
    """The independent positive control: the gate must not reject everything."""
    res = _door([_item()])
    assert res.preflight_outcomes == ()
    assert [i for i, _f in res.facts] == [0]
    assert res.facts[0][1].item.quote == _QUOTE


# ---- B. THE text_parts CONTAINER, validated once ---------------------------

@pytest.mark.parametrize("parts", [
    {"fA": "q"},                                       # a mapping, not ordered
    "fA",                                              # a string of parts
    [["fA", "q"]],                                     # entry is not a mapping
    [{"part": "fA", "content": "q", "extra": 1}],      # an extra key
    [{"part": "fA"}],                                  # no content
    [{"content": "q"}],                                # no label
    [{"part": 1, "content": "q"}],                     # non-string label
    [{"part": "  ", "content": "q"}],                  # blank label
    [{"part": "fA", "content": "q"},
     {"part": "fA", "content": "z"}],                  # duplicate label
    [{"part": "fA", "content": 1}],                    # non-string content
])
def test_824_b_malformed_text_parts_are_refused(parts):
    with pytest.raises(SchemaError):
        _door([_item()], parts)


def test_824_b_an_empty_unrelated_part_is_lawful():
    """An event part with no text is not an event error — only a part that a
    fact NAMES and cannot support is."""
    res = _door([_item()], [{"part": "fA", "content": _QUOTE},
                            {"part": "notes", "content": ""}])
    assert [i for i, _f in res.facts] == [0] and res.preflight_outcomes == ()


def test_824_b_text_parts_are_judged_even_for_an_EMPTY_xbrl_event():
    """The lawful zero-I/O return must not become a way to skip validation —
    the same hole empty `items` once opened for the source id."""
    store, provider = _Counting(), _CountingProvider()
    with pytest.raises(SchemaError):
        _door([], [{"part": "fA", "content": "q"},
                   {"part": "fA", "content": "z"}],
              store=store, provider=provider)
    assert (store.representation, provider.fetches) == (0, 0)


def test_824_b_a_lawful_empty_xbrl_event_still_returns_with_zero_io():
    store, provider = _Counting(), _CountingProvider()
    assert _door([], store=store, provider=provider).facts == ()
    assert (store.representation, provider.fetches) == (0, 0)


# ---- C. THE LOCATOR RULES, delegated to the existing owner ------------------

def test_824_c_a_part_that_was_never_supplied_is_malformed():
    _refused(_door([_item(part_ref="p99")]), "p99")


def test_824_c_unique_quote_with_a_non_null_occurrence_is_refused():
    _refused(_door([_item(occurrence=1)]),   # the quote occurs exactly once
             "unique in this part, so occurrence_in_part must be null")


def test_824_c_repeated_quote_with_a_null_occurrence_is_refused():
    _refused(_door([_item()], [{"part": "fA", "content": _TWICE}]),
             "occurs 2x in this part — occurrence_in_part required")


def test_824_c_repeated_quote_with_a_lawful_occurrence_attaches():
    res = _door([_item(occurrence=2)], [{"part": "fA", "content": _TWICE}])
    assert [i for i, _f in res.facts] == [0] and res.preflight_outcomes == ()


def test_824_c_an_occurrence_beyond_the_count_is_refused():
    _refused(_door([_item(occurrence=3)], [{"part": "fA", "content": _TWICE}]),
             "occurrence_in_part 3 outside 1..2")


@pytest.mark.parametrize("bad", [0, -1, True, 1.0, "1", Decimal(1)])
def test_824_c_a_non_positive_integer_occurrence_is_refused(bad):
    """Caught by the accepted #823 constructor, which owns the field's shape —
    recorded here so the layer that refuses each form is visible."""
    _refused(_door([_item(occurrence=bad)], [{"part": "fA", "content": _TWICE}]),
             "occurrence_in_part: null, or a 1-based count")


def test_824_c_an_int_SUBCLASS_occurrence_is_refused_by_the_locator_owner():
    """`isinstance(k, int)` admits subclasses, and a subclass can carry any
    behaviour it likes; a count is an exact `int`. The constructor's own check
    passes this value, so only the locator owner can refuse it."""
    class Sneaky(int):
        pass

    _refused(_door([_item(occurrence=Sneaky(2))],
                   [{"part": "fA", "content": _TWICE}]),
             "occurrence_in_part must be an integer")


def test_824_c_the_same_quote_in_two_parts_stays_lawful_in_each():
    """Core cannot infer which part the model 'meant'; each exact cited part is
    lawful on its own."""
    parts = [{"part": "fA", "content": _QUOTE},
             {"part": "fB", "content": _QUOTE}]
    for ref in ("fA", "fB"):
        res = _door([_item(part_ref=ref)], parts)
        assert [i for i, _f in res.facts] == [0], ref
        assert res.preflight_outcomes == (), ref


# ---- D. THE CALLER IS NOT TRUSTED AFTER ENTRY ------------------------------

def test_824_d_mutating_text_parts_after_entry_changes_nothing():
    """The filing provider is caller-supplied code that runs BETWEEN the pure
    checks and their use — the #823 TOCTOU lesson, applied to the new input."""
    parts = [{"part": "fA", "content": _QUOTE}]

    class Hostile(_CountingProvider):
        def get_filing_document(self, s):
            parts[0]["content"] = FABRICATED
            parts.append({"part": "fA", "content": "duplicate label"})
            return super().get_filing_document(s)

    res = _door([_item()], parts, provider=Hostile())
    assert [i for i, _f in res.facts] == [0] and res.preflight_outcomes == ()
    assert res.facts[0][1].item.quote == _QUOTE


# ---- E. ONE OWNER, AND THE HELPER IS NO LONGER DEAD ------------------------

def test_824_e_verify_occurrence_is_no_longer_deferred():
    from driver.core import prepared_fact_v2 as p2
    assert "verify_occurrence" not in p2.DEFERRED_HELPERS


def test_824_e_the_door_does_not_reimplement_the_occurrence_arithmetic():
    """DERIVED from the AST: the door CALLS the owner and never counts itself,
    so the rule cannot drift into two versions."""
    import ast
    import pathlib

    src = pathlib.Path("driver/core/xbrl_attach.py").read_text()
    counted = [n for n in ast.walk(ast.parse(src))
               if isinstance(n, ast.Attribute) and n.attr == "count"]
    assert not counted, "xbrl_attach counts occurrences itself — duplicate rule"
    called = [n for n in ast.walk(ast.parse(src))
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
              and n.func.id == "verify_occurrence"]
    assert len(called) == 1, "the door must call the one owner exactly once"
