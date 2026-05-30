"""Deterministic driver-name ID normalization  (PROD-CORE, pure, typed, no I/O).

S4 of the production sequence: slug + canonicalize + the §D.1 slot functions.

Implements DriverOntology_Implementation.md:
  - §C  canonicalize() — the 12-step pure function (incl. 4.5 / 8.5 / 9.5 / 10).
  - §D  shape regex + BNF grammar + new-token gate.
  - §D.1 slot classification + ordering (classify_token / resolve_unknown_slots /
        order_by_slot / effective_slot_count / freeze_known_atoms /
        rejoin_compound_metrics) — TRANSCRIBED VERBATIM.

slug() re-implements ``guidance_ids.slug`` exactly (does NOT import production).

PURE: no I/O, network, clock, randomness. Sorts explicitly; never relies on
set/dict iteration order. NO LLM of any kind.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from vocab_seed import VocabSnapshot, banned_category, MAX_EFFECTIVE_SLOTS


# ─────────────────────────────────────────────────────────────────────────────
# slug  — re-implement guidance_ids.slug exactly (guidance_ids.py:21)
# ─────────────────────────────────────────────────────────────────────────────

def slug(text: str) -> str:
    """Lowercase, replace non-alphanumeric with _, collapse repeats, trim edges.

    Byte-for-byte re-implementation of
    ``.claude/skills/earnings-orchestrator/scripts/guidance_ids.py::slug`` (line 21).
    Does NOT import production code (Harness_BuilderPrompt.md section 4).
    """
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")


# ─────────────────────────────────────────────────────────────────────────────
# Shape regex (§D) — compiled once
# ─────────────────────────────────────────────────────────────────────────────
#
# ^[a-z]([a-z0-9]|_(?!_))*[a-z0-9]$
# starts a-z; body = a-z/0-9 or a single underscore NOT followed by underscore;
# ends a-z/0-9; length >= 2. Rejects leading digit, edge underscore, doubled
# underscore, uppercase, non-ASCII, length < 2.

SHAPE_REGEX = re.compile(r"^[a-z]([a-z0-9]|_(?!_))*[a-z0-9]$")


# ─────────────────────────────────────────────────────────────────────────────
# Slot order + index (§D.1)
# ─────────────────────────────────────────────────────────────────────────────

# Immutable canonical slot order (R3 / §D). Index = canonical position.
SLOT_ORDER = ("theme", "object", "customer", "geography", "institution", "metric")
SLOT_INDEX = {slot: i for i, slot in enumerate(SLOT_ORDER)}


# ─────────────────────────────────────────────────────────────────────────────
# Rejection type + stable factories (§G register + Harness_BuilderPrompt section 4)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Rejection:
    """A canonicalize/validator rejection. ``reason`` is a stable named string;
    callers test ``isinstance(x, Rejection)``."""
    reason: str
    token: str | None = None
    category: str | None = None


# Zero-arg / one-arg factories with STABLE .reason strings.
REJECTION_INVALID_SLUG_SHAPE = Rejection("invalid_slug_shape")
REJECTION_EMPTY_AFTER_STOPWORD_STRIP = Rejection("empty_after_stopword_strip")
REJECTION_EMPTY_AFTER_DEDUP = Rejection("empty_after_dedup")
REJECTION_NO_METRIC_TOKEN = Rejection("no_metric")
REJECTION_TOO_MANY_SLOTS = Rejection("too_many_slots")
REJECTION_INVALID_POST_REORDER = Rejection("invalid_post_reorder")
REJECTION_SLOT_ANCHOR_UNAVAILABLE = Rejection("slot_anchor_unavailable")


def REJECTION_BANNED_TOKEN(token: str, category: str | None = None) -> Rejection:
    """A token in the §F.7 banned content (carries the banned category)."""
    return Rejection("banned_token", token=token, category=category)


def REJECTION_STATE_IN_NAME(token: str) -> Rejection:
    """A §F.5 state verb appearing in a name (belongs in driver_state)."""
    return Rejection("state_in_name", token=token)


def REJECTION_SLOT_AMBIGUOUS(token: str) -> Rejection:
    """An unknown token's slot is not uniquely determined between its anchors."""
    return Rejection("slot_ambiguous", token=token)


def REJECTION_SLOT_COLLISION(slot: str) -> Rejection:
    """Two tokens classify to the same slot (R3)."""
    return Rejection("slot_collision", token=slot)


# ─────────────────────────────────────────────────────────────────────────────
# §D.1 slot functions — TRANSCRIBED VERBATIM from the spec
# ─────────────────────────────────────────────────────────────────────────────

def classify_token(token: str, slot_vocabs: dict) -> str:
    """Return the token's slot, or 'UNKNOWN' if in no slot vocab.
    COV-2 fix: precedence walks the FIXED SLOT_ORDER, never dict-iteration order — this makes
    R3 'if a token classifies to more than one slot, the earlier slot wins' a SPEC RULE, not an
    implementation accident. Pure exact-match membership."""
    for slot in SLOT_ORDER:                                   # earliest slot wins (R3)
        if token in slot_vocabs.get(slot, frozenset()):       # exact-match membership
            return slot
    return "UNKNOWN"


def resolve_unknown_slots(classified: list):
    """classified = [(token, slot|'UNKNOWN')] in the ORIGINAL token order. Assign each UNKNOWN
    token the UNIQUE SLOT_ORDER position strictly between its nearest known left/right neighbours
    (per §D new-token gate (c) / R11). Fail closed:
        all tokens UNKNOWN (no anchor)        -> REJECTION_SLOT_ANCHOR_UNAVAILABLE
        0 or >1 free slot fits the gap        -> REJECTION_SLOT_AMBIGUOUS(token)
    Deterministic + idempotent: left/right anchors are read from the ORIGINAL known slots; unknowns
    are filled left-to-right, each taking the lowest free slot in its open interval, so the output
    depends only on the input. Assumes the proposer placed the new token in canonical slot order
    (the LLM is taught R3); the TRUE semantic slot of a novel token remains LLM-judgment — this rule
    only mechanically PLACES it and rejects when placement is not unique (see Reliability Ledger)."""
    if all(slot == "UNKNOWN" for (_, slot) in classified):
        return REJECTION_SLOT_ANCHOR_UNAVAILABLE
    resolved = list(classified)
    occupied = {s for (_, s) in classified if s != "UNKNOWN"}
    for i, (tok, slot) in enumerate(classified):
        if slot != "UNKNOWN":
            continue
        left = max((SLOT_INDEX[s] for (_, s) in classified[:i] if s != "UNKNOWN"), default=-1)
        right = min((SLOT_INDEX[s] for (_, s) in classified[i + 1:] if s != "UNKNOWN"), default=len(SLOT_ORDER))
        free = [idx for idx in range(left + 1, right) if SLOT_ORDER[idx] not in occupied]
        if len(free) != 1:                                    # 0 or >1 -> reject, never guess
            return REJECTION_SLOT_AMBIGUOUS(tok)
        chosen = SLOT_ORDER[free[0]]
        resolved[i] = (tok, chosen)
        occupied.add(chosen)
    return resolved


def order_by_slot(classified: list):
    """Reorder to canonical SLOT_ORDER and enforce R3 'at most one token per slot'.
    Pre-condition: no UNKNOWN remains (resolve_unknown_slots ran first)."""
    slots = [s for (_, s) in classified]
    if len(set(slots)) != len(slots):                         # two tokens, same slot -> R3 reject
        return REJECTION_SLOT_COLLISION(next(s for s in slots if slots.count(s) > 1))
    return sorted(classified, key=lambda ts: SLOT_INDEX[ts[1]])


def effective_slot_count(reordered: list) -> int:
    """Number of occupied slots, for the R8 length bound. A compound metric occupies the single
    'metric' slot, so it counts as one (R6) — guaranteed by rejoin_compound_metrics() below,
    invoked at §C step 8.5 before classification."""
    return len({slot for (_, slot) in reordered})


def freeze_known_atoms(tokens: list, frozen_atoms: set) -> tuple:
    """v11-1 IDEMPOTENCY FIX + v11-2 MULTI-TOKEN SCOPE (2026-05-29) — invoked at §C step 4.5, BEFORE
    per-token normalization. `frozen_atoms` (the VocabSnapshot.frozen_atoms field, assembled once at
    build time) = every KNOWN MULTI-TOKEN atom (contains "_") across shortcuts §F.1 ∪ compound_metrics
    §F.6 ∪ slot_vocabs §F.1 (e.g. object `vision_pro`, `cloud_service`) ∪ banned §F.7 (e.g. `us_gaap`,
    person names `elon_musk`/`tim_cook`, `basis_points`). Rejoin any adjacent span of tokens that
    together forms one of these into ONE atomic token, and return the set of those atoms as `frozen`
    so §C step 5 leaves them untouched. This:
      (a) stops the step-5 acronym/plural/synonym maps mangling a shortcut/compound FRAGMENT before
          step-8/8.5 protects it (`approval`->`approvals` in `fda_approval`; `margin`->`gross_margin`
          in `gross_margin` / `cloud_gross_margin`) — the original idempotency guarantee;
      (b) keeps a multi-token OBJECT whole so step 9 classify_token sees `vision_pro`/`cloud_service`
          as ONE object instead of [vision, pro] -> two UNKNOWNs -> slot_ambiguous (the #4 false-reject);
      (c) keeps a multi-token BANNED phrase whole so the step-7 ban matches `us_gaap`/person-names
          instead of [us, gaap] sliding past the per-token check (the #3 / K15 multi-token-ban bypass).
    Greedy LONGEST-match, left to right — same machinery as rejoin_compound_metrics(), emitting the
    frozen set. A bare token NOT in `frozen_atoms` (lone `margin`, `approval`) is NOT frozen, so its
    deliberate fold at step 5 still fires. SINGLE-token entries are EXCLUDED from `frozen_atoms` by
    construction (build_vocab_snapshot), which guarantees freezing can never suppress a single-token
    synonym/plural/acronym fold. Deterministic + idempotent (re-running is a no-op)."""
    members = frozen_atoms
    if not members:
        return tokens, set()
    max_span = max(len(m.split("_")) for m in members)
    out, frozen, i, n = [], set(), 0, len(tokens)
    while i < n:
        joined = None
        for span in range(min(max_span, n - i), 0, -1):       # longest adjacent window first, down to 1
            candidate = "_".join(tokens[i:i + span])
            if candidate in members:
                joined = candidate
                i += span
                break
        if joined is None:
            out.append(tokens[i]); i += 1
        else:
            out.append(joined); frozen.add(joined)
    return out, frozen


def split_respecting_atoms(name: str, frozen_atoms: set) -> list:
    """v11-3 (2026-05-29) SHARED atom-aware tokenizer. Split a canonical ``name``
    on '_' but KEEP every known MULTI-TOKEN atom (an entry of ``frozen_atoms`` =
    VocabSnapshot.frozen_atoms — every "_"-containing object/shortcut/compound/banned
    phrase) WHOLE. Greedy LONGEST-match left-to-right — the SAME machinery as
    freeze_known_atoms(), minus the returned ``frozen`` set.

    WHY: the §C v11-3 reorder note (DriverOntology_Implementation.md §C step 3.5)
    states the frozen-atom-aware tokenization MUST be reused EVERYWHERE a name is
    re-split — §E V4 (segment sub-dimension), V14 (new-token gate),
    reuse._new_slot_tokens — NEVER a raw ``name.split('_')``. A raw split shatters a
    multi-token atom (``vision_pro_sales`` -> [vision, pro, sales]) so the object's
    slot/known-ness is mis-handled OUTSIDE canonicalize (the #1 bug). Using this
    helper makes ``vision_pro``/``cloud_service`` ONE object token in those callers,
    exactly as canonicalize sees them at step 9.

    PURE: a name string + a set in, a token list out — no I/O. Deterministic +
    idempotent (re-splitting an already-atom-aware list's join is a no-op).
    """
    tokens = name.split("_")
    members = frozen_atoms
    if not members:
        return tokens
    max_span = max(len(m.split("_")) for m in members)
    out, i, n = [], 0, len(tokens)
    while i < n:
        joined = None
        for span in range(min(max_span, n - i), 0, -1):       # longest adjacent window first
            candidate = "_".join(tokens[i:i + span])
            if candidate in members:
                joined = candidate
                i += span
                break
        if joined is None:
            out.append(tokens[i]); i += 1
        else:
            out.append(joined)
    return out


def rejoin_compound_metrics(tokens: list, compound_metrics: set) -> list:
    """R6: re-join adjacent tokens that together form a §F.6 COMPOUND_METRICS entry into ONE
    metric token, so a compound like 'gross_margin' occupies a single metric slot instead of
    splitting across step 9.5/10 (which would reject it as slot-ambiguous or a slot collision).
    Greedy LONGEST-match, left to right. Deterministic + idempotent (re-running on an
    already-joined list is a no-op). Invoked at §C step 8.5, after the per-token maps + dedup +
    banned/state + shortcut checks, before classify_token(). NOTE (v11-1): step 4.5
    freeze_known_atoms() already pre-joins compounds present before normalization; this pass now only
    catches compounds that first become adjacent/canonical AFTER step-5 folds."""
    if not compound_metrics:
        return tokens
    max_span = max(len(cm.split("_")) for cm in compound_metrics)
    out, i, n = [], 0, len(tokens)
    while i < n:
        joined = None
        for span in range(min(max_span, n - i), 1, -1):       # try longest adjacent window first
            candidate = "_".join(tokens[i:i + span])
            if candidate in compound_metrics:
                joined = candidate
                i += span
                break
        if joined is None:
            out.append(tokens[i]); i += 1
        else:
            out.append(joined)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# canonicalize — §C steps 1..12 EXACTLY
# ─────────────────────────────────────────────────────────────────────────────

def canonicalize(candidate: str, vocab: VocabSnapshot):
    """Pure §C 12-step canonicalization. Returns str | Rejection.

    Step map (Implementation §C, v11-3):
      1   shape gate
      2   multi_token_subs longest-match-first replace
      3   split on '_'
      3.5 freeze_known_atoms -> (tokens, frozen)   # BEFORE stopword-strip (v11-3)
      4   strip stopwords from NON-frozen tokens only (empty -> reject)
      5   per-token normalize SKIPPING frozen atoms (acronym -> plural -> synonym)
      6   dedup preserving order (empty -> reject)
      7   banned (faithful §F.7) then state check
      8   standalone shortcut early-return
      8.5 rejoin_compound_metrics
      9   classify each token
      9.5 resolve_unknown_slots (propagate Rejection)
      10  order_by_slot (propagate Rejection)
      11  require a metric slot; effective_slot_count > MAX -> too_many_slots
      12  emit '_'.join and re-check SHAPE_REGEX
    """
    # 1. shape gate
    if not SHAPE_REGEX.match(candidate):
        return REJECTION_INVALID_SLUG_SHAPE

    # 2. multi-token compound substitution (longest-match first; deterministic sort)
    for k, v in sorted(vocab.multi_token_subs.items(), key=lambda kv: -len(kv[0])):
        candidate = candidate.replace(k, v)

    # 3. tokenize
    tokens = candidate.split("_")

    # 3.5 FREEZE known atoms BEFORE the stopword strip (v11-1 idempotency + v11-2
    #     multi-token + v11-3 BEFORE-stopword, 2026-05-29): freeze the FULL set of
    #     known multi-token atoms (shortcuts ∪ compounds ∪ slot_vocabs objects ∪
    #     banned phrases) carried on vocab.frozen_atoms. Running this BEFORE step 4
    #     lets a known atom that CONTAINS a stopword (cost_of_revenue,
    #     cost_of_goods_sold, sell_the_news) match WHOLE before `of`/`the` is
    #     stripped — the v11-3 fix for the interior-stopword-compound false reject.
    tokens, frozen = freeze_known_atoms(tokens, set(vocab.frozen_atoms))

    # 4. strip stopwords — but NEVER strip a frozen atom (its interior stopwords are
    #    protected inside the joined token, e.g. cost_of_revenue keeps its `of`).
    tokens = [t for t in tokens if t in frozen or t not in vocab.stopwords]
    if len(tokens) == 0:
        return REJECTION_EMPTY_AFTER_STOPWORD_STRIP

    # 5. per-token normalization (exact-match maps) — SKIP frozen shortcut/compound atoms
    normalized = []
    for t in tokens:
        if t in frozen:                    # already-canonical shortcut/compound atom — do not normalize
            normalized.append(t)
            continue
        n = vocab.acronym_map.get(t, t)    # §F.4
        n = vocab.plural_map.get(n, n)     # §F.3
        n = vocab.synonym_map.get(n, n)    # §F.2
        normalized.append(n)

    # 6. de-duplicate after normalization (preserve order)
    seen, deduped = set(), []
    for t in normalized:
        if t not in seen:
            deduped.append(t)
            seen.add(t)
    normalized = deduped
    if len(normalized) == 0:
        return REJECTION_EMPTY_AFTER_DEDUP

    # 7. banned-content check (banned FIRST, then states — §C order)
    for t in normalized:
        cat = banned_category(t, vocab)    # faithful §F.7 (static sets + period/numeric/verb_form)
        if cat is not None:
            return REJECTION_BANNED_TOKEN(t, cat)
        if t in vocab.states:              # §F.5 — verbs belong in driver_state
            return REJECTION_STATE_IN_NAME(t)

    # 8. standalone shortcut early-return
    if "_".join(normalized) in vocab.shortcuts:    # §F.1 SHORTCUTS_VOCAB
        return "_".join(normalized)

    # 8.5 compound-metric reassembly (R6)
    normalized = rejoin_compound_metrics(normalized, set(vocab.compound_metrics))

    # 9. classify each token into one slot
    classified = [(t, classify_token(t, vocab.slot_vocabs)) for t in normalized]

    # 9.5 resolve UNKNOWN-slot tokens by position (fail closed)
    classified = resolve_unknown_slots(classified)
    if isinstance(classified, Rejection):
        return classified

    # 10. reorder by SLOT_ORDER + reject two tokens classifying to the same slot (R3)
    reordered = order_by_slot(classified)
    if isinstance(reordered, Rejection):
        return reordered

    # 11. metric-presence + length bound
    if not any(slot == "metric" for (_, slot) in reordered):
        return REJECTION_NO_METRIC_TOKEN
    if effective_slot_count(reordered) > MAX_EFFECTIVE_SLOTS:   # §G
        return REJECTION_TOO_MANY_SLOTS

    # 12. emit
    result = "_".join(t for (t, _) in reordered)
    if not SHAPE_REGEX.match(result):
        return REJECTION_INVALID_POST_REORDER
    return result
