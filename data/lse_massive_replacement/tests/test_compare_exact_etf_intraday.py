from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from compare_exact_etf_intraday import (  # noqa: E402
    fixed_window_returns,
    regular_session,
    to_close_returns,
)


def test_fixed_window_returns_requires_exact_end_minute():
    index = pd.to_datetime(
        [
            "2026-01-02T15:00:00Z",
            "2026-01-02T15:05:00Z",
            "2026-01-02T15:10:00Z",
        ],
        utc=True,
    )
    closes = pd.Series([100.0, 110.0, 121.0], index=index)

    result = fixed_window_returns(closes, minutes=5)

    assert result.to_dict() == {
        index[0]: 10.0,
        index[1]: 10.0,
    }


def test_regular_session_accepts_an_empty_series():
    result = regular_session(
        pd.Series(dtype=float),
        pd.Timestamp("2026-01-02T14:30:00Z"),
        pd.Timestamp("2026-01-02T21:00:00Z"),
    )

    assert result.empty


def test_to_close_returns_rejects_an_incomplete_session():
    closes = pd.Series(
        [100.0, 101.0],
        index=pd.to_datetime(
            ["2026-01-02T15:00:00Z", "2026-01-02T15:01:00Z"],
            utc=True,
        ),
    )

    result = to_close_returns(
        closes,
        required_close_bar=pd.Timestamp("2026-01-02T20:59:00Z"),
    )

    assert result.empty
