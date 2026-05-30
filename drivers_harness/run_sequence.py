"""The S1→S6 chain in production order  (TEST-SCAFFOLD — prod = the orchestrator).

Reproduces the production sequence (Harness_BuilderPrompt.md §2) in the SAME
call order, so the integration test asserts order + hand-off shapes match prod:

  S1   catalog = render_catalog(registry, vocab)
  S2   if emit_fn: learner_result = emit_fn(evidence_packet, catalog)   [LLM seam]
  S2.5 if a learner_result exists:
          emission_json = learner_to_writer_input(learner_result, context)
       else: use the supplied emission_json directly
  S3-S6 run_one(emission_json, registry, vocab) -> decision

Deterministic passes feed a hand-crafted ``emission_json`` (no LLM, no context).
The real-LLM pass (Pass 4) supplies ``emit_fn`` (returns learner_result) + a
``context`` (RunContext). Pass 1: do NOT import llm_emit — ``emit_fn`` arrives
ONLY as a parameter.

TEST-SCAFFOLD: never imported by prod-core (Harness_BuilderPrompt.md §9). Imports
the PROD-CORE render_catalog + run_one; NO LLM, stdlib only.
"""

from __future__ import annotations

from typing import Callable, Optional

from render_catalog import render_catalog
from run_one import run_one, learner_to_writer_input
from vocab_seed import VocabSnapshot


def run_sequence(
    evidence_packet,
    registry,
    vocab: VocabSnapshot,
    *,
    emission_json: Optional[dict] = None,
    emit_fn: Optional[Callable] = None,
    context: Optional[dict] = None,
) -> dict:
    """Run S1→S6 in production order and return the run_one decision dict.

    Args:
      evidence_packet: the raw evidence the producer reads (S2). Ignored on the
                       deterministic path (no emit_fn).
      registry:        any §4 Registry implementation.
      vocab:           the VocabSnapshot.
      emission_json:   a hand-crafted WRITER emission (deterministic path).
      emit_fn:         the in-session producer-LLM seam (Pass 4); called as
                       ``emit_fn(evidence_packet, catalog)`` → learner_result.
      context:         REQUIRED when a learner_result exists (S2.5 adapter).

    Production parity (Harness_BuilderPrompt.md §7): in Pass 4 the tester wraps
    an in-session subagent into ``emit_fn`` (subscription, $0); run_sequence
    NEVER makes the LLM call itself."""
    # ── S1: render the catalog the producer sees ──
    catalog = render_catalog(registry, vocab)

    # ── S2: in-session producer-LLM (only if an emit_fn is supplied) ──
    learner_result = None
    if emit_fn is not None:
        learner_result = emit_fn(evidence_packet, catalog)

    # ── S2.5: adapt learner_result → emission JSON, else use the supplied one ──
    if learner_result is not None:
        if context is None:
            raise ValueError(
                "run_sequence: context (RunContext) is REQUIRED when a "
                "learner_result is produced (S2.5 adapter / doubt #43)"
            )
        emission_json = learner_to_writer_input(learner_result, context)
    elif emission_json is None:
        raise ValueError(
            "run_sequence: provide emission_json (deterministic path) OR an "
            "emit_fn that returns a learner_result (Pass-4 path)"
        )

    # ── S3-S6: validate shape, run the cleaner, return the decision ──
    return run_one(emission_json, registry, vocab)
