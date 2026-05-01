"""Section 10 — Prior Lessons (from learner). U45+U66 format.

Emits two sub-sections beneath the outer `## Prior Lessons (from learner)`
header (only when lessons exist):

  ## Lessons To Label (verbatim, in order)
    L1.
    <clean lesson body>

    L2. [sector: Technology]
    <clean lesson body>
    ...

  ## Context-Only (not labeled)
    ### Ticker — <quarter>
      - prediction: <dir> (<correct/wrong>), actual: <pct>, driver: <cat>
      - predicted_confidence: <int>
      - primary_driver: <text>
      - what_worked: <text>
      - what_failed: <text>
      - Data: <data_lesson>
      - Why: <why>
      - learner_result: <path>

    ### Global lesson source events
      - L<n> sector — source: <ticker> <quarter> — learner_result: <path>
      - L<n> macro  — source: <ticker> <quarter> — learner_result: <path>
      - L<n> cross  — source: <ticker> <quarter> — related: <T1,T2> — learner_result: <path>

The L# numbering is FLAT (L1..Ln across all lesson types). Markers without
useful scope info (e.g. cross_ticker with empty related_tickers) drop the
scope tag entirely — bare ``L#.``.

Empty case: returns ``## Prior Lessons (from learner)`` + the
``No prior lessons available …`` line; ``## Lessons To Label`` is absent
(predictor empty-case rule keys on this).

Critical invariant: the function's tuple element 2 (``ordered``) MUST be
byte-identical to pre-U45 behaviour for all bundles — the validator's
positional comparison depends on it. Both this renderer and the U67
catalog aggregator drive their L# numbering off ``iter_labeled_lessons``
in ``_text_utils.py`` so the two walks cannot drift.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow `from _text_utils import iter_labeled_lessons` whether this file is
# imported via package path (scripts.earnings.renderer.lessons) or via
# scripts/earnings being on sys.path (legacy direct import).
_PKG_PARENT = Path(__file__).resolve().parents[1]
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))
from _text_utils import iter_labeled_lessons  # noqa: E402


def _render_learning_context(learning_ctx: dict) -> tuple[str, list[str]]:
    """Render the lessons section. Returns (rendered_text, ordered_lesson_texts).

    The ``ordered`` list is the validator's source of truth for the
    positional ``lesson_labels[i].lesson_text`` check. It is the same set
    of strings the rendered ``## Lessons To Label`` section displays as
    L# bodies — round-trip cross-surface invariant.
    """
    parts: list[str] = []
    ordered: list[str] = []

    parts.append("## Prior Lessons (from learner)")

    # Allowlist block (Q5: between heading and first lesson sub-section).
    allowed = learning_ctx.get("_allowed_learner_paths") or []
    if allowed:
        parts.append("\n### Allowed learner reports for this prediction\n")
        for p in allowed:
            parts.append(f"- {p}")
        parts.append("")

    ticker_lessons = learning_ctx.get("ticker_lessons") or []
    global_lessons = learning_ctx.get("global_lessons") or []

    if not ticker_lessons and not global_lessons:
        parts.append("\nNo prior lessons available (first prediction for this ticker).")
        return "\n".join(parts), ordered

    # ── Pre-walk via shared generator (single source of truth for L#) ──
    # Build label_blocks AND ordered in one pass; both reflect identical
    # walk order to U67's catalog aggregator (drift impossible by design).
    label_blocks: list[tuple[str, str]] = []   # (marker_line, body)
    for n, scope, entry, body in iter_labeled_lessons(learning_ctx):
        ordered.append(body)
        if scope == "ticker":
            marker = f"L{n}."
        elif scope == "sector":
            ts = entry.get("target_sector") or "?"
            marker = f"L{n}. [sector: {ts}]"
        elif scope == "macro":
            marker = f"L{n}. [macro]"
        elif scope == "cross_ticker":
            rt = entry.get("related_tickers") or []
            # ChatGPT decision: omit cross tag entirely when related list empty.
            marker = f"L{n}. [cross: {','.join(rt)}]" if rt else f"L{n}."
        else:
            marker = f"L{n}."
        label_blocks.append((marker, body))

    # ── Render ## Lessons To Label ──
    if label_blocks:
        parts.append("\n## Lessons To Label (verbatim, in order)\n")
        for marker, body in label_blocks:
            parts.append(marker)
            parts.append(body)
            parts.append("")

    # ── Render ## Context-Only ──
    parts.append("## Context-Only (not labeled)\n")

    # Per-ticker source event sub-block (R3 fields go here).
    for tl in ticker_lessons:
        ql = tl.get("quarter_label", "?")
        parts.append(f"### Ticker — {ql}")

        correct = tl.get("direction_correct")
        actual = tl.get("actual_daily_pct")
        pred_dir = tl.get("predicted_direction", "?")
        cat = tl.get("primary_driver_category", "?")
        outcome = "correct" if correct else "wrong"
        actual_s = f"{actual:+.2f}%" if isinstance(actual, (int, float)) else "?"
        parts.append(f"- prediction: {pred_dir} ({outcome}), actual: {actual_s}, driver: {cat}")

        # R3 fields (compact sub-block per ChatGPT decision 1).
        pcs = tl.get("predicted_confidence_score")
        if pcs is not None:
            parts.append(f"- predicted_confidence: {pcs}")
        pds = tl.get("primary_driver_summary")
        if pds:
            parts.append(f"- primary_driver: {pds}")
        ww = tl.get("what_worked")
        if ww:
            if isinstance(ww, list):
                for item in ww:
                    parts.append(f"- what_worked: {item}")
            else:
                parts.append(f"- what_worked: {ww}")
        wf = tl.get("what_failed")
        if wf:
            if isinstance(wf, list):
                for item in wf:
                    parts.append(f"- what_failed: {item}")
            else:
                parts.append(f"- what_failed: {wf}")

        for dl in tl.get("data_lessons") or []:
            parts.append(f"- Data: {dl}")
        why = tl.get("why")
        if why:
            parts.append(f"- Why: {why}")
        lrp = tl.get("learner_result_path")
        if lrp:
            parts.append(f"- learner_result: {lrp}")
        parts.append("")

    # Global lesson source events sub-block.
    if global_lessons:
        parts.append("### Global lesson source events")
        # Walk via the SAME generator so L# numbering matches the labels
        # block; only emit globals here (skip ticker scope).
        for n, scope, entry, _body in iter_labeled_lessons(learning_ctx):
            if scope == "ticker":
                continue
            src = entry.get("source_ticker") or "?"
            src_ql = entry.get("source_quarter_label") or entry.get("quarter_label") or "?"
            line = f"- L{n} {scope} — source: {src} {src_ql}"
            if scope == "cross_ticker":
                rt = entry.get("related_tickers") or []
                if rt:
                    line += f" — related: {','.join(rt)}"
            lrp = entry.get("learner_result_path")
            if lrp:
                line += f" — learner_result: {lrp}"
            parts.append(line)
        parts.append("")

    return "\n".join(parts), ordered
