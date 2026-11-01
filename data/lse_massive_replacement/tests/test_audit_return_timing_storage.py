from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytz


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from audit_return_timing_storage import (  # noqa: E402
    audit_timing_values,
    compare_pending_score,
)


EASTERN = pytz.timezone("America/New_York")


def test_audit_timing_values_reconstructs_cross_session_hourly_window():
    result = audit_timing_values(
        identifier="event-1",
        created="2026-07-17T19:30:00-04:00",
        stored_market_session="post_market",
        raw_schedule={
            "hourly": "2026-07-17T20:30:00-04:00",
            "session": "2026-07-20T09:35:00-04:00",
            "daily": "2026-07-20T16:00:00-04:00",
        },
    )

    assert result["computed_windows"]["hourly"] == {
        "start": "2026-07-17T19:30:00-04:00",
        "end": "2026-07-17T20:30:00-04:00",
    }
    assert result["checks"]["stored_hourly_end_matches"] is True
    assert result["checks"]["stored_market_session_matches"] is True
    assert result["hourly_transition"] == "post_market->market_closed"


def test_audit_timing_values_accepts_json_schedule_and_finds_early_close_bug():
    result = audit_timing_values(
        identifier="event-2",
        created="2025-11-28T14:00:00-05:00",
        stored_market_session="market_closed",
        raw_schedule=(
            '{"hourly":"2025-11-28T05:00:00-05:00",'
            '"session":"2025-11-28T09:35:00-05:00",'
            '"daily":"2025-11-28T13:00:00-05:00"}'
        ),
    )

    assert result["computed_windows"]["hourly"] == {
        "start": "2025-11-28T04:00:00-05:00",
        "end": "2025-11-28T05:00:00-05:00",
    }
    assert result["checks"]["hourly_end_before_event"] is True


def test_compare_pending_score_checks_end_plus_production_delay():
    end = "2026-07-17T20:30:00-04:00"
    expected = EASTERN.localize(datetime(2026, 7, 17, 20, 47)).timestamp()

    result = compare_pending_score(
        stored_end=end,
        redis_score=expected,
        delay_seconds=17 * 60,
    )

    assert result["expected_run_time"] == "2026-07-17T20:47:00-04:00"
    assert result["score_matches"] is True
    assert result["difference_seconds"] == 0.0
