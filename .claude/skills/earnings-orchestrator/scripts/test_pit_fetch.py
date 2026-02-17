#!/usr/bin/env python3
"""Offline tests for .claude/skills/earnings-orchestrator/scripts/pit_fetch.py.

Run:
  python3 .claude/skills/earnings-orchestrator/scripts/test_pit_fetch.py
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
SCRIPT = Path(__file__).resolve().parent / "pit_fetch.py"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pit_fetch as pit_fetch_module


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

SAMPLE_PPLX_RESULTS = [
    {"url": "https://example.com/a", "title": "AAPL Q1 beat", "snippet": "EPS $2.18...",
     "date": "2024-06-10", "last_updated": "2024-06-10"},
    {"url": "https://example.com/b", "title": "AAPL guidance", "snippet": "Revenue up...",
     "date": "2024-06-14", "last_updated": "2024-06-15"},
    {"url": "https://example.com/c", "title": "Undated article", "snippet": "No date"},
]

SAMPLE_PPLX_CHAT = {
    "search_results": [
        {"url": "https://example.com/x", "title": "Chat result 1", "snippet": "...",
         "date": "2024-06-10"},
        {"url": "https://example.com/y", "title": "Chat result 2", "snippet": "...",
         "date": "2024-06-12"},
    ],
    "answer": "AAPL beat Q1 consensus EPS by $0.05.",
    "citations": ["https://example.com/x", "https://example.com/y"],
}


class FakeHTTPResponse:
    def __init__(self, payload: list[dict]) -> None:
        self.payload = payload

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self) -> "FakeHTTPResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


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
    def test_fetch_overfetches_raw_pages_before_filtering(self) -> None:
        first_page = [{"id": i} for i in range(50)]
        second_page = [{"id": 999}]
        pages: list[list[dict]] = [first_page, second_page]

        def fake_urlopen(_request, timeout=0):
            self.assertEqual(timeout, 7)
            if not pages:
                raise AssertionError("Unexpected extra page request")
            return FakeHTTPResponse(pages.pop(0))

        args = argparse.Namespace(
            limit=1,
            max_pages=3,
            date_from=None,
            date_to=None,
            updated_since=None,
            tickers=[],
            timeout=7,
        )
        with patch.object(pit_fetch_module, "urlopen", side_effect=fake_urlopen):
            out = pit_fetch_module._fetch_bz_items("fake-key", args)

        # Should continue to page 2 even when limit=1, because filtering happens later.
        self.assertEqual(len(out), 51)

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
        self.assertEqual(set(out.keys()), {"data", "gaps"})
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
        self.assertEqual(set(out.keys()), {"data", "gaps"})
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

    # ── Perplexity tests ──

    def test_pplx_search_open(self) -> None:
        """--op search, no PIT. 2 valid items, 1 undated gap."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(SAMPLE_PPLX_RESULTS), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "search",
                "--query", "dummy", "--input-file", str(path), "--limit", "10",
            )
        self.assertEqual(set(out.keys()), {"data", "gaps"})
        self.assertEqual(len(out["data"]), 2)
        self.assertTrue(any(g["type"] == "unverifiable" for g in out["gaps"]))
        self.assertIn("available_at", out["data"][0])
        self.assertEqual(out["data"][0]["available_at_source"], "provider_metadata")
        self.assertEqual(out["data"][0]["url"], "https://example.com/a")

    def test_pplx_search_pit_excludes_pit_day(self) -> None:
        """PIT=2024-06-14T16:00:00. date:2024-06-14 EXCLUDED (same day). Only 2024-06-10 passes."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(SAMPLE_PPLX_RESULTS), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "search",
                "--query", "dummy", "--input-file", str(path),
                "--pit", "2024-06-14T16:00:00-04:00", "--limit", "10",
            )
        self.assertEqual(len(out["data"]), 1)
        self.assertEqual(out["data"][0]["url"], "https://example.com/a")
        self.assertTrue(any(g["type"] == "pit_excluded" for g in out["gaps"]))

    def test_pplx_all_undated(self) -> None:
        """All items missing date -> data=[], gaps has unverifiable+no_data."""
        items = [
            {"url": "https://example.com/1", "title": "No date 1", "snippet": "..."},
            {"url": "https://example.com/2", "title": "No date 2", "snippet": "..."},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "search",
                "--query", "dummy", "--input-file", str(path),
            )
        self.assertEqual(out["data"], [])
        self.assertTrue(any(g["type"] == "unverifiable" for g in out["gaps"]))
        self.assertTrue(any(g["type"] == "no_data" for g in out["gaps"]))

    def test_pplx_date_summer_edt(self) -> None:
        """date:2024-06-10 -> available_at: 2024-06-10T00:00:00-04:00 (EDT)."""
        items = [{"url": "https://example.com/s", "title": "Summer", "snippet": "...",
                  "date": "2024-06-10"}]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "search",
                "--query", "dummy", "--input-file", str(path),
            )
        self.assertEqual(out["data"][0]["available_at"], "2024-06-10T00:00:00-04:00")

    def test_pplx_date_winter_est(self) -> None:
        """date:2024-01-15 -> available_at: 2024-01-15T00:00:00-05:00 (EST)."""
        items = [{"url": "https://example.com/w", "title": "Winter", "snippet": "...",
                  "date": "2024-01-15"}]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "search",
                "--query", "dummy", "--input-file", str(path),
            )
        self.assertEqual(out["data"][0]["available_at"], "2024-01-15T00:00:00-05:00")

    def test_pplx_dedup_by_url(self) -> None:
        """Two same-URL items -> only first kept."""
        items = [
            {"url": "https://example.com/dup", "title": "First", "snippet": "...", "date": "2024-06-10"},
            {"url": "https://example.com/dup", "title": "Second", "snippet": "...", "date": "2024-06-11"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "search",
                "--query", "dummy", "--input-file", str(path),
            )
        self.assertEqual(len(out["data"]), 1)
        self.assertEqual(out["data"][0]["title"], "First")

    def test_pplx_chat_open(self) -> None:
        """--op ask, open mode. data[] has search_results + synthesis item."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chat.json"
            path.write_text(json.dumps(SAMPLE_PPLX_CHAT), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "ask",
                "--query", "dummy", "--input-file", str(path), "--limit", "10",
            )
        search_items = [d for d in out["data"] if d.get("record_type") != "synthesis"]
        synth_items = [d for d in out["data"] if d.get("record_type") == "synthesis"]
        self.assertEqual(len(search_items), 2)
        self.assertEqual(len(synth_items), 1)
        self.assertEqual(synth_items[0]["answer"], "AAPL beat Q1 consensus EPS by $0.05.")
        self.assertEqual(synth_items[0]["citations"],
                         ["https://example.com/x", "https://example.com/y"])
        self.assertIn("available_at", synth_items[0])
        self.assertEqual(synth_items[0]["available_at_source"], "provider_metadata")

    def test_pplx_chat_pit(self) -> None:
        """--op ask + PIT. Synthesis excluded. Only pre-PIT search_results pass."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chat.json"
            path.write_text(json.dumps(SAMPLE_PPLX_CHAT), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "ask",
                "--query", "dummy", "--input-file", str(path),
                "--pit", "2024-06-11T00:00:00-04:00", "--limit", "10",
            )
        # date:2024-06-10 passes (< 2024-06-11), date:2024-06-12 excluded (>= 2024-06-11)
        search_items = [d for d in out["data"] if d.get("record_type") != "synthesis"]
        synth_items = [d for d in out["data"] if d.get("record_type") == "synthesis"]
        self.assertEqual(len(search_items), 1)
        self.assertEqual(search_items[0]["url"], "https://example.com/x")
        self.assertEqual(len(synth_items), 0)  # synthesis excluded in PIT mode

    def test_pplx_pit_utc_cross_day_boundary(self) -> None:
        """PIT in UTC crossing NY day boundary. 2024-06-15T02:00Z = 2024-06-14T22:00 EDT.
        Items dated 2024-06-14 should be EXCLUDED (PIT NY day = June 14)."""
        items = [
            {"url": "https://example.com/pre", "title": "Pre-PIT", "snippet": "...",
             "date": "2024-06-13"},
            {"url": "https://example.com/pit-day", "title": "PIT-day", "snippet": "...",
             "date": "2024-06-14"},
            {"url": "https://example.com/post", "title": "Post-PIT", "snippet": "...",
             "date": "2024-06-15"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "search",
                "--query", "dummy", "--input-file", str(path),
                "--pit", "2024-06-15T02:00:00+00:00",
            )
        # Only 2024-06-13 passes. PIT NY date = 2024-06-14, so 2024-06-14 excluded.
        self.assertEqual(len(out["data"]), 1)
        self.assertEqual(out["data"][0]["url"], "https://example.com/pre")
        self.assertTrue(any(g["type"] == "pit_excluded" for g in out["gaps"]))

    def test_pplx_open_mode_no_filtering(self) -> None:
        """Open mode passes ALL dated items with no restriction whatsoever."""
        items = [
            {"url": "https://example.com/1", "title": "Old", "snippet": "...",
             "date": "2020-01-01"},
            {"url": "https://example.com/2", "title": "Recent", "snippet": "...",
             "date": "2025-12-31"},
            {"url": "https://example.com/3", "title": "Future", "snippet": "...",
             "date": "2030-06-15"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "search",
                "--query", "dummy", "--input-file", str(path),
            )
        # ALL 3 items pass — no PIT filtering in open mode
        self.assertEqual(len(out["data"]), 3)
        self.assertFalse(any(g["type"] == "pit_excluded" for g in out["gaps"]))

    def test_pplx_open_mode_chat_all_results_plus_synthesis(self) -> None:
        """Open mode chat: ALL search_results + synthesis included, nothing excluded."""
        chat = {
            "search_results": [
                {"url": "https://example.com/a", "title": "A", "snippet": "...",
                 "date": "2020-01-01"},
                {"url": "https://example.com/b", "title": "B", "snippet": "...",
                 "date": "2030-12-31"},
            ],
            "answer": "Synthesized answer here.",
            "citations": ["https://example.com/a"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chat.json"
            path.write_text(json.dumps(chat), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "ask",
                "--query", "dummy", "--input-file", str(path),
            )
        search_items = [d for d in out["data"] if d.get("record_type") != "synthesis"]
        synth_items = [d for d in out["data"] if d.get("record_type") == "synthesis"]
        # ALL search results pass in open mode
        self.assertEqual(len(search_items), 2)
        # Synthesis included in open mode
        self.assertEqual(len(synth_items), 1)
        self.assertEqual(synth_items[0]["answer"], "Synthesized answer here.")

    def test_pplx_chat_limit_controls_search_results_only(self) -> None:
        """--limit controls search results; synthesis appended separately."""
        chat = {
            "search_results": [
                {"url": "https://example.com/a", "title": "A", "snippet": "...",
                 "date": "2024-06-10"},
                {"url": "https://example.com/b", "title": "B", "snippet": "...",
                 "date": "2024-06-12"},
                {"url": "https://example.com/c", "title": "C", "snippet": "...",
                 "date": "2024-06-13"},
            ],
            "answer": "Synthesized answer.",
            "citations": ["https://example.com/a"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chat.json"
            path.write_text(json.dumps(chat), encoding="utf-8")
            # --limit 2: 2 search results + 1 synthesis = 3 total
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "ask",
                "--query", "dummy", "--input-file", str(path),
                "--limit", "2",
            )
        search_items = [d for d in out["data"] if d.get("record_type") != "synthesis"]
        synth_items = [d for d in out["data"] if d.get("record_type") == "synthesis"]
        self.assertEqual(len(search_items), 2)  # --limit 2 caps search results
        self.assertEqual(len(synth_items), 1)    # synthesis always appended in open chat

    def test_pplx_chat_limit_1_still_has_synthesis(self) -> None:
        """--limit 1 with chat → 1 search result + synthesis (always appended)."""
        chat = {
            "search_results": [
                {"url": "https://example.com/a", "title": "A", "snippet": "...",
                 "date": "2024-06-10"},
            ],
            "answer": "Synthesized answer.",
            "citations": ["https://example.com/a"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chat.json"
            path.write_text(json.dumps(chat), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "ask",
                "--query", "dummy", "--input-file", str(path),
                "--limit", "1",
            )
        search_items = [d for d in out["data"] if d.get("record_type") != "synthesis"]
        synth_items = [d for d in out["data"] if d.get("record_type") == "synthesis"]
        self.assertEqual(len(search_items), 1)  # 1 search result
        self.assertEqual(len(synth_items), 1)    # synthesis always present in open chat

    # ── Nuance coverage: exhaustive mode/op/limit/synthesis tests ──

    def test_pplx_search_op_never_produces_synthesis(self) -> None:
        """--op search NEVER adds synthesis, even in open mode."""
        items = [
            {"url": "https://example.com/a", "title": "A", "snippet": "...",
             "date": "2024-06-10"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "search",
                "--query", "dummy", "--input-file", str(path),
            )
        synth = [d for d in out["data"] if d.get("record_type") == "synthesis"]
        self.assertEqual(len(synth), 0)  # search op never synthesizes
        self.assertEqual(len(out["data"]), 1)  # only the search result

    def test_pplx_chat_no_answer_no_synthesis(self) -> None:
        """Chat op with empty answer → no synthesis item appended."""
        chat = {
            "search_results": [
                {"url": "https://example.com/a", "title": "A", "snippet": "...",
                 "date": "2024-06-10"},
            ],
            "answer": "",
            "citations": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chat.json"
            path.write_text(json.dumps(chat), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "ask",
                "--query", "dummy", "--input-file", str(path),
            )
        synth = [d for d in out["data"] if d.get("record_type") == "synthesis"]
        self.assertEqual(len(synth), 0)  # empty answer → no synthesis
        self.assertEqual(len(out["data"]), 1)

    def test_pplx_chat_empty_search_results_synthesis_only(self) -> None:
        """Chat op with zero search results but valid answer → synthesis only in data[]."""
        chat = {
            "search_results": [],
            "answer": "No sources found but here is what I know.",
            "citations": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chat.json"
            path.write_text(json.dumps(chat), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "ask",
                "--query", "dummy", "--input-file", str(path),
            )
        self.assertEqual(len(out["data"]), 1)
        self.assertEqual(out["data"][0]["record_type"], "synthesis")
        self.assertEqual(out["data"][0]["answer"], "No sources found but here is what I know.")

    def test_pplx_pit_full_timestamp_exact_comparison(self) -> None:
        """Full ISO8601 timestamps use exact pub_dt > pit_dt, not day-level exclusion."""
        items = [
            {"url": "https://example.com/before", "title": "Before", "snippet": "...",
             "date": "2024-06-15T09:00:00-04:00"},
            {"url": "https://example.com/equal", "title": "Equal", "snippet": "...",
             "date": "2024-06-15T10:00:00-04:00"},
            {"url": "https://example.com/after", "title": "After", "snippet": "...",
             "date": "2024-06-15T11:00:00-04:00"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "search",
                "--query", "dummy", "--input-file", str(path),
                "--pit", "2024-06-15T10:00:00-04:00",
            )
        # Before (09:00 < 10:00) passes. Equal (10:00 == 10:00) passes (not >). After (11:00 > 10:00) excluded.
        self.assertEqual(len(out["data"]), 2)
        urls = [d["url"] for d in out["data"]]
        self.assertIn("https://example.com/before", urls)
        self.assertIn("https://example.com/equal", urls)
        self.assertNotIn("https://example.com/after", urls)

    def test_pplx_pit_all_items_filtered_empty_data(self) -> None:
        """PIT filters ALL items → data=[], gaps has pit_excluded."""
        items = [
            {"url": "https://example.com/a", "title": "A", "snippet": "...",
             "date": "2024-06-15"},
            {"url": "https://example.com/b", "title": "B", "snippet": "...",
             "date": "2024-06-16"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "search",
                "--query", "dummy", "--input-file", str(path),
                "--pit", "2024-06-15T00:00:00-04:00",
            )
        self.assertEqual(out["data"], [])
        self.assertTrue(any(g["type"] == "pit_excluded" for g in out["gaps"]))
        self.assertTrue(any(g["type"] == "no_data" for g in out["gaps"]))

    def test_pplx_pit_chat_limit_all_for_search_no_synthesis(self) -> None:
        """PIT chat: --limit gives ALL slots to search results, zero synthesis."""
        chat = {
            "search_results": [
                {"url": "https://example.com/a", "title": "A", "snippet": "...",
                 "date": "2024-06-01"},
                {"url": "https://example.com/b", "title": "B", "snippet": "...",
                 "date": "2024-06-05"},
            ],
            "answer": "This synthesis must not appear.",
            "citations": ["https://example.com/a"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chat.json"
            path.write_text(json.dumps(chat), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "ask",
                "--query", "dummy", "--input-file", str(path),
                "--pit", "2024-06-10T00:00:00-04:00", "--limit", "2",
            )
        search_items = [d for d in out["data"] if d.get("record_type") != "synthesis"]
        synth_items = [d for d in out["data"] if d.get("record_type") == "synthesis"]
        self.assertEqual(len(search_items), 2)  # all slots for search
        self.assertEqual(len(synth_items), 0)    # PIT mode: no synthesis ever

    def test_pplx_pit_chat_all_filtered_no_synthesis(self) -> None:
        """PIT chat: all search_results filtered + no synthesis → empty data[], pit_excluded gap."""
        chat = {
            "search_results": [
                {"url": "https://example.com/a", "title": "A", "snippet": "...",
                 "date": "2024-06-15"},
            ],
            "answer": "Synthesis should not appear.",
            "citations": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chat.json"
            path.write_text(json.dumps(chat), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "ask",
                "--query", "dummy", "--input-file", str(path),
                "--pit", "2024-06-10T00:00:00-04:00",
            )
        self.assertEqual(out["data"], [])
        synth = [d for d in out["data"] if d.get("record_type") == "synthesis"]
        self.assertEqual(len(synth), 0)
        self.assertTrue(any(g["type"] == "pit_excluded" for g in out["gaps"]))

    def test_pplx_search_limit_caps_results(self) -> None:
        """--limit for search ops caps search results correctly."""
        items = [
            {"url": f"https://example.com/{i}", "title": f"Item {i}", "snippet": "...",
             "date": f"2024-06-{10+i:02d}"}
            for i in range(5)
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "search",
                "--query", "dummy", "--input-file", str(path),
                "--limit", "3",
            )
        self.assertEqual(len(out["data"]), 3)  # capped at 3

    def test_pplx_reason_op_has_synthesis(self) -> None:
        """--op reason produces synthesis in open mode (same contract as ask)."""
        chat = {
            "search_results": [
                {"url": "https://example.com/a", "title": "A", "snippet": "...",
                 "date": "2024-06-10"},
            ],
            "answer": "Because earnings beat by 5%.",
            "citations": ["https://example.com/a"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chat.json"
            path.write_text(json.dumps(chat), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "reason",
                "--query", "dummy", "--input-file", str(path),
            )
        synth = [d for d in out["data"] if d.get("record_type") == "synthesis"]
        self.assertEqual(len(synth), 1)
        self.assertEqual(synth[0]["answer"], "Because earnings beat by 5%.")

    def test_pplx_research_op_has_synthesis(self) -> None:
        """--op research produces synthesis in open mode (same contract as ask)."""
        chat = {
            "search_results": [
                {"url": "https://example.com/a", "title": "A", "snippet": "...",
                 "date": "2024-06-10"},
            ],
            "answer": "Comprehensive analysis of AAPL Q1.",
            "citations": ["https://example.com/a"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chat.json"
            path.write_text(json.dumps(chat), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "research",
                "--query", "dummy", "--input-file", str(path),
            )
        synth = [d for d in out["data"] if d.get("record_type") == "synthesis"]
        self.assertEqual(len(synth), 1)
        self.assertEqual(synth[0]["answer"], "Comprehensive analysis of AAPL Q1.")

    def test_pplx_missing_op_gives_config_gap(self) -> None:
        """--source perplexity without --op gives config gap, not crash."""
        out = run_pit_fetch(
            "--source", "perplexity", "--query", "test",
        )
        self.assertEqual(out["data"], [])
        self.assertTrue(any(g["type"] == "config" and "--op" in g["reason"] for g in out["gaps"]))

    def test_pplx_missing_query_gives_config_gap(self) -> None:
        """--source perplexity --op search without --query gives config gap."""
        out = run_pit_fetch(
            "--source", "perplexity", "--op", "search",
        )
        self.assertEqual(out["data"], [])
        self.assertTrue(any(g["type"] == "config" and "--query" in g["reason"] for g in out["gaps"]))


if __name__ == "__main__":
    unittest.main()
