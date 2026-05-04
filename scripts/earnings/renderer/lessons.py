"""Section 10 — Prior Lessons (from learner). U45+U66+v3-decoration format.

LearnerLoopRevamp.md commit 3 (2026-05-04) — round-6 v3 lesson decoration.
v3 storage carries structured ``predictor_lessons`` dicts (lesson + mechanism
+ applies_when + invalid_if + audit_history) plus transient render-time
fields (``_render_status``, ``_render_audit_counts``) attached by
``build_learning_context._apply_render_view``.

Render shape per scope (§7.4):

  L2. [sector: <SectorName>] [status: active] [reviews: <Nh> helped, <No> outweighed]
  Lesson: <single-line body — this becomes lesson_text>
  Mechanism: <the causal chain explaining why this lesson worked in THIS event>
  Applies when: <bundle preconditions>
  Invalid if: <conditions that nullify>

Watch state (recently misled) prepends a CAUTION line BEFORE the Lesson:
line so the predictor sees it ahead of the body it would copy verbatim:

  L4. [ticker] [status: watch] [reviews: <Nh> helped, <Nm> misled]
  [CAUTION — recently misled; require sharper bundle confirmation before citing]
  Lesson: <body>
  Mechanism: <causal chain>
  Applies when: <preconditions>
  Invalid if: <nullifying conditions>

D20 invariant: ``ordered_lesson_texts`` contains the LESSON BODY ONLY —
the single string after ``Lesson:``. The validator's positional equality
check (T1) compares against this list, so decoration must NEVER bleed
into the body string. Whitespace-collapsing via ``_normalize_lesson_text``
absorbs harmless spacing differences.

Retired lessons are NEVER rendered — ``build_learning_context`` drops
them before the bundle is assembled. The renderer therefore sees only
``active`` and ``watch`` lessons.

Transitional v1 string-fallback support: storage cutover happens in
commit 4 (round-6 fresh-start wipe). Until then, this renderer accepts
both v3 lesson dicts (full decoration) AND v1 string-form
``predictor_lessons[j]`` entries (no decoration — they have no mechanism
or audit_history to render). The fallback is dead code post-cutover; the
v3 path is the production behavior.

Critical invariant: the function's tuple element 2 (``ordered``) MUST be
byte-identical to pre-U45 behaviour for v1 fixtures and equal to the v3
lesson body for v3 fixtures — the validator's positional comparison
depends on it. Both this renderer and the U67 catalog aggregator drive
their L# numbering off ``iter_labeled_lessons`` in ``_text_utils.py``
so the two walks cannot drift.
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


# Render order for the [reviews: ...] summary tag. Stable across runs so
# golden tests are deterministic. Mirrors the plan §5.3 enum order.
_REVIEW_ORDER = ("helped", "outweighed", "misled", "missed", "neutral", "unclear")

_WATCH_CAUTION = (
    "[CAUTION — recently misled; require sharper bundle confirmation before citing]"
)


def _is_v3_lesson_dict(d: object) -> bool:
    """Discriminate v3 lesson dicts (storage v2: has ``lesson_id``; OR
    render-time view: has ``audit_history``/``_render_status``) from v1-era
    dict-form global entries (``lesson``/``scope``/``source_ticker`` only,
    no v3-specific identity or state fields).

    Pre-cutover (round-6 §10.2 wipes the library at commit 4) this
    distinction matters because ``build_learning_context`` assembles
    bundles whose ``global_lessons`` entries can be EITHER shape until
    the cutover lands. v1-dict entries render bare (no Lesson: prefix,
    no mechanism block) so existing renderer goldens stay byte-stable.
    """
    if not isinstance(d, dict):
        return False
    return "lesson_id" in d or "audit_history" in d or "_render_status" in d


def _resolve_lesson_dict(scope: str, source_entry: dict, body: str) -> dict | None:
    """Find the v3 lesson dict that produced this body. For ticker scope,
    the lesson dict lives inside the quarter row's ``predictor_lessons``;
    for global scopes, the source_entry IS the lesson dict — but only
    when it's v3-shaped (passes ``_is_v3_lesson_dict``).

    Returns None for v1 string-form lessons AND v1-dict global entries
    — caller falls back to undecorated rendering for both.
    """
    if scope == "ticker":
        if not isinstance(source_entry, dict):
            return None
        for pl in source_entry.get("predictor_lessons") or []:
            if (isinstance(pl, dict) and pl.get("lesson") == body
                    and _is_v3_lesson_dict(pl)):
                return pl
        return None
    # sector / macro / cross_ticker — source_entry IS the lesson dict
    return source_entry if _is_v3_lesson_dict(source_entry) else None


def _build_marker(n: int, scope: str, source_entry: dict,
                   lesson_dict: dict | None) -> str:
    """Compose the ``L# [scope] [status] [reviews]`` marker line.

    Tags are space-joined; absent tags are omitted (no empty brackets).
    The scope tag mirrors the v1 format exactly so v1 fixtures render
    byte-identical to pre-commit-3 behavior. Status + reviews tags are
    new in v3 (drawn from the transient _render_* fields attached by
    build_learning_context)."""
    parts: list[str] = [f"L{n}."]
    # Scope tag — v1 compat (drop the tag entirely when no useful info)
    if scope == "ticker":
        pass  # bare L#. for ticker scope (matches v1)
    elif scope == "sector":
        ts = (source_entry.get("target_sector") if isinstance(source_entry, dict) else None) or "?"
        parts.append(f"[sector: {ts}]")
    elif scope == "macro":
        parts.append("[macro]")
    elif scope == "cross_ticker":
        rt = (source_entry.get("related_tickers") if isinstance(source_entry, dict) else None) or []
        if rt:
            parts.append(f"[cross: {','.join(rt)}]")
    # v3 status + reviews tags (only when render-time fields are attached)
    if isinstance(lesson_dict, dict):
        status = lesson_dict.get("_render_status")
        if isinstance(status, str) and status:
            parts.append(f"[status: {status}]")
        counts = lesson_dict.get("_render_audit_counts") or {}
        if isinstance(counts, dict) and counts:
            summary = ", ".join(
                f"{counts[r]} {r}" for r in _REVIEW_ORDER
                if isinstance(counts.get(r), int) and counts[r] > 0
            )
            if summary:
                parts.append(f"[reviews: {summary}]")
    return " ".join(parts)


def _build_body_block(body: str, lesson_dict: dict | None) -> list[str]:
    """Build the lines that follow the marker. v1 string lessons get the
    bare body line (matches pre-commit-3 behavior). v3 dicts get:

      [optional CAUTION line if status==watch]
      Lesson: <body>
      Mechanism: <...>
      Applies when: <...>
      Invalid if: <...>
    """
    lines: list[str] = []
    if isinstance(lesson_dict, dict):
        # v3 — full decoration
        if lesson_dict.get("_render_status") == "watch":
            lines.append(_WATCH_CAUTION)
        lines.append(f"Lesson: {body}")
        for label, key in (
            ("Mechanism",     "mechanism"),
            ("Applies when", "applies_when"),
            ("Invalid if",   "invalid_if"),
        ):
            v = lesson_dict.get(key)
            if isinstance(v, str) and v.strip():
                lines.append(f"{label}: {v}")
    else:
        # v1 string fallback — bare body, no decoration
        lines.append(body)
    return lines


def _render_learning_context(learning_ctx: dict) -> tuple[str, list[str]]:
    """Render the lessons section. Returns (rendered_text, ordered_lesson_texts).

    The ``ordered`` list is the validator's source of truth for the
    positional ``lesson_labels[i].lesson_text`` check. D20: it contains
    the LESSON BODY ONLY — the single string after ``Lesson:``. Decoration
    (status / reviews tags, mechanism block, CAUTION line) is NEVER
    appended to ``ordered``.
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
    label_blocks: list[tuple[str, list[str]]] = []  # (marker_line, body_block_lines)
    for n, scope, entry, body in iter_labeled_lessons(learning_ctx):
        ordered.append(body)  # D20 — body ONLY, no decoration
        lesson_dict = _resolve_lesson_dict(scope, entry, body)
        marker = _build_marker(n, scope, entry, lesson_dict)
        body_block = _build_body_block(body, lesson_dict)
        label_blocks.append((marker, body_block))

    # ── Render ## Lessons To Label ──
    if label_blocks:
        parts.append("\n## Lessons To Label (verbatim, in order)\n")
        for marker, body_block in label_blocks:
            parts.append(marker)
            for line in body_block:
                parts.append(line)
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
