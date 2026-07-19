from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import duckdb


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from compare_stored_event_returns_with_lse_seconds import prior_second_close


def test_prior_second_close_keeps_aware_target_as_an_absolute_time(tmp_path):
    parquet = tmp_path / "seconds.parquet"
    connection = duckdb.connect()
    connection.execute(
        """
        CREATE TABLE seconds AS
        SELECT *
        FROM (
          VALUES
            (TIMESTAMPTZ '2024-12-12 21:15:31+00', 100.0),
            (TIMESTAMPTZ '2024-12-12 21:15:32+00', 101.0),
            (TIMESTAMPTZ '2024-12-12 23:59:57+00', 200.0)
        ) AS rows(ts, close)
        """
    )
    connection.table("seconds").write_parquet(str(parquet))
    target = datetime.fromisoformat("2024-12-12T16:15:32-05:00")

    result = prior_second_close(connection, str(parquet), target)

    assert result is not None
    assert result["close"] == 101.0
    assert result["bar_start"] == "2024-12-12T21:15:32+00:00"
