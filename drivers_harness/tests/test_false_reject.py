"""§15C — FALSE-REJECT regression set  (Layer-1, GATED 100%)  ·  PASS 3.

A corpus of KNOWN-VALID names that MUST ALL pass. False rejects silently destroy
accuracy and are INVISIBLE in "bad -> reject" tests (those only prove the system
catches garbage; they say NOTHING about whether it wrongly rejects a legit name).
A single false-reject here is a real production accuracy loss.

The corpus is seeded (Harness_BuilderPrompt.md §15C) from:
  1. the §C / §D worked examples (iphone_china_sales, oil_price, gross_margin,
     cloud_gross_margin, cost_of_revenue, vision_pro_sales, datacenter_revenue,
     forward_guidance, fda_approval, the §F.6 compounds incl. the
     direction-word-bearing real terms short_interest / long_term_debt /
     short_term_debt, opec_supply [the supply driver — the STATE ``cut`` is handled
     separately, NOT in the name], ...);
  2. EVERY COLD_START_SEED_DRIVERS name (each MUST canonicalize to ITSELF);
  3. the accepted canonical forms PRODUCED by the §15A accumulation replay
     (imported live from test_accumulation_replay so the two stay in lock-step).

For each name the corpus asserts NO false reject at TWO levels:
  - canonicalize(name, vocab) is NOT a Rejection (the pure §C path);
  - the full reuse/run_one pipeline returns REUSE or PROPOSE_NEW, never REJECT
    (the production S3..S6 path) — against a registry where the name is reachable.

NOVEL-TOKEN NAMES (blackwell_revenue, gpu_blackwell_us_revenue) are NOT a false
reject when rejected against a COLD vocab — that is the CORRECT §D fail-closed
behavior on an as-yet-unlearned token. They are valid ONLY once the token has been
learned, so they are checked against the §15A-ACCUMULATED (warm) vocab/registry —
exactly the state in which they were legitimately accepted.

DETERMINISM / BILLING (§0a / §7 / §8): pure, offline, NO LLM, NO Neo4j, NO network.
Any synonym promotion uses the SynonymFoldEngine's DETERMINISTIC stub judge only —
never judge_llm / claude_agent_sdk / claude -p / import anthropic / ANTHROPIC_API_KEY.

§15D (BACKEND-AGNOSTIC): the pipeline checks drive the §4 Registry interface only.
# TODO(15D-neo4j): re-run the false-reject corpus against a throwaway Neo4j
#   registry in the ingestion harness; do NOT build Neo4j here (§8 fence).

Spec anchors: Harness_BuilderPrompt.md §15C, §C/§D worked examples, §F.6 compounds,
COLD_START_SEED_DRIVERS, §15A (the replay whose accepted forms seed this corpus).
"""

from __future__ import annotations

import json
import os

import pytest

from driver_ids import canonicalize, Rejection
from registry_fake import Registry
from reuse import reuse_or_propose
from vocab_seed import build_vocab_snapshot, COLD_START_SEED_DRIVERS

# Import the §15A replay so the accepted forms + warm state seed THIS corpus.
from test_accumulation_replay import _replay, _scripted_events, _starting_registry


# ─────────────────────────────────────────────────────────────────────────────
# Corpus 1 — names valid against the COLD vocab (no novel tokens). These MUST
# canonicalize WITHOUT a Rejection (the §C pure path) and round-trip to a clean
# canonical form. Seeded from the §C/§D worked examples + every cold-start name.
# ─────────────────────────────────────────────────────────────────────────────

# §C / §D worked examples (Harness_BuilderPrompt.md §15C / §6 buckets C-E + §F.6).
_WORKED_EXAMPLES = [
    "iphone_china_sales",
    "oil_price",
    "gross_margin",
    "cloud_gross_margin",
    "cost_of_revenue",
    "cost_of_goods_sold",        # interior-stopword compound (v11-3)
    "vision_pro_sales",          # multi-token OBJECT
    "datacenter_revenue",
    "forward_guidance",          # shortcut (doubt #11 / F13)
    "fda_approval",              # shortcut
    "opec_supply",               # the SUPPLY driver (state `cut` handled separately)
    "operating_margin",
    "net_margin",
    "free_cash_flow",
    "operating_cash_flow",
    "effective_tax_rate",
    # §F.6 real compounds that CONTAIN a bare-banned direction word but ACCEPT
    # whole ("strict ban on loose words, explicit allow for real terms").
    "short_interest",
    "long_term_debt",
    "short_term_debt",
    # word-order / plural folds that MUST canonicalize (not reject).
    "china_iphone_sales",        # -> iphone_china_sales
    "cloud_service_revenue",     # multi-token object kept whole
]

# COLD_START_SEED_DRIVERS names — each MUST canonicalize to ITSELF (§15C).
_COLD_START_NAMES = [d["name"] for d in COLD_START_SEED_DRIVERS]

# The union for the COLD canonicalize check (deduped, ordered).
_COLD_CORPUS = list(dict.fromkeys(_WORKED_EXAMPLES + _COLD_START_NAMES))


# ─────────────────────────────────────────────────────────────────────────────
# Corpus 2 — names valid only against the §15A-ACCUMULATED (warm) vocab/registry.
# These carry a novel token that was LEARNED during the replay; rejecting them
# against a COLD vocab is CORRECT fail-closed behaviour, not a false reject.
# Imported live from the replay's accepted forms.
# ─────────────────────────────────────────────────────────────────────────────

def _replay_accepted_forms() -> set[str]:
    """The set of canonical names ACCEPTED (REUSE or PROPOSE_NEW) anywhere in the
    §15A replay — seeds the false-reject corpus per §15C."""
    _registry, _vocab, trace, _baseline = _replay(_scripted_events())
    return {
        it["canonical_name"]
        for e in trace for it in e["decision"]["items"]
        if it["status"] in ("REUSE", "PROPOSE_NEW")
    }


# ─────────────────────────────────────────────────────────────────────────────
# pytest fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def cold_vocab():
    return build_vocab_snapshot()


@pytest.fixture(scope="module")
def warm_state():
    """The (registry, vocab) AFTER the §15A replay — the accumulated state in
    which the novel-token names were legitimately accepted."""
    registry, vocab, _trace, _baseline = _replay(_scripted_events())
    return registry, vocab


# ═════════════════════════════════════════════════════════════════════════════
# §15C — cold-vocab corpus: NO false reject at the canonicalize (pure §C) level.
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("name", _COLD_CORPUS)
def test_15C_worked_example_canonicalizes_no_reject(name, cold_vocab):
    """§15C: a KNOWN-VALID worked-example / cold-start name MUST NOT be rejected by
    canonicalize. A Rejection here is a FALSE REJECT (silent accuracy loss)."""
    result = canonicalize(name, cold_vocab)
    assert not isinstance(result, Rejection), (
        f"FALSE REJECT: canonicalize({name!r}) -> Rejection("
        f"{getattr(result, 'reason', None)!r}); §15C says this MUST pass."
    )


@pytest.mark.parametrize("name", _COLD_START_NAMES)
def test_15C_cold_start_name_round_trips_to_itself(name, cold_vocab):
    """§15C: every COLD_START_SEED_DRIVERS name canonicalizes to ITSELF (the
    accepted-form invariant; also idempotent). A drift here would mean a seeded
    driver could never be reused by exact-name match."""
    result = canonicalize(name, cold_vocab)
    assert result == name, f"{name!r} did not round-trip: -> {result!r}"


# ═════════════════════════════════════════════════════════════════════════════
# §15C — cold-vocab corpus: NO false reject through the full reuse/run_one path.
# Each worked-example name must REUSE (if it exists in the registry) or PROPOSE_NEW
# cleanly — never REJECT. We use a registry seeded with cold-start + scenario rows
# so reuse targets exist; a name not yet in the registry must PROPOSE_NEW cleanly.
# ═════════════════════════════════════════════════════════════════════════════

# Single-token SHORTCUT names that are valid drivers but, when proposed brand-new
# against an EMPTY-of-them registry, hit the §D new-token gate (a lone shortcut
# atom classifies to NO slot vocab -> V14 new_token_gate_failed). In production
# these timeless macro shortcuts are COLD-STARTED (registered), so they REUSE. We
# therefore make every corpus shortcut REACHABLE in the pipeline-test registry by
# registering a minimal valid row for it (faithful to a cold-started shortcut).
# SURFACED: a single-token shortcut NOT in the registry cannot cleanly PROPOSE_NEW
# (V14) — it must be cold-started/registered first. This is a Pass-1/2 reuse-layer
# property (NOT changed here, additive-only); flagged for the spec.
_SHORTCUT_ROW_STATES = ["raised", "lowered", "reaffirmed", "withdrawn"]


def _registry_with_shortcuts(names, vocab) -> Registry:
    """A starting registry PLUS a minimal valid row for any corpus name that is a
    bare single-token §F.1 shortcut not already seeded — so the §15C pipeline check
    exercises the REUSE path for cold-started shortcuts (production reality)."""
    registry = _starting_registry()
    for name in names:
        if (name in vocab.shortcuts and "_" not in name.split("_", 1)[0]
                and registry.lookup_exact_name(name) is None):
            registry.add_driver({
                "name": name, "aliases": [],
                "allowed_states": list(_SHORTCUT_ROW_STATES),
                "segment": "Total",
                "definition": f"The {name.replace('_', ' ')} macro driver.",
                "is_shortcut": True,
            })
    return registry


@pytest.mark.parametrize("name", _COLD_CORPUS)
def test_15C_worked_example_pipeline_not_rejected(name, cold_vocab):
    """§15C: the production reuse ladder (B1..B10 + V14) MUST resolve a known-valid
    name to REUSE or PROPOSE_NEW — never REJECT. Evidence is supplied (a SRC ref +
    evidence_text containing the name's tokens) so the §D(e) new-token gate has
    what it needs for any genuinely-novel-but-known-token combination. Bare
    shortcut names are made reachable (cold-started) so they REUSE — see the
    SURFACED single-token-shortcut note above."""
    registry = _registry_with_shortcuts(_COLD_CORPUS, cold_vocab)
    evidence_text = name.replace("_", " ")
    res = reuse_or_propose(
        name, ["SRC:NEWS:fr"], registry, cold_vocab,
        evidence_text=evidence_text,
    )
    assert res.status in ("REUSE", "PROPOSE_NEW"), (
        f"FALSE REJECT in pipeline: {name!r} -> {res.status} ({res.reason}); "
        f"§15C says a known-valid name must REUSE or PROPOSE_NEW."
    )


# ═════════════════════════════════════════════════════════════════════════════
# §15C — warm-state corpus: every §15A-accepted form is reachable (no false
# reject) given the ACCUMULATED vocab/registry it was accepted in.
# ═════════════════════════════════════════════════════════════════════════════

def test_15C_all_replay_accepted_forms_resolve_warm(warm_state):
    """§15C: EVERY canonical form the §15A replay accepted resolves cleanly against
    the accumulated (warm) vocab — no false reject. A form already in the registry
    REUSES; the accumulated vocab also lets the novel-token forms canonicalize. This
    closes the loop: the names the engine itself produced are all re-accepted."""
    registry, vocab = warm_state
    accepted = _replay_accepted_forms()
    assert accepted, "the replay produced no accepted forms (corpus would be empty)"

    false_rejects: list = []
    for name in sorted(accepted):
        # 1. canonicalize must not reject against the warm vocab.
        canon = canonicalize(name, vocab)
        if isinstance(canon, Rejection):
            false_rejects.append((name, f"canonicalize:{canon.reason}"))
            continue
        # 2. it is in the registry (it was accepted), so the ladder REUSES it.
        res = reuse_or_propose(name, ["SRC:NEWS:fr"], registry, vocab,
                               evidence_text=name.replace("_", " "))
        if res.status == "REJECT":
            false_rejects.append((name, f"pipeline:{res.reason}"))
    assert false_rejects == [], f"FALSE REJECTS among §15A-accepted forms: {false_rejects}"


def test_15C_lone_novel_token_resolves_warm_not_cold(warm_state, cold_vocab):
    """§15C nuance: the LONE-novel-token name ``blackwell_revenue`` is CORRECTLY
    rejected against a COLD vocab (fail-closed §D — a lone unknown token before the
    metric is slot_ambiguous, never guessed) and CORRECTLY resolves against the
    WARM vocab (the token WAS learned in §15A). This proves the warm corpus is not
    masking a real false reject AND that the cold fail-closed is the SPEC behaviour
    (§G bucket / §D.1 Option-A), not a false reject."""
    _registry, warm_vocab = warm_state
    cold = canonicalize("blackwell_revenue", cold_vocab)
    assert isinstance(cold, Rejection) and cold.reason == "slot_ambiguous", (
        "blackwell_revenue should be slot_ambiguous against a COLD vocab (a lone "
        f"unknown token before the metric is fail-closed §D); got {cold!r}.")
    warm = canonicalize("blackwell_revenue", warm_vocab)
    assert not isinstance(warm, Rejection) and warm == "blackwell_revenue", (
        f"FALSE REJECT: blackwell_revenue should resolve against the WARM vocab "
        f"where ``blackwell`` was learned; got {warm!r}.")


def test_15C_positionally_pinned_novel_token_resolves_either_way(
    warm_state, cold_vocab
):
    """§15C nuance (companion): a POSITIONALLY-PINNED novel token
    (``gpu_blackwell_us_revenue`` — blackwell pinned between gpu/us) resolves even
    COLD, because §D.1 resolve_unknown_slots can place it deterministically without
    the token being in the vocab. So it is NOT a false reject in either state. (Only
    a LONE novel token before the metric fails closed — see the test above.) This
    distinguishes the two §G new-token cases so neither is mistaken for a false
    reject."""
    _registry, warm_vocab = warm_state
    cold = canonicalize("gpu_blackwell_us_revenue", cold_vocab)
    warm = canonicalize("gpu_blackwell_us_revenue", warm_vocab)
    assert cold == "gpu_blackwell_us_revenue", cold
    assert warm == "gpu_blackwell_us_revenue", warm


# ═════════════════════════════════════════════════════════════════════════════
# §15C — guard: the corpus actually COVERS its mandated seeds (so a future edit
# that silently drops a worked example / cold-start name is caught).
# ═════════════════════════════════════════════════════════════════════════════

def test_15C_corpus_covers_mandated_seeds():
    """§15C: the corpus MUST include every COLD_START_SEED_DRIVERS name + the
    §C/§D worked examples cited in §15C. Belt-and-braces so the regression set
    can't silently shrink below the spec's mandated coverage."""
    cold_corpus = set(_COLD_CORPUS)
    # every cold-start name is covered.
    missing_seed = [d["name"] for d in COLD_START_SEED_DRIVERS if d["name"] not in cold_corpus]
    assert missing_seed == [], f"corpus dropped cold-start names: {missing_seed}"
    # the §15C-cited worked examples are covered.
    for cited in ("iphone_china_sales", "oil_price", "gross_margin",
                  "cloud_gross_margin", "cost_of_revenue", "vision_pro_sales",
                  "datacenter_revenue", "forward_guidance", "fda_approval",
                  "opec_supply"):
        assert cited in cold_corpus, f"§15C-cited worked example {cited!r} not in corpus"
