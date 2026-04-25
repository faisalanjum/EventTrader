"""Shared text utilities used by both the renderer (lessons) and the validator.

Originally lived inside earnings_orchestrator.py at lines 2667-2680 of the
pre-renderer-extract baseline. Moved out so renderer/lessons.py and
validate_prediction_result both depend on this sibling instead of one
depending on the other.
"""
from __future__ import annotations


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
