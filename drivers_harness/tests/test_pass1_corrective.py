"""Pass-1 CORRECTIVE-ROUND regression + missing-K tests (2026-05-29).

These tests lock in the SIX fixes from the Pass-1 corrective round (the bugs the
green 180-test suite missed; independent review found 3 real code bugs + gaps).
Each test cites the K/# it covers and derives its EXPECTED outcome from the SPEC
rule (DriverOntology_Implementation.md §C step 4.5 v11-2 / §D.1 freeze_known_atoms
/ §E V13 / §F.7 R7), never guessed. No skips, no xfails, no trivial asserts.

Fix map:
  #3 / K15  — multi-token XBRL ban (us_gaap_revenue → banned_token/xbrl_prefix).
  K12-person — multi-token person-name ban (elon_musk_*, tim_cook_* → identity_person).
  K14       — provider ban (benzinga_revenue → provider).
  K24       — effect ban (selloff → effect).
  #4        — multi-token OBJECTS classify whole (vision_pro_sales / cloud_service_revenue ACCEPT).
  #5        — V13 orphan-proposal scan in run_one (proposal_without_use).
  K17       — stopword strip (the_of_in → empty_after_stopword_strip; interior stopword folds out).
  K26       — motion/change-noun ban (revenue_collapse / collapse_revenue → motion_change).
  K53       — same-canonical collision flagged in run_one (self_consistency).
  bucket K  — vision_pro / cloud_service round-trip; us_gaap NOT in idempotency list.

ROOT-CAUSE of #3 and #4: §C step 4.5 now freezes the FULL set of known multi-token
atoms (VocabSnapshot.frozen_atoms = every "_"-containing entry across shortcuts ∪
compound_metrics ∪ slot_vocabs ∪ banned). A multi-token OBJECT stays whole for
step-9 classification; a multi-token BANNED phrase stays whole for the step-7 ban.

Pure offline (no LLM, no network, stdlib only).
"""

from __future__ import annotations

import pytest

from vocab_seed import build_vocab_snapshot, banned_category
from driver_ids import canonicalize, Rejection
from validators import V4_segment_consistent, V14_new_token_gate
from registry_fake import Registry
from reuse import reuse_or_propose, _new_slot_tokens
from run_one import run_one


@pytest.fixture(scope="module")
def vocab():
    """Frozen VocabSnapshot from the §F seeds (build_vocab_snapshot), now carrying
    the v11-2 derived frozen_atoms field + the K26 motion_change banned category."""
    return build_vocab_snapshot()


@pytest.fixture(scope="module")
def registry():
    """The scenario registry (fixtures/fake_registry.json)."""
    return Registry.from_fixture()


def _emission(items, *, proposals=None, source_catalog=None):
    """Minimal production-shape WRITER emission JSON (Harness §5) so the S3 shape
    gate passes and run_one exercises B1..B10 + V1..V14 + the emission-level passes."""
    return {
        "source_id": "TEST_2026-01-01",
        "source_type": "learner_result",
        "pit_cutoff": "2026-01-01T00:00:00Z",
        "run_id": "run-corrective",
        "result_path": "/tmp/corrective.json",
        "source_catalog": list(source_catalog or ["SRC:NEWS:1"]),
        "items": items,
        "propose_new_drivers": list(proposals or []),
    }


# ════════════════════════════════════════════════════════════════════════════
# FIX 1 (#3 / K15) — multi-token XBRL prefix ban (the bug: us_gaap split bypassed
# the per-token ban and wrongly ACCEPTED). v11-2 freeze keeps us_gaap whole so the
# §C step-7 ban catches it.
# ════════════════════════════════════════════════════════════════════════════

def test_xbrl_us_gaap_revenue_banned_K15(vocab):
    """#3 / K15 (multi-token XBRL prefix). §F.7 xbrl_prefix {us_gaap, ifrs, dei}.
    BEFORE the v11-2 freeze, ``us_gaap_revenue`` tokenized to [us, gaap, revenue]
    and slid past the per-token ban (us/gaap are not single-token banned) → it
    wrongly ACCEPTED. §C step 4.5 freeze_known_atoms now keeps ``us_gaap`` whole so
    the step-7 ban fires. EXPECT banned_token / xbrl_prefix on token 'us_gaap'."""
    r = canonicalize("us_gaap_revenue", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "banned_token"
    assert r.token == "us_gaap"
    assert r.category == "xbrl_prefix"


# ════════════════════════════════════════════════════════════════════════════
# FIX 1 (K12-person) — multi-token person-name ban (now catchable via the v11-2
# freeze of multi-token person names).
# ════════════════════════════════════════════════════════════════════════════

def test_person_elon_musk_guidance_banned_K12(vocab):
    """K12-person (identity person name). §F.7 identity persons {elon_musk,
    tim_cook, ...}. The v11-2 freeze keeps ``elon_musk`` whole so the step-7 ban
    fires (without it, [elon, musk] slipped past). EXPECT banned_token /
    identity_person on token 'elon_musk'."""
    r = canonicalize("elon_musk_guidance", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "banned_token"
    assert r.token == "elon_musk"
    assert r.category == "identity_person"


def test_person_tim_cook_sales_banned_K12(vocab):
    """K12-person (identity person name). §F.7 identity persons. ``tim_cook`` frozen
    whole by §C step 4.5 → step-7 ban. EXPECT banned_token / identity_person on
    token 'tim_cook'."""
    r = canonicalize("tim_cook_sales", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "banned_token"
    assert r.token == "tim_cook"
    assert r.category == "identity_person"


# ════════════════════════════════════════════════════════════════════════════
# FIX 5 (K14) — provider ban (single-token, but a regression guard).
# ════════════════════════════════════════════════════════════════════════════

def test_provider_benzinga_revenue_banned_K14(vocab):
    """K14 (data provider label). §F.7 provider {fiscalai, bloomberg, refinitiv,
    factset, benzinga, polygon}. ``benzinga`` is single-token banned → step-7 ban.
    EXPECT banned_token / provider on token 'benzinga'."""
    r = canonicalize("benzinga_revenue", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "banned_token"
    assert r.token == "benzinga"
    assert r.category == "provider"


# ════════════════════════════════════════════════════════════════════════════
# FIX 5 (K24) — effect-on-stock ban.
# ════════════════════════════════════════════════════════════════════════════

def test_effect_stock_selloff_banned_K24(vocab):
    """K24 (effect-on-stock word). §F.7 effect {selloff, rally, reaction,
    disappointment, surprise_factor}. ``stock`` is UNKNOWN but ``selloff`` is the
    first-fired banned token in step-7's per-token scan (step 7 runs BEFORE slot
    classification). EXPECT banned_token / effect on token 'selloff'."""
    r = canonicalize("stock_selloff", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "banned_token"
    assert r.token == "selloff"
    assert r.category == "effect"


def test_effect_selloff_revenue_banned_K24(vocab):
    """K24 (effect-on-stock word, leading). §F.7 effect. ``selloff_revenue`` →
    ``selloff`` is banned (effect). EXPECT banned_token / effect on token 'selloff'."""
    r = canonicalize("selloff_revenue", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "banned_token"
    assert r.token == "selloff"
    assert r.category == "effect"


# ════════════════════════════════════════════════════════════════════════════
# FIX 1 (#4) — multi-token OBJECTS classify whole → ACCEPT (canonicalize to self).
# BEFORE the v11-2 freeze, vision_pro/cloud_service split into two UNKNOWNs →
# slot_ambiguous (false reject). The freeze keeps the object whole.
# ════════════════════════════════════════════════════════════════════════════

def test_object_vision_pro_sales_accepts(vocab):
    """#4 (multi-token OBJECT). §F.1 OBJECTS contains ``vision_pro``. The v11-2
    freeze keeps it whole so step 9 classify_token sees ONE object → object(1) _
    metric(sales,5) is a valid 2-slot name. EXPECT canonical 'vision_pro_sales'
    (NOT slot_ambiguous)."""
    r = canonicalize("vision_pro_sales", vocab)
    assert r == "vision_pro_sales"


def test_object_cloud_service_revenue_accepts(vocab):
    """#4 (multi-token OBJECT). §F.1 OBJECTS contains ``cloud_service``. Frozen
    whole by §C step 4.5 → object(cloud_service) _ metric(revenue). EXPECT canonical
    'cloud_service_revenue' (NOT slot_ambiguous)."""
    r = canonicalize("cloud_service_revenue", vocab)
    assert r == "cloud_service_revenue"


# ════════════════════════════════════════════════════════════════════════════
# FIX 2 (#5) — V13 orphan-proposal scan in run_one (emission-level).
# A propose_new entry NOT referenced by any resolved item → proposal_without_use.
# ════════════════════════════════════════════════════════════════════════════

def test_orphan_proposal_rejected_V13_in_run_one(vocab, registry):
    """#5 / §E V13 (proposal_without_use), emission-level. A
    ``propose_new_drivers[]`` entry that NO item's resolved canonical name
    references is an orphan — run_one's emission-level pass records a V13 rejection
    ``proposal_without_use`` and keeps it out of ``proposed[]``. The only item here
    resolves to the EXISTING driver ``revenue``, so the proposal
    ``gpu_blackwell_us_revenue`` is never used. EXPECT the proposal in
    decision['rejected'] with reason proposal_without_use, and NOT in
    decision['proposed']."""
    proposal = {
        "name": "gpu_blackwell_us_revenue",
        "label": "GPU Blackwell US revenue",
        "segment": "GPU Blackwell US",
        "definition": "Revenue from Blackwell GPUs sold in the US.",
        "allowed_states": ["accelerated", "decelerated"],
        "aliases": [],
    }
    item = {
        "ticker": "NVDA", "driver_name": "revenue", "driver_state": "beat",
        "direction": "long", "evidence": ["SRC:NEWS:1"],
    }
    decision = run_one(_emission([item], proposals=[proposal]), registry, vocab)
    assert {"name": "gpu_blackwell_us_revenue", "reason": "proposal_without_use"} in decision["rejected"]
    assert "gpu_blackwell_us_revenue" not in decision["proposed"]


def test_used_proposal_not_flagged_orphan_V13(vocab, registry):
    """#5 / §E V13 (negative control). A proposal that IS referenced by an item
    with non-empty evidence is NOT an orphan — run_one must NOT add a
    proposal_without_use rejection for it. ``cloud_capex`` (theme cloud + metric
    capex, both known tokens) is proposed AND used by its own tag. EXPECT
    'cloud_capex' in proposed[] and NO proposal_without_use rejection."""
    proposal = {
        "name": "cloud_capex",
        "label": "cloud capex",
        "base_label": "CapEx",
        # `cloud` is a THEME (not a geography/customer/object sub-dimension), so V4
        # requires segment == "Total" (a theme is not a segment sub-token).
        "segment": "Total",
        "definition": "Capital expenditure on cloud infrastructure.",
        "allowed_states": ["accelerated", "decelerated", "stable", "declined"],
        "aliases": [],
    }
    item = {
        "ticker": "MSFT", "driver_name": "cloud_capex", "driver_state": "accelerated",
        "direction": "long", "evidence": ["SRC:NEWS:1"],
    }
    decision = run_one(_emission([item], proposals=[proposal]), registry, vocab)
    assert "cloud_capex" in decision["proposed"]
    assert all(r["reason"] != "proposal_without_use" for r in decision["rejected"])


# ════════════════════════════════════════════════════════════════════════════
# FIX 5 (K17) — stopwords: stopword-only name rejects; interior stopword folds out.
# ════════════════════════════════════════════════════════════════════════════

def test_stopword_only_name_empty_after_strip_K17(vocab):
    """K17 (stopword-only). §C step 4 strips §F.8 STOPWORDS {the, of, in, ...}.
    ``the_of_in`` is ALL stopwords → empty token list → EXPECT
    empty_after_stopword_strip."""
    r = canonicalize("the_of_in", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "empty_after_stopword_strip"


def test_interior_stopword_folds_out_K17(vocab):
    """K17 (interior stopword). §C step 4 removes the interior stopword ``in`` so
    ``iphone_in_china_sales`` → [iphone, china, sales] → canonical
    'iphone_china_sales' (object + geography + metric). EXPECT 'iphone_china_sales'."""
    r = canonicalize("iphone_in_china_sales", vocab)
    assert r == "iphone_china_sales"


# ════════════════════════════════════════════════════════════════════════════
# FIX 3 (K26) — motion/change-noun ban (the newly seeded §F.7/R7 category).
# ════════════════════════════════════════════════════════════════════════════

def test_motion_noun_revenue_collapse_banned_K26(vocab):
    """K26 (motion/change noun). §F.7/R7 "motion or change nouns" category — seeded
    in the corrective round as motion_change {collapse, surge, rebound, plunge,
    recovery, slump, spike, drop, jump, decline}. ``revenue_collapse`` smuggles the
    MOVEMENT into the name (the driver is ``revenue``; the move is the OUTCOME).
    EXPECT banned_token / motion_change on token 'collapse'."""
    r = canonicalize("revenue_collapse", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "banned_token"
    assert r.token == "collapse"
    assert r.category == "motion_change"


def test_motion_noun_collapse_revenue_banned_K26(vocab):
    """K26 (motion/change noun, leading). §F.7/R7 motion_change. ``collapse_revenue``
    → ``collapse`` is the first-fired banned token. EXPECT banned_token /
    motion_change on token 'collapse'."""
    r = canonicalize("collapse_revenue", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "banned_token"
    assert r.token == "collapse"
    assert r.category == "motion_change"


def test_motion_change_category_resolves_via_banned_category(vocab):
    """K26 (banned_category surfacing). banned_category() must return the
    'motion_change' category string for a seeded motion noun (so the category is
    observable, not just a generic ban). EXPECT 'motion_change' for 'collapse'."""
    assert banned_category("collapse", vocab) == "motion_change"


# ════════════════════════════════════════════════════════════════════════════
# FIX 4 (K53) — same-canonical collision flagged in run_one (self_consistency).
# Two raw names that canonicalize to the SAME name within ONE emission → flagged.
# ════════════════════════════════════════════════════════════════════════════

def test_same_canonical_collision_flagged_K53(vocab, registry):
    """K53 (self-consistency collision). Two items with raw names
    ``iphone_china_sales`` AND ``china_iphone_sales`` BOTH canonicalize to
    ``iphone_china_sales`` (§C step-10 word-order fold). run_one's emission-level
    self-consistency pass flags this so the writer never silently accepts two raw
    names for one driver. EXPECT decision['self_consistency'] to contain a record
    for canonical 'iphone_china_sales' listing BOTH raw names. NOTE: this is NOT
    V12 (V12 detects duplicate proposal NAMES only; it does not cover K53)."""
    it1 = {
        "ticker": "AAPL", "driver_name": "iphone_china_sales", "driver_state": "beat",
        "direction": "long", "evidence": ["SRC:NEWS:1"],
    }
    it2 = {
        "ticker": "AAPL", "driver_name": "china_iphone_sales", "driver_state": "beat",
        "direction": "long", "evidence": ["SRC:NEWS:1"],
    }
    decision = run_one(_emission([it1, it2]), registry, vocab)
    collisions = decision["self_consistency"]
    assert len(collisions) == 1
    rec = collisions[0]
    assert rec["canonical_name"] == "iphone_china_sales"
    assert sorted(rec["raw_names"]) == ["china_iphone_sales", "iphone_china_sales"]


def test_no_false_collision_distinct_canonicals_K53(vocab, registry):
    """K53 (negative control). Two items whose raw names canonicalize to DIFFERENT
    canonical names are NOT a collision — self_consistency must stay empty. EXPECT
    decision['self_consistency'] == []."""
    it1 = {
        "ticker": "AAPL", "driver_name": "iphone_china_sales", "driver_state": "beat",
        "direction": "long", "evidence": ["SRC:NEWS:1"],
    }
    it2 = {
        "ticker": "AAPL", "driver_name": "revenue", "driver_state": "beat",
        "direction": "long", "evidence": ["SRC:NEWS:1"],
    }
    decision = run_one(_emission([it1, it2]), registry, vocab)
    assert decision["self_consistency"] == []


# ════════════════════════════════════════════════════════════════════════════
# CORRECTIVE ROUND 2 (2026-05-29) — the 3 bugs the green 202-suite still missed.
# ════════════════════════════════════════════════════════════════════════════

# ────────────────────────────────────────────────────────────────────────────
# FIX #1 — atom-aware tokenization EVERYWHERE a name is re-split. The v11-2 freeze
# fixed canonicalize, but V4_segment_consistent, V14_new_token_gate, and
# reuse._new_slot_tokens still did a RAW name.split('_') and shattered a
# multi-token atom (vision_pro -> [vision, pro]). split_respecting_atoms (greedy
# longest-match over vocab.frozen_atoms) keeps the object WHOLE in those callers.
# ────────────────────────────────────────────────────────────────────────────

def test_V4_vision_pro_segment_matches_multitoken_object_FIX1(vocab):
    """FIX #1 / §E V4 (segment) / §C v11-3 note (re-split must respect atoms). The
    name ``vision_pro_sales`` has sub-dimension OBJECT ``vision_pro`` (a §F.1
    multi-token object). With ``split_respecting_atoms`` V4 sees ONE object sub-token
    ``vision_pro`` → segment ``"Vision Pro"`` (slug ``vision_pro``) MATCHES → ok=True.
    BEFORE the fix the raw split shattered it to [vision, pro, sales] (neither a slot
    token) → V4 saw NO sub-dimension → wrongly required ``"Total"`` → false reject."""
    ok, reason = V4_segment_consistent("Vision Pro", "vision_pro_sales", vocab)
    assert ok is True
    assert reason is None


def test_V4_total_rejected_when_multitoken_object_present_FIX1(vocab):
    """FIX #1 / §E V4 (segment). ``vision_pro`` IS a sub-dimension object, so a
    segment of ``"Total"`` is inconsistent with ``vision_pro_sales`` → reject
    ``segment_inconsistent_with_name``. (The atom-aware split now correctly DETECTS
    the sub-dimension, where the raw split missed it and wrongly accepted Total.)"""
    ok, reason = V4_segment_consistent("Total", "vision_pro_sales", vocab)
    assert ok is False
    assert reason == "segment_inconsistent_with_name"


def test_new_slot_tokens_treats_vision_pro_as_one_object_FIX1(vocab, registry):
    """FIX #1 / reuse._new_slot_tokens / §15.0 VocabToken seam. ``vision_pro`` is a
    KNOWN §F.1 object literal, so a proposal ``vision_pro_sales`` introduces NO novel
    slot token → ``_new_slot_tokens`` returns []. BEFORE the fix the raw split emitted
    spurious novel tokens {vision, pro} (mis-classified to the metric slot)."""
    assert _new_slot_tokens("vision_pro_sales", registry, vocab) == []


def test_new_slot_tokens_treats_cloud_service_as_one_object_FIX1(vocab, registry):
    """FIX #1 / reuse._new_slot_tokens. ``cloud_service`` is a KNOWN §F.1 object, so
    ``cloud_service_revenue`` introduces NO novel slot token → []. BEFORE the fix the
    raw split emitted a spurious novel token ``service``."""
    assert _new_slot_tokens("cloud_service_revenue", registry, vocab) == []


def test_V14_treats_vision_pro_as_one_known_object_FIX1(vocab, registry):
    """FIX #1 / §E V14 (new-token gate) / §D. Every token in ``vision_pro_sales`` is
    KNOWN (object ``vision_pro`` + metric ``sales``), so V14 finds NO novel token and
    PASSES (no spurious new_token_gate_failed). BEFORE the fix the raw split fed
    [vision, pro] as two novel tokens whose evidence-grounding the gate had to check.
    The evidence here mentions neither fragment, so the pre-fix gate would have
    wrongly FAILED — this asserts it now passes."""
    items = [{
        "driver_name": "vision_pro_sales",
        "evidence": ["SRC:NEWS:1"],
        "evidence_text": "Quarterly results discussed product sales.",
    }]
    ok, reason = V14_new_token_gate("vision_pro_sales", items, registry, vocab)
    assert ok is True
    assert reason is None


def test_V14_cloud_service_one_known_object_FIX1(vocab, registry):
    """FIX #1 / §E V14. ``cloud_service`` (object) + ``revenue`` (metric) are both
    KNOWN, so the gate finds no novel token → PASS. (Atom-aware split keeps
    ``cloud_service`` whole; the raw split would have made ``service`` a novel token
    requiring evidence grounding.)"""
    items = [{
        "driver_name": "cloud_service_revenue",
        "evidence": ["SRC:NEWS:1"],
        "evidence_text": "Total revenue was reported.",
    }]
    ok, reason = V14_new_token_gate("cloud_service_revenue", items, registry, vocab)
    assert ok is True
    assert reason is None


# ────────────────────────────────────────────────────────────────────────────
# FIX #2 — freeze BEFORE the stopword strip (§C v11-3 reorder). The §F.6 compounds
# cost_of_revenue / cost_of_goods_sold CONTAIN the §F.8 stopword `of`. Under the OLD
# v11-2 order the strip ran first and removed `of` before the freeze could match the
# atom, so the compound shattered and rejected. v11-3 freezes at step 3.5 (BEFORE the
# strip; the strip skips frozen atoms) so the compound survives whole and ACCEPTS.
# (The cost_of_* round-trips are ALSO asserted in test_idempotency.py bucket-K.)
# ────────────────────────────────────────────────────────────────────────────

def test_cost_of_revenue_accepts_FIX2(vocab):
    """FIX #2 / §C v11-3 (freeze at step 3.5 BEFORE stopword-strip). ``cost_of_revenue``
    is a §F.6 COMPOUND_METRIC whose interior ``of`` is a §F.8 stopword. v11-3 freezes
    the whole atom before the strip (and the strip skips frozen atoms), so it
    canonicalizes to ITSELF. EXPECT 'cost_of_revenue' (NOT slot_ambiguous)."""
    assert canonicalize("cost_of_revenue", vocab) == "cost_of_revenue"


def test_cost_of_goods_sold_accepts_FIX2(vocab):
    """FIX #2 / §C v11-3. ``cost_of_goods_sold`` is a §F.6 COMPOUND_METRIC containing
    the §F.8 stopword ``of`` (and the -ed token ``sold``). Frozen whole at step 3.5 →
    the strip never removes ``of`` and step-5/7 never touch the atom interior → it
    canonicalizes to ITSELF. EXPECT 'cost_of_goods_sold'
    (NOT slot_anchor_unavailable)."""
    assert canonicalize("cost_of_goods_sold", vocab) == "cost_of_goods_sold"


def test_bare_margin_still_folds_after_reorder_FIX2(vocab):
    """FIX #2 (negative control / §C v11-3). The reorder must NOT suppress a single-
    token fold: bare ``margin`` (a §F.2 SYNONYM key, NOT a frozen multi-token atom)
    still folds to ``gross_margin`` at step 5. EXPECT 'gross_margin'."""
    assert canonicalize("margin", vocab) == "gross_margin"


def test_interior_stopword_still_strips_after_reorder_FIX2(vocab):
    """FIX #2 (negative control / §C v11-3). An interior stopword that is NOT inside a
    frozen atom still strips: ``iphone_in_china_sales`` → ``iphone_china_sales`` (``in``
    removed). The reorder only protects frozen-atom interiors, not free stopwords."""
    assert canonicalize("iphone_in_china_sales", vocab) == "iphone_china_sales"


def test_all_stopword_name_still_rejects_after_reorder_FIX2(vocab):
    """FIX #2 (negative control / §C v11-3). A name that is ALL free stopwords still
    rejects: ``the_of_in`` → empty token list → empty_after_stopword_strip. (None of
    these spans form a frozen atom, so none are protected.)"""
    r = canonicalize("the_of_in", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "empty_after_stopword_strip"


# ────────────────────────────────────────────────────────────────────────────
# FIX #3 — ban §F.7 direction {long,short,up,down} + magnitude_word
# {large,small,big,huge,tiny,minor,major,modest,slight,significant,substantial}.
# These describe trade-direction / which-way / SIZE, not a reusable cause → banned
# from a NAME (banning long/short as NAME tokens does NOT touch V9's direction-FIELD
# enum {long,short} — different context).
# ────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("name,token", [
    ("gpu_short_us_revenue", "short"),
    ("gpu_long_us_revenue", "long"),
    ("gpu_up_us_revenue", "up"),
    ("gpu_down_us_revenue", "down"),
])
def test_direction_word_in_name_banned_FIX3(name, token, vocab):
    """FIX #3 / §F.7 direction {long, short, up, down}. A direction/polarity word in a
    NAME is banned (trade direction long/short belongs in the ``direction`` FIELD;
    up/down describe movement). EXPECT banned_token / direction on the direction
    token. (banned step 7 runs per-token before slot classification, so the leftmost
    banned token — here the direction word after the known object ``gpu``— fires.)"""
    r = canonicalize(name, vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "banned_token"
    assert r.token == token
    assert r.category == "direction"


@pytest.mark.parametrize("name,token", [
    ("gpu_large_us_revenue", "large"),
    ("gpu_small_us_revenue", "small"),
])
def test_magnitude_word_in_name_banned_FIX3(name, token, vocab):
    """FIX #3 / §F.7 magnitude_word. A qualitative-size word in a NAME is banned (it
    describes SIZE, not a reusable cause). EXPECT banned_token / magnitude_word on the
    size token."""
    r = canonicalize(name, vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "banned_token"
    assert r.token == token
    assert r.category == "magnitude_word"


def test_direction_magnitude_resolve_via_banned_category_FIX3(vocab):
    """FIX #3 / banned_category() surfacing. The category strings must be observable
    (not just a generic ban) so callers/tests can assert WHY. EXPECT 'direction' for
    'long'/'short'/'up'/'down' and 'magnitude_word' for 'large'/'small'/'huge'."""
    for t in ("long", "short", "up", "down"):
        assert banned_category(t, vocab) == "direction"
    for t in ("large", "small", "huge", "significant", "substantial"):
        assert banned_category(t, vocab) == "magnitude_word"


def test_V9_direction_enum_unaffected_by_ban_FIX3():
    """FIX #3 (no-conflict control) / §E V9. Banning long/short as NAME tokens (§F.7)
    must NOT change V9's direction-FIELD enum {long, short} — a different context (a
    companion field value vs a name token). V9 still accepts 'long'/'short' as field
    values. EXPECT V9('long') and V9('short') ok=True; V9('up') ok=False."""
    from validators import V9_direction
    assert V9_direction("long") == (True, None)
    assert V9_direction("short") == (True, None)
    ok, reason = V9_direction("up")
    assert ok is False
    assert reason == "invalid_direction_enum"


def test_explicit_allow_real_compounds_despite_banned_bare_word_FIX3(vocab):
    """FIX #3 (explicit-ALLOW half) / §F.6 + §C step-3.5 freeze (owner-approved 2026-05-29).
    Strict ban on LOOSE direction words, but legit multi-token METRICS that CONTAIN one
    (short_interest, long_term_debt, short_term_debt — seeded in §F.6 COMPOUND_METRICS) must
    ACCEPT: freeze keeps each whole, so the step-7 bare-`short`/`long` ban never sees a lone
    banned token. EXPECT each round-trips to itself; bare `short`/`long` names still REJECT.
    (Closes the seed gap surfaced in tester review — the round-2 workflow banned the bare
    words but launched before the explicit-allow seed.)"""
    for name in ("short_interest", "long_term_debt", "short_term_debt"):
        assert canonicalize(name, vocab) == name, f"{name!r} must accept + round-trip to itself"
    for bad in ("gpu_short_us_revenue", "gpu_long_us_revenue"):
        r = canonicalize(bad, vocab)
        assert isinstance(r, Rejection) and r.reason == "banned_token" and r.category == "direction"


def test_reuse_propose_accepts_seeded_compounds_FULL_PATH_round3(vocab):
    """ROUND-3 #1 / §F.6 + §C step-3.5 freeze — at the PRODUCTION-PATH level (the gap a
    canonicalize-only test missed). A seeded compound that CONTAINS a bare-banned word
    (short_interest/long_term_debt/short_term_debt) must survive `reuse_or_propose()` —
    NOT just `canonicalize()` — without a `banned_token` reject. The B9 defence-in-depth
    banned re-check (reuse.py) must atom-aware-split the canonical name, else `short` is
    seen alone and wrongly rejected. EXPECT PROPOSE_NEW / reason None. ANTI-RECURRENCE
    GUARD: if any reuse-path name-split reverts to a raw `split('_')`, this fails."""
    reg = Registry.from_fixture()
    for nm in ("short_interest", "long_term_debt", "short_term_debt"):
        tpl = {"name": nm, "label": nm.replace("_", " ").title(), "segment": "Total",
               "definition": f"The {nm.replace('_', ' ')} measure for the period.",
               "allowed_states": ["accelerated", "decelerated", "stable", "declined"]}
        r = reuse_or_propose(nm, ["SRC:NEWS:1"], reg, vocab,
                             proposal_template=tpl, evidence_text=f"{nm.replace('_', ' ')} rose")
        assert r.status == "PROPOSE_NEW" and r.reason is None, (
            f"{nm!r} must survive the full reuse/propose path; got {r.status}/{r.reason}")


def test_V4_multitoken_object_plus_subdimension_round3(vocab):
    """ROUND-3 #2 / §E V4. After the name side went atom-aware (v11-3), the SEGMENT side
    must ALSO be atom-aware — else a multi-token OBJECT next to ANOTHER sub-dimension
    (object+geography, object+customer) mismatches and wrongly rejects. EXPECT: a segment
    naming the full sub-dim set PASSES; 'Total' for a name that HAS sub-dims REJECTS."""
    assert V4_segment_consistent("Vision Pro China", "vision_pro_china_sales", vocab) == (True, None)
    assert V4_segment_consistent("Cloud Service Enterprise", "cloud_service_enterprise_revenue", vocab) == (True, None)
    ok, reason = V4_segment_consistent("Total", "vision_pro_china_sales", vocab)
    assert ok is False and reason == "segment_inconsistent_with_name"
