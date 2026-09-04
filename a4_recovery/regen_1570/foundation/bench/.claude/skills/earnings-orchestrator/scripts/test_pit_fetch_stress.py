#!/usr/bin/env python3
"""Stress / edge-case tests for pit_fetch.py covering all 3 sources.

Covers edge cases that the primary test suite does not exercise:
- Benzinga: empty payloads, duplicate IDs, body=null, mixed tz offsets,
  multiple tickers/channels/tags, limit=0/1, keyword and theme combos
- Perplexity: empty strings, whitespace dates, huge limit, duplicate URLs
  across multiple results, mixed date formats in same batch, last_updated
  but no date, chat with missing keys, search with full-timestamp PIT
- Alpha Vantage: empty quarterlyEarnings/annualEarnings, all-None bucket
  fields, mixed horizons, calendar with no matching symbol, estimates with
  every bucket field missing, earnings with duplicate fiscalDateEnding

All tests work WITHOUT network access (--input-file mode).

Run:
  cd .claude/skills/earnings-orchestrator/scripts && python3 -m unittest test_pit_fetch_stress -v
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "pit_fetch.py"


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


# ============================================================================
# Benzinga stress tests
# ============================================================================

class BenzingaStressTests(unittest.TestCase):
    """Edge-case coverage for the bz-news-api source."""

    def test_empty_input_array(self) -> None:
        """Empty JSON array -> data=[], gaps has no_data."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text("[]", encoding="utf-8")
            out = run_pit_fetch("--source", "bz-news-api", "--input-file", str(path))
        self.assertEqual(out["data"], [])
        self.assertTrue(any(g["type"] == "no_data" for g in out["gaps"]))

    def test_single_item_limit_1(self) -> None:
        """--limit 1 with 3 valid items -> only 1 returned."""
        items = [
            {"id": i, "title": f"Item {i}", "teaser": "t", "body": "b",
             "created": f"2026-02-0{i}T10:00:00-05:00",
             "stocks": [{"name": "SPY"}], "channels": [], "tags": []}
            for i in range(1, 4)
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "bz-news-api", "--input-file", str(path), "--limit", "1")
        self.assertEqual(len(out["data"]), 1)

    def test_body_null_preserved(self) -> None:
        """body=null in raw -> body=None in output (not crash)."""
        items = [
            {"id": 1, "title": "No body", "created": "2026-02-01T10:00:00-05:00",
             "body": None, "stocks": [], "channels": [], "tags": []}
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch("--source", "bz-news-api", "--input-file", str(path))
        self.assertEqual(len(out["data"]), 1)
        self.assertIsNone(out["data"][0]["body"])

    def test_body_non_string_becomes_null(self) -> None:
        """body=123 (non-string) -> body=None."""
        items = [
            {"id": 1, "title": "Numeric body", "created": "2026-02-01T10:00:00-05:00",
             "body": 12345, "stocks": [], "channels": [], "tags": []}
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch("--source", "bz-news-api", "--input-file", str(path))
        self.assertIsNone(out["data"][0]["body"])

    def test_all_items_bad_timestamps(self) -> None:
        """All items have unparseable timestamps -> data=[], gaps has unverifiable + no_data."""
        items = [
            {"id": 1, "title": "Bad ts", "created": "not-a-date", "channels": [], "tags": []},
            {"id": 2, "title": "Bad ts2", "created": "", "channels": [], "tags": []},
            {"id": 3, "title": "Bad ts3", "channels": [], "tags": []},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch("--source", "bz-news-api", "--input-file", str(path))
        self.assertEqual(out["data"], [])
        self.assertTrue(any(g["type"] == "unverifiable" for g in out["gaps"]))
        self.assertTrue(any(g["type"] == "no_data" for g in out["gaps"]))

    def test_duplicate_id_same_available_at_deduped(self) -> None:
        """Two items with same id + available_at -> only one in output."""
        items = [
            {"id": 1, "title": "First", "body": "first", "created": "2026-02-01T10:00:00-05:00",
             "stocks": [], "channels": [], "tags": []},
            {"id": 1, "title": "Duplicate", "body": "dup", "created": "2026-02-01T10:00:00-05:00",
             "stocks": [], "channels": [], "tags": []},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch("--source", "bz-news-api", "--input-file", str(path))
        self.assertEqual(len(out["data"]), 1)
        self.assertEqual(out["data"][0]["title"], "First")

    def test_pit_equal_to_created_passes(self) -> None:
        """PIT exactly equal to created timestamp -> item passes (not > pit)."""
        items = [
            {"id": 1, "title": "Exact", "body": "b", "created": "2026-02-01T10:00:00-05:00",
             "stocks": [], "channels": [], "tags": []}
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "bz-news-api", "--input-file", str(path),
                "--pit", "2026-02-01T10:00:00-05:00")
        self.assertEqual(len(out["data"]), 1)

    def test_pit_one_second_before_excludes(self) -> None:
        """PIT 1 second before created -> item excluded."""
        items = [
            {"id": 1, "title": "Just after", "body": "b", "created": "2026-02-01T10:00:01-05:00",
             "stocks": [], "channels": [], "tags": []}
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "bz-news-api", "--input-file", str(path),
                "--pit", "2026-02-01T10:00:00-05:00")
        self.assertEqual(out["data"], [])
        self.assertTrue(any(g["type"] == "pit_excluded" for g in out["gaps"]))

    def test_multiple_channel_filter(self) -> None:
        """--channels Energy,Macro -> items matching either channel pass."""
        items = [
            {"id": 1, "title": "Macro", "body": "b", "created": "2026-02-01T10:00:00-05:00",
             "stocks": [], "channels": [{"name": "Macro"}], "tags": []},
            {"id": 2, "title": "Energy", "body": "b", "created": "2026-02-02T10:00:00-05:00",
             "stocks": [], "channels": [{"name": "Energy"}], "tags": []},
            {"id": 3, "title": "Tech", "body": "b", "created": "2026-02-03T10:00:00-05:00",
             "stocks": [], "channels": [{"name": "Tech"}], "tags": []},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "bz-news-api", "--input-file", str(path),
                "--channels", "Energy,Macro")
        self.assertEqual(len(out["data"]), 2)
        ids = {d["id"] for d in out["data"]}
        self.assertEqual(ids, {"1", "2"})

    def test_tag_filter(self) -> None:
        """--tags Oil -> only items with that tag pass."""
        items = [
            {"id": 1, "title": "Oil", "body": "b", "created": "2026-02-01T10:00:00-05:00",
             "stocks": [], "channels": [], "tags": [{"name": "Oil"}]},
            {"id": 2, "title": "Rates", "body": "b", "created": "2026-02-02T10:00:00-05:00",
             "stocks": [], "channels": [], "tags": [{"name": "Rates"}]},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "bz-news-api", "--input-file", str(path),
                "--tags", "oil")
        self.assertEqual(len(out["data"]), 1)
        self.assertEqual(out["data"][0]["id"], "1")

    def test_keyword_filter_matches_body(self) -> None:
        """--keywords inflation -> matches body text."""
        items = [
            {"id": 1, "title": "News", "body": "CPI and inflation data released",
             "created": "2026-02-01T10:00:00-05:00", "stocks": [], "channels": [], "tags": []},
            {"id": 2, "title": "News2", "body": "Earnings beat expectations",
             "created": "2026-02-02T10:00:00-05:00", "stocks": [], "channels": [], "tags": []},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "bz-news-api", "--input-file", str(path),
                "--keywords", "inflation")
        self.assertEqual(len(out["data"]), 1)
        self.assertEqual(out["data"][0]["id"], "1")

    def test_theme_macro_expands_keywords(self) -> None:
        """--themes macro expands to THEME_KEYWORDS[macro] and matches title/body/tags."""
        items = [
            {"id": 1, "title": "Fed hikes rates", "body": "b",
             "created": "2026-02-01T10:00:00-05:00", "stocks": [], "channels": [], "tags": []},
            {"id": 2, "title": "Earnings season", "body": "AAPL beat",
             "created": "2026-02-02T10:00:00-05:00", "stocks": [], "channels": [], "tags": []},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "bz-news-api", "--input-file", str(path),
                "--themes", "macro")
        self.assertEqual(len(out["data"]), 1)
        self.assertEqual(out["data"][0]["id"], "1")

    def test_mixed_timezone_offsets_normalize(self) -> None:
        """Items with different tz offsets all normalize to NY tz in available_at."""
        items = [
            {"id": 1, "title": "UTC", "body": "b", "created": "2026-02-01T15:00:00+00:00",
             "stocks": [], "channels": [], "tags": []},
            {"id": 2, "title": "EST", "body": "b", "created": "2026-02-01T10:00:00-05:00",
             "stocks": [], "channels": [], "tags": []},
            {"id": 3, "title": "CST", "body": "b", "created": "2026-02-01T09:00:00-06:00",
             "stocks": [], "channels": [], "tags": []},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch("--source", "bz-news-api", "--input-file", str(path))
        # All three times are the same instant: 15:00 UTC = 10:00 EST = 09:00 CST
        for d in out["data"]:
            self.assertEqual(d["available_at"], "2026-02-01T10:00:00-05:00")

    def test_symbols_field_alt_key(self) -> None:
        """Items using 'symbols' instead of 'stocks' -> still extracts symbols."""
        items = [
            {"id": 1, "title": "Alt", "body": "b", "created": "2026-02-01T10:00:00-05:00",
             "symbols": [{"name": "AAPL"}], "channels": [], "tags": []}
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch("--source", "bz-news-api", "--input-file", str(path))
        self.assertEqual(out["data"][0]["symbols"], ["AAPL"])

    def test_tickers_filter(self) -> None:
        """--tickers AAPL -> only items with AAPL symbol."""
        items = [
            {"id": 1, "title": "AAPL", "body": "b", "created": "2026-02-01T10:00:00-05:00",
             "stocks": [{"name": "AAPL"}], "channels": [], "tags": []},
            {"id": 2, "title": "MSFT", "body": "b", "created": "2026-02-02T10:00:00-05:00",
             "stocks": [{"name": "MSFT"}], "channels": [], "tags": []},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "bz-news-api", "--input-file", str(path),
                "--tickers", "AAPL")
        self.assertEqual(len(out["data"]), 1)
        self.assertEqual(out["data"][0]["id"], "1")

    def test_large_batch_with_limit(self) -> None:
        """100 items with --limit 5 -> exactly 5 returned."""
        items = [
            {"id": i, "title": f"Item {i}", "body": "b",
             "created": f"2026-02-01T{10 + (i % 12):02d}:{i % 60:02d}:00-05:00",
             "stocks": [], "channels": [], "tags": []}
            for i in range(100)
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "bz-news-api", "--input-file", str(path), "--limit", "5")
        self.assertEqual(len(out["data"]), 5)

    def test_benzinga_alias_source_names(self) -> None:
        """'benzinga' and 'benzinga-news' are accepted as source aliases."""
        items = [
            {"id": 1, "title": "T", "body": "b", "created": "2026-02-01T10:00:00-05:00",
             "stocks": [], "channels": [], "tags": []}
        ]
        for source in ("benzinga", "benzinga-news"):
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "items.json"
                path.write_text(json.dumps(items), encoding="utf-8")
                out = run_pit_fetch("--source", source, "--input-file", str(path))
            self.assertEqual(len(out["data"]), 1, f"Failed for source={source}")

    def test_input_file_object_with_items_key(self) -> None:
        """Input JSON as {items: [...]} -> items extracted correctly."""
        payload = {"items": [
            {"id": 1, "title": "Obj", "body": "b", "created": "2026-02-01T10:00:00-05:00",
             "stocks": [], "channels": [], "tags": []}
        ]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            out = run_pit_fetch("--source", "bz-news-api", "--input-file", str(path))
        self.assertEqual(len(out["data"]), 1)

    def test_raw_item_not_object(self) -> None:
        """Non-dict items in array -> skipped as unverifiable."""
        items = ["string-item", 42, None, True]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch("--source", "bz-news-api", "--input-file", str(path))
        self.assertEqual(out["data"], [])
        self.assertTrue(any(g["type"] == "unverifiable" for g in out["gaps"]))


# ============================================================================
# Perplexity stress tests
# ============================================================================

class PerplexityStressTests(unittest.TestCase):
    """Edge-case coverage for the perplexity source."""

    def test_empty_search_results(self) -> None:
        """Empty results array -> data=[], gaps has no_data."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text("[]", encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "search",
                "--query", "test", "--input-file", str(path))
        self.assertEqual(out["data"], [])
        self.assertTrue(any(g["type"] == "no_data" for g in out["gaps"]))

    def test_whitespace_only_date_treated_as_missing(self) -> None:
        """date=" " (whitespace) -> item gapped as unverifiable."""
        items = [
            {"url": "https://example.com/ws", "title": "WS", "snippet": "...", "date": "   "}
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "search",
                "--query", "test", "--input-file", str(path))
        self.assertEqual(out["data"], [])
        self.assertTrue(any(g["type"] == "unverifiable" for g in out["gaps"]))

    def test_date_empty_string(self) -> None:
        """date="" -> gapped as unverifiable."""
        items = [
            {"url": "https://example.com/e", "title": "E", "snippet": "...", "date": ""}
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "search",
                "--query", "test", "--input-file", str(path))
        self.assertEqual(out["data"], [])
        self.assertTrue(any(g["type"] == "unverifiable" for g in out["gaps"]))

    def test_date_integer_treated_as_missing(self) -> None:
        """date=12345 (non-string) -> gapped."""
        items = [
            {"url": "https://example.com/i", "title": "I", "snippet": "...", "date": 12345}
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "search",
                "--query", "test", "--input-file", str(path))
        self.assertEqual(out["data"], [])

    def test_last_updated_without_date_still_gapped(self) -> None:
        """last_updated present but no date -> gapped (date is required for PIT)."""
        items = [
            {"url": "https://example.com/lu", "title": "LU", "snippet": "...",
             "last_updated": "2024-06-15"}
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "search",
                "--query", "test", "--input-file", str(path))
        self.assertEqual(out["data"], [])

    def test_duplicate_urls_across_batch(self) -> None:
        """Same URL appearing 5 times -> only first kept."""
        items = [
            {"url": "https://example.com/dup", "title": f"Copy {i}", "snippet": "...",
             "date": f"2024-06-{10+i:02d}"}
            for i in range(5)
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "search",
                "--query", "test", "--input-file", str(path))
        self.assertEqual(len(out["data"]), 1)
        self.assertEqual(out["data"][0]["title"], "Copy 0")

    def test_mixed_date_formats_in_batch(self) -> None:
        """Date-only and full-timestamp items in same batch both work."""
        items = [
            {"url": "https://example.com/do", "title": "DateOnly", "snippet": "...",
             "date": "2024-06-10"},
            {"url": "https://example.com/ft", "title": "FullTS", "snippet": "...",
             "date": "2024-06-12T14:30:00-04:00"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "search",
                "--query", "test", "--input-file", str(path))
        self.assertEqual(len(out["data"]), 2)
        # Date-only gets start-of-day NY
        self.assertEqual(out["data"][0]["available_at"], "2024-06-10T00:00:00-04:00")
        # Full timestamp normalized to NY
        self.assertEqual(out["data"][1]["available_at"], "2024-06-12T14:30:00-04:00")

    def test_pit_mixed_formats_filtering(self) -> None:
        """PIT with mix of date-only and full-timestamp items: correct 2-tier filtering."""
        items = [
            # Date-only: 2024-06-14 -> excluded (same day as PIT NY date)
            {"url": "https://example.com/a", "title": "A", "snippet": "...",
             "date": "2024-06-14"},
            # Full timestamp: 2024-06-14T09:00 <= PIT 10:00 -> passes
            {"url": "https://example.com/b", "title": "B", "snippet": "...",
             "date": "2024-06-14T09:00:00-04:00"},
            # Full timestamp: 2024-06-14T11:00 > PIT 10:00 -> excluded
            {"url": "https://example.com/c", "title": "C", "snippet": "...",
             "date": "2024-06-14T11:00:00-04:00"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "search",
                "--query", "test", "--input-file", str(path),
                "--pit", "2024-06-14T10:00:00-04:00")
        # Only B passes (full timestamp <= PIT)
        self.assertEqual(len(out["data"]), 1)
        self.assertEqual(out["data"][0]["url"], "https://example.com/b")

    def test_chat_missing_answer_key(self) -> None:
        """Chat JSON missing 'answer' key -> no synthesis, search results still pass."""
        chat = {
            "search_results": [
                {"url": "https://example.com/a", "title": "A", "snippet": "...",
                 "date": "2024-06-10"},
            ],
            "citations": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chat.json"
            path.write_text(json.dumps(chat), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "ask",
                "--query", "test", "--input-file", str(path))
        search = [d for d in out["data"] if d.get("record_type") != "synthesis"]
        synth = [d for d in out["data"] if d.get("record_type") == "synthesis"]
        self.assertEqual(len(search), 1)
        self.assertEqual(len(synth), 0)  # no answer -> no synthesis

    def test_chat_missing_search_results_key(self) -> None:
        """Chat JSON missing 'search_results' -> synthesis only if answer present."""
        chat = {
            "answer": "Some answer without search results.",
            "citations": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chat.json"
            path.write_text(json.dumps(chat), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "ask",
                "--query", "test", "--input-file", str(path))
        synth = [d for d in out["data"] if d.get("record_type") == "synthesis"]
        self.assertEqual(len(synth), 1)
        self.assertEqual(synth[0]["answer"], "Some answer without search results.")

    def test_chat_missing_citations_key(self) -> None:
        """Chat JSON missing 'citations' key -> synthesis has empty citations list."""
        chat = {
            "search_results": [],
            "answer": "Answer without citations key.",
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chat.json"
            path.write_text(json.dumps(chat), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "ask",
                "--query", "test", "--input-file", str(path))
        synth = [d for d in out["data"] if d.get("record_type") == "synthesis"]
        self.assertEqual(len(synth), 1)
        self.assertEqual(synth[0]["citations"], [])

    def test_search_large_limit(self) -> None:
        """--limit 1000 with 3 items -> returns all 3 (no crash from oversized limit)."""
        items = [
            {"url": f"https://example.com/{i}", "title": f"Item {i}", "snippet": "...",
             "date": f"2024-06-{10+i:02d}"}
            for i in range(3)
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "search",
                "--query", "test", "--input-file", str(path),
                "--limit", "1000")
        self.assertEqual(len(out["data"]), 3)

    def test_search_limit_0_becomes_1(self) -> None:
        """--limit 0 is clamped to 1 (min) -> returns 1 item."""
        items = [
            {"url": f"https://example.com/{i}", "title": f"Item {i}", "snippet": "...",
             "date": f"2024-06-{10+i:02d}"}
            for i in range(3)
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "search",
                "--query", "test", "--input-file", str(path),
                "--limit", "0")
        self.assertEqual(len(out["data"]), 1)

    def test_url_missing_still_passes_no_dedup(self) -> None:
        """Items with url=None -> no dedup, both pass through."""
        items = [
            {"title": "No URL 1", "snippet": "...", "date": "2024-06-10"},
            {"title": "No URL 2", "snippet": "...", "date": "2024-06-11"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "search",
                "--query", "test", "--input-file", str(path))
        self.assertEqual(len(out["data"]), 2)

    def test_non_dict_items_in_search_skipped(self) -> None:
        """Non-dict items in search results -> skipped."""
        items = ["string", 42, None, {"url": "https://example.com/ok", "title": "OK",
                                       "snippet": "...", "date": "2024-06-10"}]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "search",
                "--query", "test", "--input-file", str(path))
        self.assertEqual(len(out["data"]), 1)
        self.assertEqual(out["data"][0]["url"], "https://example.com/ok")

    def test_pit_utc_plus_offset_cross_day(self) -> None:
        """PIT in UTC+9 crossing day boundary. Verifies NY-timezone conversion."""
        # 2024-06-15T04:00:00+09:00 = 2024-06-14T19:00:00 UTC = 2024-06-14T15:00:00 EDT
        # PIT NY date = 2024-06-14
        # Date-only items: 2024-06-14 excluded (same day), 2024-06-13 passes
        items = [
            {"url": "https://example.com/pre", "title": "Pre", "snippet": "...",
             "date": "2024-06-13"},
            {"url": "https://example.com/same", "title": "Same", "snippet": "...",
             "date": "2024-06-14"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "search",
                "--query", "test", "--input-file", str(path),
                "--pit", "2024-06-15T04:00:00+09:00")
        self.assertEqual(len(out["data"]), 1)
        self.assertEqual(out["data"][0]["url"], "https://example.com/pre")

    def test_chat_pit_excludes_synthesis(self) -> None:
        """PIT mode chat: synthesis is always excluded, even with valid search results."""
        chat = {
            "search_results": [
                {"url": "https://example.com/a", "title": "A", "snippet": "...",
                 "date": "2024-06-01"},
            ],
            "answer": "Synthesis that should be excluded.",
            "citations": ["https://example.com/a"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chat.json"
            path.write_text(json.dumps(chat), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "ask",
                "--query", "test", "--input-file", str(path),
                "--pit", "2024-06-15T00:00:00-04:00")
        synth = [d for d in out["data"] if d.get("record_type") == "synthesis"]
        self.assertEqual(len(synth), 0)
        search = [d for d in out["data"] if d.get("record_type") != "synthesis"]
        self.assertEqual(len(search), 1)

    def test_invalid_pit_timestamp(self) -> None:
        """--pit not-a-date -> invalid_pit gap, items still pass (open mode fallback)."""
        items = [
            {"url": "https://example.com/a", "title": "A", "snippet": "...",
             "date": "2024-06-10"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "perplexity", "--op", "search",
                "--query", "test", "--input-file", str(path),
                "--pit", "not-a-date")
        self.assertTrue(any(g["type"] == "invalid_pit" for g in out["gaps"]))


# ============================================================================
# Alpha Vantage stress tests
# ============================================================================

class AlphaVantageStressTests(unittest.TestCase):
    """Edge-case coverage for the alphavantage source."""

    def test_empty_quarterly_and_annual(self) -> None:
        """Empty quarterlyEarnings + annualEarnings -> data=[], gaps has no_data."""
        sample = {"symbol": "AAPL", "annualEarnings": [], "quarterlyEarnings": []}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "av.json"
            path.write_text(json.dumps(sample), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "alphavantage", "--op", "earnings",
                "--symbol", "AAPL", "--input-file", str(path))
        self.assertEqual(out["data"], [])
        self.assertTrue(any(g["type"] == "no_data" for g in out["gaps"]))

    def test_quarterly_missing_reported_date(self) -> None:
        """Quarterly item without reportedDate -> gapped as unverifiable."""
        sample = {
            "symbol": "AAPL", "annualEarnings": [],
            "quarterlyEarnings": [
                {"fiscalDateEnding": "2024-09-30", "reportedEPS": "1.64"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "av.json"
            path.write_text(json.dumps(sample), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "alphavantage", "--op", "earnings",
                "--symbol", "AAPL", "--input-file", str(path))
        self.assertEqual(len([d for d in out["data"] if d.get("record_type") == "quarterly_earnings"]), 0)
        self.assertTrue(any(g["type"] == "unverifiable" for g in out["gaps"]))

    def test_quarterly_empty_reported_date(self) -> None:
        """reportedDate="" -> gapped as unverifiable."""
        sample = {
            "symbol": "AAPL", "annualEarnings": [],
            "quarterlyEarnings": [
                {"fiscalDateEnding": "2024-09-30", "reportedDate": "",
                 "reportedEPS": "1.64"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "av.json"
            path.write_text(json.dumps(sample), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "alphavantage", "--op", "earnings",
                "--symbol", "AAPL", "--input-file", str(path))
        quarterly = [d for d in out["data"] if d.get("record_type") == "quarterly_earnings"]
        self.assertEqual(len(quarterly), 0)

    def test_duplicate_fiscal_date_ending_quarterly(self) -> None:
        """Two quarterly items with same fiscalDateEnding but different reportedDate -> both pass."""
        sample = {
            "symbol": "AAPL", "annualEarnings": [],
            "quarterlyEarnings": [
                {"fiscalDateEnding": "2024-09-30", "reportedDate": "2024-10-31",
                 "reportedEPS": "1.64"},
                {"fiscalDateEnding": "2024-09-30", "reportedDate": "2024-10-31",
                 "reportedEPS": "1.64"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "av.json"
            path.write_text(json.dumps(sample), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "alphavantage", "--op", "earnings",
                "--symbol", "AAPL", "--input-file", str(path))
        quarterly = [d for d in out["data"] if d.get("record_type") == "quarterly_earnings"]
        # Both pass (no dedup on AV quarterly)
        self.assertEqual(len(quarterly), 2)

    def test_annual_multiple_unresolved(self) -> None:
        """Multiple annual items with no matching quarterly -> all unresolved."""
        sample = {
            "symbol": "AAPL",
            "annualEarnings": [
                {"fiscalDateEnding": "2020-09-30", "reportedEPS": "3.28"},
                {"fiscalDateEnding": "2019-09-30", "reportedEPS": "2.97"},
                {"fiscalDateEnding": "2018-09-30", "reportedEPS": "2.98"},
            ],
            "quarterlyEarnings": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "av.json"
            path.write_text(json.dumps(sample), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "alphavantage", "--op", "earnings",
                "--symbol", "AAPL", "--input-file", str(path))
        annual = [d for d in out["data"] if d.get("record_type") == "annual_earnings"]
        self.assertEqual(len(annual), 0)
        unverifiable = [g for g in out["gaps"] if g["type"] == "unverifiable"
                        and "annual" in g.get("reason", "").lower()]
        self.assertTrue(len(unverifiable) > 0)
        # reason should mention all 3 unresolved
        self.assertIn("3", unverifiable[0]["reason"])

    def test_earnings_limit_caps_quarterly(self) -> None:
        """--limit 2 with 4 quarterly -> only first 2 returned."""
        sample = {
            "symbol": "AAPL", "annualEarnings": [],
            "quarterlyEarnings": [
                {"fiscalDateEnding": f"2024-{(i*3):02d}-30", "reportedDate": f"2024-{(i*3)+1:02d}-15",
                 "reportedEPS": str(1.5 + i * 0.1)}
                for i in range(1, 5)
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "av.json"
            path.write_text(json.dumps(sample), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "alphavantage", "--op", "earnings",
                "--symbol", "AAPL", "--input-file", str(path),
                "--limit", "2")
        quarterly = [d for d in out["data"] if d.get("record_type") == "quarterly_earnings"]
        self.assertEqual(len(quarterly), 2)

    def test_estimates_empty(self) -> None:
        """Empty estimates array -> data=[], gaps has no_data."""
        sample = {"symbol": "AAPL", "estimates": []}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "av.json"
            path.write_text(json.dumps(sample), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "alphavantage", "--op", "estimates",
                "--symbol", "AAPL", "--input-file", str(path))
        self.assertEqual(out["data"], [])
        self.assertTrue(any(g["type"] == "no_data" for g in out["gaps"]))

    def test_estimates_all_buckets_none(self) -> None:
        """All bucket fields are None -> gapped with 'missing revision bucket'."""
        sample = {"symbol": "AAPL", "estimates": [
            {"date": "2024-06-30", "horizon": "historical fiscal quarter",
             "eps_estimate_average": "1.35",
             "eps_estimate_average_7_days_ago": None,
             "eps_estimate_average_30_days_ago": None,
             "eps_estimate_average_60_days_ago": None,
             "eps_estimate_average_90_days_ago": None},
        ]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "av.json"
            path.write_text(json.dumps(sample), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "alphavantage", "--op", "estimates",
                "--symbol", "AAPL", "--input-file", str(path),
                "--pit", "2024-06-27T10:00:00-04:00")
        resolved = [d for d in out["data"] if d["record_type"] == "estimate"]
        self.assertEqual(len(resolved), 0)
        self.assertTrue(any("missing revision bucket" in g.get("reason", "") for g in out["gaps"]))

    def test_estimates_bucket_value_dash(self) -> None:
        """Bucket field = '-' (dash) -> treated as missing, item gapped."""
        sample = {"symbol": "AAPL", "estimates": [
            {"date": "2024-06-30", "horizon": "historical fiscal quarter",
             "eps_estimate_average": "1.35",
             "eps_estimate_average_7_days_ago": "-",
             "eps_estimate_average_30_days_ago": "1.24"},
        ]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "av.json"
            path.write_text(json.dumps(sample), encoding="utf-8")
            # PIT 3 days before fiscal end -> selects 7d bucket -> value is "-" -> gap
            out = run_pit_fetch(
                "--source", "alphavantage", "--op", "estimates",
                "--symbol", "AAPL", "--input-file", str(path),
                "--pit", "2024-06-27T10:00:00-04:00")
        resolved = [d for d in out["data"] if d["record_type"] == "estimate"]
        self.assertEqual(len(resolved), 0)

    def test_estimates_bucket_value_none_string(self) -> None:
        """Bucket field = 'None' (string) -> treated as missing."""
        sample = {"symbol": "AAPL", "estimates": [
            {"date": "2024-06-30", "horizon": "historical fiscal quarter",
             "eps_estimate_average": "1.35",
             "eps_estimate_average_7_days_ago": "None",
             "eps_estimate_average_30_days_ago": "1.24"},
        ]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "av.json"
            path.write_text(json.dumps(sample), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "alphavantage", "--op", "estimates",
                "--symbol", "AAPL", "--input-file", str(path),
                "--pit", "2024-06-27T10:00:00-04:00")
        resolved = [d for d in out["data"] if d["record_type"] == "estimate"]
        self.assertEqual(len(resolved), 0)

    def test_estimates_mixed_horizons_pit(self) -> None:
        """Mix of historical and forward horizons in PIT mode: only historical resolved."""
        sample = {"symbol": "AAPL", "estimates": [
            {"date": "2024-03-31", "horizon": "historical fiscal quarter",
             "eps_estimate_average": "1.50",
             "eps_estimate_average_7_days_ago": "1.49",
             "eps_estimate_average_30_days_ago": "1.45"},
            {"date": "2024-09-30", "horizon": "historical fiscal year",
             "eps_estimate_average": "6.00",
             "eps_estimate_average_7_days_ago": "5.95",
             "eps_estimate_average_30_days_ago": "5.85"},
            {"date": "2025-06-30", "horizon": "next fiscal quarter",
             "eps_estimate_average": "1.72"},
            {"date": "2025-09-30", "horizon": "next fiscal year",
             "eps_estimate_average": "8.49"},
        ]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "av.json"
            path.write_text(json.dumps(sample), encoding="utf-8")
            # PIT after both historical fiscal ends
            out = run_pit_fetch(
                "--source", "alphavantage", "--op", "estimates",
                "--symbol", "AAPL", "--input-file", str(path),
                "--pit", "2024-10-15T10:00:00-04:00")
        resolved = [d for d in out["data"] if d["record_type"] == "estimate"]
        # Both historical items should be at_period_end
        self.assertEqual(len(resolved), 2)
        for d in resolved:
            self.assertEqual(d["pit_bucket"], "at_period_end")
        # Forward gapped
        self.assertTrue(any("forward-looking" in g.get("reason", "") for g in out["gaps"]))

    def test_estimates_open_mode_all_pass(self) -> None:
        """Open mode: all estimates pass regardless of horizon."""
        sample = {"symbol": "AAPL", "estimates": [
            {"date": "2024-03-31", "horizon": "historical fiscal quarter",
             "eps_estimate_average": "1.50"},
            {"date": "2025-06-30", "horizon": "next fiscal quarter",
             "eps_estimate_average": "1.72"},
        ]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "av.json"
            path.write_text(json.dumps(sample), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "alphavantage", "--op", "estimates",
                "--symbol", "AAPL", "--input-file", str(path))
        self.assertEqual(len(out["data"]), 2)
        self.assertTrue(all(d["record_type"] == "estimate" for d in out["data"]))

    def test_estimates_missing_date_field(self) -> None:
        """Estimate item with missing 'date' field in PIT mode -> gapped."""
        sample = {"symbol": "AAPL", "estimates": [
            {"horizon": "historical fiscal quarter",
             "eps_estimate_average": "1.50",
             "eps_estimate_average_7_days_ago": "1.49"},
        ]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "av.json"
            path.write_text(json.dumps(sample), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "alphavantage", "--op", "estimates",
                "--symbol", "AAPL", "--input-file", str(path),
                "--pit", "2024-10-15T10:00:00-04:00")
        resolved = [d for d in out["data"] if d["record_type"] == "estimate"]
        self.assertEqual(len(resolved), 0)

    def test_calendar_no_matching_symbol(self) -> None:
        """Calendar CSV with no matching symbol -> data=[], gaps has no_data."""
        csv_text = "symbol,name,reportDate,fiscalDateEnding,estimate,currency,timeOfTheDay\nMSFT,MICROSOFT CORP,2025-07-22,2025-06-30,3.25,USD,post-market\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cal.csv"
            path.write_text(csv_text, encoding="utf-8")
            out = run_pit_fetch(
                "--source", "alphavantage", "--op", "calendar",
                "--symbol", "AAPL", "--input-file", str(path))
        cal = [d for d in out["data"] if d.get("record_type") == "earnings_calendar"]
        self.assertEqual(len(cal), 0)
        self.assertTrue(any(g["type"] == "no_data" for g in out["gaps"]))

    def test_calendar_multiple_symbols(self) -> None:
        """Calendar CSV with multiple symbols -> only matching symbol returned."""
        csv_text = (
            "symbol,name,reportDate,fiscalDateEnding,estimate,currency,timeOfTheDay\n"
            "AAPL,APPLE INC,2025-07-31,2025-06-30,1.72,USD,post-market\n"
            "MSFT,MICROSOFT CORP,2025-07-22,2025-06-30,3.25,USD,post-market\n"
            "AAPL,APPLE INC,2025-10-30,2025-09-30,2.10,USD,post-market\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cal.csv"
            path.write_text(csv_text, encoding="utf-8")
            out = run_pit_fetch(
                "--source", "alphavantage", "--op", "calendar",
                "--symbol", "AAPL", "--input-file", str(path))
        cal = [d for d in out["data"] if d.get("record_type") == "earnings_calendar"]
        self.assertEqual(len(cal), 2)
        self.assertTrue(all(c["symbol"] == "AAPL" for c in cal))

    def test_calendar_case_insensitive_symbol(self) -> None:
        """Calendar symbol filter is case-insensitive (--symbol aapl matches AAPL)."""
        csv_text = "symbol,name,reportDate,fiscalDateEnding,estimate,currency,timeOfTheDay\nAAPL,APPLE INC,2025-07-31,2025-06-30,1.72,USD,post-market\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cal.csv"
            path.write_text(csv_text, encoding="utf-8")
            out = run_pit_fetch(
                "--source", "alphavantage", "--op", "calendar",
                "--symbol", "aapl", "--input-file", str(path))
        cal = [d for d in out["data"] if d.get("record_type") == "earnings_calendar"]
        self.assertEqual(len(cal), 1)

    def test_av_error_information_key(self) -> None:
        """AV 'Information' error response -> upstream_error gap."""
        error_json = json.dumps({"Information": "Please consider upgrading to a premium plan."})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "av.json"
            path.write_text(error_json, encoding="utf-8")
            out = run_pit_fetch(
                "--source", "alphavantage", "--op", "earnings",
                "--symbol", "AAPL", "--input-file", str(path))
        self.assertTrue(any(g["type"] == "upstream_error" for g in out["gaps"]))
        self.assertEqual(out["data"], [])

    def test_av_error_with_extra_keys_not_error(self) -> None:
        """AV response with 'Note' + other keys -> NOT treated as error."""
        data = {
            "Note": "Some note",
            "quarterlyEarnings": [],
            "annualEarnings": [],
            "symbol": "AAPL",
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "av.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "alphavantage", "--op", "earnings",
                "--symbol", "AAPL", "--input-file", str(path))
        # Not an error (Note + other keys means it's a valid response with a note)
        self.assertFalse(any(g["type"] == "upstream_error" for g in out["gaps"]))

    def test_estimates_at_period_end_strips_nothing_in_open(self) -> None:
        """Open mode estimates preserve all fields (no stripping)."""
        sample = {"symbol": "AAPL", "estimates": [
            {"date": "2024-06-30", "horizon": "historical fiscal quarter",
             "eps_estimate_average": "1.35",
             "eps_estimate_average_7_days_ago": "1.34",
             "eps_estimate_average_30_days_ago": "1.24",
             "eps_estimate_average_60_days_ago": "1.32",
             "eps_estimate_average_90_days_ago": "1.22"},
        ]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "av.json"
            path.write_text(json.dumps(sample), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "alphavantage", "--op", "estimates",
                "--symbol", "AAPL", "--input-file", str(path))
        d = out["data"][0]
        self.assertEqual(d["eps_estimate_average"], "1.35")
        self.assertEqual(d["eps_estimate_average_7_days_ago"], "1.34")
        self.assertEqual(d["eps_estimate_average_30_days_ago"], "1.24")
        self.assertEqual(d["eps_estimate_average_60_days_ago"], "1.32")
        self.assertEqual(d["eps_estimate_average_90_days_ago"], "1.22")
        # No pit-specific fields in open mode
        self.assertNotIn("pit_consensus_eps", d)
        self.assertNotIn("pit_bucket", d)

    def test_estimates_pit_strips_contaminating_fields(self) -> None:
        """PIT mode estimates strip eps_estimate_average and all bucket columns."""
        sample = {"symbol": "AAPL", "estimates": [
            {"date": "2024-06-30", "horizon": "historical fiscal quarter",
             "eps_estimate_average": "1.35",
             "eps_estimate_average_7_days_ago": "1.34",
             "eps_estimate_average_30_days_ago": "1.24",
             "eps_estimate_average_60_days_ago": "1.32",
             "eps_estimate_average_90_days_ago": "1.22"},
        ]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "av.json"
            path.write_text(json.dumps(sample), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "alphavantage", "--op", "estimates",
                "--symbol", "AAPL", "--input-file", str(path),
                "--pit", "2024-06-27T10:00:00-04:00")
        d = out["data"][0]
        self.assertIn("pit_consensus_eps", d)
        self.assertIn("pit_bucket", d)
        # All contaminating fields must be absent
        self.assertNotIn("eps_estimate_average", d)
        self.assertNotIn("eps_estimate_high", d)
        self.assertNotIn("eps_estimate_low", d)
        self.assertNotIn("revenue_estimate_average", d)
        self.assertNotIn("eps_estimate_average_7_days_ago", d)
        self.assertNotIn("eps_estimate_average_30_days_ago", d)
        self.assertNotIn("eps_estimate_average_60_days_ago", d)
        self.assertNotIn("eps_estimate_average_90_days_ago", d)

    def test_earnings_pit_excludes_reported_date_same_day(self) -> None:
        """Quarterly reportedDate on PIT day -> excluded (date-only >= comparison).
        Annual cross-ref with same reportedDate -> also excluded."""
        sample = {
            "symbol": "AAPL",
            "annualEarnings": [
                {"fiscalDateEnding": "2024-09-30", "reportedEPS": "6.08"},
            ],
            "quarterlyEarnings": [
                {"fiscalDateEnding": "2024-09-30", "reportedDate": "2024-10-31",
                 "reportedEPS": "1.64"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "av.json"
            path.write_text(json.dumps(sample), encoding="utf-8")
            # PIT = 2024-10-31 -> reportedDate "2024-10-31" >= "2024-10-31" -> excluded
            out = run_pit_fetch(
                "--source", "alphavantage", "--op", "earnings",
                "--symbol", "AAPL", "--input-file", str(path),
                "--pit", "2024-10-31T10:00:00-04:00")
        quarterly = [d for d in out["data"] if d.get("record_type") == "quarterly_earnings"]
        annual = [d for d in out["data"] if d.get("record_type") == "annual_earnings"]
        self.assertEqual(len(quarterly), 0)
        self.assertEqual(len(annual), 0)

    def test_av_missing_op(self) -> None:
        """--source alphavantage without --op -> config gap."""
        out = run_pit_fetch("--source", "alphavantage", "--symbol", "AAPL")
        self.assertEqual(out["data"], [])
        self.assertTrue(any(g["type"] == "config" and "--op" in g.get("reason", "") for g in out["gaps"]))

    def test_av_missing_symbol(self) -> None:
        """--source alphavantage --op earnings without --symbol -> config gap."""
        out = run_pit_fetch("--source", "alphavantage", "--op", "earnings")
        self.assertEqual(out["data"], [])
        self.assertTrue(any(g["type"] == "config" and "--symbol" in g.get("reason", "") for g in out["gaps"]))

    def test_estimates_pit_at_period_end_uses_final_consensus(self) -> None:
        """PIT on fiscal end date -> at_period_end bucket selected."""
        sample = {"symbol": "AAPL", "estimates": [
            {"date": "2024-06-30", "horizon": "historical fiscal quarter",
             "eps_estimate_average": "1.35",
             "eps_estimate_average_7_days_ago": "1.34",
             "eps_estimate_average_30_days_ago": "1.24"},
        ]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "av.json"
            path.write_text(json.dumps(sample), encoding="utf-8")
            # PIT exactly on fiscal end date
            out = run_pit_fetch(
                "--source", "alphavantage", "--op", "estimates",
                "--symbol", "AAPL", "--input-file", str(path),
                "--pit", "2024-06-30T10:00:00-04:00")
        resolved = [d for d in out["data"] if d["record_type"] == "estimate"]
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0]["pit_consensus_eps"], "1.35")
        self.assertEqual(resolved[0]["pit_bucket"], "at_period_end")

    def test_estimates_fiscal_year_horizon(self) -> None:
        """'historical fiscal year' horizon is also resolved in PIT mode."""
        sample = {"symbol": "AAPL", "estimates": [
            {"date": "2024-09-30", "horizon": "historical fiscal year",
             "eps_estimate_average": "6.00",
             "eps_estimate_average_7_days_ago": "5.95",
             "eps_estimate_average_30_days_ago": "5.85",
             "eps_estimate_average_60_days_ago": "5.80",
             "eps_estimate_average_90_days_ago": "5.70"},
        ]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "av.json"
            path.write_text(json.dumps(sample), encoding="utf-8")
            out = run_pit_fetch(
                "--source", "alphavantage", "--op", "estimates",
                "--symbol", "AAPL", "--input-file", str(path),
                "--pit", "2024-10-15T10:00:00-04:00")
        resolved = [d for d in out["data"] if d["record_type"] == "estimate"]
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0]["pit_bucket"], "at_period_end")
        self.assertEqual(resolved[0]["pit_consensus_eps"], "6.00")
        self.assertEqual(resolved[0]["horizon"], "historical fiscal year")

    def test_calendar_empty_csv(self) -> None:
        """Calendar CSV with only header row -> data=[], gaps has no_data."""
        csv_text = "symbol,name,reportDate,fiscalDateEnding,estimate,currency,timeOfTheDay\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cal.csv"
            path.write_text(csv_text, encoding="utf-8")
            out = run_pit_fetch(
                "--source", "alphavantage", "--op", "calendar",
                "--symbol", "AAPL", "--input-file", str(path))
        cal = [d for d in out["data"] if d.get("record_type") == "earnings_calendar"]
        self.assertEqual(len(cal), 0)
        self.assertTrue(any(g["type"] == "no_data" for g in out["gaps"]))

    def test_calendar_pit_mode_always_gapped(self) -> None:
        """Calendar in PIT mode -> gapped with forward-looking snapshot reason."""
        csv_text = "symbol,name,reportDate,fiscalDateEnding,estimate,currency,timeOfTheDay\nAAPL,APPLE INC,2025-07-31,2025-06-30,1.72,USD,post-market\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cal.csv"
            path.write_text(csv_text, encoding="utf-8")
            out = run_pit_fetch(
                "--source", "alphavantage", "--op", "calendar",
                "--symbol", "AAPL", "--input-file", str(path),
                "--pit", "2025-06-01T10:00:00-04:00")
        self.assertEqual(len([d for d in out["data"] if d.get("record_type") == "earnings_calendar"]), 0)
        self.assertTrue(any("forward-looking snapshot" in g.get("reason", "") for g in out["gaps"]))


# ============================================================================
# Cross-source / structural tests
# ============================================================================

class CrossSourceStressTests(unittest.TestCase):
    """Tests that verify structural invariants across all sources."""

    def test_output_always_has_data_and_gaps(self) -> None:
        """Every source always returns {data: [], gaps: []} structure."""
        cases = [
            ("bz-news-api", ["--input-file", "__PLACEHOLDER__"]),
            ("perplexity", ["--op", "search", "--query", "test", "--input-file", "__PLACEHOLDER__"]),
            ("alphavantage", ["--op", "earnings", "--symbol", "AAPL", "--input-file", "__PLACEHOLDER__"]),
        ]
        for source, extra_args in cases:
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "data.json"
                if source == "bz-news-api":
                    path.write_text("[]", encoding="utf-8")
                elif source == "perplexity":
                    path.write_text("[]", encoding="utf-8")
                else:
                    path.write_text(json.dumps({"symbol": "AAPL", "annualEarnings": [], "quarterlyEarnings": []}),
                                    encoding="utf-8")
                args = [a.replace("__PLACEHOLDER__", str(path)) for a in extra_args]
                out = run_pit_fetch("--source", source, *args)
            self.assertIn("data", out, f"Missing 'data' for source={source}")
            self.assertIn("gaps", out, f"Missing 'gaps' for source={source}")
            self.assertIsInstance(out["data"], list, f"'data' not list for source={source}")
            self.assertIsInstance(out["gaps"], list, f"'gaps' not list for source={source}")

    def test_no_data_gap_on_empty_results(self) -> None:
        """All sources add a 'no_data' gap when data is empty."""
        cases = [
            ("bz-news-api", ["--input-file", "__PLACEHOLDER__"], "[]"),
            ("perplexity", ["--op", "search", "--query", "test", "--input-file", "__PLACEHOLDER__"], "[]"),
            ("alphavantage", ["--op", "earnings", "--symbol", "AAPL", "--input-file", "__PLACEHOLDER__"],
             json.dumps({"symbol": "AAPL", "annualEarnings": [], "quarterlyEarnings": []})),
        ]
        for source, extra_args, content in cases:
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "data.json"
                path.write_text(content, encoding="utf-8")
                args = [a.replace("__PLACEHOLDER__", str(path)) for a in extra_args]
                out = run_pit_fetch("--source", source, *args)
            self.assertTrue(
                any(g["type"] == "no_data" for g in out["gaps"]),
                f"Missing 'no_data' gap for source={source}")


if __name__ == "__main__":
    unittest.main()
