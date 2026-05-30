"""§E validator rules V1..V14 + emission-shape pre-check  (PROD-CORE, pure).

Transcribes DriverOntology_Implementation.md §E (V1..V14) — companion-field +
emission-level cross-checks that §B (reuse ladder) + §C (canonicalize) do NOT
catch. Each validator returns ``(ok: bool, reason: str | None)`` with the §E
rejection-reason string on failure.

PURE: no I/O, network, clock, randomness. NO LLM. stdlib only. Reads the
``VocabSnapshot`` + (for cross-emission checks) the registry as ARGUMENTS — no
hidden globals (Harness_BuilderPrompt.md §9). Imports only the PROD-CORE
foundation (driver_ids, vocab_seed); never imports registry_fake / run_sequence.

V15 (registry-global sorted-token dedup) is INGESTION — NOT built here; its
concern is prevented by B8 sorted-token reuse (Harness_BuilderPrompt.md §4).

SURFACED — F.5-vs-F.9 (V6 / banned): ``restricted``/``accumulated`` appear in
BOTH §F.5 STATES (policy_action / quantity_move) and historically in §F.9
ALLOWED_VERBAL_FORMS. The 2026-05-29 spec fix REMOVED them from §F.9 (they are
states → belong in driver_state, banned from names by canonicalize step 7).
The foundation vocab_seed.py already reflects that fix, so V6's "every state in
STATES, all from ONE class" reads a clean STATE_CLASSES and ``banned_category``
treats those two as verb_form-allowed-because-state (then the SEPARATE state
check fires). Best first-cut taken; see TODO below.
"""

from __future__ import annotations

import re
from typing import Optional

from driver_ids import canonicalize, slug, SHAPE_REGEX, Rejection, split_respecting_atoms
from vocab_seed import (
    VocabSnapshot,
    banned_category,
    is_known_token,
    STATES_MIN,
    STATES_MAX,
    EVIDENCE_MIN_PER_TAG,
)

# A validator result: (ok, reason). reason is None on success, the §E string on fail.
ValidatorResult = tuple[bool, Optional[str]]

# TODO(harden-in-test): F.5-vs-F.9 contradiction (restricted / accumulated).
#   The foundation vocab_seed already applied the 2026-05-29 fix (both removed
#   from ALLOWED_VERBAL_FORMS, kept in STATES). V6 below therefore treats them
#   purely as states. If the tester re-introduces them to §F.9, V6's "all from
#   ONE state class" + the canonicalize step-7 state ban will disagree — revisit
#   then. Surfaced in the return report.

# ─────────────────────────────────────────────────────────────────────────────
# SRC:* evidence catalog format (Harness_BuilderPrompt.md §5 / DriverProcess.html)
#   SRC:REPORT:<accession>#<section>   (8-K / 10-K / 10-Q)
#   SRC:TR:<id>                        (transcript)
#   SRC:NEWS:<id>                      (news)
#   SRC:FISCAL:<row>                   (fiscal.ai)
# ─────────────────────────────────────────────────────────────────────────────

_SRC_REPORT_RE = re.compile(r"^SRC:REPORT:[^#]+#.+$")
_SRC_TR_RE = re.compile(r"^SRC:TR:.+$")
_SRC_NEWS_RE = re.compile(r"^SRC:NEWS:.+$")
_SRC_FISCAL_RE = re.compile(r"^SRC:FISCAL:.+$")
_SRC_PATTERNS = (_SRC_REPORT_RE, _SRC_TR_RE, _SRC_NEWS_RE, _SRC_FISCAL_RE)

# Exactly one sentence-final punctuation, at the very end (V7).
_SENTENCE_FINAL_RE = re.compile(r"[.!?]")

# Allowed direction enum (V9).
_DIRECTIONS = frozenset({"long", "short"})


def _is_valid_src(entry: str) -> bool:
    """True iff ``entry`` matches one SRC:* catalog format (V10 syntactic half)."""
    return any(p.match(entry) for p in _SRC_PATTERNS)


# ─────────────────────────────────────────────────────────────────────────────
# V1 — alias canonicalizes TO the parent driver name (E6 fix: == parent.name)
# ─────────────────────────────────────────────────────────────────────────────

def V1_alias_canonicalizes_to_parent(
    alias: str, parent_name: str, vocab: VocabSnapshot
) -> ValidatorResult:
    """§E V1: every alias is a spelling/order VARIANT of the parent's canonical
    name → ``canonicalize(alias, vocab) == parent.name`` (E6 correctness fix —
    NOT ``== alias``; the pre-E6 rule would reject valid order variants like
    ``china_iphone_sales`` as an alias of ``iphone_china_sales``).
    Rejection reason: ``alias_does_not_canonicalize_to_parent``."""
    result = canonicalize(alias, vocab)
    if isinstance(result, Rejection):
        return False, "alias_does_not_canonicalize_to_parent"
    if result != parent_name:
        return False, "alias_does_not_canonicalize_to_parent"
    return True, None


# ─────────────────────────────────────────────────────────────────────────────
# V2 — alias does not bridge unrelated drivers
# ─────────────────────────────────────────────────────────────────────────────

def V2_alias_no_bridge(
    alias: str, parent_name: str, registry
) -> ValidatorResult:
    """§E V2: ``alias`` must not match another Driver's ``name`` or any OTHER
    Driver's ``aliases`` entry (R10: aliases never bridge two drivers).
    Rejection reason: ``alias_bridges_unrelated_drivers``."""
    for d in registry.all_drivers():
        if d["name"] == parent_name:
            continue
        if alias == d["name"]:
            return False, "alias_bridges_unrelated_drivers"
        if alias in d.get("aliases", []):
            return False, "alias_bridges_unrelated_drivers"
    return True, None


# ─────────────────────────────────────────────────────────────────────────────
# V3 — label tokens == name tokens (as a set)
# ─────────────────────────────────────────────────────────────────────────────

def V3_label_matches_name(label: str, name: str) -> ValidatorResult:
    """§E V3: ``sorted(slug(label).split('_')) == sorted(name.split('_'))``.
    Rejection reason: ``label_concept_mismatch``."""
    if sorted(slug(label).split("_")) != sorted(name.split("_")):
        return False, "label_concept_mismatch"
    return True, None


# ─────────────────────────────────────────────────────────────────────────────
# V4 — segment consistent with the name's sub-dimension
# ─────────────────────────────────────────────────────────────────────────────

def V4_segment_consistent(
    segment: str, name: str, vocab: VocabSnapshot
) -> ValidatorResult:
    """§E V4: (``segment == 'Total'`` AND ``name`` has no sub-dimension) OR
    (``segment`` matches the geography/customer/object sub-token in ``name``).

    "Sub-dimension" = any name token classifying to the geography, customer, or
    object slot. ``slug(segment)`` is compared against those sub-tokens so a
    human-readable segment label (``"iPhone China"`` → ``iphone_china``) matches
    a multi-sub-dim name; a single-sub-dim name matches that one sub-token.
    Rejection reason: ``segment_inconsistent_with_name``.

    v11-3 (2026-05-29): the name is re-split with ``split_respecting_atoms`` (NOT a
    raw ``name.split('_')``) so a multi-token OBJECT (``vision_pro``,
    ``cloud_service``) stays WHOLE and is recognised as ONE object sub-dimension —
    exactly as canonicalize/step-9 classify_token sees it. A raw split shattered
    ``vision_pro`` into [vision, pro] (neither a slot token) → the name looked like
    it had NO sub-dimension → it wrongly required segment ``"Total"`` (the #1 bug)."""
    sub_slots = ("object", "customer", "geography")
    sub_tokens = [
        t for t in split_respecting_atoms(name, set(vocab.frozen_atoms))
        if any(t in vocab.slot_vocabs.get(s, frozenset()) for s in sub_slots)
    ]
    if not sub_tokens:
        # no sub-dimension → segment MUST be "Total"
        if segment == "Total":
            return True, None
        return False, "segment_inconsistent_with_name"
    # has sub-dimension(s) → segment slug tokens must equal the sub-token set
    if segment == "Total":
        return False, "segment_inconsistent_with_name"
    if sorted(split_respecting_atoms(slug(segment), set(vocab.frozen_atoms))) == sorted(sub_tokens):
        return True, None
    # also accept a segment naming exactly ONE of the sub-tokens (single sub-dim)
    if len(sub_tokens) == 1 and slug(segment) == sub_tokens[0]:
        return True, None
    return False, "segment_inconsistent_with_name"


# ─────────────────────────────────────────────────────────────────────────────
# V5 — base_label null or in CANONICAL_BASE_LABELS
# ─────────────────────────────────────────────────────────────────────────────

def V5_base_label(
    base_label: Optional[str], vocab: VocabSnapshot
) -> ValidatorResult:
    """§E V5: ``base_label IS NULL`` OR ``base_label ∈ CANONICAL_BASE_LABELS``.
    Rejection reason: ``invalid_base_label``."""
    if base_label is None:
        return True, None
    if base_label in vocab.canonical_base_labels:
        return True, None
    return False, "invalid_base_label"


# ─────────────────────────────────────────────────────────────────────────────
# V6 — allowed_states: all in STATES, one class, STATES_MIN..STATES_MAX
# ─────────────────────────────────────────────────────────────────────────────

def V6_allowed_states(
    allowed_states: list, vocab: VocabSnapshot
) -> ValidatorResult:
    """§E V6: every entry ∈ §F.5 STATES AND all entries drawn from ONE state
    class AND ``STATES_MIN <= len <= STATES_MAX`` (§G).
    Rejection reason: ``invalid_allowed_states``."""
    if not (STATES_MIN <= len(allowed_states) <= STATES_MAX):
        return False, "invalid_allowed_states"
    if any(s not in vocab.states for s in allowed_states):
        return False, "invalid_allowed_states"
    # all from ONE class: there must exist a class containing ALL of them.
    state_set = set(allowed_states)
    for cls_tokens in vocab.state_classes.values():
        if state_set <= cls_tokens:
            return True, None
    return False, "invalid_allowed_states"


# ─────────────────────────────────────────────────────────────────────────────
# V7 — definition: non-empty, one sentence-final punct, not a name restatement
# ─────────────────────────────────────────────────────────────────────────────

def V7_definition(definition: Optional[str], name: str) -> ValidatorResult:
    """§E V7: ``definition`` is non-empty, has EXACTLY ONE sentence-final
    punctuation (``.`` / ``!`` / ``?``), and is NOT a token-only restatement of
    ``name``. Rejection reason: ``bad_definition``.

    Token-only restatement = the alphabetic words of the definition, lowercased,
    equal (as a set) the underscore tokens of the name and nothing else (e.g.
    name ``iphone_china_sales`` def ``"iPhone China sales."``).

    # TODO(harden-in-test): "exactly one sentence-final punctuation" counts EVERY
    #   ``.!?``, so an abbreviation like "U.S." trips the count (3 periods). The
    #   foundation COLD_START_SEED_DRIVERS uses "U.S." definitions that would fail
    #   V7 under this strict reading. Best first-cut: keep the strict count and
    #   author abbreviation-free definitions in the fixture. Revisit if the spec
    #   wants abbreviation-aware sentence segmentation. Surfaced in the report."""
    if not definition or not definition.strip():
        return False, "bad_definition"
    if len(_SENTENCE_FINAL_RE.findall(definition)) != 1:
        return False, "bad_definition"
    # sentence-final punctuation must be at the very end (one sentence).
    if not definition.rstrip()[-1] in ".!?":
        return False, "bad_definition"
    words = re.findall(r"[a-z0-9]+", definition.lower())
    name_tokens = set(name.split("_"))
    if words and set(words) == name_tokens:
        return False, "bad_definition"
    return True, None


# ─────────────────────────────────────────────────────────────────────────────
# V8 — driver_state in driver.allowed_states
# ─────────────────────────────────────────────────────────────────────────────

def V8_state_in_allowed(driver_state: str, allowed_states: list) -> ValidatorResult:
    """§E V8: ``driver_state ∈ Driver.allowed_states``.
    Rejection reason: ``state_not_in_allowed_states``."""
    if driver_state in allowed_states:
        return True, None
    return False, "state_not_in_allowed_states"


# ─────────────────────────────────────────────────────────────────────────────
# V9 — direction enum {long, short}
# ─────────────────────────────────────────────────────────────────────────────

def V9_direction(direction: str) -> ValidatorResult:
    """§E V9: ``direction ∈ {long, short}``.
    Rejection reason: ``invalid_direction_enum``."""
    if direction in _DIRECTIONS:
        return True, None
    return False, "invalid_direction_enum"


# ─────────────────────────────────────────────────────────────────────────────
# V10 — evidence count + SRC format + catalog resolution
# ─────────────────────────────────────────────────────────────────────────────

def V10_evidence(evidence: list, source_catalog: list) -> ValidatorResult:
    """§E V10 (E18 strict): ``len(evidence) >= EVIDENCE_MIN_PER_TAG`` AND each
    entry follows the SRC catalog format AND each entry RESOLVES against the
    emission's ``source_catalog`` (catalog resolution prevents hallucinated SRC
    IDs — syntactic format alone is insufficient).
    Rejection reason: ``empty_or_malformed_or_unresolved_src``."""
    if not isinstance(evidence, list) or len(evidence) < EVIDENCE_MIN_PER_TAG:
        return False, "empty_or_malformed_or_unresolved_src"
    catalog = set(source_catalog or [])
    for entry in evidence:
        if not isinstance(entry, str) or not _is_valid_src(entry):
            return False, "empty_or_malformed_or_unresolved_src"
        if entry not in catalog:
            return False, "empty_or_malformed_or_unresolved_src"
    return True, None


# ─────────────────────────────────────────────────────────────────────────────
# V11 — every used driver_name resolves (registry OR a propose_new in this emission)
# ─────────────────────────────────────────────────────────────────────────────

def V11_name_resolves(
    driver_name: str, registry, propose_new_names: set
) -> ValidatorResult:
    """§E V11: every ``driver_name`` used in producer fields resolves to an
    existing ``Driver.name`` OR a ``propose_new_drivers[]`` entry in the SAME
    emission. Rejection reason: ``unresolved_driver_name``."""
    if registry.lookup_exact_name(driver_name) is not None:
        return True, None
    if driver_name in propose_new_names:
        return True, None
    return False, "unresolved_driver_name"


# ─────────────────────────────────────────────────────────────────────────────
# V12 — no two propose_new entries share a name
# ─────────────────────────────────────────────────────────────────────────────

def V12_no_duplicate_proposal(propose_new: list) -> ValidatorResult:
    """§E V12: no two ``propose_new_drivers[]`` entries in the same emission
    share a ``name``. Rejection reason: ``duplicate_proposal``."""
    names = [p.get("name") for p in propose_new]
    if len(names) != len(set(names)):
        return False, "duplicate_proposal"
    return True, None


# ─────────────────────────────────────────────────────────────────────────────
# V13 — every propose_new name is used by >=1 tag with non-empty evidence
# ─────────────────────────────────────────────────────────────────────────────

def V13_proposal_used(
    proposal_name: str, items: list
) -> ValidatorResult:
    """§E V13: for every ``propose_new_drivers[]`` entry, that ``name`` is used
    at least once in a tag with NON-EMPTY evidence.
    Rejection reason: ``proposal_without_use``."""
    for it in items:
        if it.get("driver_name") == proposal_name and it.get("evidence"):
            return True, None
    return False, "proposal_without_use"


# ─────────────────────────────────────────────────────────────────────────────
# V14 — new-token gate (§D) for every novel token in a propose_new name
# ─────────────────────────────────────────────────────────────────────────────

def V14_new_token_gate(
    proposal_name: str,
    items: list,
    registry,
    vocab: VocabSnapshot,
) -> ValidatorResult:
    """§E V14: for every token in a ``propose_new`` name NOT present in
    registry/banks, the §D new-token gate passes. The gate clauses (§D):
      (a) token matches the shape regex,
      (b) token not in §F.7 BANNED_CONTENT,
      (c) token's slot is unambiguously determined by position — already
          enforced by canonicalize's resolve_unknown_slots (a name reaching here
          via reuse.py B9 was canonicalized OK, so (c) held); we re-affirm the
          token is not slot-ambiguous by confirming the name canonicalizes,
      (d) token does not equal any existing Driver.name / alias / vocab entry,
      (e) the SAME emission's tag using this name has non-empty evidence AND the
          token (or its synonym/plural/acronym PRE-IMAGE) appears as a
          case-insensitive substring of the joined evidence text.
    Rejection reason: ``new_token_gate_failed``.

    "joined evidence text" — the harness has only SRC:* IDs as evidence (no raw
    text in Layer 1); §D(e) is the case-insensitive substring of the joined
    evidence. We join the tag's evidence entries (the SRC IDs) AND, when present,
    any ``evidence_text`` the item carries (Pass-4 packets). See TODO."""
    # collect the joined evidence text for tags using this proposal name
    joined_parts: list[str] = []
    for it in items:
        if it.get("driver_name") == proposal_name:
            for e in it.get("evidence", []):
                joined_parts.append(str(e))
            if it.get("evidence_text"):
                joined_parts.append(str(it["evidence_text"]))
    joined = " ".join(joined_parts).lower()

    # pre-image map: a known token may appear in evidence under its raw form
    # (synonym/plural/acronym KEY) which §C maps to the canonical token.
    pre_images: dict[str, set[str]] = {}
    for m in (vocab.synonym_map, vocab.plural_map, vocab.acronym_map):
        for k, v in m.items():
            pre_images.setdefault(v, set()).add(k)

    # v11-3 (2026-05-29): re-split the name with split_respecting_atoms (NOT a raw
    # name.split('_')) so a multi-token OBJECT (vision_pro / cloud_service) is treated
    # as ONE known object token, not [vision, pro] fragments that would each be checked
    # as a spurious novel token. (#1 bug — same root cause as V4.)
    for token in split_respecting_atoms(proposal_name, set(vocab.frozen_atoms)):
        # token already known (registry name/alias OR vocab/banks) → not novel
        if _token_in_registry_or_banks(token, registry, vocab):
            continue
        # (a) shape
        if not SHAPE_REGEX.match(token):
            return False, "new_token_gate_failed"
        # (b) not banned
        if banned_category(token, vocab) is not None:
            return False, "new_token_gate_failed"
        # (d) not equal to an existing name/alias/vocab entry (= known-token set)
        #     novel-by-construction here (passed the registry/banks check), so OK.
        # (e) appears (or a pre-image appears) in joined evidence text
        candidates = {token} | pre_images.get(token, set())
        if not any(c.lower() in joined for c in candidates):
            return False, "new_token_gate_failed"
    # (c) re-affirm slot determinacy: the canonical name must be a clean string
    if isinstance(canonicalize(proposal_name, vocab), Rejection):
        return False, "new_token_gate_failed"
    return True, None


def _token_in_registry_or_banks(token: str, registry, vocab: VocabSnapshot) -> bool:
    """Helper: is ``token`` a KNOWN token — present in some Driver.name, some
    Driver.aliases, a §F.1-F.5 slot/state/compound bank, or a synonym/plural/
    acronym KEY or VALUE? (The §D new-token-gate "known" range.)"""
    if is_known_token(token, vocab):
        return True
    if token in vocab.states:
        return True
    for m in (vocab.synonym_map, vocab.plural_map, vocab.acronym_map):
        if token in m or token in m.values():
            return True
    for d in registry.all_drivers():
        if token in d["name"].split("_"):
            return True
        for a in d.get("aliases", []):
            if token in a.split("_"):
                return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# validate_emission_shape — S3 orchestrator pre-check
# ─────────────────────────────────────────────────────────────────────────────

# Required top-level emission keys (Harness_BuilderPrompt.md §5 emission JSON).
_EMISSION_KEYS = (
    "source_id", "source_type", "pit_cutoff", "run_id",
    "result_path", "source_catalog", "items", "propose_new_drivers",
)
_EMISSION_SOURCE_TYPES = frozenset({"learner_result", "news", "fiscal_kpi"})
# Required per-item keys (the writer ``item`` shape; exposure_role is optional).
_ITEM_KEYS = ("ticker", "driver_name", "driver_state", "direction", "evidence")
# Required per-proposal keys (the ``propose_new`` entry shape).
_PROPOSAL_KEYS = ("name", "label", "segment", "definition", "allowed_states", "aliases")


def validate_emission_shape(emission) -> tuple[bool, list]:
    """S3 (Harness_BuilderPrompt.md §2 / §5): validate the emission JSON has the
    production-complete WRITER shape BEFORE the cleaner runs. Returns
    ``(ok, errors)`` where ``errors`` is a list of human-readable strings
    (empty on success). Shape-only — does NOT run V1..V14 (run_one does that)."""
    errors: list[str] = []
    if not isinstance(emission, dict):
        return False, ["emission is not a dict"]

    for key in _EMISSION_KEYS:
        if key not in emission:
            errors.append(f"missing emission key: {key}")

    st = emission.get("source_type")
    if st is not None and st not in _EMISSION_SOURCE_TYPES:
        errors.append(f"invalid source_type: {st!r}")

    sc = emission.get("source_catalog")
    if sc is not None and not isinstance(sc, list):
        errors.append("source_catalog is not a list")

    items = emission.get("items")
    if items is None:
        pass  # already flagged missing
    elif not isinstance(items, list):
        errors.append("items is not a list")
    else:
        for i, it in enumerate(items):
            if not isinstance(it, dict):
                errors.append(f"items[{i}] is not a dict")
                continue
            for k in _ITEM_KEYS:
                if k not in it:
                    errors.append(f"items[{i}] missing key: {k}")
            if "evidence" in it and not isinstance(it["evidence"], list):
                errors.append(f"items[{i}].evidence is not a list")

    pnd = emission.get("propose_new_drivers")
    if pnd is None:
        pass  # already flagged missing
    elif not isinstance(pnd, list):
        errors.append("propose_new_drivers is not a list")
    else:
        for i, p in enumerate(pnd):
            if not isinstance(p, dict):
                errors.append(f"propose_new_drivers[{i}] is not a dict")
                continue
            for k in _PROPOSAL_KEYS:
                if k not in p:
                    errors.append(f"propose_new_drivers[{i}] missing key: {k}")

    return (len(errors) == 0), errors
