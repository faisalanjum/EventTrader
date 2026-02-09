#!/usr/bin/env python3
"""Offline tests for scripts/pit_fetch.py.

Run:
  python3 scripts/test_pit_fetch.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "pit_fetch.py"


SAMPLE_ITEMS = [
    {
        "id": 101,
        "title": "Fed minutes signal sticky inflation",
        "teaser": "Macro markets react to rates outlook.",
        "body": "The macro backdrop remains inflation-driven.",
        "created": "2026-02-01T10:00:00-05:00",
        "updated": "2026-02-01T10:10:00-05:00",
        "url": "https://example.com/a",
        "stocks": [{"name": "SPY"}],
        "channels": [{"name": "Macro"}],
        "tags": [{"name": "Inflation"}],
    },
    {
        "id": 102,
        "title": "WTI extends gains",
        "teaser": "Oil markets rally on OPEC signals.",
        "body": "Crude and Brent rise together.",
        "created": "2026-02-03T11:00:00-05:00",
        "updated": "2026-02-03T11:05:00-05:00",
        "url": "https://example.com/b",
        "stocks": [{"name": "XOM"}],
        "channels": [{"name": "Energy"}],
        "tags": [{"name": "Oil"}],
    },
    {
        "id": 103,
        "title": "Broken timestamp item",
        "created": "not-a-date",
        "channels": [{"name": "Macro"}],
        "tags": [{"name": "Rates"}],
    },
]


def run_pit_fetch(*args: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if proc.returncode != 0:
        raise AssertionError(f"pit_fetch exited {proc.returncode}: {proc.stderr}")
    try:
        return json.loads(proc.stdout.strip())
    except json.JSONDecodeError as exc:
        raise AssertionError(f"pit_fetch stdout is not JSON: {proc.stdout}") from exc


class PitFetchTests(unittest.TestCase):
    def test_open_mode_normalization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(SAMPLE_ITEMS), encoding="utf-8")
            out = run_pit_fetch(
                "--source",
                "bz-news-api",
                "--input-file",
                str(path),
                "--limit",
                "10",
            )
        self.assertEqual(out["source"], "bz-news-api")
        self.assertEqual(out["mode"], "open")
        self.assertEqual(len(out["data"]), 2)
        self.assertTrue(any(g["type"] == "unverifiable" for g in out["gaps"]))
        self.assertIn("available_at", out["data"][0])
        self.assertIn("available_at_source", out["data"][0])
        self.assertIn("body", out["data"][0])
        self.assertIn("created", out["data"][0])
        self.assertIn("updated", out["data"][0])
        self.assertEqual(out["data"][0]["body"], SAMPLE_ITEMS[0]["body"])
        self.assertEqual(out["data"][0]["available_at"], "2026-02-01T10:00:00-05:00")

    def test_pit_cutoff_filters_future_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(SAMPLE_ITEMS), encoding="utf-8")
            out = run_pit_fetch(
                "--source",
                "bz-news-api",
                "--input-file",
                str(path),
                "--pit",
                "2026-02-02T00:00:00-05:00",
                "--limit",
                "10",
            )
        self.assertEqual(out["mode"], "pit")
        self.assertEqual(len(out["data"]), 1)
        self.assertEqual(out["data"][0]["id"], "101")
        self.assertTrue(any(g["type"] == "pit_excluded" for g in out["gaps"]))

    def test_theme_and_channel_filters(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(SAMPLE_ITEMS), encoding="utf-8")
            out_macro = run_pit_fetch(
                "--source",
                "bz-news-api",
                "--input-file",
                str(path),
                "--themes",
                "macro",
            )
            out_energy = run_pit_fetch(
                "--source",
                "bz-news-api",
                "--input-file",
                str(path),
                "--channels",
                "Energy",
            )
        self.assertEqual([x["id"] for x in out_macro["data"]], ["101"])
        self.assertEqual([x["id"] for x in out_energy["data"]], ["102"])

    def test_naive_timestamp_assumes_new_york(self) -> None:
        sample = [
            {
                "id": 201,
                "title": "Naive timestamp sample",
                "teaser": "No timezone info",
                "body": "Test content",
                "created": "2026-02-10T09:30:00",
                "updated": "2026-02-10T09:45:00",
                "stocks": [{"name": "SPY"}],
                "channels": [{"name": "Macro"}],
                "tags": [{"name": "Rates"}],
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(sample), encoding="utf-8")
            out = run_pit_fetch("--source", "bz-news-api", "--input-file", str(path))
        self.assertEqual(out["data"][0]["available_at"], "2026-02-10T09:30:00-05:00")

    def test_utc_timestamp_normalizes_to_new_york_dst(self) -> None:
        sample = [
            {
                "id": 202,
                "title": "UTC summer sample",
                "teaser": "Timezone conversion check",
                "body": "Test content",
                "created": "2026-07-01T16:00:00+00:00",
                "updated": "2026-07-01T16:10:00+00:00",
                "stocks": [{"name": "SPY"}],
                "channels": [{"name": "Macro"}],
                "tags": [{"name": "Rates"}],
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(sample), encoding="utf-8")
            out = run_pit_fetch("--source", "bz-news-api", "--input-file", str(path))
        self.assertEqual(out["data"][0]["available_at"], "2026-07-01T12:00:00-04:00")


if __name__ == "__main__":
    unittest.main()
