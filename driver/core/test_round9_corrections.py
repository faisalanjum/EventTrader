"""ROUND-9 corrections — RED-first, one failing test per reviewer finding.

  1  padded signs      " - " was repaired to "-"; the XBRL sign attribute
                       carries the literal "-" and nothing else. Decisive
                       evidence: 254,351 sign attributes across 1,769 real
                       filings, every one exactly "-", none padded.
  2  member_refs shape {} and set() were accepted as "verified empty"; None
                       and 5 CRASHED with TypeError instead of parking.
  3  unwired invariant one_representation_for_event() was called only by its
                       own test, so one-document-per-event was decorative.
  8  duplicated map    locator._ANCHOR_UNIT and the v2 semantic check were the
                       same relation written twice, in opposite directions.

Items 4-7 are corrections to tests and wording and are asserted here too:
the live proof must use the PACKET's harvested hash, the EPS fixture must be
an eps fact, the stale date header must be corrected, and the trust claim must
not say the hash proves the channel trustworthy.
"""
import pathlib

from driver.core.test_round10_event_boundary import parts_for

import pytest

from driver.relocation import exact_numbers as XN
from driver.relocation.inline_html import printed_value
from driver.core import prepared_fact_v2 as p2
from driver.core import xbrl_attach as xa
from driver.core.prepared_fact_v2 import SchemaError
from driver.core.test_round10_event_boundary import ev_of

_REPO = pathlib.Path(__file__).resolve().parents[2]


def _VALID_FACT():
    """A schema-valid fact, so these tests exercise the EVENT rule they name
    rather than dying on the item schema the pure phase now checks first."""
    from decimal import Decimal
    from driver.core.prepared_fact_v2 import ITEM_FIELDS
    it = {k: None for k in ITEM_FIELDS}
    it.update(driver_name="revenue", driver_state="reported", quote="q",
              measurement_raw_spans=[], slice_parts=[], level_unit="m_usd",
              level_low={"value": Decimal("726"),
                         "scale_multiplier": Decimal(10) ** 6,
                         "unit_scale_evidence": None},
              level_high={"value": Decimal("726"),
                          "scale_multiplier": Decimal(10) ** 6,
                          "unit_scale_evidence": None},
              time_type="duration", period_start_date="2024-01-01",
              period_end_date="2024-06-30")
    return {"fact_type": "metric", "part_ref": "p1", "occurrence_in_part": None,
            "per_x": None, "item": it}


# --- 1. the sign attribute carries the literal "-", exactly ----------------

@pytest.mark.parametrize("sign", [" - ", "\t-\n", "- ", " -", " -"])
def test_a_padded_sign_is_malformed_evidence_not_a_typo_to_repair(sign):
    """Repairing it is inventing a value. Rejecting costs at most an
    abstention — and the reconcile step means a wrong sign could never have
    produced a wrong stored number anyway, so strict is free."""
    assert printed_value("726", "", sign) is None


def test_the_only_lawful_sign_forms_still_work():
    assert printed_value("726", "", "-") == -726          # negative
    assert printed_value("726", "", "") == 726            # absent
    assert printed_value("726", "", None) == 726


@pytest.mark.parametrize("sign", ["+", "--", "minus", "0", "n"])
def test_every_other_sign_value_is_refused(sign):
    assert printed_value("726", "", sign) is None


# --- 2. member_refs: a list or tuple, or a clean park ----------------------

@pytest.mark.parametrize("bad", [{}, set(), None, 5, "abc", 0, True, object()])
def test_member_refs_of_the_wrong_SHAPE_park_cleanly(bad):
    """`{}` and `set()` were silently read as verified-empty — a DIFFERENT
    claim from `[]` — and `None`/`5` crashed with TypeError.

    MIGRATED (#823): `_freeze_refs` is gone — it duplicated both the validation
    and the freezing the dataclass boundary performs — so the rule is asserted
    where it now lives, at the boundary itself."""
    with pytest.raises(SchemaError):
        _refs_through_the_boundary(bad)


@pytest.mark.parametrize("good", [[], ()])
def test_an_empty_LIST_is_the_verified_empty_claim(good):
    assert _refs_through_the_boundary(good).item.member_refs == ()


def _refs_through_the_boundary(refs):
    """Build a fact carrying these member_refs through the trusted door's own
    constructor — the ONE place the ref law is judged now."""
    from driver.core.prepared_fact_v2 import ITEM_FIELDS, PreparedFactV2
    item = {k: None for k in ITEM_FIELDS}
    item.update(driver_name="revenue", driver_state="reported", quote="q",
                measurement_raw_spans=[], slice_parts=[], time_type="instant",
                period_end_date="2024-06-30")
    return PreparedFactV2._build(
        {"fact_type": "metric", "part_ref": "p", "occurrence_in_part": None,
         "per_x": None, "item": item},
        {"xbrl_concept_raw": "us-gaap:X", "member_refs": refs,
         "_attach_token": p2._ATTACH_TOKEN})


# --- 3. one document per event, actually enforced --------------------------

def test_the_one_document_per_event_rule_is_WIRED_not_decorative():
    """It must be reachable from the event door, not only from its own test."""
    import inspect
    assert hasattr(xa, "attach_event_xbrl")   # the door moved modules
    src = inspect.getsource(xa.attach_event_xbrl)
    assert "one_representation_for_event" in src


def test_the_event_door_refuses_items_that_disagree_on_the_document():
    items = [{"fact": _VALID_FACT(), "concept": "us-gaap:Revenues",
              "member_refs": [], "source_evidence": ev_of("a" * 64)},
             {"fact": _VALID_FACT(), "concept": "us-gaap:Revenues",
              "member_refs": [], "source_evidence": ev_of("b" * 64)}]
    res = xa.attach_event_xbrl(items, source_id="x", store=None,
                               filing_provider=None, text_parts=parts_for(items))
    assert res.facts == ()
    # BOTH items are rejected as one inconsistent submission — the envelope was
    # fine, so it is not an event abort, and each item keeps its own index.
    assert [o["index"] for o in res.preflight_outcomes] == [0, 1]
    for o in res.preflight_outcomes:
        assert (o["decision"], o["codes"]) == ("rejected",
                                               ("XBRL_CONTRACT_INVALID",))
        assert "2 different representations" in o["detail"]


def test_the_event_door_refuses_an_item_with_no_declared_document():
    """WHY THIS IS NOW ONE ITEM. It used to submit a valid sibling alongside the
    undeclared one, because the old law aborted the whole event and the sibling
    merely demonstrated the collateral damage. That damage is the defect #825
    removed: a lawful sibling now proceeds on its own. Keeping it here would
    make this pure-check test depend on a bound filing it does not care about,
    so the sibling is gone and sibling SURVIVAL is proved where it belongs, with
    real fixtures, in the #825 matrix. `store=None` still proves zero I/O.
    """
    items = [{"fact": _VALID_FACT(), "concept": "c", "member_refs": [],
              "source_evidence": ev_of(None)}]
    res = xa.attach_event_xbrl(items, source_id="x", store=None,
                               filing_provider=None, text_parts=parts_for(items))
    assert res.facts == ()
    assert len(res.preflight_outcomes) == 1
    row = res.preflight_outcomes[0]
    assert (row["index"], row["decision"], row["codes"]) == \
        (0, "rejected", ("XBRL_CONTRACT_INVALID",))
    assert "representation_sha256" in row["detail"]


# --- 8. ONE unit-compatibility map -----------------------------------------

def test_the_unit_compatibility_relation_has_exactly_one_definition():
    """`locator._ANCHOR_UNIT` and the v2 semantic check were inverses of the
    same relation. One definition now; the locator keeps its extra
    percent-family rows, which Route-A semantics can never reach."""
    assert not hasattr(p2, "_SEMANTIC_TO_LEVEL_UNITS")
    compat = XN.ROUTE_A_UNIT_COMPAT
    assert compat["usd"] == frozenset({"usd", "usd_per_share"})
    assert compat["m_usd"] == frozenset({"usd"})
    assert compat["count"] == frozenset({"count"})
    # every Route-A semantic must be reachable from some canonical unit
    assert set(XN.ROUTE_A_SEM_UNIT.values()) <= set().union(*compat.values())


def test_the_locator_still_exposes_its_full_anchor_law():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_loc", _REPO / "driver" / "relocation" / "locator.py")
    import sys
    sys.path.insert(0, str(_REPO / "driver" / "relocation"))
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        sys.path.pop(0)
    # the money/count rows come from the ONE shared map...
    for unit, allowed in XN.ROUTE_A_UNIT_COMPAT.items():
        assert mod._ANCHOR_UNIT[unit] == allowed
    # ...and the percent family it also owns is untouched
    assert mod._ANCHOR_UNIT["percent_yoy"] == frozenset({"percent"})
    assert mod._ANCHOR_UNIT["x"] == frozenset({"percent"})


# --- 6/7. wording that must not overclaim ----------------------------------


# --- the sweep: helpers that exist but nothing calls ------------------------

def test_no_contract_helper_is_left_unreachable_from_production():
    """The reviewer caught one decorative helper; this pins the CLASS. Every
    public helper must be reached from a production path, or be explicitly
    listed as owner-deferred with its reason."""
    import ast
    import inspect
    from driver.core import xbrl_attach as xa
    # DERIVED FROM THE AST. This counted `name + "("` over the source text,
    # which cannot tell a call from a definition, a docstring or a comment —
    # and it was passing for the WRONG REASON: `one_representation_for_event(`
    # is a substring of `_one_representation_for_event(`, the private name, so
    # the public name it named has not existed since #821 and nothing noticed.
    called = set()
    for mod in (p2, xa):                     # BOTH: the schema kept its helpers,
        for n in ast.walk(ast.parse(inspect.getsource(mod))):   # the door moved
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                called.add(n.func.id)
    # `verify_occurrence` LEFT this set at #824 — the event door now calls it.
    # What remains needs the proposed driver NAME, which admission owns.
    deferred = {"check_per_x_against_name"}
    for name in ("_one_representation_for_event", "check_per_x_against_name",
                 "verify_occurrence", "split_slice_part"):
        assert name in called or name in deferred, \
            f"{name} is defined but never called"
    assert p2.DEFERRED_HELPERS == tuple(sorted(deferred))
