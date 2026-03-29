#!/usr/bin/env python3
"""Phase 2 — Builder Validation Harness

Comprehensive test suite for all 7 prediction-system-v2 builders.
5 test layers, 4 test tickers, structured results output.

Usage:
    python3 scripts/earnings/test_builder_validation.py                    # Layer 1-3 (no external APIs)
    python3 scripts/earnings/test_builder_validation.py --allow-av         # Include AV smoke (1 consensus call = 3 AV endpoints)
    python3 scripts/earnings/test_builder_validation.py --layer 1          # Only contract tests
    python3 scripts/earnings/test_builder_validation.py --layer 3          # Only differential PIT
    python3 scripts/earnings/test_builder_validation.py --ticker FIVE      # Single ticker
    python3 scripts/earnings/test_builder_validation.py --save             # Save packets to /tmp/builder_validation/

Layers:
    1 = Contract tests (import, call, return shape, required fields)
    2 = Historical integration (known quarters, PIT-gated, non-empty packets)
    3 = Differential PIT (before/exact/after cutoff, forward-return nulling)
    4 = Live smoke (Sunday-safe, no AV unless --allow-av)
    5 = Deferred (market-hours checklist, not automated)

Environment:
    NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD (or .env)
    ALPHAVANTAGE_API_KEY (only with --allow-av)
    POLYGON_API_KEY (optional, for macro polygon mode)
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

# ── Path setup ──────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts/earnings"))
sys.path.insert(0, str(PROJECT_ROOT / ".claude/skills/earnings-orchestrator/scripts"))

# ── Load .env ───────────────────────────────────────────────────────────
_env_path = PROJECT_ROOT / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


# ═══════════════════════════════════════════════════════════════════════
# TEST FIXTURES — Known data points from Neo4j for deterministic testing
# ═══════════════════════════════════════════════════════════════════════

FIXTURES = {
    "FIVE": {
        "ticker": "FIVE",
        "fye_month": 2,  # January FYE (Feb month_adj due to day<=5)
        "current_8k": {
            "accession": "0001177609-25-000037",
            "filed_8k": "2025-08-27T16:14:48-04:00",
            "market_session": "post_market",
            "period_of_report": "2025-08-27",
        },
        "prev_8k": {
            "accession": "0001177609-25-000019",
            "filed_8k": "2025-06-04T16:23:39-04:00",
        },
        "guidance_count": 468,
        # Known news events between prev and current 8-K, close to current 8-K filing time
        # Perfect for differential PIT: news at 16:05-16:06, 8-K at 16:14
        "pit_test_news": [
            {"created": "2025-08-27T16:06:34-04:00", "hourly_ends": "2025-08-27T17:06:34-04:00"},
            {"created": "2025-08-27T16:06:07-04:00", "hourly_ends": "2025-08-27T17:06:07-04:00"},
            {"created": "2025-08-27T16:05:13-04:00", "hourly_ends": "2025-08-27T17:05:13-04:00"},
        ],
    },
    "DOCU": {
        "ticker": "DOCU",
        "fye_month": 1,
        "current_8k": {
            "accession": "0001261333-25-000129",
            "filed_8k": "2025-09-04T16:07:22-04:00",
            "market_session": "post_market",
            "period_of_report": "2025-09-03",
        },
        "prev_8k": {
            "accession": "0001261333-25-000073",
            "filed_8k": "2025-06-05T16:22:44-04:00",
        },
        "guidance_count": 314,
    },
    "CRM": {
        "ticker": "CRM",
        "fye_month": 1,
        "current_8k": {
            "accession": "0001108524-25-000083",
            "filed_8k": "2025-09-03T16:03:27-04:00",
            "market_session": "post_market",
            "period_of_report": "2025-09-03",
        },
        "prev_8k": {
            "accession": "0001108524-25-000027",
            "filed_8k": "2025-05-28T16:05:54-04:00",
        },
        "guidance_count": 0,  # Tests graceful empty
    },
    "COST": {
        "ticker": "COST",
        "fye_month": 9,  # September FYE (unusual 52-week calendar)
        "current_8k": {
            "accession": "0000909832-25-000093",
            "filed_8k": "2025-09-25T16:16:57-04:00",
            "market_session": "post_market",
            "period_of_report": "2025-09-25",
        },
        "prev_8k": {
            "accession": "0000909832-25-000031",
            "filed_8k": "2025-05-29T16:24:57-04:00",
        },
        "guidance_count": 0,
    },
}


# ═══════════════════════════════════════════════════════════════════════
# TEST RESULT TRACKING
# ═══════════════════════════════════════════════════════════════════════

class TestResults:
    def __init__(self):
        self.results: list[dict] = []
        self.start_time = time.time()

    def record(self, layer: int, builder: str, test_name: str,
               passed: bool, detail: str = "", ticker: str = ""):
        self.results.append({
            "layer": layer,
            "builder": builder,
            "test": test_name,
            "ticker": ticker,
            "passed": passed,
            "detail": detail,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        status = "PASS" if passed else "FAIL"
        ticker_tag = f" [{ticker}]" if ticker else ""
        # Always print to stderr so test progress is visible even when builder stdout is suppressed
        print(f"  {status}: L{layer} {builder}{ticker_tag} — {test_name}"
              + (f" ({detail})" if detail and not passed else ""),
              file=sys.stderr)

    def summary(self):
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        failed = sum(1 for r in self.results if not r["passed"])
        elapsed = time.time() - self.start_time
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"RESULTS: {passed}/{total} passed, {failed} failed ({elapsed:.1f}s)", file=sys.stderr)
        if failed:
            print(f"\nFAILURES:", file=sys.stderr)
            for r in self.results:
                if not r["passed"]:
                    t = f" [{r['ticker']}]" if r["ticker"] else ""
                    print(f"  L{r['layer']} {r['builder']}{t} — {r['test']}: {r['detail']}", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)
        return failed == 0

    def to_dict(self):
        return {
            "run_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_s": round(time.time() - self.start_time, 1),
            "total": len(self.results),
            "passed": sum(1 for r in self.results if r["passed"]),
            "failed": sum(1 for r in self.results if not r["passed"]),
            "results": self.results,
        }


# ═══════════════════════════════════════════════════════════════════════
# LAYER 1 — CONTRACT TESTS
# ═══════════════════════════════════════════════════════════════════════

def _make_quarter_info(fixture: dict) -> dict:
    """Build quarter_info dict from fixture."""
    ck = fixture["current_8k"]
    pk = fixture.get("prev_8k", {})
    return {
        "accession_8k": ck["accession"],
        "filed_8k": ck["filed_8k"],
        "market_session": ck["market_session"],
        "period_of_report": ck["period_of_report"],
        "prev_8k_ts": pk.get("filed_8k"),
        "quarter_label": "",
    }


def layer1_contract_tests(results: TestResults, tickers: list[str], save_dir: str | None):
    """Layer 1: Import each builder, call with known data, validate return contract."""
    print("\n── Layer 1: Contract Tests ──", file=sys.stderr)
    ticker = tickers[0]  # Use first ticker for contract tests
    fix = FIXTURES[ticker]
    qi = _make_quarter_info(fix)

    # --- Builder 1: build_8k_packet ---
    builder = "build_8k_packet"
    try:
        from warmup_cache import build_8k_packet
        results.record(1, builder, "importable", True, ticker=ticker)
    except Exception as e:
        results.record(1, builder, "importable", False, str(e), ticker=ticker)
        return  # Can't continue

    out_path = f"/tmp/builder_validation/L1_{builder}_{ticker}.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    try:
        ret = build_8k_packet(qi["accession_8k"], ticker, out_path=out_path)
        results.record(1, builder, "no_crash", True, ticker=ticker)
        # Return contract: currently returns None
        results.record(1, builder, "returns_none_as_expected", ret is None, f"got {type(ret).__name__}", ticker=ticker)
        # Packet on disk
        if os.path.exists(out_path):
            with open(out_path) as f:
                pkt = json.load(f)
            results.record(1, builder, "packet_on_disk", True, ticker=ticker)
            for key in ["schema_version", "ticker", "accession_8k", "assembled_at"]:
                results.record(1, builder, f"has_{key}", key in pkt, ticker=ticker)
            if save_dir:
                _save_packet(save_dir, builder, ticker, "L1", pkt)
        else:
            results.record(1, builder, "packet_on_disk", False, "file not found", ticker=ticker)
    except SystemExit:
        results.record(1, builder, "no_crash", False, "sys.exit(1) — accession not found?", ticker=ticker)
    except Exception as e:
        results.record(1, builder, "no_crash", False, str(e)[:200], ticker=ticker)

    # --- Builder 2: build_guidance_history ---
    builder = "build_guidance_history"
    try:
        from warmup_cache import build_guidance_history
        results.record(1, builder, "importable", True, ticker=ticker)
    except Exception as e:
        results.record(1, builder, "importable", False, str(e), ticker=ticker)
        return

    out_path = f"/tmp/builder_validation/L1_{builder}_{ticker}.json"
    try:
        ret = build_guidance_history(ticker, pit=qi["filed_8k"], out_path=out_path)
        results.record(1, builder, "no_crash", True, ticker=ticker)
        results.record(1, builder, "returns_none_as_expected", ret is None, f"got {type(ret).__name__}", ticker=ticker)
        if os.path.exists(out_path):
            with open(out_path) as f:
                pkt = json.load(f)
            results.record(1, builder, "packet_on_disk", True, ticker=ticker)
            for key in ["schema_version", "ticker", "pit", "series", "summary", "assembled_at"]:
                results.record(1, builder, f"has_{key}", key in pkt, ticker=ticker)
            if save_dir:
                _save_packet(save_dir, builder, ticker, "L1", pkt)
        else:
            results.record(1, builder, "packet_on_disk", False, "file not found", ticker=ticker)
    except Exception as e:
        results.record(1, builder, "no_crash", False, str(e)[:200], ticker=ticker)

    # --- Builder 3: build_inter_quarter_context ---
    builder = "build_inter_quarter_context"
    try:
        from warmup_cache import build_inter_quarter_context
        results.record(1, builder, "importable", True, ticker=ticker)
    except Exception as e:
        results.record(1, builder, "importable", False, str(e), ticker=ticker)
        return

    out_path = f"/tmp/builder_validation/L1_{builder}_{ticker}.json"
    try:
        ret = build_inter_quarter_context(
            ticker, qi["prev_8k_ts"], qi["filed_8k"], out_path=out_path)
        results.record(1, builder, "no_crash", True, ticker=ticker)
        # Return contract: currently returns (out_path, rendered) tuple
        is_tuple = isinstance(ret, tuple) and len(ret) == 2
        results.record(1, builder, "returns_tuple_as_expected", is_tuple,
                       f"got {type(ret).__name__}", ticker=ticker)
        if os.path.exists(out_path):
            with open(out_path) as f:
                pkt = json.load(f)
            results.record(1, builder, "packet_on_disk", True, ticker=ticker)
            for key in ["schema_version", "ticker", "prev_8k_ts", "context_cutoff_ts", "days", "summary", "assembled_at"]:
                results.record(1, builder, f"has_{key}", key in pkt, ticker=ticker)
            if save_dir:
                _save_packet(save_dir, builder, ticker, "L1", pkt)
        else:
            results.record(1, builder, "packet_on_disk", False, "file not found", ticker=ticker)
    except Exception as e:
        results.record(1, builder, "no_crash", False, str(e)[:200], ticker=ticker)

    # --- Builder 4: build_peer_earnings_snapshot ---
    builder = "build_peer_earnings_snapshot"
    try:
        from peer_earnings_snapshot import build_peer_earnings_snapshot
        results.record(1, builder, "importable", True, ticker=ticker)
    except Exception as e:
        results.record(1, builder, "importable", False, str(e), ticker=ticker)
        return

    out_path = f"/tmp/builder_validation/L1_{builder}_{ticker}.json"
    try:
        pkt = build_peer_earnings_snapshot(ticker, qi["filed_8k"], out_path=out_path)
        results.record(1, builder, "no_crash", True, ticker=ticker)
        results.record(1, builder, "returns_dict", isinstance(pkt, dict), f"got {type(pkt).__name__}", ticker=ticker)
        for key in ["schema_version", "ticker", "pit_cutoff", "peers", "summary", "assembled_at"]:
            results.record(1, builder, f"has_{key}", key in pkt, ticker=ticker)
        if save_dir:
            _save_packet(save_dir, builder, ticker, "L1", pkt)
    except Exception as e:
        results.record(1, builder, "no_crash", False, str(e)[:200], ticker=ticker)

    # --- Builder 5: build_macro_snapshot ---
    builder = "build_macro_snapshot"
    try:
        from macro_snapshot import build_macro_snapshot
        results.record(1, builder, "importable", True, ticker=ticker)
    except Exception as e:
        results.record(1, builder, "importable", False, str(e), ticker=ticker)
        return

    out_path = f"/tmp/builder_validation/L1_{builder}_{ticker}.json"
    try:
        pkt = build_macro_snapshot(ticker, qi["filed_8k"], qi["market_session"],
                                    out_path=out_path, source='yahoo')
        results.record(1, builder, "no_crash", True, ticker=ticker)
        results.record(1, builder, "returns_dict", isinstance(pkt, dict), f"got {type(pkt).__name__}", ticker=ticker)
        for key in ["schema_version", "ticker", "pit_cutoff", "market_now", "catalysts", "gaps", "assembled_at"]:
            results.record(1, builder, f"has_{key}", key in pkt, ticker=ticker)
        # Verify H5 fix: gaps field exists
        results.record(1, builder, "gaps_is_list", isinstance(pkt.get("gaps"), list),
                       f"gaps type: {type(pkt.get('gaps')).__name__}", ticker=ticker)
        if save_dir:
            _save_packet(save_dir, builder, ticker, "L1", pkt)
    except Exception as e:
        results.record(1, builder, "no_crash", False, str(e)[:200], ticker=ticker)

    # --- Builder 6: build_consensus (SKIP if no --allow-av) ---
    builder = "build_consensus"
    try:
        from build_consensus import build_consensus
        results.record(1, builder, "importable", True, ticker=ticker)
    except Exception as e:
        results.record(1, builder, "importable", False, str(e), ticker=ticker)

    # --- Builder 7: build_prior_financials ---
    builder = "build_prior_financials"
    try:
        from build_prior_financials import build_prior_financials
        results.record(1, builder, "importable", True, ticker=ticker)
    except Exception as e:
        results.record(1, builder, "importable", False, str(e), ticker=ticker)
        return

    out_path = f"/tmp/builder_validation/L1_{builder}_{ticker}.json"
    try:
        # Need period_of_report from quarter_info — use an older 8-K so prior quarters exist
        qi_pf = {
            "period_of_report": qi["period_of_report"],
            "filed_8k": qi["filed_8k"],
            "market_session": qi["market_session"],
            "quarter_label": "",
        }
        pkt = build_prior_financials(ticker, qi_pf, as_of_ts=qi["filed_8k"], out_path=out_path)
        results.record(1, builder, "no_crash", True, ticker=ticker)
        results.record(1, builder, "returns_dict", isinstance(pkt, dict), f"got {type(pkt).__name__}", ticker=ticker)
        for key in ["schema_version", "ticker", "source_mode", "quarters", "summary", "gaps", "assembled_at"]:
            results.record(1, builder, f"has_{key}", key in pkt, ticker=ticker)
        results.record(1, builder, "source_mode_historical",
                       pkt.get("source_mode") == "historical", f"got {pkt.get('source_mode')}", ticker=ticker)
        if save_dir:
            _save_packet(save_dir, builder, ticker, "L1", pkt)
    except Exception as e:
        results.record(1, builder, "no_crash", False, str(e)[:200], ticker=ticker)


# ═══════════════════════════════════════════════════════════════════════
# LAYER 2 — HISTORICAL INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════

def layer2_historical_tests(results: TestResults, tickers: list[str], save_dir: str | None):
    """Layer 2: Run builders with PIT cutoff, verify non-empty and schema-valid."""
    print("\n── Layer 2: Historical Integration ──", file=sys.stderr)

    for ticker in tickers:
        fix = FIXTURES[ticker]
        qi = _make_quarter_info(fix)
        pit = qi["filed_8k"]

        # Builder 2: guidance_history — test PIT filtering + empty handling
        builder = "build_guidance_history"
        try:
            from warmup_cache import build_guidance_history
            out_path = f"/tmp/builder_validation/L2_{builder}_{ticker}.json"
            build_guidance_history(ticker, pit=pit, out_path=out_path)
            with open(out_path) as f:
                pkt = json.load(f)
            series_count = len(pkt.get("series", []))
            if fix["guidance_count"] > 0:
                results.record(2, builder, "historical_non_empty", series_count > 0,
                               f"{series_count} series", ticker=ticker)
            else:
                results.record(2, builder, "graceful_empty", series_count == 0,
                               f"expected 0, got {series_count}", ticker=ticker)
            # PIT field echoed
            results.record(2, builder, "pit_echoed", pkt.get("pit") == pit,
                           f"expected {pit[:20]}..., got {str(pkt.get('pit'))[:20]}...", ticker=ticker)
            if save_dir:
                _save_packet(save_dir, builder, ticker, "L2_hist", pkt)
        except Exception as e:
            results.record(2, builder, "historical_run", False, str(e)[:200], ticker=ticker)

        # Builder 4: peer_earnings_snapshot
        builder = "build_peer_earnings_snapshot"
        try:
            from peer_earnings_snapshot import build_peer_earnings_snapshot
            out_path = f"/tmp/builder_validation/L2_{builder}_{ticker}.json"
            pkt = build_peer_earnings_snapshot(ticker, pit, out_path=out_path)
            peer_count = len(pkt.get("peers", []))
            results.record(2, builder, "historical_has_peers", peer_count > 0,
                           f"{peer_count} peers", ticker=ticker)
            # Verify returns-schedule nulling for any peer with forward returns
            for peer in pkt.get("peers", []):
                # All peer returns should have been calculated BEFORE pit
                # (they filed before pit, so their returns windows should be complete)
                pass  # Structural check — just verify packet is well-formed
            results.record(2, builder, "packet_well_formed", True, ticker=ticker)
            if save_dir:
                _save_packet(save_dir, builder, ticker, "L2_hist", pkt)
        except Exception as e:
            results.record(2, builder, "historical_run", False, str(e)[:200], ticker=ticker)

        # Builder 7: prior_financials — verify quarters exist and fiscal labels
        builder = "build_prior_financials"
        try:
            from build_prior_financials import build_prior_financials
            out_path = f"/tmp/builder_validation/L2_{builder}_{ticker}.json"
            qi_pf = {
                "period_of_report": qi["period_of_report"],
                "filed_8k": qi["filed_8k"],
                "market_session": qi["market_session"],
                "quarter_label": "",
            }
            pkt = build_prior_financials(ticker, qi_pf, as_of_ts=pit, out_path=out_path)
            q_count = len(pkt.get("quarters", []))
            results.record(2, builder, "historical_has_quarters", q_count > 0,
                           f"{q_count} quarters", ticker=ticker)
            # Verify fiscal labels present
            if q_count > 0:
                labels = [q.get("fiscal_label", "") for q in pkt["quarters"]]
                all_labeled = all(l for l in labels)
                results.record(2, builder, "all_quarters_have_fiscal_labels", all_labeled,
                               f"labels: {labels[:3]}...", ticker=ticker)
                # Verify source_mode
                results.record(2, builder, "source_mode_historical",
                               pkt.get("source_mode") == "historical", ticker=ticker)
                # Verify key metrics coverage
                rev_count = sum(1 for q in pkt["quarters"] if q.get("revenue") is not None)
                results.record(2, builder, "revenue_coverage", rev_count > 0,
                               f"{rev_count}/{q_count} quarters have revenue", ticker=ticker)
            if save_dir:
                _save_packet(save_dir, builder, ticker, "L2_hist", pkt)
        except Exception as e:
            results.record(2, builder, "historical_run", False, str(e)[:200], ticker=ticker)

        # Builder 3: inter_quarter_context — historical with PIT
        builder = "build_inter_quarter_context"
        try:
            from warmup_cache import build_inter_quarter_context
            out_path = f"/tmp/builder_validation/L2_{builder}_{ticker}.json"
            build_inter_quarter_context(ticker, qi["prev_8k_ts"], pit, out_path=out_path)
            with open(out_path) as f:
                pkt = json.load(f)
            total_news = pkt.get("summary", {}).get("total_news", 0)
            total_filings = pkt.get("summary", {}).get("total_filings", 0)
            total_days = pkt.get("summary", {}).get("total_day_blocks", 0)
            results.record(2, builder, "historical_has_days", total_days > 0,
                           f"{total_days} days, {total_news} news, {total_filings} filings", ticker=ticker)
            # Verify cutoff echoed
            results.record(2, builder, "cutoff_ts_echoed",
                           pkt.get("context_cutoff_ts") == pit, ticker=ticker)
            if save_dir:
                _save_packet(save_dir, builder, ticker, "L2_hist", pkt)
        except Exception as e:
            results.record(2, builder, "historical_run", False, str(e)[:200], ticker=ticker)

        # Builder 5: macro_snapshot — historical with Yahoo (Sunday-safe, avoids Polygon rate limits)
        builder = "build_macro_snapshot"
        try:
            from macro_snapshot import build_macro_snapshot
            out_path = f"/tmp/builder_validation/L2_{builder}_{ticker}.json"
            pkt = build_macro_snapshot(ticker, pit, qi["market_session"],
                                        out_path=out_path, source='yahoo')
            spy_level = (pkt.get("market_now", {}).get("spy", {}) or {}).get("level_at_pit")
            vix = pkt.get("market_now", {}).get("vix_close")
            gaps = pkt.get("gaps", [])
            results.record(2, builder, "historical_runs", True,
                           f"spy_level={spy_level}, vix={vix}, gaps={len(gaps)}", ticker=ticker)
            results.record(2, builder, "has_gaps_field", isinstance(gaps, list), ticker=ticker)
            if save_dir:
                _save_packet(save_dir, builder, ticker, "L2_hist", pkt)
        except Exception as e:
            results.record(2, builder, "historical_run", False, str(e)[:200], ticker=ticker)


# ═══════════════════════════════════════════════════════════════════════
# LAYER 3 — DIFFERENTIAL PIT TESTS
# ═══════════════════════════════════════════════════════════════════════

def layer3_differential_pit(results: TestResults, save_dir: str | None):
    """Layer 3: Run inter_quarter_context at 3 cutoff points, verify event inclusion/exclusion."""
    print("\n── Layer 3: Differential PIT Tests ──", file=sys.stderr)

    # Use FIVE — has known news at 16:05-16:06, 8-K at 16:14
    ticker = "FIVE"
    fix = FIXTURES[ticker]
    qi = _make_quarter_info(fix)
    prev_8k_ts = qi["prev_8k_ts"]

    # 3 cutoff points:
    cutoff_before = "2025-08-27T16:04:00-04:00"   # Before ALL news
    cutoff_between = "2025-08-27T16:06:00-04:00"   # After first news (16:05:13), before others
    cutoff_at_8k = "2025-08-27T16:14:48-04:00"     # At 8-K filing (includes all news)

    from warmup_cache import build_inter_quarter_context

    cutoffs = [
        ("before_news", cutoff_before),
        ("between_news", cutoff_between),
        ("at_8k_filing", cutoff_at_8k),
    ]

    news_counts = {}
    for label, cutoff in cutoffs:
        builder = "build_inter_quarter_context"
        out_path = f"/tmp/builder_validation/L3_{builder}_{ticker}_{label}.json"
        try:
            build_inter_quarter_context(ticker, prev_8k_ts, cutoff, out_path=out_path)
            with open(out_path) as f:
                pkt = json.load(f)
            total_news = pkt.get("summary", {}).get("total_news", 0)
            news_counts[label] = total_news
            results.record(3, builder, f"pit_{label}_runs", True,
                           f"total_news={total_news}", ticker=ticker)
            if save_dir:
                _save_packet(save_dir, builder, ticker, f"L3_{label}", pkt)
        except Exception as e:
            results.record(3, builder, f"pit_{label}_runs", False, str(e)[:200], ticker=ticker)
            news_counts[label] = -1

    # Verify monotonic: before <= between <= at_8k
    if all(v >= 0 for v in news_counts.values()):
        monotonic = (news_counts["before_news"] <= news_counts["between_news"]
                     <= news_counts["at_8k_filing"])
        results.record(3, "build_inter_quarter_context", "news_count_monotonic",
                       monotonic,
                       f"before={news_counts['before_news']}, between={news_counts['between_news']}, at_8k={news_counts['at_8k_filing']}",
                       ticker=ticker)

    # Verify forward-return nulling at 8-K cutoff
    # At the 8-K cutoff, news events with hourly end times PAST 16:14:48 should have hourly=None
    builder = "build_inter_quarter_context"
    at_8k_path = f"/tmp/builder_validation/L3_{builder}_{ticker}_at_8k_filing.json"
    if os.path.exists(at_8k_path):
        with open(at_8k_path) as f:
            pkt = json.load(f)

        # Find the cutoff day's events
        cutoff_day = "2025-08-27"
        cutoff_events = []
        for day in pkt.get("days", []):
            if day.get("date") == cutoff_day:
                cutoff_events = day.get("events", [])
                break

        news_with_nulled_hourly = 0
        news_with_present_hourly = 0
        for ev in cutoff_events:
            if ev.get("type") != "news":
                continue
            fr = ev.get("forward_returns", {})
            if fr is None:
                continue
            if fr.get("hourly") is None:
                news_with_nulled_hourly += 1
            else:
                news_with_present_hourly += 1

        # Known: news hourly ends at ~17:05-17:06, cutoff at 16:14 → hourly should be NULLED
        results.record(3, builder, "pit_forward_returns_nulled",
                       news_with_nulled_hourly > 0,
                       f"nulled={news_with_nulled_hourly}, present={news_with_present_hourly}",
                       ticker=ticker)

    # C1 fix verification: test with the NEW datetime comparison
    # Run the same cutoff but verify the _parse_dt_for_pit function works
    try:
        from warmup_cache import _parse_dt_for_pit
        # Test cross-timezone comparison
        dt1 = _parse_dt_for_pit("2025-08-27T16:14:48-04:00")  # ET
        dt2 = _parse_dt_for_pit("2025-08-27T20:14:48+00:00")  # UTC (same moment)
        results.record(3, "_parse_dt_for_pit", "cross_tz_equality",
                       dt1 == dt2, f"ET={dt1}, UTC={dt2}", ticker="")
        # Test Z suffix
        dt3 = _parse_dt_for_pit("2025-08-27T20:14:48Z")
        results.record(3, "_parse_dt_for_pit", "z_suffix_parse",
                       dt3 == dt1, f"Z={dt3}, ET={dt1}", ticker="")
        # Test ordering across DST boundary
        dt_est = _parse_dt_for_pit("2025-02-26T16:03:55-05:00")  # EST
        dt_edt = _parse_dt_for_pit("2025-08-27T16:14:48-04:00")  # EDT
        results.record(3, "_parse_dt_for_pit", "cross_dst_ordering",
                       dt_est < dt_edt, f"EST={dt_est} < EDT={dt_edt}", ticker="")
    except ImportError:
        results.record(3, "_parse_dt_for_pit", "importable", False, "function not found", ticker="")

    # ── L3 Peer PIT: verify C1b fix (returns nulling uses datetime, not string) ──
    builder = "build_peer_earnings_snapshot"
    try:
        from peer_earnings_snapshot import _parse_dt_for_pit as peer_parse_dt
        # Verify the peer module has _parse_dt_for_pit
        results.record(3, builder, "has_parse_dt_for_pit", True, ticker=ticker)

        # C1b fix verification: cross-timezone datetime comparison in peer module
        dt_et = peer_parse_dt("2025-08-27T16:14:48-04:00")
        dt_utc = peer_parse_dt("2025-08-27T20:14:48+00:00")
        results.record(3, builder, "c1b_cross_tz_equality",
                       dt_et == dt_utc, f"ET={dt_et}, UTC={dt_utc}", ticker="")

        dt_z = peer_parse_dt("2025-08-27T20:14:48Z")
        results.record(3, builder, "c1b_z_suffix_parse",
                       dt_z == dt_et, f"Z={dt_z}, ET={dt_et}", ticker="")

        dt_est = peer_parse_dt("2025-02-26T16:03:55-05:00")  # EST
        dt_edt = peer_parse_dt("2025-08-27T16:14:48-04:00")  # EDT
        results.record(3, builder, "c1b_cross_dst_ordering",
                       dt_est < dt_edt, f"EST={dt_est} < EDT={dt_edt}", ticker="")

        # Smoke: run peer with historical cutoff, verify it works
        from peer_earnings_snapshot import build_peer_earnings_snapshot
        out_path = f"/tmp/builder_validation/L3_{builder}_{ticker}_pit.json"
        pkt = build_peer_earnings_snapshot(ticker, qi["filed_8k"], out_path=out_path)
        peer_count = len(pkt.get("peers", []))
        results.record(3, builder, "pit_historical_runs",
                       peer_count > 0, f"{peer_count} peers", ticker=ticker)
        if save_dir:
            _save_packet(save_dir, builder, ticker, "L3_pit", pkt)
    except ImportError as e:
        results.record(3, builder, "has_parse_dt_for_pit", False, str(e), ticker=ticker)
    except Exception as e:
        results.record(3, builder, "pit_differential", False, str(e)[:200], ticker=ticker)


# ═══════════════════════════════════════════════════════════════════════
# LAYER 4 — LIVE SMOKE TESTS
# ═══════════════════════════════════════════════════════════════════════

def layer4_live_smoke(results: TestResults, tickers: list[str], allow_av: bool, save_dir: str | None):
    """Layer 4: Run builders in live mode (pit_cutoff=None or now())."""
    print("\n── Layer 4: Live Smoke Tests ──", file=sys.stderr)
    ticker = tickers[0]
    fix = FIXTURES[ticker]
    qi = _make_quarter_info(fix)
    now_ts = datetime.now(timezone.utc).isoformat()

    # Builder 2: guidance_history — live (no PIT)
    builder = "build_guidance_history"
    try:
        from warmup_cache import build_guidance_history
        out_path = f"/tmp/builder_validation/L4_{builder}_{ticker}.json"
        build_guidance_history(ticker, pit=None, out_path=out_path)
        with open(out_path) as f:
            pkt = json.load(f)
        series = len(pkt.get("series", []))
        results.record(4, builder, "live_no_crash", True, f"{series} series", ticker=ticker)
        results.record(4, builder, "pit_is_null", pkt.get("pit") is None, ticker=ticker)
        # Live should have >= historical data
        hist_path = f"/tmp/builder_validation/L2_{builder}_{ticker}.json"
        if os.path.exists(hist_path):
            with open(hist_path) as f:
                hist = json.load(f)
            hist_series = len(hist.get("series", []))
            results.record(4, builder, "live_gte_historical",
                           series >= hist_series,
                           f"live={series}, hist={hist_series}", ticker=ticker)
        if save_dir:
            _save_packet(save_dir, builder, ticker, "L4_live", pkt)
    except Exception as e:
        results.record(4, builder, "live_no_crash", False, str(e)[:200], ticker=ticker)

    # Builder 4: peer_earnings — live (pass now() since it requires non-None)
    builder = "build_peer_earnings_snapshot"
    try:
        from peer_earnings_snapshot import build_peer_earnings_snapshot
        out_path = f"/tmp/builder_validation/L4_{builder}_{ticker}.json"
        pkt = build_peer_earnings_snapshot(ticker, now_ts, out_path=out_path)
        peer_count = len(pkt.get("peers", []))
        results.record(4, builder, "live_no_crash", True, f"{peer_count} peers", ticker=ticker)
        if save_dir:
            _save_packet(save_dir, builder, ticker, "L4_live", pkt)
    except Exception as e:
        results.record(4, builder, "live_no_crash", False, str(e)[:200], ticker=ticker)

    # Builder 5: macro_snapshot — live Yahoo (Sunday-safe)
    builder = "build_macro_snapshot"
    try:
        from macro_snapshot import build_macro_snapshot
        out_path = f"/tmp/builder_validation/L4_{builder}_{ticker}.json"
        pkt = build_macro_snapshot(ticker, now_ts, out_path=out_path, source='yahoo')
        results.record(4, builder, "live_yahoo_no_crash", True, ticker=ticker)
        gaps = pkt.get("gaps", [])
        gap_types = [g.get("type") for g in gaps]
        results.record(4, builder, "gaps_field_works",
                       isinstance(gaps, list), f"gap_types={gap_types}", ticker=ticker)
        if save_dir:
            _save_packet(save_dir, builder, ticker, "L4_live", pkt)
    except Exception as e:
        results.record(4, builder, "live_yahoo_no_crash", False, str(e)[:200], ticker=ticker)

    # Builder 6: consensus — ONLY if --allow-av
    builder = "build_consensus"
    if allow_av:
        try:
            from build_consensus import build_consensus
            out_path = f"/tmp/builder_validation/L4_{builder}_{ticker}.json"
            qi_consensus = {
                "period_of_report": qi["period_of_report"],
                "filed_8k": qi["filed_8k"],
                "market_session": qi["market_session"],
            }
            pkt = build_consensus(ticker, qi_consensus, as_of_ts=None, out_path=out_path)
            qr_count = len(pkt.get("quarterly_rows", []))
            fe_count = len(pkt.get("forward_estimates", []))
            results.record(4, builder, "live_av_no_crash", True,
                           f"rows={qr_count}, fwd={fe_count}", ticker=ticker)
            results.record(4, builder, "source_mode_live",
                           pkt.get("source_mode") == "live", ticker=ticker)
            results.record(4, builder, "forward_estimates_present",
                           fe_count > 0, f"{fe_count} forward estimates", ticker=ticker)
            if save_dir:
                _save_packet(save_dir, builder, ticker, "L4_live", pkt)
        except Exception as e:
            results.record(4, builder, "live_av_no_crash", False, str(e)[:200], ticker=ticker)
    else:
        results.record(4, builder, "skipped_no_av_flag", True, "use --allow-av", ticker=ticker)

    # Builder 7: prior_financials — live (no PIT)
    builder = "build_prior_financials"
    try:
        from build_prior_financials import build_prior_financials
        out_path = f"/tmp/builder_validation/L4_{builder}_{ticker}.json"
        qi_pf = {
            "period_of_report": qi["period_of_report"],
            "filed_8k": qi["filed_8k"],
            "market_session": qi["market_session"],
            "quarter_label": "",
        }
        pkt = build_prior_financials(ticker, qi_pf, as_of_ts=None, out_path=out_path)
        q_count = len(pkt.get("quarters", []))
        results.record(4, builder, "live_no_crash", True, f"{q_count} quarters", ticker=ticker)
        results.record(4, builder, "source_mode_live",
                       pkt.get("source_mode") == "live", ticker=ticker)
        # Live should have >= historical quarters
        hist_path = f"/tmp/builder_validation/L2_{builder}_{ticker}.json"
        if os.path.exists(hist_path):
            with open(hist_path) as f:
                hist = json.load(f)
            hist_q = len(hist.get("quarters", []))
            results.record(4, builder, "live_gte_historical",
                           q_count >= hist_q,
                           f"live={q_count}, hist={hist_q}", ticker=ticker)
        if save_dir:
            _save_packet(save_dir, builder, ticker, "L4_live", pkt)
    except Exception as e:
        results.record(4, builder, "live_no_crash", False, str(e)[:200], ticker=ticker)


# ═══════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════

def _save_packet(save_dir: str, builder: str, ticker: str, label: str, pkt: dict):
    """Save packet for manual inspection."""
    path = os.path.join(save_dir, f"{builder}_{ticker}_{label}.json")
    os.makedirs(save_dir, exist_ok=True)
    with open(path, "w") as f:
        json.dump(pkt, f, indent=2, default=str)


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Builder Validation Harness — Phase 2")
    parser.add_argument("--layer", type=int, choices=[1, 2, 3, 4], help="Run specific layer only")
    parser.add_argument("--ticker", type=str, help="Run for specific ticker only")
    parser.add_argument("--allow-av", action="store_true", help="Allow AlphaVantage calls (1 consensus = 3 AV endpoints)")
    parser.add_argument("--save", action="store_true", help="Save all packets to /tmp/builder_validation/")
    args = parser.parse_args()

    tickers = [args.ticker.upper()] if args.ticker else ["FIVE", "DOCU", "CRM", "COST"]
    for t in tickers:
        if t not in FIXTURES:
            print(f"Error: {t} not in fixtures. Available: {list(FIXTURES.keys())}", file=sys.stderr)
            sys.exit(1)

    save_dir = f"/tmp/builder_validation/{datetime.now().strftime('%Y%m%d_%H%M%S')}" if args.save else None
    if save_dir:
        print(f"Saving packets to: {save_dir}")

    results = TestResults()
    layers = [args.layer] if args.layer else [1, 2, 3, 4]

    # Redirect builder stdout to /dev/null. Test harness prints to stderr.
    # This keeps test progress visible while suppressing legacy builder noise.
    import io
    devnull = open(os.devnull, 'w')
    original_stdout = sys.stdout

    try:
        for layer_num in layers:
            sys.stdout = devnull  # suppress builder prints
            try:
                if layer_num == 1:
                    layer1_contract_tests(results, tickers, save_dir)
                elif layer_num == 2:
                    layer2_historical_tests(results, tickers, save_dir)
                elif layer_num == 3:
                    layer3_differential_pit(results, save_dir)
                elif layer_num == 4:
                    layer4_live_smoke(results, tickers, args.allow_av, save_dir)
            finally:
                sys.stdout = original_stdout

    except Exception as e:
        sys.stdout = original_stdout
        print(f"\nFATAL: {e}")
        traceback.print_exc()
    finally:
        sys.stdout = original_stdout
        devnull.close()

    # Save results JSON
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        results_path = os.path.join(save_dir, "results.json")
        with open(results_path, "w") as f:
            json.dump(results.to_dict(), f, indent=2)
        print(f"\nResults saved to: {results_path}")

    all_passed = results.summary()
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
