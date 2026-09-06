"""The drafter prompt must state the LIVE closed values, and the period wire.

Codex SEQ 1352 item 2/3. Every closed set here is read from its owning module,
and the polarity pair is read from the V2 owner's own syntax tree, so a change
in the law moves this proof automatically. Nothing is typed in as a literal
list: that is exactly how the prompt came to teach V1's retired polarity tokens
while V2 rejected them.

    venv/bin/python -m pytest <this file> -q
"""
import ast
import inspect
import io
import os

import pytest

import build_exp5_contract as C

from driver.core.driver_ids import PERIOD_SENTINEL_SCOPE, SLICE_KINDS
from driver.core.driver_period_resolver import PERIOD_TIME_TYPES
from driver.core.driver_validators import (BASELINES, LANE_STATES,
                                           _SURPRISE_BASES, _VALID_SHAPES)
from driver.core.slot_convert import CANONICAL_UNITS
import driver.core.prepared_fact_v2 as V2
from a1_reader import CONTINUITY_KINDS


def _polarity_pair():
    """The closed pair V2 enforces, read from its OWN source structure.

    Structural, never a text match: find the `proof["polarity"] not in (...)`
    comparison inside the V2 owner and return that tuple's literal values.
    """
    tree = ast.parse(inspect.getsource(V2))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare) or len(node.ops) != 1:
            continue
        if not isinstance(node.ops[0], ast.NotIn):
            continue
        left = node.left
        if (isinstance(left, ast.Subscript)
                and isinstance(left.value, ast.Name)
                and left.value.id == "proof"
                and isinstance(left.slice, ast.Constant)
                and left.slice.value == "polarity"):
            return tuple(ast.literal_eval(node.comparators[0]))
    raise AssertionError("the V2 owner states no closed polarity pair")


def _drafter():
    return C.build_prompt("drafter")


CLOSED = {
    "lane": tuple(sorted(LANE_STATES)),
    "driver_state": tuple(sorted(set().union(*map(set, LANE_STATES.values())))),
    "shape": tuple(sorted(_VALID_SHAPES)),
    "unit": tuple(sorted(CANONICAL_UNITS)),
    "time_type": tuple(sorted(PERIOD_TIME_TYPES)),
    "sentinel_class": tuple(sorted(PERIOD_SENTINEL_SCOPE.values())),
    "slice_kind": tuple(sorted(SLICE_KINDS)),
    "surprise_basis": tuple(sorted(_SURPRISE_BASES)),
    "comparison_baseline": tuple(sorted(BASELINES)),
    "continuity_kind": tuple(sorted(CONTINUITY_KINDS)),
    "polarity": _polarity_pair(),
}


@pytest.mark.parametrize("field", sorted(CLOSED))
def test_the_prompt_states_every_live_closed_value(field):
    text = _drafter()
    missing = [v for v in CLOSED[field] if str(v) not in text]
    assert not missing, ("the prompt omits %d of %d live %s values: %s"
                         % (len(missing), len(CLOSED[field]), field, missing[:8]))


def test_the_prompt_teaches_no_retired_polarity_token():
    """THE ACTUAL DEFECT: the prompt taught tokens V2 refuses, so every proof
    it produced was invalid on arrival."""
    text = _drafter()
    live = set(_polarity_pair())
    retired = [w for w in ("higher_favorable", "lower_favorable") if w in text]
    assert not retired, ("the prompt still teaches %s, which V2 refuses; the "
                         "live pair is %s" % (retired, sorted(live)))


# ------------------------------------------------- the period wire sentence ---
def test_the_prompt_states_the_period_wire_the_resolver_enforces():
    """The live resolver parks anything else, so the prompt has to say it."""
    text = _drafter()
    missing = [w for w in ("YYYY-MM-DD",) if w not in text]
    assert not missing, "the prompt never states the date wire format"


def _resolver_ranges():
    """The resolver's own (name, lo, hi) triples, read from its syntax tree.

    Structural, never a text match: the ranges live in one tuple of 3-element
    tuples, so a change there moves this proof with it.
    """
    from driver.core import driver_period_resolver as R
    tree = ast.parse(inspect.getsource(R))
    out = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Tuple):
            continue
        for el in node.elts:
            if (isinstance(el, ast.Tuple) and len(el.elts) == 3
                    and isinstance(el.elts[0], ast.Constant)
                    and isinstance(el.elts[0].value, str)):
                try:
                    name, lo, hi = ast.literal_eval(el)
                except ValueError:
                    continue
                if isinstance(lo, int) and isinstance(hi, int):
                    out.setdefault(name, (lo, hi))
    assert out, "the resolver states no period ranges"
    return out


#: the wire-shaped fields whose range the prompt must teach - the year bounds
#: are computed, not chosen, so only the small closed counters appear here
_COUNTERS = ("fiscal_quarter", "half", "month")


@pytest.mark.parametrize("field", _COUNTERS)
def test_the_prompt_states_each_live_period_range(field):
    """The ranges are the resolver's own; a drift there must fail here."""
    lo, hi = _resolver_ranges()[field]
    text = _drafter()
    assert "%s`" % field in text or "`%s`" % field in text, \
        "the prompt never names %s" % field
    assert "%d-%d" % (lo, hi) in text or "%d to %d" % (lo, hi) in text, \
        "the prompt never states the %s range %d-%d" % (field, lo, hi)


def test_the_prompt_states_the_long_range_pairing_rule():
    """A start year without an end year parks; an end year may stand alone."""
    text = _drafter()
    assert "long_range_start_year" in text and "long_range_end_year" in text
    assert "requires" in text or "without" in text, \
        "the prompt never states how the two long-range years pair"
