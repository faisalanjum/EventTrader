"""Section 10 — Prior Lessons (from learner).

Extracted from earnings_orchestrator.py (commit 17/20) — body copied verbatim
from the pre-renderer-extract baseline at line 2683.

Pure renderer — no external dependencies. (Plan §3 noted lessons.py would
import _normalize_lesson_text from the sibling _text_utils, but inspection
confirms _render_learning_context itself does not call it; only
validate_prediction_result in the orchestrator does.)
"""
from __future__ import annotations


def _render_learning_context(learning_ctx: dict) -> tuple[str, list[str]]:
    """Render learning context and emit the ordered list of LABELED lesson texts.

    Returns (rendered_text, ordered_lesson_texts). The list is the authoritative
    source of truth for T1 lesson_labels positional validation — by
    construction, it is emitted in the same traversal order the render emits.
    Excludes data_lessons, why, and quarter-header metadata per T1 scope rules.

    Traversal order (must match SKILL.md Phase 0):
      1. Each ticker_lesson, walking predictor_lessons[] in array order
      2. Globals by scope: sector → macro → cross_ticker (recency within scope)
    """
    parts: list[str] = []
    ordered: list[str] = []  # T1: labeled lesson texts in render order

    parts.append("## Prior Lessons (from learner)")

    ticker_lessons = learning_ctx.get("ticker_lessons", [])
    global_lessons = learning_ctx.get("global_lessons", [])

    if not ticker_lessons and not global_lessons:
        parts.append("\nNo prior lessons available (first prediction for this ticker).")
        return "\n".join(parts), ordered

    # ── Ticker-specific lessons ──
    if ticker_lessons:
        parts.append(f"\n### Ticker Lessons ({len(ticker_lessons)} most recent quarters)\n")
        for lesson in ticker_lessons:
            ql = lesson.get("quarter_label", "?")
            correct = lesson.get("direction_correct")
            actual = lesson.get("actual_daily_pct")
            pred_dir = lesson.get("predicted_direction", "?")
            cat = lesson.get("primary_driver_category", "?")
            icon = "correct" if correct else "wrong"
            parts.append(f"**{ql}** — prediction {icon} ({pred_dir}), actual {actual:+.2f}%, driver: {cat}")
            for pl in lesson.get("predictor_lessons", []):
                parts.append(f"  - Predictor: {pl}")
                if isinstance(pl, str) and pl.strip():
                    ordered.append(pl)                     # T1: LABELED
            for dl in lesson.get("data_lessons", []):
                parts.append(f"  - Data: {dl}")            # T1: NOT labeled (fetch/weight heuristic)
            why = lesson.get("why")
            if why:
                parts.append(f"  - Why: {why}")            # T1: NOT labeled (metadata)
            parts.append("")

    # ── Global lessons — split into three sub-sections by scope (amendment
    # 2026-04-17): heading was previously "Cross-Ticker Insights" for all three
    # scopes which was misleading. scope_key removed from display — rendering
    # uses routing fields (target_sector, related_tickers) only.
    if global_lessons:
        by_scope: dict[str, list[dict]] = {"sector": [], "macro": [], "cross_ticker": []}
        for entry in global_lessons:
            by_scope.setdefault(entry.get("scope"), []).append(entry)

        if by_scope["sector"]:
            parts.append(f"\n### Sector Lessons ({len(by_scope['sector'])} entries)\n")
            for entry in by_scope["sector"]:
                ts = entry.get("target_sector") or "?"
                src = entry.get("source_ticker") or "?"
                lesson_text = entry.get("lesson", "")
                parts.append(f"- [sector:{ts}] ({src}) {lesson_text}")
                if isinstance(lesson_text, str) and lesson_text.strip():
                    ordered.append(lesson_text)            # T1: LABELED

        if by_scope["macro"]:
            parts.append(f"\n### Macro Lessons ({len(by_scope['macro'])} entries)\n")
            for entry in by_scope["macro"]:
                src = entry.get("source_ticker") or "?"
                lesson_text = entry.get("lesson", "")
                parts.append(f"- [macro] ({src}) {lesson_text}")
                if isinstance(lesson_text, str) and lesson_text.strip():
                    ordered.append(lesson_text)            # T1: LABELED

        if by_scope["cross_ticker"]:
            parts.append(f"\n### Cross-Ticker Lessons ({len(by_scope['cross_ticker'])} entries)\n")
            for entry in by_scope["cross_ticker"]:
                rt = entry.get("related_tickers") or []
                src = entry.get("source_ticker") or "?"
                lesson_text = entry.get("lesson", "")
                parts.append(f"- [cross:{','.join(rt)}] ({src}) {lesson_text}")
                if isinstance(lesson_text, str) and lesson_text.strip():
                    ordered.append(lesson_text)            # T1: LABELED
        parts.append("")

    return "\n".join(parts), ordered
