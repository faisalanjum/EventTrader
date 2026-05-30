"""Bucket K (CORE — MUST be green): canonicalize idempotency + map-key disjointness.

Proves the determinism contract for S4 (driver_ids.canonicalize):

  K (Harness_BuilderPrompt.md section 6 "K. Determinism (CORE)"; req_canonical.md
  B-M1 determinism contract; doubt #45):
    For a BROAD set of inputs, whenever canonicalize(x) is a STRING (an ACCEPTED
    canonical name), canonicalize(canonicalize(x)) == canonicalize(x).
    The idempotency input set MUST include:
      - every COLD_START_SEED_DRIVERS name (valid driver names),
      - the worked examples (buckets C/D/E/F + adversarial), and
      - the EXPLICIT shortcut/compound list that MUST each round-trip to ITSELF:
        fda_approval, oil_price, oil_supply, yield_curve, forward_guidance,
        gross_margin, cloud_gross_margin.

  WHY the shortcut/compound names round-trip (Harness_BuilderPrompt.md section 6
  bucket K + DriverOntology_Implementation.md §C step 4.5 freeze_known_atoms,
  owner spec fix 2026-05-29): the seed deliberately has `margin` (SYNONYM key) ⊂
  `gross_margin` (COMPOUND) and `approval` (PLURAL key) ⊂ `fda_approval`
  (SHORTCUT). §C step 4.5 freezes any span forming a known shortcut/compound into
  ONE atomic token BEFORE step-5 normalization, and step 5 SKIPS frozen atoms, so
  the known names survive intact while bare `margin`/`approval` still fold. If any
  of these red, that is a BUILDER bug in step 4.5 to SURFACE — NEVER edit §C,
  delete a seed fold, or force-green.

  The ONE safe structural assertion (Harness_BuilderPrompt.md section 6 bucket K
  "The ONE assertion that IS safe to keep"): the three normalize maps' (synonym /
  plural / acronym) KEY-sets are pairwise disjoint — a true property distinct from
  the shortcut/compound question.

All inputs are deterministic and the SPEC rule fixes each EXPECTED outcome; this
file asserts no incidental fields. Layer 1, offline, NO LLM.
"""

from __future__ import annotations

import pytest

from vocab_seed import (
    build_vocab_snapshot,
    COLD_START_SEED_DRIVERS,
    SYNONYM_MAP,
    PLURAL_MAP,
    ACRONYM_MAP,
)
from driver_ids import canonicalize, Rejection


@pytest.fixture(scope="module")
def vocab():
    """Frozen VocabSnapshot from the static seeds (build_vocab_snapshot,
    Harness_BuilderPrompt.md section 4 vocab_seed)."""
    return build_vocab_snapshot()


# ─────────────────────────────────────────────────────────────────────────────
# Input sets (broad; EXPECTED outcomes derive from the §C rule, not guessed)
# ─────────────────────────────────────────────────────────────────────────────

# The EXPLICIT shortcut/compound/multi-token-object list that MUST each round-trip
# to ITSELF. (Harness_BuilderPrompt.md section 6 bucket K; §C step 4.5
# freeze_known_atoms, v11-1 + v11-2 broadened freeze.)
SHORTCUT_COMPOUND_SELF_ROUNDTRIP = [
    "fda_approval",        # §F.1 SHORTCUT; `approval` ⊂ it is a §F.3 PLURAL key
    "oil_price",           # §F.1 SHORTCUT
    "oil_supply",          # §F.1 SHORTCUT
    "yield_curve",         # §F.1 SHORTCUT
    "forward_guidance",    # §F.1 SHORTCUT (authorised seed addition, doubt #11/F13)
    "gross_margin",        # §F.6 COMPOUND; `margin` ⊂ it is a §F.2 SYNONYM key
    "cloud_gross_margin",  # theme `cloud` + §F.6 COMPOUND `gross_margin` (R6)
    # FIX #2 (§C v11-3, 2026-05-29): §F.6 COMPOUNDS that CONTAIN the §F.8 stopword
    # `of`. Under the OLD v11-2 order (freeze AFTER the stopword-strip) `of` was
    # stripped at step 4 before step 4.5 could match the atom, so [cost, revenue] /
    # [cost, goods, sold] failed slot resolution (slot_ambiguous /
    # slot_anchor_unavailable). v11-3 freezes at step 3.5 BEFORE the strip (and the
    # strip skips frozen atoms), so both survive WHOLE and round-trip to themselves.
    "cost_of_revenue",     # §F.6 COMPOUND with interior stopword `of`
    "cost_of_goods_sold",  # §F.6 COMPOUND with interior stopword `of` (and `sold`)
    # v11-2 multi-token OBJECT freeze (#4 fix): a name built on a multi-token §F.1
    # OBJECT (`vision_pro`, `cloud_service`) must classify the object WHOLE and
    # round-trip to itself — BEFORE the broadened freeze these split into two
    # UNKNOWNs and rejected slot_ambiguous. (The bare object alone is no_metric;
    # it must be paired with a metric, which is why the VALID driver name — not the
    # bare object — is the round-trip subject. `us_gaap` is intentionally NOT in
    # this list: it REJECTS banned_token/xbrl_prefix — see the assertion below.)
    "vision_pro_sales",       # object `vision_pro` (frozen whole) + metric `sales`
    "cloud_service_revenue",  # object `cloud_service` (frozen whole) + metric `revenue`
]

# Worked examples drawn from buckets C/D/E/F + the adversarial/boundary set
# (Harness_BuilderPrompt.md section 6). Only those whose canonicalize() result is
# a STRING participate in idempotency; rejections are filtered (see test).
WORKED_EXAMPLES = [
    "china_iphone_sales",            # C: word-order fold -> iphone_china_sales
    "sales_iphone_china",            # C: word-order fold -> iphone_china_sales
    "iphone_china_sale",             # C: plural fold sale->sales -> iphone_china_sales
    "china_iphones_topline",         # C: iphones->iphone + topline->revenue
    "topline",                       # D: synonym topline->revenue
    "gm",                            # D: acronym gm->gross_margin
    "gross_profit",                  # D: multi-token gross_profit->gross_margin
    "fcf",                           # D: acronym fcf->free_cash_flow
    "revenue",                       # E: bare valid metric ACCEPTS
    "iphone_china_sales",            # F: exact canonical
    "iphone_iphones_sales",          # adversarial: plural fold + dedup -> iphone_sales
    "ai_datacenter_us_gross_margin", # boundary: compound makes it 4-not-5 slots ACCEPT
]


# ─────────────────────────────────────────────────────────────────────────────
# K — the explicit shortcut/compound list MUST each round-trip to ITSELF
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", SHORTCUT_COMPOUND_SELF_ROUNDTRIP)
def test_shortcut_compound_round_trips_to_itself(name, vocab):
    """K / doubt #45 — §C step 4.5 freeze_known_atoms (DriverOntology_Implementation.md
    §C, owner spec fix 2026-05-29): each known shortcut/compound name canonicalizes to
    ITSELF (the frozen atom skips step-5 normalization, so `margin`->`gross_margin` and
    `approval`->`approvals` cannot mangle the fragment). A red here is a builder bug in
    step 4.5 to surface, NOT a spec/seed issue."""
    result = canonicalize(name, vocab)
    assert result == name, (
        f"{name!r} must round-trip to itself (§C step 4.5 freeze_known_atoms); "
        f"got {result!r}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# K — every COLD_START_SEED_DRIVERS name round-trips to ITSELF
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("driver", COLD_START_SEED_DRIVERS, ids=lambda d: d["name"])
def test_cold_start_seed_round_trips_to_itself(driver, vocab):
    """K (Harness_BuilderPrompt.md section 6 bucket K + section 4 vocab_seed:
    "Every name here MUST canonicalize to ITSELF"). COLD_START_SEED_DRIVERS are the
    Tier-1 TIMELESS valid driver names; each is already canonical, so canonicalize is
    the identity on it. (Any non-identity result would mean a seeded "valid" name is not
    actually canonical — a builder/seed bug to surface.)"""
    name = driver["name"]
    result = canonicalize(name, vocab)
    assert result == name, (
        f"COLD_START_SEED_DRIVERS name {name!r} must canonicalize to itself; "
        f"got {result!r}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# K — broad idempotency: canonicalize(canonicalize(x)) == canonicalize(x)
# ─────────────────────────────────────────────────────────────────────────────

# The broad input set = explicit shortcut/compound/object list + every cold-start
# name + the worked examples (deduped, order preserved for stable parametrize ids).
# NOTE (corrective round 2026-05-29): the idempotency contract is stated ONLY for
# STRING canonicalize outputs, so we FILTER the parametrize set to inputs whose
# canonicalize(x) is a string at COLLECTION time — there is no longer any in-test
# pytest.skip (a skip that never fired before but would have been a latent
# "force-green" risk). Every parametrized case is a real asserting case → the run
# reports 0 skipped.
def _broad_idempotency_inputs() -> list[str]:
    seen: set[str] = set()
    raw: list[str] = []
    for src in (
        SHORTCUT_COMPOUND_SELF_ROUNDTRIP,
        [d["name"] for d in COLD_START_SEED_DRIVERS],
        WORKED_EXAMPLES,
    ):
        for name in src:
            if name not in seen:
                seen.add(name)
                raw.append(name)
    # Keep ONLY the inputs that canonicalize to a STRING — the only inputs the
    # idempotency rule applies to. (Built once at import using a fresh snapshot;
    # canonicalize is pure so this collection-time filter is deterministic.)
    _v = build_vocab_snapshot()
    return [name for name in raw if isinstance(canonicalize(name, _v), str)]


BROAD_IDEMPOTENCY_INPUTS = _broad_idempotency_inputs()


@pytest.mark.parametrize("name", BROAD_IDEMPOTENCY_INPUTS)
def test_canonicalize_is_idempotent_when_string(name, vocab):
    """K (Harness_BuilderPrompt.md section 6 "K. Determinism (CORE)"; req_canonical.md
    B-M1; doubt #45) — the canonicalize idempotency contract: whenever canonicalize(x)
    is a STRING (an accepted canonical name), applying canonicalize again is a no-op:
    canonicalize(canonicalize(x)) == canonicalize(x). This is the §C-wide stability
    guarantee (steps 4.5/8.5 freeze/rejoin make folds converge in one pass). The
    parametrize set is PRE-FILTERED to string-canonicalizing inputs (see
    _broad_idempotency_inputs), so every case here asserts — no skip, no xfail."""
    first = canonicalize(name, vocab)
    assert isinstance(first, str), (
        f"{name!r} should canonicalize to a string in the filtered idempotency set"
    )
    second = canonicalize(first, vocab)
    assert second == first, (
        f"canonicalize is not idempotent on {name!r}: "
        f"canonicalize({name!r})={first!r} but canonicalize({first!r})={second!r}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# K (#4 freeze) — us_gaap REJECTS, so it is intentionally NOT a round-trip name
# ─────────────────────────────────────────────────────────────────────────────

def test_us_gaap_not_in_idempotency_list_because_it_rejects(vocab):
    """K / #3 / K15 (corrective round) — confirm ``us_gaap`` is NOT a round-trip
    candidate: with the v11-2 multi-token freeze it canonicalizes to a REJECTION
    (banned_token / xbrl_prefix), so it cannot belong in the self-round-trip list
    above (which only holds names that canonicalize to themselves). This documents
    the asymmetry vs ``vision_pro``/``cloud_service`` objects (whose VALID driver
    names DO round-trip). EXPECT us_gaap NOT in the list AND a Rejection."""
    assert "us_gaap" not in SHORTCUT_COMPOUND_SELF_ROUNDTRIP
    assert "us_gaap" not in BROAD_IDEMPOTENCY_INPUTS
    r = canonicalize("us_gaap", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "banned_token"
    assert r.category == "xbrl_prefix"


# ─────────────────────────────────────────────────────────────────────────────
# K — the ONE safe structural assertion: normalize maps' KEY-sets are disjoint
# ─────────────────────────────────────────────────────────────────────────────

def test_normalize_map_keysets_pairwise_disjoint():
    """K (Harness_BuilderPrompt.md section 6 bucket K, "The ONE assertion that IS safe
    to keep"): the three step-5 normalize maps — §F.2 SYNONYM_MAP (single-token), §F.3
    PLURAL_MAP, §F.4 ACRONYM_MAP — have pairwise-disjoint KEY-sets. This is a true,
    distinct property (a token is folded by AT MOST ONE of acronym/plural/synonym), so
    the step-5 fold order does not let two maps fight over the same key. It is separate
    from the shortcut/compound idempotency question above (which §C step 4.5 handles)."""
    syn_keys = set(SYNONYM_MAP)
    plu_keys = set(PLURAL_MAP)
    acr_keys = set(ACRONYM_MAP)
    assert syn_keys.isdisjoint(plu_keys), (
        f"SYNONYM_MAP/PLURAL_MAP key overlap: {sorted(syn_keys & plu_keys)}"
    )
    assert syn_keys.isdisjoint(acr_keys), (
        f"SYNONYM_MAP/ACRONYM_MAP key overlap: {sorted(syn_keys & acr_keys)}"
    )
    assert plu_keys.isdisjoint(acr_keys), (
        f"PLURAL_MAP/ACRONYM_MAP key overlap: {sorted(plu_keys & acr_keys)}"
    )
