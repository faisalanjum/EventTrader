from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from analyze_hourly_close_coverage import session_close_presence  # noqa: E402


def test_session_close_presence_requires_exact_hour_before_close():
    rows = [
        {"ts": "2026-05-11 18:00:00", "close": 99},
        {"ts": "2026-05-11 19:00:00", "close": 100},
        {"ts": "2026-05-12 18:00:00", "close": 101},
    ]
    sessions = ["2026-05-11", "2026-05-12"]
    closes = {
        "2026-05-11": "2026-05-11T20:00:00+00:00",
        "2026-05-12": "2026-05-12T20:00:00+00:00",
    }

    assert session_close_presence(rows, sessions, closes) == {
        "2026-05-11"
    }
