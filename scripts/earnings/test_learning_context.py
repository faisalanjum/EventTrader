#!/usr/bin/env python3
"""Writer / Reader / Integration tests for learning-context machinery.

Covers W1–W8, R1–R15, I7–I10 per .claude/plans/learner-edits.md §7.2–§7.4.

I1–I6 require a real SDK round-trip and are covered by the post-commit smoke
test in §8.3 STEP 1. These tests are self-contained and do NOT require Neo4j.
"""
from __future__ import annotations

import io
import json
import logging
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "earnings"))

import earnings_orchestrator as orch


# ── Shared fixtures ──────────────────────────────────────────────────


def _tmp_learnings():
    """Return a fresh tempdir + patch orchestrator.LEARNINGS_DIR to point at it."""
    tmp = Path(tempfile.mkdtemp(prefix="learner_edits_test_"))
    orig = orch.LEARNINGS_DIR
    orch.LEARNINGS_DIR = tmp
    # Clear the anti-poisoning sector cache so mocks take effect.
    orch._SECTOR_CACHE.clear()
    return tmp, orig


def _restore(orig):
    orch.LEARNINGS_DIR = orig
    orch._SECTOR_CACHE.clear()


def _attribution(
    ticker="AVGO",
    quarter="Q1_FY2023",
    globals_=None,
    attributed_at="2026-04-17T12:00:00Z",
):
    """Minimal attribution-result shape sufficient for append_* tests."""
    return {
        "ticker": ticker,
        "quarter_label": quarter,
        "attributed_at": attributed_at,
        "global_observations": globals_ if globals_ is not None else [],
        "feedback": {
            "prediction_comparison": {},
            "what_worked": [],
            "what_failed": [],
            "predictor_lessons": [],
            "data_lessons": [],
            "why": "demo",
        },
        "primary_driver": {"summary": "demo", "category": "demo"},
        "actual_return": {"daily_stock_pct": 1.0},
    }


# ── W-suite: writer behavior ─────────────────────────────────────────


class WriterTests(unittest.TestCase):

    def setUp(self):
        self.tmp, self._orig = _tmp_learnings()

    def tearDown(self):
        _restore(self._orig)
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _patch_sector(self, mapping):
        """Patch _lookup_company_sector to return values from a dict."""
        return mock.patch.object(
            orch, "_lookup_company_sector",
            side_effect=lambda t: mapping.get((t or "").upper()),
        )

    # W1: source_sector stamped on every entry when lookup succeeds
    def test_W1_source_sector_stamped(self):
        with self._patch_sector({"AVGO": "Technology"}):
            path = orch.append_global_lessons(_attribution(globals_=[
                {"scope": "macro", "lesson": "m1"},
            ]))
        data = json.loads(path.read_text())
        self.assertEqual(len(data["entries"]), 1)
        self.assertEqual(data["entries"][0]["source_sector"], "Technology")

    # W2: None lookup → None stamped
    def test_W2_source_sector_none(self):
        with self._patch_sector({}):
            path = orch.append_global_lessons(_attribution(
                ticker="ZZZZZ",
                globals_=[{"scope": "macro", "lesson": "m1"}],
            ))
        data = json.loads(path.read_text())
        self.assertIsNone(data["entries"][0]["source_sector"])

    # W3: related_tickers and target_sector pass through untouched
    def test_W3_routing_fields_passthrough(self):
        with self._patch_sector({"AVGO": "Technology"}):
            path = orch.append_global_lessons(_attribution(globals_=[
                {"scope": "cross_ticker", "related_tickers": ["NVDA", "AMD"], "lesson": "c"},
                {"scope": "sector", "target_sector": "Technology", "lesson": "s"},
            ]))
        entries = json.loads(path.read_text())["entries"]
        self.assertEqual(entries[0]["related_tickers"], ["NVDA", "AMD"])
        self.assertEqual(entries[1]["target_sector"], "Technology")

    # W4: concurrent writes with fcntl.flock don't corrupt
    def test_W4_concurrent_writes_no_corruption(self):
        with self._patch_sector({"AVGO": "Technology", "BURL": "ConsumerCyclical"}):
            def write(ticker, quarter, n):
                for i in range(n):
                    orch.append_global_lessons(_attribution(
                        ticker=ticker, quarter=quarter,
                        attributed_at=f"2026-04-17T12:00:{i:02d}Z",
                        globals_=[{"scope": "macro", "lesson": f"{ticker}-{i}"}],
                    ))
            t1 = threading.Thread(target=write, args=("AVGO", "Q1", 10))
            t2 = threading.Thread(target=write, args=("BURL", "Q1", 10))
            t1.start(); t2.start(); t1.join(); t2.join()
        data = json.loads((self.tmp / "global.json").read_text())
        sources = {(e["source_ticker"], e["quarter_label"]) for e in data["entries"]}
        self.assertEqual(sources, {("AVGO", "Q1"), ("BURL", "Q1")})

    # W5: atomic write crash mid-write → file unchanged
    def test_W5_atomic_write_crash(self):
        with self._patch_sector({"AVGO": "Technology"}):
            orch.append_global_lessons(_attribution(globals_=[
                {"scope": "macro", "lesson": "before-crash"},
            ]))
        pre_crash_text = (self.tmp / "global.json").read_text()

        with self._patch_sector({"AVGO": "Technology"}):
            with mock.patch.object(orch, "_atomic_write_json",
                                   side_effect=RuntimeError("simulated crash")):
                with self.assertRaises(RuntimeError):
                    orch.append_global_lessons(_attribution(
                        attributed_at="2026-04-17T13:00:00Z",
                        globals_=[{"scope": "macro", "lesson": "after-crash"}],
                    ))
        self.assertEqual((self.tmp / "global.json").read_text(), pre_crash_text)

    # W6: global.json upsert by (source_ticker, quarter_label)
    def test_W6_global_upsert(self):
        with self._patch_sector({"AVGO": "Technology"}):
            orch.append_global_lessons(_attribution(
                attributed_at="2026-04-17T12:00:00Z",
                globals_=[{"scope": "macro", "lesson": "v1"}],
            ))
            orch.append_global_lessons(_attribution(
                attributed_at="2026-04-17T13:00:00Z",
                globals_=[{"scope": "macro", "lesson": "v2"}],
            ))
        entries = json.loads((self.tmp / "global.json").read_text())["entries"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["lesson"], "v2")

    # W7: ticker.json upsert by quarter_label
    def test_W7_ticker_upsert(self):
        attr = _attribution()
        attr["feedback"]["why"] = "first"
        orch.append_ticker_lesson("AVGO", attr)
        attr["feedback"]["why"] = "second"
        orch.append_ticker_lesson("AVGO", attr)
        data = json.loads((self.tmp / "ticker" / "AVGO.json").read_text())
        self.assertEqual(len(data["lessons"]), 1)
        self.assertEqual(data["lessons"][0]["why"], "second")

    # W8: scope_key (if present in input) is NOT passed through to storage
    def test_W8_scope_key_dropped_by_writer(self):
        with self._patch_sector({"AVGO": "Technology"}):
            path = orch.append_global_lessons(_attribution(globals_=[
                {"scope": "macro", "scope_key": "leftover", "lesson": "m"},
            ]))
        entries = json.loads(path.read_text())["entries"]
        self.assertNotIn("scope_key", entries[0])

    # W9: sector-scope entry stored WITHOUT null-padded related_tickers key.
    # Amendment 2026-04-17 follow-up: writer mirrors source-observation
    # key-presence rather than always stamping. Keeps stored shape clean and
    # honors the schema contract ("MUST NOT be present" on off-scope) in
    # storage as well as in-transit.
    def test_W9_sector_entry_omits_related_tickers(self):
        with self._patch_sector({"AVGO": "Technology"}):
            path = orch.append_global_lessons(_attribution(globals_=[
                {"scope": "sector", "target_sector": "Technology", "lesson": "s"},
            ]))
        entry = json.loads(path.read_text())["entries"][0]
        self.assertNotIn("related_tickers", entry,
                         "sector entry must NOT carry a null-padded related_tickers key")
        self.assertEqual(entry["target_sector"], "Technology")

    # W10: macro-scope entry stored WITHOUT either routing field.
    def test_W10_macro_entry_omits_both_routing_fields(self):
        with self._patch_sector({"AVGO": "Technology"}):
            path = orch.append_global_lessons(_attribution(globals_=[
                {"scope": "macro", "lesson": "m"},
            ]))
        entry = json.loads(path.read_text())["entries"][0]
        self.assertNotIn("related_tickers", entry,
                         "macro entry must NOT carry a null-padded related_tickers key")
        self.assertNotIn("target_sector", entry,
                         "macro entry must NOT carry a null-padded target_sector key")

    # W11: cross_ticker-scope entry stored with related_tickers but WITHOUT
    # a null-padded target_sector key.
    def test_W11_cross_ticker_entry_omits_target_sector(self):
        with self._patch_sector({"AVGO": "Technology"}):
            path = orch.append_global_lessons(_attribution(globals_=[
                {"scope": "cross_ticker", "related_tickers": ["ROST"], "lesson": "c"},
            ]))
        entry = json.loads(path.read_text())["entries"][0]
        self.assertEqual(entry["related_tickers"], ["ROST"])
        self.assertNotIn("target_sector", entry,
                         "cross_ticker entry must NOT carry a null-padded target_sector key")

    # Extra: upsert runs even with empty observations (purge stale entries)
    def test_empty_observations_still_purges(self):
        with self._patch_sector({"AVGO": "Technology"}):
            orch.append_global_lessons(_attribution(globals_=[
                {"scope": "macro", "lesson": "stale"},
            ]))
            path = orch.append_global_lessons(_attribution(
                attributed_at="2026-04-17T13:00:00Z", globals_=[],
            ))
        self.assertIsNotNone(path)  # contract: always returns path
        entries = json.loads((self.tmp / "global.json").read_text())["entries"]
        self.assertEqual(entries, [])


# ── R-suite: reader behavior ─────────────────────────────────────────


class ReaderTests(unittest.TestCase):

    def setUp(self):
        self.tmp, self._orig = _tmp_learnings()

    def tearDown(self):
        _restore(self._orig)
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_global(self, entries):
        (self.tmp / "global.json").write_text(json.dumps({
            "schema_version": "global_lessons.v1",
            "updated_at": "2026-04-17T00:00:00Z",
            "entries": entries,
        }))

    def _log_capture(self):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.INFO)
        logger = orch.log
        logger.addHandler(handler)
        prior_level = logger.level
        logger.setLevel(logging.INFO)
        return handler, stream, logger, prior_level

    def _log_uninstall(self, handler, logger, prior_level):
        logger.removeHandler(handler)
        logger.setLevel(prior_level)

    # R1: empty global.json entries list
    def test_R1_empty_entries(self):
        self._write_global([])
        ctx = orch.build_learning_context("AAPL", sector="Technology", base_dir=self.tmp)
        self.assertEqual(ctx["global_lessons"], [])
        self.assertEqual(ctx["ticker_lessons"], [])

    # R2: file absent — both empty, log still fires
    def test_R2_file_absent(self):
        h, stream, logger, prior = self._log_capture()
        try:
            ctx = orch.build_learning_context("AAPL", sector="Technology", base_dir=self.tmp)
        finally:
            self._log_uninstall(h, logger, prior)
        self.assertEqual(ctx["global_lessons"], [])
        self.assertIn("included[sector=0 macro=0 cross=0]", stream.getvalue())

    # R3: sector match
    def test_R3_sector_match(self):
        self._write_global([
            {"scope": "sector", "target_sector": "Technology",
             "source_ticker": "AVGO", "quarter_label": "Q1",
             "attributed_at": "2025-01-01", "lesson": "tech-match"},
        ])
        ctx = orch.build_learning_context("AAPL", sector="Technology", base_dir=self.tmp)
        self.assertEqual([e["lesson"] for e in ctx["global_lessons"]], ["tech-match"])

    # R4: sector mismatch
    def test_R4_sector_mismatch(self):
        self._write_global([
            {"scope": "sector", "target_sector": "Healthcare",
             "source_ticker": "X", "quarter_label": "Q1",
             "attributed_at": "2025-01-01", "lesson": "hc"},
        ])
        h, stream, logger, prior = self._log_capture()
        try:
            ctx = orch.build_learning_context("AAPL", sector="Technology", base_dir=self.tmp)
        finally:
            self._log_uninstall(h, logger, prior)
        self.assertEqual(ctx["global_lessons"], [])
        self.assertIn("sector_mismatch=1", stream.getvalue())

    # R5: normalized sector compare
    def test_R5_sector_normalized(self):
        self._write_global([
            {"scope": "sector", "target_sector": "technology",
             "source_ticker": "Y", "quarter_label": "Q1",
             "attributed_at": "2025-01-01", "lesson": "norm"},
        ])
        ctx = orch.build_learning_context("AAPL", sector="Technology", base_dir=self.tmp)
        self.assertEqual([e["lesson"] for e in ctx["global_lessons"]], ["norm"])

    # R6: sector missing target_sector → legacy_schema
    def test_R6_sector_legacy(self):
        self._write_global([
            {"scope": "sector", "source_ticker": "Z", "quarter_label": "Q1",
             "attributed_at": "2025-01-01", "lesson": "legacy"},
        ])
        h, stream, logger, prior = self._log_capture()
        try:
            ctx = orch.build_learning_context("AAPL", sector="Technology", base_dir=self.tmp)
        finally:
            self._log_uninstall(h, logger, prior)
        self.assertEqual(ctx["global_lessons"], [])
        self.assertIn("legacy_schema=1", stream.getvalue())

    # R7: macro always included
    def test_R7_macro_included(self):
        self._write_global([
            {"scope": "macro", "source_ticker": "SPY", "quarter_label": "Q1",
             "attributed_at": "2025-01-01", "lesson": "macro-lesson"},
        ])
        ctx = orch.build_learning_context("AAPL", sector="Technology", base_dir=self.tmp)
        self.assertEqual([e["lesson"] for e in ctx["global_lessons"]], ["macro-lesson"])

    # R8: cross_ticker hit
    def test_R8_cross_ticker_hit(self):
        self._write_global([
            {"scope": "cross_ticker", "related_tickers": ["AAPL"],
             "source_ticker": "AVGO", "quarter_label": "Q1",
             "attributed_at": "2025-01-01", "lesson": "cross-hit"},
        ])
        ctx = orch.build_learning_context("AAPL", sector="Technology", base_dir=self.tmp)
        self.assertEqual([e["lesson"] for e in ctx["global_lessons"]], ["cross-hit"])

    # R9: cross_ticker miss
    def test_R9_cross_ticker_miss(self):
        self._write_global([
            {"scope": "cross_ticker", "related_tickers": ["MSFT"],
             "source_ticker": "BURL", "quarter_label": "Q1",
             "attributed_at": "2025-01-01", "lesson": "cross-miss"},
        ])
        h, stream, logger, prior = self._log_capture()
        try:
            ctx = orch.build_learning_context("AAPL", sector="Technology", base_dir=self.tmp)
        finally:
            self._log_uninstall(h, logger, prior)
        self.assertEqual(ctx["global_lessons"], [])
        self.assertIn("cross_ticker_not_listed=1", stream.getvalue())

    # R10: cross_ticker missing related_tickers
    def test_R10_cross_ticker_missing_related(self):
        self._write_global([
            {"scope": "cross_ticker", "source_ticker": "BURL", "quarter_label": "Q1",
             "attributed_at": "2025-01-01", "lesson": "cross-legacy"},
        ])
        h, stream, logger, prior = self._log_capture()
        try:
            ctx = orch.build_learning_context("AAPL", sector="Technology", base_dir=self.tmp)
        finally:
            self._log_uninstall(h, logger, prior)
        self.assertEqual(ctx["global_lessons"], [])
        self.assertIn("cross_ticker_missing_related=1", stream.getvalue())

    # R11: 10 sector-matching → cap at 4, newest-first
    def test_R11_sector_cap_4(self):
        entries = []
        for i in range(10):
            entries.append({
                "scope": "sector", "target_sector": "Technology",
                "source_ticker": f"T{i}", "quarter_label": f"Q{i}",
                "attributed_at": f"2025-01-{i+1:02d}", "lesson": f"s{i}",
            })
        self._write_global(entries)
        ctx = orch.build_learning_context("AAPL", sector="Technology", base_dir=self.tmp)
        sector_lessons = [e["lesson"] for e in ctx["global_lessons"] if e["scope"] == "sector"]
        self.assertEqual(len(sector_lessons), 4)
        # Newest-first: "2025-01-10" (s9) is the newest by attributed_at.
        self.assertEqual(sector_lessons[0], "s9")

    # R12: 10 cross_ticker hits → cap at 2
    def test_R12_cross_cap_2(self):
        entries = []
        for i in range(10):
            entries.append({
                "scope": "cross_ticker", "related_tickers": ["AAPL"],
                "source_ticker": f"T{i}", "quarter_label": f"Q{i}",
                "attributed_at": f"2025-01-{i+1:02d}", "lesson": f"c{i}",
            })
        self._write_global(entries)
        ctx = orch.build_learning_context("AAPL", sector="Technology", base_dir=self.tmp)
        cross = [e for e in ctx["global_lessons"] if e["scope"] == "cross_ticker"]
        self.assertEqual(len(cross), 2)

    # R13: dedupe by lesson text
    def test_R13_dedupe_lesson_text(self):
        self._write_global([
            {"scope": "macro", "source_ticker": "SPY", "quarter_label": "Q1",
             "attributed_at": "2025-01-01", "lesson": "same text"},
            {"scope": "macro", "source_ticker": "QQQ", "quarter_label": "Q2",
             "attributed_at": "2025-01-02", "lesson": "same text"},
        ])
        ctx = orch.build_learning_context("AAPL", sector="Technology", base_dir=self.tmp)
        macros = [e for e in ctx["global_lessons"] if e["scope"] == "macro"]
        self.assertEqual(len(macros), 1)

    # R14: unknown scope
    def test_R14_unknown_scope(self):
        self._write_global([
            {"scope": "foo", "source_ticker": "X", "quarter_label": "Q1",
             "attributed_at": "2025-01-01", "lesson": "weird"},
        ])
        h, stream, logger, prior = self._log_capture()
        try:
            ctx = orch.build_learning_context("AAPL", sector="Technology", base_dir=self.tmp)
        finally:
            self._log_uninstall(h, logger, prior)
        self.assertEqual(ctx["global_lessons"], [])
        self.assertIn("unknown_scope=1", stream.getvalue())

    # R16 (regression, amendment 2026-04-17): lowercase caller ticker must
    # match uppercase stored related_tickers. Prior bug silently dropped
    # valid cross_ticker lessons when the CLI/caller passed a lowercase ticker.
    def test_R16_lowercase_caller_ticker_matches(self):
        self._write_global([
            {"scope": "cross_ticker", "related_tickers": ["AAPL"],
             "source_ticker": "AVGO", "quarter_label": "Q1",
             "attributed_at": "2025-01-01", "lesson": "case-insensitive-hit"},
        ])
        ctx = orch.build_learning_context("aapl", sector="Technology", base_dir=self.tmp)
        self.assertEqual(
            [e["lesson"] for e in ctx["global_lessons"]],
            ["case-insensitive-hit"],
        )

    # R15: log shape always complete — 6 counter names + 3 included counts
    def test_R15_log_shape_complete(self):
        self._write_global([])
        h, stream, logger, prior = self._log_capture()
        try:
            orch.build_learning_context("AAPL", sector="Technology", base_dir=self.tmp)
        finally:
            self._log_uninstall(h, logger, prior)
        log_text = stream.getvalue()
        # No regex — substring assertion per plan §7.3.
        for counter in [
            "sector_mismatch", "current_sector_unknown", "cross_ticker_not_listed",
            "cross_ticker_missing_related", "unknown_scope", "legacy_schema",
        ]:
            self.assertIn(counter, log_text, f"missing counter key in log: {counter}")
        for inclusion in ["included[sector=", "macro=", "cross="]:
            self.assertIn(inclusion, log_text)


# ── I-suite: integration (mocked SDK) ────────────────────────────────


class IntegrationTests(unittest.TestCase):

    def setUp(self):
        self.tmp, self._orig = _tmp_learnings()

    def tearDown(self):
        _restore(self._orig)
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    # I7: corrupted global.json → log.error, bundle builds with empty lessons
    def test_I7_corrupted_global_json(self):
        (self.tmp / "global.json").write_text("{this is not json")
        with self.assertLogs(orch.log, level="ERROR") as cap:
            ctx = orch.build_learning_context("AAPL", sector="Technology", base_dir=self.tmp)
        self.assertEqual(ctx["global_lessons"], [])
        self.assertTrue(any("malformed" in m for m in cap.output))

    # I8: OSError on read → log.error, same defensive behavior
    def test_I8_oserror_on_read(self):
        (self.tmp / "global.json").write_text("{}")
        real_read_text = Path.read_text

        def failing_read_text(self, *a, **kw):
            if str(self).endswith("global.json"):
                raise OSError("simulated permission denied")
            return real_read_text(self, *a, **kw)

        with mock.patch.object(Path, "read_text", new=failing_read_text):
            with self.assertLogs(orch.log, level="ERROR") as cap:
                ctx = orch.build_learning_context("AAPL", sector="Technology", base_dir=self.tmp)
        self.assertEqual(ctx["global_lessons"], [])
        self.assertTrue(any("read failed" in m for m in cap.output))

    # I9: re-running a quarter produces no duplicates
    def test_I9_rerun_no_duplicates(self):
        with mock.patch.object(orch, "_lookup_company_sector",
                               side_effect=lambda t: "Technology"):
            for _ in range(3):
                orch.append_global_lessons(_attribution(
                    globals_=[{"scope": "macro", "lesson": "same-run"}],
                ))
                orch.append_ticker_lesson("AVGO", _attribution())
        global_entries = json.loads((self.tmp / "global.json").read_text())["entries"]
        ticker_entries = json.loads(
            (self.tmp / "ticker" / "AVGO.json").read_text()
        )["lessons"]
        self.assertEqual(len(global_entries), 1)
        self.assertEqual(len(ticker_entries), 1)

    # I10: H2 acceptance gate — informed retry produces corrective prompt
    def test_I10_informed_retry_prompt(self):
        # Attempt 1: no prior errors fed in → plain prompt
        first = orch._build_learner_prompt(
            skill_content="SKILL",
            ticker="AVGO",
            quarter_info={"quarter_label": "Q1", "filed_8k": "", "accession_8k": ""},
            actual_return={"daily_stock_pct": 1.0},
            pit_mode="historical",
            pit_cutoff="2025-01-01",
            pit_boundary_source="next_quarter",
            result_path=Path("/tmp/r"),
            prediction_result_path=Path("/tmp/p"),
            context_bundle_path=Path("/tmp/b"),
            prior_lessons_path=Path("/tmp/L"),
        )
        self.assertNotIn("YOUR PRIOR OUTPUT WAS REJECTED", first)

        # Attempt 2: validation errors from attempt 1 fed back
        errs = [
            "global_observations[0].related_tickers must be a non-empty list for cross_ticker scope",
            "global_observations[1].target_sector must be one of [...] (got 'semiconductors')",
        ]
        retry = orch._build_learner_prompt(
            skill_content="SKILL",
            ticker="AVGO",
            quarter_info={"quarter_label": "Q1", "filed_8k": "", "accession_8k": ""},
            actual_return={"daily_stock_pct": 1.0},
            pit_mode="historical",
            pit_cutoff="2025-01-01",
            pit_boundary_source="next_quarter",
            result_path=Path("/tmp/r"),
            prediction_result_path=Path("/tmp/p"),
            context_bundle_path=Path("/tmp/b"),
            prior_lessons_path=Path("/tmp/L"),
            prior_validation_errors=errs,
        )
        self.assertIn("YOUR PRIOR OUTPUT WAS REJECTED", retry)
        self.assertIn("related_tickers must be a non-empty list", retry)
        self.assertIn("target_sector must be one of", retry)
        self.assertIn("Fix these EXACT errors", retry)
        # Numbered listing:
        self.assertIn("1.", retry)
        self.assertIn("2.", retry)


if __name__ == "__main__":
    unittest.main(verbosity=2)
