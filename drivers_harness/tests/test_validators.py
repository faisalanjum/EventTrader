"""Bucket H — §E validators V1..V14, EVERY one with a pass case and a fail case.

Spec sources (transcribed, not paraphrased):
  - DriverOntology_Implementation.md §E (V1..V14 table, :441-454) — the Check +
    the exact Rejection-reason string each validator returns on failure.
  - DriverOntology_Implementation.md §F.5/§F.6/§F.7/§F.9 + §G — the vocab banks +
    thresholds the validators read.
  - DriverOntology_Implementation.md §D — the new-token gate V14 enforces.
  - _workflow/req_canonical.md — the deduped risks K38-K49 / K53-K57 and the
    field contract rows B-F1..B-F10 each validator implements:
      V1  -> K45/K46 alias rules           (B-F5)
      V2  -> K46 aliases bridge drivers     (B-F5 / R10)
      V3  -> K49 label != name              (B-F6 label tokens = name tokens as a SET)
      V4  -> K39 segment Total-vs-subdim    (B-F7)
      V5  -> K48 base_label resolution      (B-F8)
      V6  -> K40/K41/K42/K43 allowed_states (B-F10: one class, verbs, size bound)
      V7  -> K38 bad/empty/>1-sentence def  (B-F9 exactly one sentence, not a tautology)
      V8  -> K44/K56 state not in allowed   (B-F2)
      V9  -> K55 direction enum             (B-F3)
      V10 -> K57 empty / non-SRC evidence   (B-F4)
      V11 -> K54 unresolved driver_name
      V12 -> duplicate proposal NAMES only  (does NOT cover K53 — K53 is the
             canonical-collision self-consistency check, enforced in run_one's
             emission-level pass, NOT V12; see test_pass1_corrective.py::
             test_same_canonical_collision_flagged_K53)
      V13 -> proposal_without_use           (orphan-proposal scan also enforced at
             the emission level in run_one — see test_pass1_corrective.py)
      V14 -> §D new-token gate              (K58 / R11 new-driver gate)

Each test asserts the (ok, reason) tuple shape validators.py returns — the
PROPERTY (ok bool + the §E Rejection.reason string) — not incidental fields.

SURFACED (best first-cut, per Harness_BuilderPrompt.md §0a SURFACE-DON'T-FIX):
  The §F.5-vs-§F.9 ``restricted`` / ``accumulated`` contradiction — historically
  those two tokens lived in BOTH §F.5 STATES (policy_action / quantity_move) AND
  §F.9 ALLOWED_VERBAL_FORMS. The 2026-05-29 spec fix REMOVED them from §F.9 (they
  are states → belong in driver_state, banned from a NAME by canonicalize step 7).
  The foundation vocab_seed.py already reflects that fix (ALLOWED_VERBAL_FORMS has
  neither token; STATE_CLASSES still has both), so V6 below treats them purely as
  states. These tests do NOT silently re-resolve the contradiction — they assert
  the post-fix behavior the SPEC now dictates and flag the tension in this
  docstring + the return report. If a tester re-introduces them to §F.9, V6's
  "all from ONE state class" check would still pass them as states while the name
  ban (canonicalize step 7) would reject them in a name — surfaced, not patched.
"""

from __future__ import annotations

import json
import os

import pytest

from vocab_seed import build_vocab_snapshot, COLD_START_SEED_DRIVERS
from registry_fake import Registry
from validators import (
    V1_alias_canonicalizes_to_parent,
    V2_alias_no_bridge,
    V3_label_matches_name,
    V4_segment_consistent,
    V5_base_label,
    V6_allowed_states,
    V7_definition,
    V8_state_in_allowed,
    V9_direction,
    V10_evidence,
    V11_name_resolves,
    V12_no_duplicate_proposal,
    V13_proposal_used,
    V14_new_token_gate,
)


@pytest.fixture(scope="module")
def vocab():
    return build_vocab_snapshot()


@pytest.fixture(scope="module")
def registry():
    # scenario registry: iphone_china_sales (alias china_iphone_sales), oil_price,
    # gross_margin, fda_approval, revenue, sales, eps, gpu_hyperscaler_bookings, ...
    return Registry.from_fixture()


# ─────────────────────────────────────────────────────────────────────────────
# V1 — alias canonicalizes TO the parent driver name (§E:441, K45, B-F5)
#   E6 fix: canonicalize(alias) == parent.name (NOT == alias).
# ─────────────────────────────────────────────────────────────────────────────

def test_V1_pass_order_variant_is_valid_alias(vocab):
    """V1 PASS (§E:441, K45/B-F5): ``china_iphone_sales`` is a valid alias of
    parent ``iphone_china_sales`` because it canonicalizes TO the parent name
    (E6 word-order variant). The pre-E6 ``== alias`` rule would have wrongly
    rejected it — the spec explicitly cites this exact case."""
    ok, reason = V1_alias_canonicalizes_to_parent(
        "china_iphone_sales", "iphone_china_sales", vocab
    )
    assert ok is True
    assert reason is None


def test_V1_fail_revenue_is_not_an_alias_of_iphone_china_sales(vocab):
    """V1 FAIL (§E:441, K45 'alias too loose'): ``revenue`` canonicalizes to
    ``revenue`` != parent ``iphone_china_sales`` → reject
    ``alias_does_not_canonicalize_to_parent`` (the brief's V1 fail example:
    revenue is NOT a valid alias of iphone_china_sales)."""
    ok, reason = V1_alias_canonicalizes_to_parent(
        "revenue", "iphone_china_sales", vocab
    )
    assert ok is False
    assert reason == "alias_does_not_canonicalize_to_parent"


# ─────────────────────────────────────────────────────────────────────────────
# V1 CLASS-GUARD — every SEEDED alias must canonicalize to its parent (§E:441 V1)
#   added 2026-05-29: catches a SYNONYM mis-filed as a seed alias — the whole
#   bug-class, not one instance (e.g. the removed oil_price crude_price/brent_price).
# ─────────────────────────────────────────────────────────────────────────────

def test_every_seeded_alias_canonicalizes_to_its_parent(vocab):
    """V1 class-guard (§E:441 V1 / B-F5): EVERY alias seeded in COLD_START_SEED_DRIVERS
    (prod-core — copies to production) AND in fixtures/fake_registry.json (test-scaffold)
    MUST canonicalize TO its parent driver's name. An alias is a spelling/ORDER variant
    (china_iphone_sales -> iphone_china_sales); a SYNONYM (a different word, e.g.
    crude_price) is NOT an alias — it canonicalizes elsewhere / rejects, and is the
    Pass-2 synonym-learner's job. Without this guard a synonym mis-filed as a seed alias
    ships SILENTLY (the crude_price/brent_price bug, removed 2026-05-29). Fails LOUD with
    the offending (alias, parent, V1-reason) so this class can never silently recur."""
    fixture = os.path.join(os.path.dirname(__file__), "fixtures", "fake_registry.json")
    with open(fixture, encoding="utf-8") as f:
        seeded = list(COLD_START_SEED_DRIVERS) + json.load(f)
    offenders = []
    for d in seeded:
        for alias in d.get("aliases", []):
            ok, reason = V1_alias_canonicalizes_to_parent(alias, d["name"], vocab)
            if not ok:
                offenders.append((alias, d["name"], reason))
    assert not offenders, (
        "seeded aliases that are NOT valid V1 aliases (a synonym mis-filed as an alias — "
        f"move it to the Pass-2 synonym-learner): {offenders}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# V2 — alias must not bridge another driver (§E:442, K46, R10)
# ─────────────────────────────────────────────────────────────────────────────

def test_V2_pass_alias_does_not_collide_with_another_driver(registry):
    """V2 PASS (§E:442, K46/R10): an alias that matches NO other driver's name
    or aliases is fine — here ``brent_price`` for parent ``oil_price`` collides
    with nothing else in the registry."""
    ok, reason = V2_alias_no_bridge("brent_price", "oil_price", registry)
    assert ok is True
    assert reason is None


def test_V2_fail_alias_equals_another_drivers_name(registry):
    """V2 FAIL (§E:442, K46): proposing ``revenue`` (an EXISTING different
    driver's name) as an alias of parent ``oil_price`` bridges two unrelated
    drivers → reject ``alias_bridges_unrelated_drivers``."""
    ok, reason = V2_alias_no_bridge("revenue", "oil_price", registry)
    assert ok is False
    assert reason == "alias_bridges_unrelated_drivers"


# ─────────────────────────────────────────────────────────────────────────────
# V3 — label tokens == name tokens as a SET (§E:443, K49, B-F6)
# ─────────────────────────────────────────────────────────────────────────────

def test_V3_pass_label_tokens_equal_name_tokens(vocab):
    """V3 PASS (§E:443, K49/B-F6): ``sorted(slug(label).split('_')) ==
    sorted(name.split('_'))`` — label ``"China iPhone Sales"`` slugs to the same
    token SET as name ``iphone_china_sales`` (order-insensitive)."""
    ok, reason = V3_label_matches_name("China iPhone Sales", "iphone_china_sales")
    assert ok is True
    assert reason is None


def test_V3_fail_label_describes_a_different_concept(vocab):
    """V3 FAIL (§E:443, K49): label ``"Gross Margin"`` (tokens {gross, margin})
    describes a different concept than name ``iphone_china_sales`` → reject
    ``label_concept_mismatch``."""
    ok, reason = V3_label_matches_name("Gross Margin", "iphone_china_sales")
    assert ok is False
    assert reason == "label_concept_mismatch"


# ─────────────────────────────────────────────────────────────────────────────
# V4 — segment Total-vs-subdimension (§E:444, K39, B-F7)
# ─────────────────────────────────────────────────────────────────────────────

def test_V4_pass_total_for_no_subdimension(vocab):
    """V4 PASS (§E:444, K39/B-F7): name ``revenue`` has no sub-dimension slot →
    segment MUST be ``"Total"`` → accept."""
    ok, reason = V4_segment_consistent("Total", "revenue", vocab)
    assert ok is True
    assert reason is None


def test_V4_pass_subdimension_segment_matches_name(vocab):
    """V4 PASS (§E:444, K39/B-F7): name ``iphone_china_sales`` has sub-dimension
    tokens {iphone(object), china(geography)} → segment ``"iPhone China"`` slugs
    to {iphone, china} which matches → accept."""
    ok, reason = V4_segment_consistent("iPhone China", "iphone_china_sales", vocab)
    assert ok is True
    assert reason is None


def test_V4_fail_total_when_name_has_subdimension(vocab):
    """V4 FAIL (§E:444, K39): name ``iphone_china_sales`` carries a sub-dimension
    but segment is ``"Total"`` → mismatch → reject
    ``segment_inconsistent_with_name``."""
    ok, reason = V4_segment_consistent("Total", "iphone_china_sales", vocab)
    assert ok is False
    assert reason == "segment_inconsistent_with_name"


# ─────────────────────────────────────────────────────────────────────────────
# V5 — base_label null OR in CANONICAL_BASE_LABELS (§E:445, K48, B-F8, §F.6)
# ─────────────────────────────────────────────────────────────────────────────

def test_V5_pass_none_base_label(vocab):
    """V5 PASS (§E:445, K48/B-F8): ``base_label IS NULL`` is explicitly allowed."""
    ok, reason = V5_base_label(None, vocab)
    assert ok is True
    assert reason is None


def test_V5_pass_canonical_base_label(vocab):
    """V5 PASS (§E:445, §F.6): ``"Sales"`` ∈ CANONICAL_BASE_LABELS → accept."""
    ok, reason = V5_base_label("Sales", vocab)
    assert ok is True
    assert reason is None


def test_V5_fail_junk_base_label(vocab):
    """V5 FAIL (§E:445, K48 'base_label is junk'): ``"Topline"`` is NOT in
    §F.6 CANONICAL_BASE_LABELS → reject ``invalid_base_label``."""
    ok, reason = V5_base_label("Topline", vocab)
    assert ok is False
    assert reason == "invalid_base_label"


# ─────────────────────────────────────────────────────────────────────────────
# V6 — allowed_states: one class + size bound (§E:446, K40-K43, B-F10, §F.5/§G)
# ─────────────────────────────────────────────────────────────────────────────

def test_V6_pass_one_class_within_bounds(vocab):
    """V6 PASS (§E:446, B-F10/§F.5): {accelerated, decelerated, stable, declined}
    are all in the ONE ``trend_motion`` class and len=4 is within
    STATES_MIN(2)..STATES_MAX(8) → accept."""
    ok, reason = V6_allowed_states(
        ["accelerated", "decelerated", "stable", "declined"], vocab
    )
    assert ok is True
    assert reason is None


def test_V6_fail_mixed_state_classes(vocab):
    """V6 FAIL (§E:446, K43 'mixed verb classes'): {raised(financial_outcome),
    steepened(rate_curve)} span TWO classes → no single class contains both →
    reject ``invalid_allowed_states`` (spec K43 example: raised + ... + steepened)."""
    ok, reason = V6_allowed_states(["raised", "steepened"], vocab)
    assert ok is False
    assert reason == "invalid_allowed_states"


def test_V6_fail_too_short_below_min(vocab):
    """V6 FAIL (§E:446, K40 'too narrow' / §G STATES_MIN=2): a single-state list
    is below STATES_MIN → reject ``invalid_allowed_states``."""
    ok, reason = V6_allowed_states(["approved"], vocab)
    assert ok is False
    assert reason == "invalid_allowed_states"


def test_V6_fail_too_long_above_max(vocab):
    """V6 FAIL (§E:446, K41 'too broad' / §G STATES_MAX=8): 9 states exceeds
    STATES_MAX → reject ``invalid_allowed_states``. (All 9 are real financial_
    outcome/quantity tokens so the size bound — not membership — is what fires;
    9 > 8 is caught before the one-class check.)"""
    nine = ["beat", "missed", "inline", "raised", "lowered",
            "reaffirmed", "withdrawn", "cut", "expanded"]
    ok, reason = V6_allowed_states(nine, vocab)
    assert ok is False
    assert reason == "invalid_allowed_states"


def test_V6_fail_non_state_token(vocab):
    """V6 FAIL (§E:446, K42 'not verbs'): a list containing a non-§F.5 token
    (``"growth"`` — a noun, the K42 example) → reject ``invalid_allowed_states``."""
    ok, reason = V6_allowed_states(["beat", "growth"], vocab)
    assert ok is False
    assert reason == "invalid_allowed_states"


# ─────────────────────────────────────────────────────────────────────────────
# V7 — definition: non-empty / exactly one sentence / not a name restatement
#       (§E:447, K38, B-F9)
# ─────────────────────────────────────────────────────────────────────────────

def test_V7_pass_clean_one_sentence_definition(vocab):
    """V7 PASS (§E:447, K38/B-F9): a non-empty, single-sentence definition that
    is NOT a token-only restatement of the name → accept."""
    ok, reason = V7_definition(
        "Unit sales of iPhone in the China market.", "iphone_china_sales"
    )
    assert ok is True
    assert reason is None


def test_V7_fail_empty_definition(vocab):
    """V7 FAIL (§E:447, K38 'empty'): an empty/whitespace definition →
    reject ``bad_definition``."""
    ok, reason = V7_definition("   ", "iphone_china_sales")
    assert ok is False
    assert reason == "bad_definition"


def test_V7_fail_more_than_one_sentence(vocab):
    """V7 FAIL (§E:447, K38 '>1 sentence'): two sentence-final punctuations →
    not 'exactly one sentence' → reject ``bad_definition``."""
    ok, reason = V7_definition(
        "Unit sales of iPhone in China. It fell sharply.", "iphone_china_sales"
    )
    assert ok is False
    assert reason == "bad_definition"


def test_V7_fail_token_only_restatement_of_name(vocab):
    """V7 FAIL (§E:447, K38 'circular/tautology' / B-F9 'NOT a tautology of the
    name tokens'): definition whose words == the name's underscore tokens as a
    set (``"iPhone China sales."`` for ``iphone_china_sales``) → reject
    ``bad_definition``."""
    ok, reason = V7_definition("iPhone China sales.", "iphone_china_sales")
    assert ok is False
    assert reason == "bad_definition"


# ─────────────────────────────────────────────────────────────────────────────
# V8 — driver_state in driver.allowed_states (§E:448, K44/K56, B-F2)
# ─────────────────────────────────────────────────────────────────────────────

def test_V8_pass_state_in_allowed(vocab):
    """V8 PASS (§E:448, B-F2): ``"decelerated"`` ∈ the driver's allowed_states →
    accept."""
    ok, reason = V8_state_in_allowed(
        "decelerated", ["accelerated", "decelerated", "stable", "declined"]
    )
    assert ok is True
    assert reason is None


def test_V8_fail_state_not_in_allowed(vocab):
    """V8 FAIL (§E:448, K44/K56): the K44 example — ``"beat"`` is NOT an allowed
    state of a yield_curve-style driver whose states are
    {steepened, flattened, inverted, normalized} → reject
    ``state_not_in_allowed_states``."""
    ok, reason = V8_state_in_allowed(
        "beat", ["steepened", "flattened", "inverted", "normalized"]
    )
    assert ok is False
    assert reason == "state_not_in_allowed_states"


# ─────────────────────────────────────────────────────────────────────────────
# V9 — direction enum {long, short} (§E:449, K55, B-F3)
# ─────────────────────────────────────────────────────────────────────────────

def test_V9_pass_long_and_short(vocab):
    """V9 PASS (§E:449, B-F3): the closed enum {long, short} — both accept."""
    assert V9_direction("long") == (True, None)
    assert V9_direction("short") == (True, None)


def test_V9_fail_non_enum_direction(vocab):
    """V9 FAIL (§E:449, K55 'direction enum violation'): ``"up"`` (and
    ``"bullish"``) are outside {long, short} → reject ``invalid_direction_enum``."""
    ok, reason = V9_direction("up")
    assert ok is False
    assert reason == "invalid_direction_enum"
    assert V9_direction("bullish")[1] == "invalid_direction_enum"


# ─────────────────────────────────────────────────────────────────────────────
# V10 — evidence SRC format + source_catalog resolution (§E:450, K57, B-F4)
# ─────────────────────────────────────────────────────────────────────────────

def test_V10_pass_src_resolves_against_catalog(vocab):
    """V10 PASS (§E:450, K57/B-F4): a SRC:* entry that is BOTH well-formed AND
    present in the emission's source_catalog → accept. Uses a SRC:TR: id so the
    transcript-source separation (doubt A15/TA2) is exercised."""
    catalog = ["SRC:REPORT:0001#MDA", "SRC:TR:txn42"]
    ok, reason = V10_evidence(["SRC:TR:txn42"], catalog)
    assert ok is True
    assert reason is None


def test_V10_fail_empty_evidence(vocab):
    """V10 FAIL (§E:450, K57 'evidence empty'): an empty evidence list is below
    EVIDENCE_MIN_PER_TAG → reject ``empty_or_malformed_or_unresolved_src``."""
    ok, reason = V10_evidence([], ["SRC:REPORT:0001#MDA"])
    assert ok is False
    assert reason == "empty_or_malformed_or_unresolved_src"


def test_V10_fail_hallucinated_src_not_in_catalog(vocab):
    """V10 FAIL (§E:450 E18 strict): a SRC id that is well-FORMED but NOT in the
    source_catalog is a hallucinated reference → reject
    ``empty_or_malformed_or_unresolved_src`` (catalog resolution, not syntax
    alone — the spec's exact E18 rationale)."""
    catalog = ["SRC:REPORT:0001#MDA"]
    ok, reason = V10_evidence(["SRC:NEWS:9999"], catalog)
    assert ok is False
    assert reason == "empty_or_malformed_or_unresolved_src"


# ─────────────────────────────────────────────────────────────────────────────
# V11 — driver_name resolves to registry OR a same-emission proposal
#       (§E:451, K54)
# ─────────────────────────────────────────────────────────────────────────────

def test_V11_pass_name_in_registry(registry):
    """V11 PASS (§E:451): ``iphone_china_sales`` exists in the registry → the
    used name resolves → accept."""
    ok, reason = V11_name_resolves("iphone_china_sales", registry, set())
    assert ok is True
    assert reason is None


def test_V11_pass_name_in_same_emission_proposal(registry):
    """V11 PASS (§E:451): a name absent from the registry but present in this
    emission's ``propose_new_drivers[]`` set closes the loop → accept."""
    ok, reason = V11_name_resolves(
        "gpu_blackwell_revenue", registry, {"gpu_blackwell_revenue"}
    )
    assert ok is True
    assert reason is None


def test_V11_fail_unresolved_name(registry):
    """V11 FAIL (§E:451, K54 'unresolved driver_name'): a name in NEITHER the
    registry NOR any propose_new entry → reject ``unresolved_driver_name``."""
    ok, reason = V11_name_resolves("totally_made_up_driver", registry, set())
    assert ok is False
    assert reason == "unresolved_driver_name"


# ─────────────────────────────────────────────────────────────────────────────
# V12 — no two propose_new entries share a name (§E:452, duplicate_proposal)
# ─────────────────────────────────────────────────────────────────────────────

def test_V12_pass_distinct_proposal_names(vocab):
    """V12 PASS (§E:452): two propose_new entries with DISTINCT names → accept."""
    proposals = [{"name": "gpu_hyperscaler_capex"}, {"name": "datacenter_demand"}]
    ok, reason = V12_no_duplicate_proposal(proposals)
    assert ok is True
    assert reason is None


def test_V12_fail_two_proposals_same_name(vocab):
    """V12 FAIL (§E:452): two ``propose_new_drivers[]`` entries sharing the same
    ``name`` in one emission → reject ``duplicate_proposal``."""
    proposals = [{"name": "gpu_capex"}, {"name": "gpu_capex"}]
    ok, reason = V12_no_duplicate_proposal(proposals)
    assert ok is False
    assert reason == "duplicate_proposal"


# ─────────────────────────────────────────────────────────────────────────────
# V13 — every proposal name is used by >=1 tag with non-empty evidence
#       (§E:453, proposal_without_use)
# ─────────────────────────────────────────────────────────────────────────────

def test_V13_pass_proposal_used_by_a_tag(vocab):
    """V13 PASS (§E:453): the proposal name is used by a tag that carries
    non-empty evidence → accept."""
    items = [{"driver_name": "gpu_capex", "evidence": ["SRC:NEWS:1"]}]
    ok, reason = V13_proposal_used("gpu_capex", items)
    assert ok is True
    assert reason is None


def test_V13_fail_proposal_no_tag_references_it(vocab):
    """V13 FAIL (§E:453): a ``propose_new`` entry that NO tag references → reject
    ``proposal_without_use`` (an unused proposal must not be written)."""
    items = [{"driver_name": "revenue", "evidence": ["SRC:NEWS:1"]}]
    ok, reason = V13_proposal_used("gpu_capex", items)
    assert ok is False
    assert reason == "proposal_without_use"


# ─────────────────────────────────────────────────────────────────────────────
# V14 — new-token gate (§E:454, §D, K58 / R11 new-driver gate)
# ─────────────────────────────────────────────────────────────────────────────

def test_V14_pass_novel_token_grounded_in_evidence(registry, vocab):
    """V14 PASS (§E:454, §D(e)): proposal ``china_blackwell_sales`` has one novel
    token (``blackwell``) whose slot is determinable (canonicalizes cleanly) AND
    that token appears in the tag's joined evidence text → the §D new-token gate
    passes → accept. (K58 / R11: a new token is admissible iff grounded in
    evidence.)"""
    items = [{
        "driver_name": "china_blackwell_sales",
        "evidence": ["SRC:NEWS:1"],
        "evidence_text": "Blackwell chip sales in China accelerated.",
    }]
    ok, reason = V14_new_token_gate("china_blackwell_sales", items, registry, vocab)
    assert ok is True
    assert reason is None


def test_V14_fail_novel_token_absent_from_evidence(registry, vocab):
    """V14 FAIL (§E:454, §D(e) hallucination guard): same novel-token proposal
    but ``blackwell`` does NOT appear in the evidence text → the §D gate's
    evidence-grounding clause fails → reject ``new_token_gate_failed``."""
    items = [{
        "driver_name": "china_blackwell_sales",
        "evidence": ["SRC:NEWS:1"],
        "evidence_text": "China sales rose broadly across the lineup.",
    }]
    ok, reason = V14_new_token_gate("china_blackwell_sales", items, registry, vocab)
    assert ok is False
    assert reason == "new_token_gate_failed"
