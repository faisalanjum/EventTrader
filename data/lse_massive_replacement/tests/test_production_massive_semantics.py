from __future__ import annotations

import logging
import math
import sys
import threading
import unittest
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytz


REPO_ROOT = Path("/home/faisal/EventMarketDB")
sys.path.insert(0, str(REPO_ROOT))

from eventReturns.polygonClass import Polygon  # noqa: E402
from utils.market_session import MarketSessionClassifier  # noqa: E402


EASTERN = pytz.timezone("America/New_York")


class FakeExecutor:
    def shutdown(self, wait: bool = False) -> None:
        return None


class FakeSession:
    def close(self) -> None:
        return None


@dataclass
class FakeAgg:
    timestamp: int
    close: float


class RecordingAggClient:
    def __init__(self, responder=None):
        self.calls: list[dict] = []
        self.responder = responder or (lambda call: [])

    def get_aggs(self, **kwargs):
        self.calls.append(kwargs)
        return self.responder(kwargs)


def isolated_polygon(client: RecordingAggClient) -> Polygon:
    """Build a Polygon object without running its networked initializer."""

    value = Polygon.__new__(Polygon)
    value.api_key = "not-used"
    value.polygon_subscription_delay = 0
    value.http_semaphore = threading.BoundedSemaphore(1)
    value.market_session = MarketSessionClassifier()
    value.logger = logging.getLogger("massive-audit-test")
    value.last_error = {}
    value.ticker_validation_cache = {}
    value.executor = FakeExecutor()
    value.session = FakeSession()
    value.get_rest_client = lambda: client
    return value


class ProductionPriceSelectionTests(unittest.TestCase):
    def test_get_last_trade_queries_descending_one_second_bars(self) -> None:
        target = EASTERN.localize(datetime(2025, 7, 17, 10, 0, 0))
        target_ms = int(target.timestamp() * 1000)

        def responder(call):
            return [
                FakeAgg(target_ms + 1000, 999.0),
                FakeAgg(target_ms, 101.25),
                FakeAgg(target_ms - 1000, 101.0),
            ]

        client = RecordingAggClient(responder)
        polygon = isolated_polygon(client)

        price = polygon.get_last_trade("SPY", target)

        self.assertEqual(price, 101.25)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.calls[0]["multiplier"], 1)
        self.assertEqual(client.calls[0]["timespan"], "second")
        self.assertIs(client.calls[0]["adjusted"], True)
        self.assertEqual(client.calls[0]["sort"], "desc")
        self.assertEqual(client.calls[0]["limit"], 5000)
        self.assertEqual(client.calls[0]["from_"], target_ms - 300_000)
        self.assertEqual(client.calls[0]["to"], target_ms)

    def test_empty_search_uses_expanding_contiguous_requested_windows(self) -> None:
        target = EASTERN.localize(datetime(2025, 7, 17, 10, 0, 0))
        target_ms = int(target.timestamp() * 1000)
        client = RecordingAggClient()
        polygon = isolated_polygon(client)

        price = polygon.get_last_trade("SPY", target, max_days_back=5)

        self.assertTrue(math.isnan(price))
        widths = [
            (call["to"] - call["from_"]) // 1000
            for call in client.calls
        ]
        self.assertEqual(
            widths,
            [300, 600, 1200, 2400, 4800, 9600, 19200, 38400,
             76800, 153600, 307200],
        )
        self.assertEqual(client.calls[0]["limit"], 5000)
        self.assertTrue(
            all(call["limit"] == 49998 for call in client.calls[1:])
        )
        for previous, current in zip(client.calls, client.calls[1:]):
            self.assertEqual(current["to"], previous["from_"])

        # Despite the parameter name, the final requested window reaches
        # 614,100 seconds (7d 2h 35m) back because the last window is not
        # clamped to the stated five-day boundary.
        self.assertEqual(
            target_ms - client.calls[-1]["from_"],
            614_100_000,
        )

    def test_subsecond_target_selects_the_bar_that_started_that_second(self) -> None:
        target = EASTERN.localize(
            datetime(2025, 7, 17, 10, 0, 0, 500_000)
        )
        target_ms = int(target.timestamp() * 1000)
        second_start_ms = target_ms - 500

        def responder(call):
            return [
                FakeAgg(second_start_ms + 1000, 999.0),
                FakeAgg(second_start_ms, 101.25),
                FakeAgg(second_start_ms - 1000, 101.0),
            ]

        client = RecordingAggClient(responder)
        polygon = isolated_polygon(client)

        price = polygon.get_last_trade("SPY", target)

        self.assertEqual(price, 101.25)

    def test_nominal_after_hours_end_can_use_an_earlier_bar(self) -> None:
        target = EASTERN.localize(datetime(2025, 7, 17, 20, 30, 0))
        last_extended_hours_bar = EASTERN.localize(
            datetime(2025, 7, 17, 19, 59, 59)
        )
        bar_ms = int(last_extended_hours_bar.timestamp() * 1000)

        def responder(call):
            if call["from_"] <= bar_ms <= call["to"]:
                return [FakeAgg(bar_ms, 123.45)]
            return []

        client = RecordingAggClient(responder)
        polygon = isolated_polygon(client)

        price = polygon.get_last_trade("SPY", target)

        self.assertEqual(price, 123.45)
        self.assertEqual(len(client.calls), 3)


class ProductionWindowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.market = MarketSessionClassifier()

    @staticmethod
    def iso(value) -> str:
        return value.isoformat()

    def test_normal_trading_day_windows(self) -> None:
        pre = "2026-07-17T08:00:00-04:00"
        regular = "2026-07-17T10:00:00-04:00"
        post = "2026-07-17T17:00:00-04:00"
        closed = "2026-07-17T21:00:00-04:00"

        self.assertEqual(
            self.iso(self.market.get_start_time(pre)),
            "2026-07-17T08:00:00-04:00",
        )
        self.assertEqual(
            self.iso(self.market.get_end_time(pre)),
            "2026-07-17T09:35:00-04:00",
        )
        self.assertEqual(
            tuple(map(self.iso, self.market.get_1d_impact_times(pre))),
            (
                "2026-07-16T16:00:00-04:00",
                "2026-07-17T16:00:00-04:00",
            ),
        )

        self.assertEqual(
            self.iso(self.market.get_end_time(regular)),
            "2026-07-17T16:00:00-04:00",
        )
        self.assertEqual(
            self.iso(self.market.get_interval_end_time(regular, 60, False)),
            "2026-07-17T11:00:00-04:00",
        )

        self.assertEqual(
            self.iso(self.market.get_end_time(post)),
            "2026-07-20T09:35:00-04:00",
        )
        self.assertEqual(
            tuple(map(self.iso, self.market.get_1d_impact_times(post))),
            (
                "2026-07-17T16:00:00-04:00",
                "2026-07-20T16:00:00-04:00",
            ),
        )

        self.assertEqual(
            self.iso(self.market.get_start_time(closed)),
            "2026-07-17T20:00:00-04:00",
        )
        self.assertEqual(
            self.iso(self.market.get_interval_start_time(closed)),
            "2026-07-20T04:00:00-04:00",
        )

    def test_hourly_windows_are_always_60_wall_clock_minutes_from_start(self) -> None:
        cases = {
            "pre_market": (
                "2026-07-17T08:00:00-04:00",
                "2026-07-17T08:00:00-04:00",
                "2026-07-17T09:00:00-04:00",
            ),
            "pre_market_crossing_open": (
                "2026-07-17T09:00:00-04:00",
                "2026-07-17T09:00:00-04:00",
                "2026-07-17T10:00:00-04:00",
            ),
            "regular_market_crossing_close": (
                "2026-07-17T15:30:00-04:00",
                "2026-07-17T15:30:00-04:00",
                "2026-07-17T16:30:00-04:00",
            ),
            "post_market": (
                "2026-07-17T17:00:00-04:00",
                "2026-07-17T17:00:00-04:00",
                "2026-07-17T18:00:00-04:00",
            ),
            "post_market_crossing_8pm": (
                "2026-07-17T19:30:00-04:00",
                "2026-07-17T19:30:00-04:00",
                "2026-07-17T20:30:00-04:00",
            ),
        }

        for label, (event, expected_start, expected_end) in cases.items():
            with self.subTest(label=label):
                self.assertEqual(
                    self.iso(self.market.get_interval_start_time(event)),
                    expected_start,
                )
                self.assertEqual(
                    self.iso(
                        self.market.get_interval_end_time(event, 60, False)
                    ),
                    expected_end,
                )

    def test_closed_hours_use_the_next_4am_to_5am_window(self) -> None:
        cases = {
            "before_pre_market": "2026-07-17T03:00:00-04:00",
            "at_after_hours_end": "2026-07-17T20:00:00-04:00",
            "later_that_night": "2026-07-17T21:00:00-04:00",
            "weekend": "2026-07-18T12:00:00-04:00",
        }
        expected = {
            "before_pre_market": (
                "2026-07-17T04:00:00-04:00",
                "2026-07-17T05:00:00-04:00",
            ),
            "at_after_hours_end": (
                "2026-07-20T04:00:00-04:00",
                "2026-07-20T05:00:00-04:00",
            ),
            "later_that_night": (
                "2026-07-20T04:00:00-04:00",
                "2026-07-20T05:00:00-04:00",
            ),
            "weekend": (
                "2026-07-20T04:00:00-04:00",
                "2026-07-20T05:00:00-04:00",
            ),
        }

        for label, event in cases.items():
            with self.subTest(label=label):
                start, end = expected[label]
                self.assertEqual(
                    self.iso(self.market.get_interval_start_time(event)),
                    start,
                )
                self.assertEqual(
                    self.iso(
                        self.market.get_interval_end_time(event, 60, False)
                    ),
                    end,
                )

    def test_weekend_windows(self) -> None:
        event = "2026-07-18T12:00:00-04:00"

        self.assertEqual(
            self.iso(self.market.get_start_time(event)),
            "2026-07-17T20:00:00-04:00",
        )
        self.assertEqual(
            self.iso(self.market.get_end_time(event)),
            "2026-07-20T09:35:00-04:00",
        )
        self.assertEqual(
            self.iso(self.market.get_interval_start_time(event)),
            "2026-07-20T04:00:00-04:00",
        )
        self.assertEqual(
            tuple(map(self.iso, self.market.get_1d_impact_times(event))),
            (
                "2026-07-17T16:00:00-04:00",
                "2026-07-20T16:00:00-04:00",
            ),
        )

    def test_exact_close_and_after_hours_end_boundaries(self) -> None:
        close = "2026-07-17T16:00:00-04:00"
        just_after_close = "2026-07-17T16:00:01-04:00"
        after_hours_end = "2026-07-17T20:00:00-04:00"

        self.assertEqual(self.market.get_market_session(close), "in_market")
        self.assertEqual(
            self.iso(self.market.get_start_time(close)),
            "2026-07-17T16:00:00-04:00",
        )
        self.assertEqual(
            self.iso(self.market.get_end_time(close)),
            "2026-07-17T16:00:00-04:00",
        )
        self.assertEqual(
            self.market.get_market_session(just_after_close), "post_market"
        )
        self.assertEqual(
            self.market.get_market_session(after_hours_end), "market_closed"
        )
        self.assertEqual(
            self.iso(self.market.get_interval_start_time(after_hours_end)),
            "2026-07-20T04:00:00-04:00",
        )

    def test_weekend_windows_preserve_dst_offset_changes(self) -> None:
        before_spring_change = "2026-03-06T17:00:00-05:00"
        before_fall_change = "2026-10-30T17:00:00-04:00"

        self.assertEqual(
            self.iso(self.market.get_end_time(before_spring_change)),
            "2026-03-09T09:35:00-04:00",
        )
        self.assertEqual(
            self.iso(self.market.get_end_time(before_fall_change)),
            "2026-11-02T09:35:00-05:00",
        )

    def test_early_close_after_close_uses_the_code_actual_windows(self) -> None:
        # 2025-11-28 was a 1:00 PM ET early close. At 2:00 PM the code
        # classifies the market as closed but still tests "after 4 PM".
        event = "2025-11-28T14:00:00-05:00"

        self.assertEqual(self.market.get_market_session(event), "market_closed")
        self.assertEqual(
            self.iso(self.market.get_start_time(event)),
            "2025-11-26T20:00:00-05:00",
        )
        self.assertEqual(
            self.iso(self.market.get_end_time(event)),
            "2025-11-28T09:35:00-05:00",
        )
        self.assertEqual(
            self.iso(self.market.get_interval_start_time(event)),
            "2025-11-28T04:00:00-05:00",
        )
        self.assertEqual(
            self.iso(self.market.get_interval_end_time(event, 60, False)),
            "2025-11-28T05:00:00-05:00",
        )
        self.assertEqual(
            tuple(map(self.iso, self.market.get_1d_impact_times(event))),
            (
                "2025-11-26T16:00:00-05:00",
                "2025-11-28T13:00:00-05:00",
            ),
        )


if __name__ == "__main__":
    unittest.main()
