"""The fake-writer APPLY step — ``apply_decision`` (Harness_BuilderPrompt.md
§15.0)  ·  TEST-SCAFFOLD (NEVER imported by prod-core, §9).

After ``run_one`` returns a would-write ``decision`` dict, production MERGEs the
accepted drivers / aliases / new vocab tokens into Neo4j so the NEXT event sees
them. This module is the OFFLINE, in-memory stand-in for that MERGE: it mutates
the fake ``registry`` AND rebuilds the frozen ``vocab`` snapshot so the
accumulation replay (§15A) can carry state forward across events.

Without this step run #2 can never reuse run #1's driver — the entire cross-run
reuse/dedup story (§15A) would be untested.

WHAT IT DOES (reads ``decision["items"]`` per the §5 per-item record), per item:
  • status PROPOSE_NEW → ``registry.add_driver(proposal_payload)``; AUTO-ALIAS the
        raw_name onto the new driver IFF ``canonicalize(raw_name) == canonical_name``
        AND ``raw_name != canonical_name`` (the §15A B4 fast-path seed); merge the
        item's ``new_slot_tokens`` (SINGLE-token novel literals) into the snapshot's
        ``slot_vocabs`` (the VocabToken read-seam, §15.0).
  • status REUSE       → no new driver; apply the record's ``aliases_added`` to the
        existing driver via ``registry.add_alias`` so a later emission of that folded
        form hits B4; count the reuse (feeds the reuse metric).
  • promoted synonym (from a Pass-2 ``SynonymFoldEngine`` with its DETERMINISTIC
        STUB judge — NEVER a real LLM) → fold ``{from→to}`` into the snapshot's
        ``synonym_map``.

HOW IT REBUILDS THE VOCAB (without modifying ``vocab_seed`` — §15.0 / §9):
  ``dataclasses.replace(vocab, slot_vocabs=<merged>, synonym_map=<merged>)``.
  Accumulated SINGLE-token ``new_slot_tokens`` + promoted single-token synonyms are
  carried forward this way. NEW slot tokens here are SINGLE-token (multi-token atom
  growth is the ingestion-phase :VocabToken Pattern-A1 path, §11B / §8 — NOT built
  here), so ``frozen_atoms`` (multi-token only) is UNAFFECTED and left untouched.
  ``vocab_seed`` module-level seeds (SYNONYM_MAP, slot vocabs) are NEVER mutated;
  only the immutable snapshot is rebuilt — verified by tests.

DETERMINISM / BILLING: pure, offline, NO LLM, NO network, NO Neo4j. Any synonym
promotion comes from a ``SynonymFoldEngine`` driven by its deterministic stub
judge (Harness_BuilderPrompt.md §13) — never ``judge_llm`` / ``claude_agent_sdk``
/ ``claude -p`` / ``import anthropic`` / ``ANTHROPIC_API_KEY``. The real LLM is
Pass 4 (§15B), NOT built here.

§15D (registry-backend contract, BACKEND-AGNOSTIC): this writes only through the
§4 ``Registry`` interface (``add_driver`` / ``add_alias``), so the SAME apply
logic runs against ANY ``Registry`` implementation.
# TODO(15D-neo4j): run the accumulation/contract assertions against a throwaway
#   Neo4j registry in the ingestion harness; do NOT build Neo4j here (§8 fence).
"""

from __future__ import annotations

import dataclasses
from typing import Optional, Tuple

from driver_ids import canonicalize, Rejection
from vocab_seed import VocabSnapshot


def _merge_new_slot_tokens(
    vocab: VocabSnapshot, new_slot_tokens: list
) -> Tuple[dict, bool]:
    """Merge ``[{slot, token}, ...]`` into a COPY of ``vocab.slot_vocabs``.

    Returns ``(merged_slot_vocabs, changed)``. Each ``token`` is added to its
    declared ``slot``'s frozenset (the VocabToken read-seam, §15.0). ``changed``
    is True iff at least one token was genuinely new to its slot — so the caller
    only rebuilds the snapshot when something actually changed (determinism +
    avoids needless churn). A token already in the slot, or whose slot is not one
    of the snapshot's slot keys, is skipped."""
    merged = {k: set(v) for k, v in vocab.slot_vocabs.items()}
    changed = False
    for entry in new_slot_tokens or []:
        slot = entry.get("slot")
        token = entry.get("token")
        if slot is None or token is None:
            continue
        if slot not in merged:
            # the snapshot does not carry this slot key — skip (defensive; the
            # reuse layer only ever emits the 6 SLOT_ORDER slot names).
            continue
        if token not in merged[slot]:
            merged[slot].add(token)
            changed = True
    return {k: frozenset(v) for k, v in merged.items()}, changed


def apply_decision(
    decision: dict,
    registry,
    vocab: VocabSnapshot,
    *,
    promoted_synonyms: Optional[dict] = None,
):
    """Apply a ``run_one`` ``decision`` to the fake ``registry`` + ``vocab`` so the
    NEXT event sees it (Harness_BuilderPrompt.md §15.0). Returns
    ``(registry, vocab')`` — ``registry`` is mutated IN PLACE (the same object,
    its drivers/aliases grown) and a possibly-NEW frozen ``vocab`` snapshot is
    returned (the old one is never mutated — it is frozen).

    Args:
      decision: a ``run_one`` decision dict (§5) — reads ``decision["items"]``.
      registry: any §4 ``Registry`` (backend-agnostic, §15D).
      vocab:    the current frozen ``VocabSnapshot``.
      promoted_synonyms: OPTIONAL ``{from_token: to_token}`` from a Pass-2
                ``SynonymFoldEngine.promoted_synonyms()`` (driven by its
                DETERMINISTIC stub judge — NEVER a real LLM). Folded into the
                snapshot's ``synonym_map`` (§15.0 "promoted synonym"). When None /
                empty, the synonym_map is carried forward unchanged.

    PURE-ish: deterministic given its args; mutates only ``registry`` (the
    in-memory MERGE stand-in) and returns a rebuilt snapshot. NO LLM / network /
    Neo4j."""
    accumulated_new_slot_tokens: list = []

    for record in decision.get("items", []):
        status = record.get("status")
        raw_name = record.get("raw_name")
        canonical_name = record.get("canonical_name")

        if status == "PROPOSE_NEW":
            payload = record.get("proposal_payload")
            if payload is not None:
                registry.add_driver(payload)
            # AUTO-ALIAS the raw form onto the new driver IFF it folds to the
            # accepted name AND differs from it (the §15A B4 fast-path seed). The
            # reuse layer already vetted V1 + folding when it populated
            # aliases_added; re-confirm the fold here so apply_decision is
            # self-contained and never aliases a non-folding raw form.
            if (
                canonical_name is not None
                and raw_name is not None
                and raw_name != canonical_name
            ):
                folded = canonicalize(raw_name, vocab)
                if not isinstance(folded, Rejection) and folded == canonical_name:
                    registry.add_alias(canonical_name, raw_name)
            # Also persist any aliases the reuse layer recorded on the record /
            # payload (idempotent; add_alias dedups).
            for alias in record.get("aliases_added", []) or []:
                if canonical_name is not None:
                    registry.add_alias(canonical_name, alias)
            # Merge this proposal's novel SINGLE-token slot literals (VocabToken
            # read-seam, §15.0).
            accumulated_new_slot_tokens.extend(record.get("new_slot_tokens", []) or [])

        elif status == "REUSE":
            # No new driver. Apply the auto-alias the canonical fold produced so a
            # LATER emission of that folded raw form hits B4 (the fast-path
            # guarantee, §15A). canonical_name is the existing driver.
            for alias in record.get("aliases_added", []) or []:
                if canonical_name is not None:
                    registry.add_alias(canonical_name, alias)
            # (the reuse count is observable via the decision itself; no registry
            # mutation needed — recorded by the replay loop / metric.)

        # status REJECT → nothing is written (out-of-scope auto-repair, §8).

    # ── Rebuild the vocab snapshot WITHOUT modifying vocab_seed (§15.0 / §9) ──
    new_slot_vocabs, slots_changed = _merge_new_slot_tokens(
        vocab, accumulated_new_slot_tokens
    )

    # Fold promoted synonyms into the snapshot's synonym_map (§15.0 "promoted
    # synonym"). The promoted dict comes from a SynonymFoldEngine's STUB judge —
    # deterministic, NO LLM. Promoted entries take precedence over the seed, exactly
    # as build_vocab_snapshot merges them (§11B wiring).
    syn_changed = False
    new_synonym_map = dict(vocab.synonym_map)
    if promoted_synonyms:
        for frm, to in promoted_synonyms.items():
            if new_synonym_map.get(frm) != to:
                new_synonym_map[frm] = to
                syn_changed = True

    if not slots_changed and not syn_changed:
        # nothing carried forward this event — return the SAME snapshot (frozen,
        # untouched) so re-running an idempotent event is a true no-op (§15A(e)).
        return registry, vocab

    # NOTE: frozen_atoms is multi-token only; new_slot_tokens here are SINGLE-token
    # (multi-token atom growth = ingestion :VocabToken Pattern-A1, §11B / §8), so
    # frozen_atoms is carried forward unchanged.
    new_vocab = dataclasses.replace(
        vocab, slot_vocabs=new_slot_vocabs, synonym_map=new_synonym_map
    )
    return registry, new_vocab
