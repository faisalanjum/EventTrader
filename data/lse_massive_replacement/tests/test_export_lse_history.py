from __future__ import annotations

import sys
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from export_lse_history import resolve_period  # noqa: E402


def test_resolve_period_expands_one_day_to_exclusive_end():
    assert resolve_period("2026-01-02", None, None) == (
        "2026-01-02",
        "2026-01-03",
    )


def test_resolve_period_accepts_explicit_range():
    assert resolve_period(None, "2023-01-01", "2026-01-01") == (
        "2023-01-01",
        "2026-01-01",
    )


def test_resolve_period_rejects_mixed_or_incomplete_arguments():
    with pytest.raises(ValueError):
        resolve_period("2026-01-02", "2023-01-01", "2026-01-01")
    with pytest.raises(ValueError):
        resolve_period(None, "2023-01-01", None)
