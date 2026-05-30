"""S4 reuse/propose ladder (B1..B10) — bucket F over the fake registry.

Authoritative spec sources (read in full, transcribed not paraphrased):
  - Harness_BuilderPrompt.md §6 bucket F (reuse ladder), §4 reuse.py contract +
    auto-alias, §5 ReuseResult per-item record fields.
  - DriverOntology_Implementation.md §B B1..B10 (the ladder), §C canonicalize,
    §E V1 (alias->parent).
  - DriverProcess.html §C2.1 "4 tries" (Try 1-4 == B3/B4/B6/B7), §D2 auto-alias.
  - _workflow/req_canonical.md: B-R1 (reuse-first incl. canonical form),
    B-M5 (china_iphone_sales -> reuse iphone_china_sales), K50 (catalog consulted
    first / exact-match reuse), K51 (alias reuse), A2 (slug-normalize per variable).
  - DoubtsInHTML.md doubt #6 (sorted-token reuse gated on all-known-tokens; no
    hardcoded examples), doubt #16 (aliases responsibility / flow).

The fake registry (tests/fixtures/fake_registry.json) has, among others:
  iphone_china_sales  (alias: china_iphone_sales),  oil_price,  gross_margin.

PROPERTIES asserted: ReuseResult.status / .canonical_name / .aliases_added — the
exact §5 record fields the writer (apply_decision) consumes. We do NOT over-assert
incidental fields (definition/segment placeholders) unless the rule is about them.

NO LLM, stdlib only (Harness_BuilderPrompt.md §0a / §7).
"""

from __future__ import annotations

import pytest

from vocab_seed import build_vocab_snapshot
from registry_fake import Registry
from reuse import reuse_or_propose
from driver_ids import canonicalize, Rejection
import validators as V


# ─────────────────────────────────────────────────────────────────────────────
# fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def vocab():
    """The frozen VocabSnapshot built from the §F.1-F.9 seeds (Harness §4)."""
    return build_vocab_snapshot()


@pytest.fixture()
def registry():
    """The scenario registry loaded from fake_registry.json (Harness §4 /
    §3 fixtures). Function-scoped so auto-alias mutations in one test never
    leak into another (each test gets a fresh load)."""
    return Registry.from_fixture()


# A non-empty, well-formed SRC evidence list (V10 needs >=1; the B10 gate needs
# non-empty evidence per B-R11d). Layer-1 evidence is SRC IDs only.
EV = ["SRC:NEWS:reuse-test-1"]


# ─────────────────────────────────────────────────────────────────────────────
# B3 — exact NAME reuse
# ─────────────────────────────────────────────────────────────────────────────

def test_B3_exact_name_reuse_iphone_china_sales(registry, vocab):
    """B3 exact-name reuse (DriverProcess.html Try 1; req_canonical B-R1 / K50).
    The candidate equals a registry Driver.name exactly -> REUSE that name, no
    canonicalize needed, no alias recorded. K50 = 'registry catalog consulted
    first / exact-match reuse'."""
    res = reuse_or_propose("iphone_china_sales", EV, registry, vocab)
    assert res.status == "REUSE"
    assert res.canonical_name == "iphone_china_sales"
    assert res.aliases_added == []          # exact name hit -> nothing to alias


def test_B3_exact_name_reuse_oil_price_shortcut(registry, vocab):
    """B3 exact-name reuse for the shortcut driver oil_price (req_canonical B-R1).
    A shortcut that already exists in the registry as an exact name reuses at B3
    (the cheap exact lookup), BEFORE the canonicalize shortcut early-return."""
    res = reuse_or_propose("oil_price", EV, registry, vocab)
    assert res.status == "REUSE"
    assert res.canonical_name == "oil_price"


def test_B3_exact_name_reuse_gross_margin_compound(registry, vocab):
    """B3 exact-name reuse for the compound-metric driver gross_margin
    (req_canonical B-R1). gross_margin is a single metric slot (R6); it exists as
    a registry name -> exact B3 reuse."""
    res = reuse_or_propose("gross_margin", EV, registry, vocab)
    assert res.status == "REUSE"
    assert res.canonical_name == "gross_margin"


# ─────────────────────────────────────────────────────────────────────────────
# B4 — exact ALIAS reuse
# ─────────────────────────────────────────────────────────────────────────────

def test_B4_exact_alias_reuse(registry, vocab):
    """B4 exact-alias reuse (DriverProcess.html Try 2; req_canonical K51 = 'skipped
    alias reuse' is the FAILURE this rung prevents). The candidate equals an
    existing Driver's aliases[] entry: fake_registry has
    iphone_china_sales.aliases == ['china_iphone_sales']. The raw 'china_iphone_sales'
    therefore hits B4 (alias) and reuses the parent name iphone_china_sales.
    Because the candidate is ALREADY a stored alias, no NEW alias is recorded."""
    res = reuse_or_propose("china_iphone_sales", EV, registry, vocab)
    assert res.status == "REUSE"
    assert res.canonical_name == "iphone_china_sales"
    assert res.aliases_added == []          # already an alias -> no re-add


def test_B4_exact_alias_reuse_gpu_hyperscaler(registry, vocab):
    """B4 exact-alias reuse, second instance (req_canonical K51). fake_registry has
    gpu_hyperscaler_bookings.aliases == ['hyperscaler_gpu_bookings']; the raw alias
    reuses the parent name without minting a new driver."""
    res = reuse_or_propose("hyperscaler_gpu_bookings", EV, registry, vocab)
    assert res.status == "REUSE"
    assert res.canonical_name == "gpu_hyperscaler_bookings"


# ─────────────────────────────────────────────────────────────────────────────
# B6 — CANONICAL-NAME reuse (word-order fold)  + auto-alias (DriverProcess §D2)
# ─────────────────────────────────────────────────────────────────────────────

def test_B6_canonical_name_reuse_word_order_fold(vocab):
    """B6 canonical-name reuse (DriverProcess.html Try 3; req_canonical B-R1 /
    B-M5 / K32). A word-order variant whose canonical form equals a registry name
    but is NEITHER an exact name NOR a stored alias must REUSE via the canonical
    fold. B-M5 worked example is china_iphone_sales -> reuse iphone_china_sales;
    here we use a registry WITHOUT that alias so the fold travels B5->B6 (not B4),
    and we use sales_iphone_china (metric-first variant) so canonicalize must
    reorder to slot order iphone_china_sales (R3).

    AUTO-ALIAS (DriverProcess.html §D2 / doubt #16): the raw form folded to the
    accepted name via the canonical fold, so the raw is recorded in aliases_added
    (it canonicalizes TO the name and passes V1)."""
    reg = Registry([{
        "name": "iphone_china_sales",
        "aliases": [],          # NO alias -> force the B5->B6 canonical fold
        "allowed_states": ["accelerated", "decelerated", "stable", "declined"],
        "segment": "iPhone China",
        "definition": "Unit sales of iPhone in the China market.",
        "base_label": "Sales",
    }])
    assert canonicalize("sales_iphone_china", vocab) == "iphone_china_sales"
    res = reuse_or_propose("sales_iphone_china", EV, reg, vocab)
    assert res.status == "REUSE"
    assert res.canonical_name == "iphone_china_sales"
    # auto-alias: raw folded to the name -> recorded.
    assert res.aliases_added == ["sales_iphone_china"]


def test_B6_canonical_reuse_auto_alias_china_iphone_sales(vocab):
    """Auto-alias on the B-M5 worked example itself (DriverProcess.html §D2 /
    doubt #16 / req_canonical B-M5). PROPOSE china_iphone_sales 'as if new' against
    a registry whose iphone_china_sales has NO alias yet: it folds (B5 canonicalize
    -> iphone_china_sales) and REUSES at B6, AND china_iphone_sales is recorded in
    aliases_added — IFF it canonicalizes to the accepted name (it does) AND passes
    V1 (alias->parent). This is precisely the §D2 'next emission hits B4 fast path'
    mechanism. Contrast test_B4_exact_alias_reuse, where the alias already exists."""
    reg = Registry([{
        "name": "iphone_china_sales",
        "aliases": [],          # the alias is NOT yet present
        "allowed_states": ["accelerated", "decelerated", "stable", "declined"],
        "segment": "iPhone China",
        "definition": "Unit sales of iPhone in the China market.",
        "base_label": "Sales",
    }])
    # precondition: china_iphone_sales canonicalizes to the accepted name (B-M5).
    assert canonicalize("china_iphone_sales", vocab) == "iphone_china_sales"
    # precondition: V1 (alias canonicalizes to parent) passes -> auto-alias allowed.
    ok, _ = V.V1_alias_canonicalizes_to_parent(
        "china_iphone_sales", "iphone_china_sales", vocab
    )
    assert ok is True

    res = reuse_or_propose("china_iphone_sales", EV, reg, vocab)
    assert res.status == "REUSE"
    assert res.canonical_name == "iphone_china_sales"
    assert res.aliases_added == ["china_iphone_sales"]


# ─────────────────────────────────────────────────────────────────────────────
# B7 — ALIAS-OF-CANONICAL reuse
# ─────────────────────────────────────────────────────────────────────────────

def test_B7_alias_of_canonical_reuse(vocab):
    """B7 alias-of-canonical reuse (DriverProcess.html Try 4; req_canonical B-R1).
    The candidate's CANONICAL form is not any Driver.name but IS another Driver's
    alias -> REUSE the parent of that alias. Registry: datacenter_demand with alias
    gpu_demand. Raw 'demand_gpu' canonicalizes (R3 reorder) to gpu_demand, which is
    an alias of datacenter_demand -> REUSE datacenter_demand.

    aliases_added is EMPTY here: the §D2 auto-alias only records the raw form when
    it folds to the ACCEPTED NAME; 'demand_gpu' folds to the alias gpu_demand, not
    to the name datacenter_demand, so V1(raw->name) does not hold and nothing is
    auto-added (the implementation's _auto_alias correctly returns None)."""
    reg = Registry([{
        "name": "datacenter_demand",
        "aliases": ["gpu_demand"],
        "allowed_states": ["accelerated", "decelerated", "stable", "declined"],
        "segment": "Datacenter",
        "definition": "Customer demand for datacenter products and capacity.",
        "base_label": "Sales",
    }])
    assert canonicalize("demand_gpu", vocab) == "gpu_demand"   # != the name
    res = reuse_or_propose("demand_gpu", EV, reg, vocab)
    assert res.status == "REUSE"
    assert res.canonical_name == "datacenter_demand"
    assert res.aliases_added == []          # raw folds to the alias, not the name


# ─────────────────────────────────────────────────────────────────────────────
# B8 — SORTED-TOKEN reuse (all-known-tokens gate)  (doubt #6)
# ─────────────────────────────────────────────────────────────────────────────

def test_B8_sorted_token_reuse_all_known(vocab):
    """B8 sorted-token reuse, gated on ALL tokens known (DriverProcess.html §C2.1
    B8; DoubtsInHTML doubt #6 'sorted-token reuse (gated on all known tokens)').
    Reached only when B6/B7 miss but a registry name has the SAME token SET. To
    force B8 (canonicalize already slot-sorts, so a canonical fold usually hits B6),
    the registry stores a NON-canonical-ordered name 'sales_iphone_china'. The raw
    'iphone_china_sales' canonicalizes to itself (already slot order), which is
    NOT the stored name and NOT an alias, so B5/B6/B7 miss; B8 then matches on
    sorted(tokens) == sorted({sales,iphone,china}) and REUSES the stored name.

    The gate: every canonical token (iphone/china/sales) is a known slot literal,
    so the all-known-tokens guard is satisfied and B8 is allowed to fire (doubt #6:
    no hardcoded example — the gate is membership in vocab/registry, not a list)."""
    reg = Registry([{
        "name": "sales_iphone_china",        # deliberately NOT slot-ordered
        "aliases": [],
        "allowed_states": ["accelerated", "decelerated", "stable", "declined"],
        "segment": "iPhone China",
        "definition": "Unit sales of iPhone in the China market.",
        "base_label": "Sales",
    }])
    assert canonicalize("iphone_china_sales", vocab) == "iphone_china_sales"
    res = reuse_or_propose("iphone_china_sales", EV, reg, vocab)
    assert res.status == "REUSE"
    assert res.canonical_name == "sales_iphone_china"   # the stored name is reused


# ─────────────────────────────────────────────────────────────────────────────
# Genuinely-NEW concept -> PROPOSE_NEW (the ladder reaches B9/B10)
# ─────────────────────────────────────────────────────────────────────────────

def test_genuinely_new_concept_proposes_new(registry, vocab):
    """A genuinely new concept (no exact/alias/canonical/sorted-token match) ->
    PROPOSE_NEW (req_canonical B-R1 inverse: propose only AFTER reuse exhausted;
    DriverProcess.html B7 propose-new). 'datacenter_capex' is a clean combination
    of known slot tokens (object datacenter + metric capex) that is NOT in the
    fake registry under any rung, so the ladder falls through to B10 and proposes
    the canonical name. The raw == canonical, so the §D2 auto-alias adds nothing."""
    assert canonicalize("datacenter_capex", vocab) == "datacenter_capex"
    # precondition: it is not already a registry name/alias under any rung.
    assert registry.lookup_exact_name("datacenter_capex") is None
    assert registry.lookup_by_alias("datacenter_capex") is None

    res = reuse_or_propose("datacenter_capex", EV, registry, vocab)
    assert res.status == "PROPOSE_NEW"
    assert res.canonical_name == "datacenter_capex"
    # proposal payload carries the canonical name (the §5 propose_new entry shape).
    assert res.proposal_payload is not None
    assert res.proposal_payload["name"] == "datacenter_capex"
    # raw == canonical -> no auto-alias (DriverProcess.html §D2 'differs from name').
    assert res.aliases_added == []


def test_reuse_is_tried_before_propose_K50(registry, vocab):
    """K50 (registry catalog consulted first / never propose when a usable match
    exists): a raw whose canonical form already exists as a registry name must NOT
    propose a new driver. 'china_iphone_sales' is a stored alias of
    iphone_china_sales -> the ladder REUSES (B4) and NEVER reaches PROPOSE_NEW.
    Guards K50 (= B-R1 reuse-before-create READ path = A20)."""
    res = reuse_or_propose("china_iphone_sales", EV, registry, vocab)
    assert res.status == "REUSE"
    assert res.status != "PROPOSE_NEW"
    assert res.canonical_name == "iphone_china_sales"


# ─────────────────────────────────────────────────────────────────────────────
# A2 — slug-normalization THROUGH the pipeline (NOT a direct-canonicalize shape
# reject)  ·  contrast with test_canonicalize  (A2, B-M5, doubt #6, doubt #16)
# ─────────────────────────────────────────────────────────────────────────────

def test_A2_rough_phrase_slug_normalizes_then_reuses(registry, vocab):
    """A2 slug-normalization via the pipeline (Harness §6 bucket A2; req_canonical
    A2 / B-M5; DoubtsInHTML #6/#16). A rough noun phrase 'iPhone China Sales'
    enters reuse_or_propose at B2 slug() FIRST -> 'iphone_china_sales', which then
    hits the reuse ladder and REUSES the registry driver. This is NOT a shape
    reject: the pipeline normalizes before any shape gate.

    CONTRAST (Harness §6 A1 vs A2 split): a DIRECT canonicalize() call on the same
    rough phrase WOULD reject on shape (invalid_slug_shape), because canonicalize's
    step-1 shape gate fires on un-slugged input. test_canonicalize owns the direct
    reject; here we assert the SAME input survives the pipeline because B2 slug()
    runs first. We assert both halves so the contrast is explicit and self-proving."""
    # half 1 — DIRECT canonicalize rejects on shape (the A1 path, owned elsewhere;
    # asserted here only to PROVE the contrast, not to duplicate that test's intent).
    direct = canonicalize("iPhone China Sales", vocab)
    assert isinstance(direct, Rejection)
    assert direct.reason == "invalid_slug_shape"

    # half 2 — the PIPELINE slugs first (B2) then reuses (A2 path).
    res = reuse_or_propose("iPhone China Sales", EV, registry, vocab)
    assert res.status == "REUSE"
    assert res.canonical_name == "iphone_china_sales"


def test_A2_rough_phrase_with_punctuation_slug_normalizes(registry, vocab):
    """A2 slug-normalization, second instance (req_canonical A2; DriverProcess.html
    §C2.1 'slug("iPhone China Sales!") -> iphone_china_sales'). Trailing punctuation
    and mixed case both normalize through B2 slug() -> REUSE, never a shape reject."""
    res = reuse_or_propose("iPhone China Sales!", EV, registry, vocab)
    assert res.status == "REUSE"
    assert res.canonical_name == "iphone_china_sales"


# ─────────────────────────────────────────────────────────────────────────────
# TODO(harden-in-test): the B8 all-known-tokens gate is exercised only on its
#   POSITIVE side (all tokens known -> B8 fires). A clean NEGATIVE demonstration
#   (canonical succeeds, a sorted-token match exists, but one token is NOT
#   _known_token -> B8 SKIPPED, falls to B9/B10) is hard to construct offline:
#   any token unknown to the slot vocabs makes canonicalize reject earlier
#   (slot_ambiguous / slot_anchor_unavailable) before B8 is reached, so the gate's
#   negative branch is currently unreachable via canonicalize in Layer 1. The
#   gate's INTENT (don't fold an unknown-token name onto an existing driver by
#   coincidence of token set) is preserved; revisit if a future seed admits a
#   positionally-resolvable novel token that also sorted-matches a registry name.
# ─────────────────────────────────────────────────────────────────────────────
