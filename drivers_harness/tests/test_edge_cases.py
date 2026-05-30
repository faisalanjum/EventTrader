"""Edge-cases bucket — the toughest adversarial/boundary set for Pass 1.

Covers (Harness_BuilderPrompt.md §6 "ADVERSARIAL + BOUNDARY", bucket B, bucket G):
  - Bucket B banned content (K7-K17, K20, K24, K25 / B-R7a..m): REJECT with the
    named token + category.
  - Bucket G new-driver gate (R11 / V14 / B-R11a..g, K18, K58): PROPOSE_NEW vs
    hallucination-reject vs slot_anchor_unavailable vs one-off durability.
  - Stacked-violation first-fired reason; exact 4/5 slot boundaries; fold+dedup
    combos; multi-variable A2/K22 split.
  - Doubts #11 (forward_guidance vs guidance_lowered), #13 (two geographies ->
    slot_collision), #44 (direction may be inferred, not verbatim).

Every EXPECTED outcome is derived from the SPEC rule cited in the docstring:
  - DriverOntology_Implementation.md §C (canonicalize steps), §D (shape + BNF +
    new-token gate clauses a-e), §D.1 (resolve_unknown_slots / order_by_slot),
    §E (V9/V14), §F.5 STATES, §F.7 BANNED_CONTENT, §G MAX_EFFECTIVE_SLOTS=4.
  - DriverOntology.md R2/R3/R5/R7/R8/R9/R11.
  - _workflow/req_canonical.md K-risks + B-R rows.

Pure offline (no LLM, no network). canonicalize() rejections are direct-call
shape-gated; reuse/run_one paths slug-normalize first (§6 bucket A split).

SURFACED (see this file's module-level note + the agent return report):
  * The brief's bucket-G example ``blackwell_revenue`` (a lone novel token
    DIRECTLY before the metric) does NOT canonicalize to ACCEPT under the spec's
    §D.1 resolve_unknown_slots: a single UNKNOWN token before <metric> has FIVE
    candidate slots (theme/object/customer/geography/institution) -> len(free)!=1
    -> REJECTION_SLOT_AMBIGUOUS (fail-closed "never guess", §D.1). This is a
    SPEC-vs-brief-prose tension, NOT an impl bug: the implementation faithfully
    follows §D.1. The spec-faithful ACCEPT form needs the novel token's slot to
    be POSITIONALLY UNIQUE (§D clause c / R11), so the ACCEPT test below uses
    ``gpu_blackwell_us_revenue`` (object _ UNKNOWN _ geography _ metric -> the
    only free slot between object(1) and geography(3) is customer(2) -> unique).
    The bare ``blackwell_revenue`` case is kept as an explicit slot_ambiguous
    test documenting the tension. diagnosis=spec-contradiction-surfaced (brief
    prose vs §D.1); no impl edit.
"""

from __future__ import annotations

import pytest

from vocab_seed import build_vocab_snapshot
from driver_ids import canonicalize, Rejection
from registry_fake import Registry
from reuse import reuse_or_propose
from run_one import run_one


@pytest.fixture(scope="module")
def vocab():
    """The frozen VocabSnapshot built from the §F seeds (build_vocab_snapshot)."""
    return build_vocab_snapshot()


@pytest.fixture(scope="module")
def registry():
    """The scenario registry (fixtures/fake_registry.json) — cold-start anchors
    PLUS modern scenario drivers (iphone_china_sales, gross_margin, ...)."""
    return Registry.from_fixture()


def _emission(items, *, proposals=None, source_catalog=None):
    """Build a minimal production-shape WRITER emission JSON (Harness §5) so the
    S3 shape gate passes and run_one exercises B1..B10 + V1..V14."""
    return {
        "source_id": "TEST_2026-01-01",
        "source_type": "learner_result",
        "pit_cutoff": "2026-01-01T00:00:00Z",
        "run_id": "run-edge",
        "result_path": "/tmp/edge.json",
        "source_catalog": list(source_catalog or ["SRC:NEWS:1"]),
        "items": items,
        "propose_new_drivers": list(proposals or []),
    }


# ════════════════════════════════════════════════════════════════════════════
# BUCKET B — banned content (REJECT with the named token + category)
# Collision-free representatives; canonicalize() is the DIRECT entry point.
# ════════════════════════════════════════════════════════════════════════════

def test_B_state_verb_cut_in_name_opec_supply_cut(vocab):
    """B-R7a / K7 (state verb baked into name). DriverOntology.md R7 + §C step 7
    state check + §F.5 quantity_move ``cut``. ``opec_supply_cut`` -> the correct
    form is ``opec_supply`` (shortcut) + state ``cut``; the verb must NOT enter
    the name. EXPECT REJECTION_STATE_IN_NAME(token='cut')."""
    r = canonicalize("opec_supply_cut", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "state_in_name"
    assert r.token == "cut"


def test_B_state_verb_lowered_guidance_lowered(vocab):
    """B-R7a / K7 + doubt #11. §F.5 financial_outcome ``lowered`` is a STATE;
    the correct form is ``forward_guidance`` + state ``lowered`` — NOT a name
    with the state baked in. EXPECT REJECTION_STATE_IN_NAME(token='lowered')."""
    r = canonicalize("guidance_lowered", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "state_in_name"
    assert r.token == "lowered"


def test_B_ticker_aapl_iphone_sales(vocab):
    """B-R7d / K12 (ticker). §F.7 identity tickers (BANNED_TICKERS offline seed,
    Harness §4). ``aapl`` is first-fired. EXPECT banned_token / identity_ticker."""
    r = canonicalize("aapl_iphone_sales", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "banned_token"
    assert r.token == "aapl"
    assert r.category == "identity_ticker"


def test_B_company_apple_china_sales(vocab):
    """B-R7d / K12 (legal company name). §F.7 identity company set. ``apple`` is
    first-fired. EXPECT banned_token / identity_company."""
    r = canonicalize("apple_china_sales", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "banned_token"
    assert r.token == "apple"
    assert r.category == "identity_company"


def test_B_period_q3_revenue(vocab):
    """B-R7e / K10 (period token). §F.7 period pattern ^(q\\d|...)$. ``q3``
    matches. EXPECT banned_token / period."""
    r = canonicalize("q3_revenue", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "banned_token"
    assert r.token == "q3"
    assert r.category == "period"


def test_B_numeric_magnitude_non_leading_margin_100bps(vocab):
    """B-R7f / K11 (numeric magnitude). §F.7 numeric pattern ^\\d. The magnitude
    token must NOT lead — a leading-digit token (``100bps_margin``) fails the
    SHAPE gate (step 1) first (regex starts ^[a-z]). So we place ``100bps`` SECOND
    (``margin_100bps``) where it survives the shape gate and is caught by the §C
    step-7 numeric ban. EXPECT banned_token / numeric on token '100bps'."""
    r = canonicalize("margin_100bps", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "banned_token"
    assert r.token == "100bps"
    assert r.category == "numeric"


def test_B_leading_magnitude_fails_shape_first_100bps_margin(vocab):
    """B-R7f / K11 ordering note. A LEADING-digit token fails the §C step-1 SHAPE
    gate BEFORE the step-7 numeric ban can fire. Documents why the numeric-ban
    representative above is non-leading. EXPECT invalid_slug_shape (NOT
    banned_token)."""
    r = canonicalize("100bps_margin", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "invalid_slug_shape"


def test_B_sentiment_bullish_guidance(vocab):
    """B-R7j / K20 (sentiment adjective). §F.7 sentiment set ``bullish``.
    EXPECT banned_token / sentiment."""
    r = canonicalize("bullish_guidance", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "banned_token"
    assert r.token == "bullish"
    assert r.category == "sentiment"


def test_B_source_type_leading_letter_transcript_revenue(vocab):
    """B-R7g / K13 (source-type label). §F.7 source_type set. We use a
    LEADING-LETTER source token (``transcript``) because a leading-DIGIT source
    token like ``8k`` fails the SHAPE gate first (^[a-z]...). EXPECT banned_token
    / source_type on 'transcript'."""
    r = canonicalize("transcript_revenue", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "banned_token"
    assert r.token == "transcript"
    assert r.category == "source_type"


def test_B_metaphor_headwind_revenue(vocab):
    """B-R7j / K25 (metaphor). §F.7 metaphor set ``headwind``. EXPECT
    banned_token / metaphor."""
    r = canonicalize("headwind_revenue", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "banned_token"
    assert r.token == "headwind"
    assert r.category == "metaphor"


def test_B_vague_descriptor_outlook(vocab):
    """B-R7l / K19 (vague descriptor as a token). §F.7 vague_descriptor set
    ``outlook``. A bare vague descriptor -> banned. EXPECT banned_token /
    vague_descriptor."""
    r = canonicalize("outlook", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "banned_token"
    assert r.token == "outlook"
    assert r.category == "vague_descriptor"


def test_B_vague_descriptor_momentum(vocab):
    """B-R7l / K19 (vague descriptor). §F.7 vague_descriptor set ``momentum`` —
    fired even when paired with a metric (``momentum_revenue``), since the banned
    check (§C step 7) iterates every token. EXPECT banned_token / vague_descriptor
    on 'momentum'."""
    r = canonicalize("momentum_revenue", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "banned_token"
    assert r.token == "momentum"
    assert r.category == "vague_descriptor"


# ════════════════════════════════════════════════════════════════════════════
# BUCKET G — new-driver gate (R11 / V14 / §D clauses a-e, K18, K58)
# These exercise the reuse.py B9/B10 ladder (new-token gate reads evidence).
# ════════════════════════════════════════════════════════════════════════════

def test_G_novel_token_in_evidence_proposes_new(vocab, registry):
    """B-R11c / §D clause (e) / K58 (evidence-at-registration). A novel token whose
    SLOT IS POSITIONALLY UNIQUE (§D clause c) AND that appears in the evidence text
    -> PROPOSE_NEW. ``gpu_blackwell_us_revenue``: object(gpu,1) _ UNKNOWN _
    geography(us,3) _ metric(revenue,5) -> only free slot between 1 and 3 is
    customer(2) -> unique placement; ``blackwell`` appears in evidence_text ->
    clause (e) satisfied. EXPECT PROPOSE_NEW canonical 'gpu_blackwell_us_revenue'.

    (The brief names bare ``blackwell_revenue`` here, but a lone novel token before
    <metric> is slot_ambiguous under §D.1 — see this module's SURFACED note and
    test_G_bare_novel_token_before_metric_is_slot_ambiguous below.)"""
    r = reuse_or_propose(
        "gpu_blackwell_us_revenue", ["SRC:NEWS:1"], registry, vocab,
        evidence_text="Blackwell GPU revenue in the US accelerated.",
    )
    assert r.status == "PROPOSE_NEW"
    assert r.canonical_name == "gpu_blackwell_us_revenue"
    assert r.reason is None


def test_G_novel_token_not_in_evidence_rejects_hallucination(vocab, registry):
    """B-R11c / §D clause (e) hallucination guard. SAME positionally-unique novel
    token, but ``blackwell`` is ABSENT from the evidence text -> the §D new-token
    gate clause (e) substring check fails -> REJECT new_token_gate_failed (V14).
    EXPECT REJECT reason 'new_token_gate_failed'."""
    r = reuse_or_propose(
        "gpu_blackwell_us_revenue", ["SRC:NEWS:1"], registry, vocab,
        evidence_text="GPU revenue in the US accelerated broadly.",
    )
    assert r.status == "REJECT"
    assert r.reason == "new_token_gate_failed"


def test_G_all_unknown_tokens_slot_anchor_unavailable(vocab, registry):
    """B-R11c / §D.1 resolve_unknown_slots fail-closed + §F.10 EDGE CASE. A name
    of ALL-UNKNOWN tokens has NO known anchor for position-based slot inference ->
    REJECTION_SLOT_ANCHOR_UNAVAILABLE. EXPECT REJECT reason 'slot_anchor_unavailable'."""
    r = reuse_or_propose(
        "zzz_qqq", ["SRC:NEWS:1"], registry, vocab,
        evidence_text="zzz qqq happened.",
    )
    assert r.status == "REJECT"
    assert r.reason == "slot_anchor_unavailable"


def test_G_bare_novel_token_before_metric_is_slot_ambiguous(vocab):
    """SPEC-vs-brief-prose tension (SURFACED). §D.1 resolve_unknown_slots: a lone
    UNKNOWN token directly before <metric> has FIVE free candidate slots
    (theme/object/customer/geography/institution) -> len(free)!=1 -> never-guess
    -> REJECTION_SLOT_AMBIGUOUS. The brief's bucket-G prose names bare
    ``blackwell_revenue`` as ACCEPT, but the spec mechanically rejects it; the impl
    faithfully follows §D.1 (NOT an impl bug). EXPECT slot_ambiguous on 'blackwell'."""
    r = canonicalize("blackwell_revenue", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "slot_ambiguous"
    assert r.token == "blackwell"


def test_G_one_off_single_event_name_rejected_durability(vocab):
    """B-R11e / K18 (durability — single-event scope). A one-off name framed to a
    single company-quarter/keynote event smuggles a PERIOD token, the mechanical
    lever closing K18 here: ``iphone_keynote_q2_2026_revenue`` -> §C step-7 period
    ban fires on ``q2`` (^(q\\d|...)$). EXPECT banned_token / period on 'q2'.
    (The pure semantic "single-use scope" judgment of R11e is LLM-judgment,
    deferred to Layer-2; the deterministic lever is the period/identity ban.)"""
    r = canonicalize("iphone_keynote_q2_2026_revenue", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "banned_token"
    assert r.token == "q2"
    assert r.category == "period"


# ════════════════════════════════════════════════════════════════════════════
# ADVERSARIAL + BOUNDARY (stacked violations, exact slot bounds, fold+dedup)
# ════════════════════════════════════════════════════════════════════════════

def test_ADV_stacked_violations_first_fired_reason(vocab):
    """Harness §6 stacked-violations. ``aapl_q3_iphone_china_sales_cut`` smuggles
    ticker(aapl) + period(q3) + state(cut). §C step-7 iterates tokens in order and
    returns the FIRST-fired reason -> ``aapl`` (ticker) is token[0]. EXPECT
    banned_token / identity_ticker on 'aapl' (the first-fired reason)."""
    r = canonicalize("aapl_q3_iphone_china_sales_cut", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "banned_token"
    assert r.token == "aapl"
    assert r.category == "identity_ticker"


def test_ADV_weak_100bps_margin_decline_rejects_first_fired(vocab):
    """Harness §6 stacked-violations. ``weak_100bps_margin_decline`` smuggles
    sentiment(weak) + numeric(100bps) + state(decline). §C step-7 first-fired ->
    ``weak`` (sentiment) is token[0]. EXPECT banned_token / sentiment on 'weak'."""
    r = canonicalize("weak_100bps_margin_decline", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "banned_token"
    assert r.token == "weak"
    assert r.category == "sentiment"


def test_ADV_exactly_four_effective_slots_accepts(vocab):
    """Harness §6 exact-boundary / R8 + §G MAX_EFFECTIVE_SLOTS=4. A name at EXACTLY
    4 effective slots ACCEPTS. ``ai_iphone_china_sales`` = theme(ai) + object(iphone)
    + geography(china) + metric(sales) = 4 slots -> at the bound, not over. EXPECT
    canonical 'ai_iphone_china_sales' (round-trips to itself)."""
    r = canonicalize("ai_iphone_china_sales", vocab)
    assert r == "ai_iphone_china_sales"


def test_ADV_five_distinct_slots_too_many_slots(vocab):
    """Harness §6 exact-boundary / R8 + §G. FIVE DISTINCT slots exceeds
    MAX_EFFECTIVE_SLOTS=4. ``ai_datacenter_hyperscaler_us_capex`` = theme + object
    + customer + geography + metric = 5 -> §C step-11 too_many_slots (slot-collision
    at step 10 does NOT fire — all five are DISTINCT slots). EXPECT too_many_slots."""
    r = canonicalize("ai_datacenter_hyperscaler_us_capex", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "too_many_slots"


def test_ADV_compound_metric_makes_four_not_five_accepts(vocab):
    """Harness §6 + R6 (compound counts as ONE slot). ``ai_datacenter_us_gross_margin``
    = theme + object + geography + gross_margin(ONE metric slot via §F.6 / §C step
    8.5 rejoin) = 4 effective slots -> ACCEPT (not 5). EXPECT canonical
    'ai_datacenter_us_gross_margin'."""
    r = canonicalize("ai_datacenter_us_gross_margin", vocab)
    assert r == "ai_datacenter_us_gross_margin"


def test_ADV_plural_fold_then_dedup_iphone_iphones_sales(vocab):
    """Harness §6 fold+dedup combo (single deterministic result). §F.3 PLURAL_MAP
    iphones->iphone (§C step 5), then §C step-6 dedup collapses [iphone, iphone,
    sales] -> [iphone, sales]. EXPECT exactly 'iphone_sales' (object + metric)."""
    r = canonicalize("iphone_iphones_sales", vocab)
    assert r == "iphone_sales"


def test_ADV_dedup_leaves_single_object_no_metric(vocab):
    """Harness §6 fold+dedup combo. ``iphone_iphones``: §F.3 iphones->iphone (step
    5) then dedup (step 6) -> [iphone] only. §C step-11 requires a metric slot ->
    REJECT no_metric. EXPECT REJECTION_NO_METRIC_TOKEN."""
    r = canonicalize("iphone_iphones", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "no_metric"


# ════════════════════════════════════════════════════════════════════════════
# SLOT-COLLISION boundary (doubt #13) + ordering vs too_many_slots
# ════════════════════════════════════════════════════════════════════════════

def test_doubt13_two_geographies_slot_collision(vocab):
    """Doubt #13 + R3 ("at most one token per slot") + §C step-10 order_by_slot.
    ``china_japan_sales``: china + japan both classify to the GEOGRAPHY slot ->
    two tokens, one slot -> REJECTION_SLOT_COLLISION(slot='geography'). This fires
    at step 10 BEFORE the step-11 length check. EXPECT slot_collision, token
    (carrying the colliding slot) == 'geography'."""
    r = canonicalize("china_japan_sales", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "slot_collision"
    assert r.token == "geography"


# ════════════════════════════════════════════════════════════════════════════
# DOUBT #11 — forward_guidance vs guidance_lowered vs iphone_guidance
# ════════════════════════════════════════════════════════════════════════════

def test_doubt11_forward_guidance_round_trips(vocab):
    """Doubt #11 + R5 (standalone shortcut). With no product in evidence the
    correct form is ``forward_guidance`` (§F.1 SHORTCUTS_VOCAB seed addition, Harness
    §4) + state ``lowered`` (carried separately). ``forward_guidance`` is a
    standalone shortcut -> §C step-8 early-return to ITSELF. EXPECT 'forward_guidance'."""
    r = canonicalize("forward_guidance", vocab)
    assert r == "forward_guidance"


def test_doubt11_guidance_lowered_is_state_in_name(vocab):
    """Doubt #11. ``guidance_lowered`` bakes the STATE into the name; the correct
    form is forward_guidance + state lowered. §C step-7 state check fires on
    ``lowered`` (§F.5 financial_outcome). EXPECT state_in_name(token='lowered')."""
    r = canonicalize("guidance_lowered", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "state_in_name"
    assert r.token == "lowered"


def test_doubt11_iphone_guidance_not_mechanically_resolvable(vocab):
    """Doubt #11 (granularity = R9 LLM-judgment) + SURFACED seed note. The brief
    says ``iphone_guidance`` is *acceptable* given product-specific evidence, but
    that is an R9 GRANULARITY judgment (Layer-2). Mechanically, ``guidance`` is NOT
    seeded as a metric slot token (§F.1 METRICS has no ``guidance``; only the
    SHORTCUT ``forward_guidance``), so ``guidance`` classifies UNKNOWN with no metric
    anchor -> §D.1 slot_ambiguous. This documents that iphone_guidance is an R9
    judgment, not a deterministic canonicalize ACCEPT. EXPECT slot_ambiguous on
    'guidance'."""
    r = canonicalize("iphone_guidance", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "slot_ambiguous"
    assert r.token == "guidance"


# ════════════════════════════════════════════════════════════════════════════
# MULTI-VARIABLE A2 / K22 — two causes => two separate tags (run_one)
# ════════════════════════════════════════════════════════════════════════════

def test_A2_K22_two_causes_yield_two_separate_tags(vocab, registry):
    """A2 / K22 + R2 (split-per-variable, never bundle). An emission whose evidence
    names TWO causal variables -> TWO separate driver tags, NEVER one bundled name.
    ``iphone_china_sales`` (reuse) + ``gross_margin`` (reuse) come through as two
    distinct accepted items. EXPECT 2 items, both accepted, no bundled single tag,
    no rejections."""
    em = _emission([
        {"ticker": "AAPL", "driver_name": "china_iphone_sales",
         "driver_state": "decelerated", "direction": "short",
         "evidence": ["SRC:NEWS:1"]},
        {"ticker": "AAPL", "driver_name": "gross_margin",
         "driver_state": "contracted", "direction": "short",
         "evidence": ["SRC:NEWS:1"]},
    ])
    d = run_one(em, registry, vocab)
    assert d["shape_ok"] is True
    assert len(d["items"]) == 2
    # both resolve to SEPARATE canonical drivers (never bundled into one name)
    assert d["accepted"] == ["iphone_china_sales", "gross_margin"]
    assert d["rejected"] == []
    assert {it["status"] for it in d["items"]} == {"REUSE"}


# ════════════════════════════════════════════════════════════════════════════
# DOUBT #44 — direction may be INFERRED, not verbatim (V9 only checks the enum)
# ════════════════════════════════════════════════════════════════════════════

def test_doubt44_direction_inferred_not_rejected(vocab, registry):
    """Doubt #44 + §E V9. V9 checks ONLY ``direction ∈ {long, short}`` — it does
    NOT require the direction word to be a literal substring of the evidence. A tag
    whose direction was INFERRED (here ``short``, while the evidence text says
    nothing literal about long/short) must NOT be rejected merely for that. EXPECT
    the tag ACCEPTS (REUSE iphone_china_sales), no rejection on direction."""
    em = _emission([
        {"ticker": "AAPL", "driver_name": "iphone_china_sales",
         "driver_state": "decelerated", "direction": "short",
         "evidence": ["SRC:NEWS:1"]},
    ])
    d = run_one(em, registry, vocab)
    assert d["rejected"] == []
    assert d["accepted"] == ["iphone_china_sales"]
    assert d["items"][0]["status"] == "REUSE"


def test_doubt44_bad_direction_enum_is_rejected(vocab, registry):
    """Doubt #44 boundary / §E V9. The ONLY direction rule is the enum: a direction
    OUTSIDE {long, short} (e.g. ``up``) IS rejected -> invalid_direction_enum. Pairs
    with the inferred-direction test to show V9 enforces the enum and nothing more.
    EXPECT REJECT reason 'invalid_direction_enum'."""
    em = _emission([
        {"ticker": "AAPL", "driver_name": "iphone_china_sales",
         "driver_state": "decelerated", "direction": "up",
         "evidence": ["SRC:NEWS:1"]},
    ])
    d = run_one(em, registry, vocab)
    assert d["accepted"] == []
    assert d["rejected"] == [{"name": "iphone_china_sales",
                              "reason": "invalid_direction_enum"}]
