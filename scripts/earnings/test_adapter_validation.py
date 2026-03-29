#!/usr/bin/env python3
"""Phase 3 — Adapter Validation Suite

Thorough validation that builder_adapters.py correctly wraps all 7 legacy builders.
Tests adapters across all 4 tickers in both historical and live modes.

Test categories:
    A. Contract: every adapter returns dict with required enrichment fields
    B. Content equivalence: adapter output matches legacy output (same data, extra fields)
    C. Mode correctness: source_mode, pit_cutoff, effective_cutoff_ts per the §2b table
    D. All tickers: FIVE, DOCU, CRM, COST (different FYE months, guidance coverage, peer counts)
    E. Consensus with AV: actual AV call through adapter
    F. Edge cases: missing quarter_info fields, SystemExit catching

Usage:
    python3 scripts/earnings/test_adapter_validation.py                    # All tests except AV
    python3 scripts/earnings/test_adapter_validation.py --allow-av         # Include consensus (3 AV calls)
    python3 scripts/earnings/test_adapter_validation.py --ticker FIVE      # Single ticker
    python3 scripts/earnings/test_adapter_validation.py --save             # Save packets

Environment:
    NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD (or .env)
    ALPHAVANTAGE_API_KEY (only with --allow-av)
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

_env_path = PROJECT_ROOT / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

# ── Fixtures ────────────────────────────────────────────────────────────

FIXTURES = {
    "FIVE": {
        "ticker": "FIVE",
        "current_8k": {
            "accession": "0001177609-25-000037",
            "filed_8k": "2025-08-27T16:14:48-04:00",
            "market_session": "post_market",
            "period_of_report": "2025-08-27",
        },
        "prev_8k_ts": "2025-06-04T16:23:39-04:00",
        "guidance_count": 468,
    },
    "DOCU": {
        "ticker": "DOCU",
        "current_8k": {
            "accession": "0001261333-25-000129",
            "filed_8k": "2025-09-04T16:07:22-04:00",
            "market_session": "post_market",
            "period_of_report": "2025-09-03",
        },
        "prev_8k_ts": "2025-06-05T16:22:44-04:00",
        "guidance_count": 314,
    },
    "CRM": {
        "ticker": "CRM",
        "current_8k": {
            "accession": "0001108524-25-000083",
            "filed_8k": "2025-09-03T16:03:27-04:00",
            "market_session": "post_market",
            "period_of_report": "2025-09-03",
        },
        "prev_8k_ts": "2025-05-28T16:05:54-04:00",
        "guidance_count": 0,
    },
    "COST": {
        "ticker": "COST",
        "current_8k": {
            "accession": "0000909832-25-000093",
            "filed_8k": "2025-09-25T16:16:57-04:00",
            "market_session": "post_market",
            "period_of_report": "2025-09-25",
        },
        "prev_8k_ts": "2025-05-29T16:24:57-04:00",
        "guidance_count": 0,
    },
}

REQUIRED_ENRICHMENT_KEYS = ["pit_cutoff", "source_mode", "effective_cutoff_ts"]
REQUIRED_BASE_KEYS = ["schema_version", "ticker", "assembled_at"]


def _make_qi(fix: dict) -> dict:
    ck = fix["current_8k"]
    return {
        "accession_8k": ck["accession"],
        "filed_8k": ck["filed_8k"],
        "market_session": ck["market_session"],
        "period_of_report": ck["period_of_report"],
        "prev_8k_ts": fix.get("prev_8k_ts"),
        "quarter_label": "",
    }


# ── Test Results ────────────────────────────────────────────────────────

class Results:
    def __init__(self):
        self.results: list[dict] = []
        self.start = time.time()

    def record(self, cat: str, builder: str, test: str, passed: bool,
               detail: str = "", ticker: str = ""):
        self.results.append({
            "cat": cat, "builder": builder, "test": test,
            "ticker": ticker, "passed": passed, "detail": detail,
        })
        status = "PASS" if passed else "FAIL"
        t = f" [{ticker}]" if ticker else ""
        msg = f"  {status}: {cat} {builder}{t} — {test}"
        if detail and not passed:
            msg += f" ({detail})"
        print(msg, file=sys.stderr)

    def summary(self):
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        failed = total - passed
        elapsed = time.time() - self.start
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"ADAPTER VALIDATION: {passed}/{total} passed, {failed} failed ({elapsed:.1f}s)", file=sys.stderr)
        if failed:
            print(f"\nFAILURES:", file=sys.stderr)
            for r in self.results:
                if not r["passed"]:
                    t = f" [{r['ticker']}]" if r["ticker"] else ""
                    print(f"  {r['cat']} {r['builder']}{t} — {r['test']}: {r['detail']}", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)
        return failed == 0

    def to_dict(self):
        return {
            "run_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_s": round(time.time() - self.start, 1),
            "total": len(self.results),
            "passed": sum(1 for r in self.results if r["passed"]),
            "failed": len(self.results) - sum(1 for r in self.results if r["passed"]),
            "results": self.results,
        }


# ═══════════════════════════════════════════════════════════════════════
# A. CONTRACT TESTS — required fields, return type, both modes
# ═══════════════════════════════════════════════════════════════════════

def test_contract(R: Results, tickers: list[str], save_dir: str | None):
    """Every adapter returns dict with enrichment fields in both modes."""
    print("\n── A. Contract Tests ──", file=sys.stderr)

    import builder_adapters as A

    # Expected effective_cutoff_ts per builder per mode
    # None = null, "pit" = equals pit_cutoff, "filed" = equals filed_8k, "now" = non-null derived
    EFF_EXPECT = {
        "build_8k_packet":              {"hist": None,  "live": None},
        "build_guidance_history":       {"hist": "pit", "live": None},
        "build_inter_quarter_context":  {"hist": "pit", "live": "filed"},
        "build_peer_earnings_snapshot": {"hist": "pit", "live": "now"},
        "build_macro_snapshot":         {"hist": "pit", "live": "now"},
        "build_consensus":              {"hist": "pit", "live": None},
        "build_prior_financials":       {"hist": "pit", "live": None},
    }

    ADAPTERS = [
        ("build_8k_packet", A.build_8k_packet, {}),
        ("build_guidance_history", A.build_guidance_history, {}),
        ("build_inter_quarter_context", A.build_inter_quarter_context, {}),
        ("build_peer_earnings_snapshot", A.build_peer_earnings_snapshot, {}),
        ("build_macro_snapshot", A.build_macro_snapshot, {"source": "yahoo"}),
        # consensus skipped here (AV-gated)
        ("build_prior_financials", A.build_prior_financials, {}),
    ]

    for ticker in tickers:
        fix = FIXTURES[ticker]
        qi = _make_qi(fix)
        pit = qi["filed_8k"]

        for name, fn, kw in ADAPTERS:
            for mode, pit_arg in [("hist", pit), ("live", None)]:
                out = f"/tmp/adapter_validation/{name}_{ticker}_{mode}.json" if save_dir else None
                if out:
                    os.makedirs(os.path.dirname(out), exist_ok=True)
                try:
                    pkt = fn(ticker, qi, pit_cutoff=pit_arg, out_path=out, **kw)

                    # Returns dict
                    R.record("A", name, f"{mode}_returns_dict",
                             isinstance(pkt, dict), f"got {type(pkt).__name__}", ticker)

                    # Has base keys
                    for key in REQUIRED_BASE_KEYS:
                        R.record("A", name, f"{mode}_has_{key}",
                                 key in pkt, ticker=ticker)

                    # Has enrichment keys
                    for key in REQUIRED_ENRICHMENT_KEYS:
                        R.record("A", name, f"{mode}_has_{key}",
                                 key in pkt, ticker=ticker)

                    # source_mode correct
                    expected_mode = "historical" if pit_arg else "live"
                    R.record("A", name, f"{mode}_source_mode",
                             pkt.get("source_mode") == expected_mode,
                             f"got {pkt.get('source_mode')}", ticker)

                    # pit_cutoff echoed correctly
                    R.record("A", name, f"{mode}_pit_cutoff_echoed",
                             pkt.get("pit_cutoff") == pit_arg,
                             f"expected {str(pit_arg)[:20]}, got {str(pkt.get('pit_cutoff'))[:20]}", ticker)

                    # effective_cutoff_ts per §2b table
                    eff = pkt.get("effective_cutoff_ts")
                    expect = EFF_EXPECT[name][mode]
                    if expect is None:
                        ok = eff is None
                        detail = f"expected null, got {str(eff)[:25]}"
                    elif expect == "pit":
                        ok = eff == pit
                        detail = f"expected pit, got {str(eff)[:25]}"
                    elif expect == "filed":
                        ok = eff == qi["filed_8k"]
                        detail = f"expected filed_8k, got {str(eff)[:25]}"
                    elif expect == "now":
                        ok = eff is not None and eff != pit
                        detail = f"expected now()-derived, got {str(eff)[:25]}"
                    else:
                        ok = False
                        detail = f"unexpected expect={expect}"
                    R.record("A", name, f"{mode}_effective_cutoff_ts", ok, detail, ticker)

                    if save_dir and out:
                        with open(out, "w") as f:
                            json.dump(pkt, f, indent=2, default=str)

                except Exception as e:
                    R.record("A", name, f"{mode}_no_crash", False, str(e)[:200], ticker)


# ═══════════════════════════════════════════════════════════════════════
# B. CONTENT EQUIVALENCE — adapter packet contains all legacy data
# ═══════════════════════════════════════════════════════════════════════

def test_content_equivalence(R: Results, save_dir: str | None):
    """Adapter output for builders 4-7 (dict-returning) contains same data as legacy."""
    print("\n── B. Content Equivalence ──", file=sys.stderr)

    ticker = "FIVE"
    fix = FIXTURES[ticker]
    qi = _make_qi(fix)
    pit = qi["filed_8k"]

    # Builder 4: peer — compare adapter vs legacy
    try:
        from peer_earnings_snapshot import build_peer_earnings_snapshot as legacy_peer
        import builder_adapters as A

        legacy_pkt = legacy_peer(ticker, pit, out_path="/tmp/adapter_validation/equiv_peer_legacy.json")
        adapter_pkt = A.build_peer_earnings_snapshot(ticker, qi, pit_cutoff=pit,
                                                      out_path="/tmp/adapter_validation/equiv_peer_adapter.json")

        # Same peers
        legacy_peers = {p["ticker"] for p in legacy_pkt.get("peers", [])}
        adapter_peers = {p["ticker"] for p in adapter_pkt.get("peers", [])}
        R.record("B", "build_peer_earnings_snapshot", "same_peer_set",
                 legacy_peers == adapter_peers,
                 f"legacy={len(legacy_peers)}, adapter={len(adapter_peers)}", ticker)

        # Same schema_version
        R.record("B", "build_peer_earnings_snapshot", "same_schema_version",
                 legacy_pkt.get("schema_version") == adapter_pkt.get("schema_version"), ticker=ticker)

        # Adapter has enrichment fields (some may already exist in legacy with same name)
        has_all_enrichment = all(k in adapter_pkt for k in REQUIRED_ENRICHMENT_KEYS)
        R.record("B", "build_peer_earnings_snapshot", "adapter_has_all_enrichment_keys",
                 has_all_enrichment,
                 f"has: {[k for k in REQUIRED_ENRICHMENT_KEYS if k in adapter_pkt]}", ticker)
    except Exception as e:
        R.record("B", "build_peer_earnings_snapshot", "equivalence_test", False, str(e)[:200], ticker)

    # Builder 7: prior_financials — compare adapter vs legacy
    try:
        from build_prior_financials import build_prior_financials as legacy_pf
        import builder_adapters as A

        qi_legacy = {
            "period_of_report": qi["period_of_report"],
            "filed_8k": qi["filed_8k"],
            "market_session": qi["market_session"],
            "quarter_label": "",
        }
        legacy_pkt = legacy_pf(ticker, qi_legacy, as_of_ts=pit,
                                out_path="/tmp/adapter_validation/equiv_pf_legacy.json")
        adapter_pkt = A.build_prior_financials(ticker, qi, pit_cutoff=pit,
                                                out_path="/tmp/adapter_validation/equiv_pf_adapter.json")

        # Same quarter count
        legacy_q = len(legacy_pkt.get("quarters", []))
        adapter_q = len(adapter_pkt.get("quarters", []))
        R.record("B", "build_prior_financials", "same_quarter_count",
                 legacy_q == adapter_q,
                 f"legacy={legacy_q}, adapter={adapter_q}", ticker)

        # Same periods
        legacy_periods = [q["period"] for q in legacy_pkt.get("quarters", [])]
        adapter_periods = [q["period"] for q in adapter_pkt.get("quarters", [])]
        R.record("B", "build_prior_financials", "same_periods",
                 legacy_periods == adapter_periods,
                 f"legacy={legacy_periods[:3]}, adapter={adapter_periods[:3]}", ticker)

        # Same source_mode value (legacy already has it)
        R.record("B", "build_prior_financials", "same_source_mode",
                 legacy_pkt.get("source_mode") == adapter_pkt.get("source_mode"), ticker=ticker)
    except Exception as e:
        R.record("B", "build_prior_financials", "equivalence_test", False, str(e)[:200], ticker)

    # Builder 1: 8k_packet — adapter reads from disk, should match legacy disk output
    try:
        from warmup_cache import build_8k_packet as legacy_8k
        import builder_adapters as A

        legacy_path = "/tmp/adapter_validation/equiv_8k_legacy.json"
        legacy_8k(qi["accession_8k"], ticker, out_path=legacy_path)
        with open(legacy_path) as f:
            legacy_pkt = json.load(f)

        adapter_pkt = A.build_8k_packet(ticker, qi, pit_cutoff=pit,
                                         out_path="/tmp/adapter_validation/equiv_8k_adapter.json")

        # Same accession
        R.record("B", "build_8k_packet", "same_accession",
                 legacy_pkt.get("accession_8k") == adapter_pkt.get("accession_8k"), ticker=ticker)

        # Same section count
        legacy_secs = len(legacy_pkt.get("sections", []))
        adapter_secs = len(adapter_pkt.get("sections", []))
        R.record("B", "build_8k_packet", "same_section_count",
                 legacy_secs == adapter_secs,
                 f"legacy={legacy_secs}, adapter={adapter_secs}", ticker)

        # Same exhibit count
        legacy_ex = len(legacy_pkt.get("exhibits_99", []))
        adapter_ex = len(adapter_pkt.get("exhibits_99", []))
        R.record("B", "build_8k_packet", "same_exhibit_count",
                 legacy_ex == adapter_ex,
                 f"legacy={legacy_ex}, adapter={adapter_ex}", ticker)
    except SystemExit:
        R.record("B", "build_8k_packet", "equivalence_test", False, "legacy sys.exit", ticker)
    except Exception as e:
        R.record("B", "build_8k_packet", "equivalence_test", False, str(e)[:200], ticker)


# ═══════════════════════════════════════════════════════════════════════
# C. CONSENSUS WITH AV
# ═══════════════════════════════════════════════════════════════════════

def test_consensus_av(R: Results, save_dir: str | None):
    """Test consensus adapter with actual AV call."""
    print("\n── C. Consensus AV Test ──", file=sys.stderr)

    ticker = "FIVE"
    fix = FIXTURES[ticker]
    qi = _make_qi(fix)

    import builder_adapters as A

    # Historical mode
    try:
        pkt = A.build_consensus(ticker, qi, pit_cutoff=qi["filed_8k"],
                                 out_path="/tmp/adapter_validation/consensus_hist.json")
        qr = len(pkt.get("quarterly_rows", []))
        fe = len(pkt.get("forward_estimates", []))
        R.record("C", "build_consensus", "hist_returns_dict", isinstance(pkt, dict), ticker=ticker)
        R.record("C", "build_consensus", "hist_source_mode",
                 pkt.get("source_mode") == "historical", ticker=ticker)
        R.record("C", "build_consensus", "hist_has_quarterly_rows",
                 qr > 0, f"{qr} rows", ticker)
        R.record("C", "build_consensus", "hist_no_forward_estimates",
                 fe == 0, f"{fe} forward estimates (expected 0)", ticker)
        R.record("C", "build_consensus", "hist_pit_cutoff_echoed",
                 pkt.get("pit_cutoff") == qi["filed_8k"], ticker=ticker)
        R.record("C", "build_consensus", "hist_effective_cutoff",
                 pkt.get("effective_cutoff_ts") == qi["filed_8k"], ticker=ticker)

        # Check gaps — should include pit_excluded for forward estimates
        gap_types = [g.get("type") for g in pkt.get("gaps", [])]
        R.record("C", "build_consensus", "hist_pit_excluded_gap",
                 "pit_excluded" in gap_types,
                 f"gap_types={gap_types}", ticker)
    except Exception as e:
        R.record("C", "build_consensus", "hist_run", False, str(e)[:200], ticker)


# ═══════════════════════════════════════════════════════════════════════
# D. EDGE CASES
# ═══════════════════════════════════════════════════════════════════════

def test_edge_cases(R: Results):
    """Test adapter error handling and edge cases."""
    print("\n── D. Edge Cases ──", file=sys.stderr)

    import builder_adapters as A

    # E1: build_8k_packet with bad accession → should raise ValueError, not SystemExit
    try:
        qi_bad = {
            "accession_8k": "0000000000-00-000000",
            "filed_8k": "2025-01-01T00:00:00-05:00",
            "market_session": "post_market",
            "period_of_report": "2025-01-01",
        }
        try:
            A.build_8k_packet("ZZZZZ", qi_bad, pit_cutoff=None)
            R.record("D", "build_8k_packet", "bad_accession_raises", False,
                     "expected ValueError, got no error")
        except ValueError:
            R.record("D", "build_8k_packet", "bad_accession_raises_valueerror", True)
        except SystemExit:
            R.record("D", "build_8k_packet", "bad_accession_raises_valueerror", False,
                     "got SystemExit — adapter failed to catch it")
    except Exception as e:
        R.record("D", "build_8k_packet", "bad_accession_test", False, str(e)[:200])

    # E2: build_inter_quarter_context without prev_8k_ts → should raise ValueError
    try:
        qi_no_prev = {
            "accession_8k": "0001177609-25-000037",
            "filed_8k": "2025-08-27T16:14:48-04:00",
            "market_session": "post_market",
            "period_of_report": "2025-08-27",
            # prev_8k_ts intentionally missing
        }
        try:
            A.build_inter_quarter_context("FIVE", qi_no_prev, pit_cutoff=None)
            R.record("D", "build_inter_quarter_context", "missing_prev_raises", False,
                     "expected ValueError")
        except ValueError:
            R.record("D", "build_inter_quarter_context", "missing_prev_raises_valueerror", True)
    except Exception as e:
        R.record("D", "build_inter_quarter_context", "missing_prev_test", False, str(e)[:200])

    # E3: build_prior_financials without period_of_report → should raise ValueError
    try:
        qi_no_period = {
            "accession_8k": "0001177609-25-000037",
            "filed_8k": "2025-08-27T16:14:48-04:00",
            "market_session": "post_market",
            "period_of_report": "",  # empty
        }
        try:
            A.build_prior_financials("FIVE", qi_no_period, pit_cutoff=qi_no_period["filed_8k"])
            R.record("D", "build_prior_financials", "empty_period_raises", False,
                     "expected ValueError")
        except ValueError:
            R.record("D", "build_prior_financials", "empty_period_raises_valueerror", True)
    except Exception as e:
        R.record("D", "build_prior_financials", "empty_period_test", False, str(e)[:200])

    # E4: CRM guidance (0 count) — adapter should return packet with empty series
    try:
        qi_crm = _make_qi(FIXTURES["CRM"])
        pkt = A.build_guidance_history("CRM", qi_crm, pit_cutoff=qi_crm["filed_8k"])
        series = len(pkt.get("series", []))
        R.record("D", "build_guidance_history", "crm_empty_guidance",
                 series == 0, f"{series} series", "CRM")
        R.record("D", "build_guidance_history", "crm_has_enrichment",
                 all(k in pkt for k in REQUIRED_ENRICHMENT_KEYS), ticker="CRM")
    except Exception as e:
        R.record("D", "build_guidance_history", "crm_empty_test", False, str(e)[:200], "CRM")


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Adapter Validation Suite — Phase 3")
    parser.add_argument("--ticker", type=str, help="Single ticker")
    parser.add_argument("--allow-av", action="store_true", help="Include consensus AV test (3 AV endpoints)")
    parser.add_argument("--save", action="store_true", help="Save packets to /tmp/adapter_validation/")
    args = parser.parse_args()

    tickers = [args.ticker.upper()] if args.ticker else ["FIVE", "DOCU", "CRM", "COST"]
    save_dir = "/tmp/adapter_validation" if args.save else None

    R = Results()

    # Suppress builder stdout noise
    devnull = open(os.devnull, 'w')
    original_stdout = sys.stdout

    try:
        sys.stdout = devnull
        test_contract(R, tickers, save_dir)
        sys.stdout = original_stdout

        sys.stdout = devnull
        test_content_equivalence(R, save_dir)
        sys.stdout = original_stdout

        if args.allow_av:
            sys.stdout = devnull
            test_consensus_av(R, save_dir)
            sys.stdout = original_stdout

        sys.stdout = devnull
        test_edge_cases(R)
        sys.stdout = original_stdout

    except Exception as e:
        sys.stdout = original_stdout
        print(f"\nFATAL: {e}", file=sys.stderr)
        traceback.print_exc()
    finally:
        sys.stdout = original_stdout
        devnull.close()

    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        with open(os.path.join(save_dir, "adapter_results.json"), "w") as f:
            json.dump(R.to_dict(), f, indent=2)
        print(f"\nResults saved to: {save_dir}/adapter_results.json", file=sys.stderr)

    all_ok = R.summary()
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
