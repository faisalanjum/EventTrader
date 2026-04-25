"""Layer 2 supplement: per-helper unit tests for branches not covered by goldens.

Coverage analysis would normally drive what tests live here. With pytest-cov
unavailable, this file covers the obvious edge cases for formatters and
guidance helpers — the ones most likely to silently change semantics under
a copy-paste error during the renderer extraction.
"""
from __future__ import annotations
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))
from earnings_orchestrator import (   # noqa: E402  ← OLD path (works pre/during/post)
    _fmt_num,
    _fmt_money,
    _fmt_pct,
    _fmt_guidance_value,
    _compute_change,
    _md_table,
    _fmt_financial_cell,
    _fmt_split_pct,
    _is_segmented_label,
    _guidance_target_key,
    _guidance_target_label,
    _normalize_lesson_text,
    _iq_cell,
    _iq_val,
    _iq_bool,
    _iq_join,
)


# ── _fmt_num guards ──────────────────────────────────────────────────

def test_fmt_num_none_returns_dash():
    assert _fmt_num(None) == "—"


def test_fmt_num_nan_returns_dash():
    assert _fmt_num(float("nan")) == "—"


def test_fmt_num_pos_inf_returns_dash():
    assert _fmt_num(float("inf")) == "—"


def test_fmt_num_neg_inf_returns_dash():
    assert _fmt_num(float("-inf")) == "—"


def test_fmt_num_zero():
    assert _fmt_num(0) == "0"


def test_fmt_num_billions():
    assert "B" in _fmt_num(2.5e9)


def test_fmt_num_millions():
    assert "M" in _fmt_num(2.5e6)


def test_fmt_num_thousands():
    assert "K" in _fmt_num(2.5e3)


def test_fmt_num_with_prefix_suffix():
    assert _fmt_num(1000, prefix="$", suffix="!") == "$1K!"


# ── _fmt_money guards ────────────────────────────────────────────────

def test_fmt_money_none_returns_dash():
    assert _fmt_money(None) == "—"


def test_fmt_money_nan_returns_dash():
    assert _fmt_money(float("nan")) == "—"


def test_fmt_money_inf_returns_dash():
    assert _fmt_money(float("inf")) == "—"
    assert _fmt_money(float("-inf")) == "—"


def test_fmt_money_billions_has_dollar():
    assert _fmt_money(2.5e9).startswith("$")


# ── _fmt_pct guards + sign convention ────────────────────────────────

def test_fmt_pct_none_returns_dash():
    assert _fmt_pct(None) == "—"


def test_fmt_pct_nan_returns_dash():
    assert _fmt_pct(float("nan")) == "—"


def test_fmt_pct_inf_returns_dash():
    assert _fmt_pct(float("inf")) == "—"


def test_fmt_pct_positive_has_plus():
    s = _fmt_pct(2.5)
    assert s.startswith("+"), f"expected '+' prefix, got {s!r}"


def test_fmt_pct_negative_no_plus():
    s = _fmt_pct(-2.5)
    assert s.startswith("-"), f"expected '-' prefix, got {s!r}"
    assert not s.startswith("+"), f"negative pct must not have +"


def test_fmt_pct_zero():
    s = _fmt_pct(0.0)
    # 0 is not > 0, so no '+' prefix
    assert "+" not in s
    assert s.endswith("%")


# ── _fmt_financial_cell ──────────────────────────────────────────────

def test_fmt_financial_cell_none():
    assert _fmt_financial_cell(None, "money") == "—"


def test_fmt_financial_cell_nan():
    assert _fmt_financial_cell(float("nan"), "money") == "—"


def test_fmt_financial_cell_money_billions():
    assert "B" in _fmt_financial_cell(2.5e9, "money")


def test_fmt_financial_cell_usd_eps():
    assert _fmt_financial_cell(1.25, "usd") == "$1.25"
    assert _fmt_financial_cell(-1.25, "usd") == "-$1.25"


def test_fmt_financial_cell_pct():
    assert _fmt_financial_cell(45.0, "pct") == "45.0%"


def test_fmt_financial_cell_count():
    assert "M" in _fmt_financial_cell(1e6, "count")


def test_fmt_financial_cell_ratio():
    assert _fmt_financial_cell(2.5, "ratio") == "2.50"


# ── _fmt_split_pct ───────────────────────────────────────────────────

def test_fmt_split_pct_none():
    assert _fmt_split_pct(None) == "—"


def test_fmt_split_pct_value():
    assert _fmt_split_pct(45.5) == "45.5%"


# ── _compute_change enum ─────────────────────────────────────────────

def test_compute_change_new_when_no_prior():
    assert _compute_change({"low": 1, "high": 2}, None) == "new"


def test_compute_change_maintained():
    cur = {"low": 1, "high": 2}
    pri = {"low": 1, "high": 2}
    assert _compute_change(cur, pri) == "maintained"


def test_compute_change_raised():
    cur = {"low": 2, "high": 3}
    pri = {"low": 1, "high": 2}
    assert _compute_change(cur, pri) == "raised"


def test_compute_change_lowered():
    cur = {"low": 1, "high": 2}
    pri = {"low": 2, "high": 3}
    assert _compute_change(cur, pri) == "lowered"


def test_compute_change_revised():
    cur = {"low": 1, "high": 4}     # wider range, neither pure raise nor lower
    pri = {"low": 2, "high": 3}
    assert _compute_change(cur, pri) == "revised"


def test_compute_change_qualitative_only_maintained():
    cur = {"qualitative": "strong"}
    pri = {"qualitative": "strong"}
    assert _compute_change(cur, pri) == "maintained"


def test_compute_change_qualitative_only_revised():
    cur = {"qualitative": "weak"}
    pri = {"qualitative": "strong"}
    assert _compute_change(cur, pri) == "revised"


# ── _fmt_guidance_value units ────────────────────────────────────────

def test_fmt_guidance_value_qualitative_only():
    s = _fmt_guidance_value({"qualitative": "strong growth"}, "unknown")
    assert "strong growth" in s


def test_fmt_guidance_value_m_usd_range():
    s = _fmt_guidance_value({"low": 1000, "high": 2000}, "m_usd")
    assert "B" in s   # 1000M = 1B


def test_fmt_guidance_value_usd_eps():
    s = _fmt_guidance_value({"low": 3.20, "high": 3.40}, "usd")
    assert s == "$3.20-$3.40"


def test_fmt_guidance_value_percent():
    s = _fmt_guidance_value({"low": 5, "high": 10}, "percent")
    assert "%" in s


def test_fmt_guidance_value_basis_points():
    s = _fmt_guidance_value({"low": 50, "high": 50}, "basis_points")
    assert "bps" in s


def test_fmt_guidance_value_x_multiplier():
    s = _fmt_guidance_value({"low": 2.5, "high": 2.5}, "x")
    assert "x" in s


def test_fmt_guidance_value_dash_when_empty():
    assert _fmt_guidance_value({}, "unknown") == "—"


# ── _md_table column padding ─────────────────────────────────────────

def test_md_table_basic():
    out = _md_table(["A", "B"], [["1", "2"], ["10", "20"]])
    lines = out.split("\n")
    assert len(lines) == 4   # header, sep, 2 rows
    # Each line starts with | and ends with |
    for line in lines:
        assert line.startswith("|") and line.endswith("|")


# ── _normalize_lesson_text behavior ──────────────────────────────────

def test_normalize_lesson_text_collapses_whitespace():
    assert _normalize_lesson_text("  hello   world  ") == "hello world"


def test_normalize_lesson_text_casefolds():
    assert _normalize_lesson_text("Hello WORLD") == "hello world"


def test_normalize_lesson_text_none_returns_empty():
    assert _normalize_lesson_text(None) == ""


def test_normalize_lesson_text_empty_string():
    assert _normalize_lesson_text("") == ""


# ── _iq_* helpers ────────────────────────────────────────────────────

def test_iq_cell_escapes_pipes():
    assert _iq_cell("a|b") == "a\\|b"


def test_iq_cell_strips_newlines():
    assert _iq_cell("a\nb") == "a b"


def test_iq_val_none():
    assert _iq_val(None) == "—"


def test_iq_val_zero():
    assert _iq_val(0) == "0"


def test_iq_bool_true():
    assert _iq_bool(True) == "Y"


def test_iq_bool_false():
    assert _iq_bool(False) == "N"


def test_iq_bool_none():
    assert _iq_bool(None) == "—"


def test_iq_join_empty():
    assert _iq_join([]) == "—"


def test_iq_join_none():
    assert _iq_join(None) == "—"


def test_iq_join_values():
    assert _iq_join(["a", "b"]) == "a ; b"


# ── _is_segmented_label ──────────────────────────────────────────────

def test_is_segmented_label_with_em_dash():
    assert _is_segmented_label("Revenue — Cloud") is True


def test_is_segmented_label_without_em_dash():
    assert _is_segmented_label("Revenue") is False


# ── _guidance_target_key + _guidance_target_label ────────────────────

def test_guidance_target_key_is_tuple():
    update = {"period_start": "2026-01-01", "period_end": "2026-03-31",
              "fiscal_year": 2026, "fiscal_quarter": 1}
    key = _guidance_target_key(update)
    assert isinstance(key, tuple)
    assert len(key) == 4


def test_guidance_target_label_quarter():
    label = _guidance_target_label("quarter", 2026, 1, None, None)
    assert "Q1" in label and "FY2026" in label


def test_guidance_target_label_annual():
    label = _guidance_target_label("annual", 2026, None, None, None)
    assert "FY2026" in label


def test_guidance_target_label_unspecified_fallback():
    label = _guidance_target_label("", None, None, None, None)
    assert label  # non-empty


# ── TEMPORARY (removed in stage 2) — equivalence between two copies ──
# During stage 1, _fmt_financial_cell exists in BOTH financials.py and
# _formatters.py. This test asserts they produce identical output for every
# supported fmt_type before stage 2's cutover collapses them into ONE object.
# Removed in stage 2 because the cutover makes them the same object (identity
# becomes the stronger guarantee than functional equivalence).

import importlib

def test_TEMP_fmt_financial_cell_equivalence_both_copies():
    """STAGE-1 ONLY: assert financials._fmt_financial_cell and
    _formatters._fmt_financial_cell produce identical output for every
    supported fmt_type and edge case. REMOVE in stage 2."""
    fin = importlib.import_module("scripts.earnings.renderer.financials")._fmt_financial_cell
    fmt = importlib.import_module("scripts.earnings.renderer._formatters")._fmt_financial_cell
    cases = [
        # (value, fmt_type)
        (None, "money"), (None, "usd"), (None, "pct"), (None, "count"), (None, "ratio"),
        (float("nan"), "money"), (float("inf"), "usd"), (float("-inf"), "pct"),
        (0, "money"), (0, "usd"), (0, "pct"), (0, "count"), (0, "ratio"),
        (1.25, "usd"), (-1.25, "usd"), (1.25, "money"), (-1e9, "money"),
        (45.0, "pct"), (-12.5, "pct"),
        (1e6, "count"), (1e9, "count"),
        (2.5, "ratio"), (-0.75, "ratio"),
        (1.0, "unknown_type"),  # falls through to str(value)
    ]
    for value, fmt_type in cases:
        assert fin(value, fmt_type) == fmt(value, fmt_type), (
            f"divergence at ({value!r}, {fmt_type!r}): "
            f"financials={fin(value, fmt_type)!r}, _formatters={fmt(value, fmt_type)!r}"
        )
