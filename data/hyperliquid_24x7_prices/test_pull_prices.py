import unittest
from unittest.mock import patch

import pull_prices


class PullPricesTests(unittest.TestCase):
    def test_group_lookup(self):
        self.assertEqual(pull_prices.group_of("GOLD"), "commodity")
        self.assertEqual(pull_prices.group_of("SP500"), "index")
        self.assertEqual(pull_prices.group_of("AAPL"), "stock")

    def test_snapshot_normalizes_api_rows(self):
        response = [
            {
                "universe": [
                    {"name": "xyz:GOLD", "maxLeverage": 20},
                    {"name": "xyz:AAPL", "maxLeverage": 10},
                ]
            },
            [
                {
                    "markPx": "2400.5",
                    "funding": "0.0001",
                    "openInterest": "12",
                    "dayNtlVlm": "1000",
                },
                {
                    "markPx": "200",
                    "funding": None,
                    "openInterest": "5",
                    "dayNtlVlm": "bad",
                },
            ],
        ]

        with patch.object(pull_prices, "_post", return_value=response):
            rows = pull_prices.snapshot()

        self.assertEqual(rows[0]["sym"], "GOLD")
        self.assertEqual(rows[0]["group"], "commodity")
        self.assertEqual(rows[0]["mark"], 2400.5)
        self.assertEqual(rows[1]["group"], "stock")
        self.assertEqual(rows[1]["funding"], 0.0)
        self.assertEqual(rows[1]["vol"], 0.0)

    def test_funding_request_uses_xyz_symbol(self):
        with (
            patch.object(pull_prices.time, "time", return_value=1000),
            patch.object(pull_prices, "_post", side_effect=lambda body: body),
        ):
            body = pull_prices.funding_history("GOLD", hours=1)

        self.assertEqual(
            body,
            {"type": "fundingHistory", "coin": "xyz:GOLD", "startTime": -2600000},
        )

    def test_candle_request_uses_requested_window(self):
        with (
            patch.object(pull_prices.time, "time", return_value=1000),
            patch.object(pull_prices, "_post", side_effect=lambda body: body),
        ):
            body = pull_prices.candles("SILVER", interval="15m", hours=2)

        self.assertEqual(body["type"], "candleSnapshot")
        self.assertEqual(
            body["req"],
            {
                "coin": "xyz:SILVER",
                "interval": "15m",
                "startTime": -6200000,
                "endTime": 1000000,
            },
        )


if __name__ == "__main__":
    unittest.main()
