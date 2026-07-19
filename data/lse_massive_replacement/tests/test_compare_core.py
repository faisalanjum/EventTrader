from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path


AUDIT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AUDIT_ROOT / "scripts"))

from compare_core import (  # noqa: E402
    Bar,
    compare_daily_panels,
    compare_daily_series,
    daily_returns,
    normalize_lse_bar,
    normalize_massive_bar,
    normalize_neo4j_bar,
)


class NormalizeBarTests(unittest.TestCase):
    def test_normalize_massive_bar(self) -> None:
        row = {
            "o": 100.0,
            "h": 103.0,
            "l": 99.5,
            "c": 102.0,
            "v": 12345,
            "vw": 101.25,
            "n": 987,
            "t": 1672722000000,
        }

        bar = normalize_massive_bar("ABC", row)

        self.assertEqual(bar.symbol, "ABC")
        self.assertEqual(bar.date, "2023-01-03")
        self.assertEqual(bar.open, 100.0)
        self.assertEqual(bar.close, 102.0)
        self.assertEqual(bar.volume, 12345.0)
        self.assertEqual(bar.vwap, 101.25)
        self.assertEqual(bar.transactions, 987)

    def test_normalize_lse_bar_accepts_raw_ts(self) -> None:
        row = {
            "symbol": "ABC",
            "ts": "2023-01-03 00:00:00.000000",
            "open": 100,
            "high": 103,
            "low": 99.5,
            "close": 102,
            "volume": 12345,
        }

        bar = normalize_lse_bar(row)

        self.assertEqual(bar.symbol, "ABC")
        self.assertEqual(bar.date, "2023-01-03")
        self.assertEqual(bar.close, 102.0)
        self.assertIsNone(bar.vwap)
        self.assertIsNone(bar.transactions)

    def test_normalize_neo4j_bar_preserves_all_stored_fields(self) -> None:
        row = {
            "symbol": "ABC",
            "date": "2023-01-03",
            "open": 100,
            "high": 103,
            "low": 99.5,
            "close": 102,
            "volume": 12345,
            "vwap": 101.25,
            "transactions": 987,
            "timestamp": "2023-01-03T00:00:00-05:00",
        }

        bar = normalize_neo4j_bar(row)

        self.assertEqual(bar.symbol, "ABC")
        self.assertEqual(bar.date, "2023-01-03")
        self.assertEqual(bar.vwap, 101.25)
        self.assertEqual(bar.transactions, 987)


class ReturnTests(unittest.TestCase):
    def test_daily_returns_match_production_formula_and_rounding(self) -> None:
        bars = {
            "2023-01-03": Bar("ABC", "2023-01-03", 100, 103, 99, 101, 10),
            "2023-01-04": Bar("ABC", "2023-01-04", 101, 104, 100, 103, 11),
        }

        returns = daily_returns(bars)

        self.assertEqual(returns, {"2023-01-04": 1.98})

    def test_daily_returns_skip_non_finite_or_zero_closes(self) -> None:
        bars = {
            "2023-01-03": Bar("ABC", "2023-01-03", 1, 1, 1, 0, 10),
            "2023-01-04": Bar("ABC", "2023-01-04", 1, 1, 1, 1, 10),
            "2023-01-05": Bar("ABC", "2023-01-05", 1, 1, 1, math.nan, 10),
        }

        self.assertEqual(daily_returns(bars), {})

    def test_daily_returns_do_not_bridge_a_missing_trading_session(self) -> None:
        bars = {
            "2023-01-03": Bar("ABC", "2023-01-03", 1, 1, 1, 100, 10),
            "2023-01-05": Bar("ABC", "2023-01-05", 1, 1, 1, 110, 10),
        }

        returns = daily_returns(
            bars,
            session_dates=["2023-01-03", "2023-01-04", "2023-01-05"],
        )

        self.assertEqual(returns, {})


class ComparisonTests(unittest.TestCase):
    def test_compare_daily_series_counts_dates_and_return_matches(self) -> None:
        massive = {
            "2023-01-03": Bar("ABC", "2023-01-03", 100, 102, 99, 101, 1000),
            "2023-01-04": Bar("ABC", "2023-01-04", 101, 104, 100, 103, 1100),
            "2023-01-05": Bar("ABC", "2023-01-05", 103, 105, 102, 104, 1200),
        }
        lse = {
            "2023-01-03": Bar("ABC", "2023-01-03", 100, 102, 99, 101, 1000),
            "2023-01-04": Bar("ABC", "2023-01-04", 101, 104, 100, 103, 1100),
            "2023-01-06": Bar("ABC", "2023-01-06", 104, 106, 103, 105, 1300),
        }

        result = compare_daily_series(massive, lse)

        self.assertEqual(result["massive_dates"], 3)
        self.assertEqual(result["lse_dates"], 3)
        self.assertEqual(result["overlap_dates"], 2)
        self.assertEqual(result["massive_only_dates"], 1)
        self.assertEqual(result["lse_only_dates"], 1)
        self.assertEqual(result["ohlc"]["close"]["exact"], 2)
        self.assertEqual(result["daily_returns"]["overlap_dates"], 1)
        self.assertEqual(result["daily_returns"]["same_rounded_2dp"], 1)

    def test_compare_daily_panels_keeps_symbol_return_series_separate(self) -> None:
        reference = {
            "AAA": {
                "2023-01-03": Bar(
                    "AAA", "2023-01-03", 100, 101, 99, 100, 1000
                ),
                "2023-01-04": Bar(
                    "AAA", "2023-01-04", 100, 111, 99, 110, 1100
                ),
            },
            "BBB": {
                "2023-01-03": Bar(
                    "BBB", "2023-01-03", 50, 51, 49, 50, 500
                ),
                "2023-01-04": Bar(
                    "BBB", "2023-01-04", 50, 56, 49, 55, 550
                ),
            },
        }
        candidate = {
            symbol: dict(rows) for symbol, rows in reference.items()
        }

        result = compare_daily_panels(
            reference,
            candidate,
            session_dates=["2023-01-03", "2023-01-04"],
        )

        self.assertEqual(result["coverage"]["symbols"], 2)
        self.assertEqual(result["coverage"]["overlap_symbol_dates"], 4)
        self.assertEqual(result["daily_returns"]["compared"], 2)
        self.assertEqual(result["daily_returns"]["same_rounded_2dp"], 2)
        self.assertEqual(result["ohlc"]["close"]["exact"], 4)


if __name__ == "__main__":
    unittest.main()
