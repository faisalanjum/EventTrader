"""Shared text utilities used by both the renderer (lessons) and the validator.

Originally lived inside earnings_orchestrator.py at lines 2667-2680 of the
pre-renderer-extract baseline. Moved out so renderer/lessons.py and
validate_prediction_result both depend on this sibling instead of one
depending on the other.
"""
from __future__ import annotations

from typing import Iterator


def _normalize_lesson_text(s: str) -> str:
    """Whitespace-collapse + strip + case-fold for stable comparison.

    Used by T1 labeled-lesson-consumption contract for:
      (a) positional equality between LLM-emitted lesson_text and the
          renderer's expected list,
      (b) the analysis-field substring floor (rejects verbatim quotes of
          non-confirmed lessons in the predictor's free-text analysis).

    Case-folding absorbs harmless capitalization drift — LLMs do not
    reliably preserve case, and an intentional verbatim quote survives
    .lower(). See .claude/plans/learner.md Appendix B §5.3.
    """
    return " ".join((s or "").strip().split()).lower()


def iter_labeled_lessons(learning_ctx: dict) -> Iterator[tuple[int, str, dict, str]]:
    """Yield (n, scope, entry, body) for each labeled lesson in canonical
    render order — single source of truth for the L# numbering used by
    BOTH renderer/lessons.py (rendered ## Lessons To Label) AND
    earnings_orchestrator.build_evidence_source_catalog (#S10.lesson.L#).

    Walk order (must not change without updating both call sites):
      1. ticker_lessons[i] in array order, walking predictor_lessons[j]
         in array order. scope = "ticker".
      2. global_lessons grouped by scope, in fixed order:
         "sector" → "macro" → "cross_ticker".

    Skips empty / non-string lesson bodies — only ``n += 1`` when a real
    body is yielded.

    LearnerLoopRevamp.md (round-6 fresh-start, 2026-05-04, commit 4):
      - v3 storage emits structured ``predictor_lessons[j]`` dicts. The
        v1 string-form fallback was REMOVED in commit 4 alongside the
        §10.2 cutover (which wipes the legacy library). Non-dict entries
        are silently skipped — defensive against partially-migrated test
        fixtures, but the validator + ``append_ticker_lesson`` enforce
        dict shape on writes. After cutover, all production data is v3.
      - Skip lessons whose transient ``_render_status == "retired"`` —
        the bundle assembler attaches this in ``build_learning_context``
        AFTER PIT-filtering audit_history and computing status. Retired
        lessons must never be rendered to the predictor.
    """
    n = 0
    for tl in learning_ctx.get("ticker_lessons") or []:
        for pl in tl.get("predictor_lessons") or []:
            if not isinstance(pl, dict):
                continue  # round-6 fresh-start: v1 string fallback removed
            if pl.get("_render_status") == "retired":
                continue
            body = pl.get("lesson", "")
            if isinstance(body, str) and body.strip():
                n += 1
                yield (n, "ticker", tl, body)
    by_scope: dict[str, list[dict]] = {"sector": [], "macro": [], "cross_ticker": []}
    for entry in learning_ctx.get("global_lessons") or []:
        if not isinstance(entry, dict):
            continue
        if entry.get("_render_status") == "retired":
            continue
        by_scope.setdefault(entry.get("scope"), []).append(entry)
    for scope in ("sector", "macro", "cross_ticker"):
        for entry in by_scope.get(scope, []):
            body = entry.get("lesson", "")
            if isinstance(body, str) and body.strip():
                n += 1
                yield (n, scope, entry, body)
