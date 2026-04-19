#!/usr/bin/env python3
"""Phase 4 Calibration: Run learner on 3-5 historical quarters for one ticker.

Usage (from terminal, NOT from inside Claude Code):
  source venv/bin/activate
  python3 scripts/calibrate_learner.py AVGO --max-quarters 5

This bypasses bundle building — only runs the learner on quarters that
already have prediction/result.json. Uses event.json for PIT derivation.
"""
import argparse
import json
import logging
import sys
import os
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "earnings"))

from earnings_orchestrator import (
    COMPANIES_DIR,
    LearnerOutcome,
    run_learner_for_quarter,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("calibrate_learner")


def main():
    parser = argparse.ArgumentParser(description="Learner calibration — run on historical quarters")
    parser.add_argument("ticker", help="Company ticker")
    parser.add_argument("--max-quarters", type=int, default=5, help="Max quarters to process")
    parser.add_argument("--dry-run", action="store_true", help="Show what would run without invoking learner")
    args = parser.parse_args()

    ticker = args.ticker.upper()
    event_path = COMPANIES_DIR / ticker / "events" / "event.json"
    live_state_path = COMPANIES_DIR / ticker / "events" / "live_state.json"

    if not event_path.exists():
        log.error("event.json not found: %s", event_path)
        sys.exit(1)

    events = json.loads(event_path.read_text())["events"]
    log.info("%s: %d quarters in event.json", ticker, len(events))

    # Find quarters with prediction but no learning result yet.
    # The learning/ dir is the post-migration path (renamed from attribution/
    # per obsidian_thinking.md 2026-04-17); checking the old path would mis-
    # flag every completed quarter as "eligible".
    eligible = []
    for i, e in enumerate(events):
        ql = e.get("quarter_label", "?")
        pred_path  = COMPANIES_DIR / ticker / "events" / ql / "prediction" / "result.json"
        learn_path = COMPANIES_DIR / ticker / "events" / ql / "learning"   / "result.json"
        if pred_path.exists() and not learn_path.exists():
            eligible.append((i, e))

    log.info("Eligible (prediction exists, learning missing): %d quarters", len(eligible))
    for _, e in eligible:
        log.info("  %s (filed %s)", e.get("quarter_label"), e.get("filed_8k", "?")[:10])

    # Process sequentially (up to max_quarters)
    to_process = eligible[:args.max_quarters]
    log.info("Will process: %d quarters", len(to_process))

    if args.dry_run:
        log.info("DRY RUN — not invoking learner")
        return

    results = []
    for idx, (event_index, event) in enumerate(to_process):
        ql = event.get("quarter_label", "?")
        log.info("\n{'='*60}")
        log.info("Quarter %d/%d: %s %s", idx + 1, len(to_process), ticker, ql)
        log.info("{'='*60}")

        # Build quarter_info from event
        quarter_info = {
            "accession_8k": event.get("accession_8k"),
            "filed_8k": event.get("filed_8k"),
            "market_session": event.get("market_session_8k"),
            "period_of_report": None,  # not needed for learner
            "prev_8k_ts": None,
            "quarter_label": event.get("quarter_label"),
        }

        t0 = datetime.now()
        attribution, outcome = run_learner_for_quarter(
            ticker=ticker,
            quarter_info=quarter_info,
            events=events,
            current_index=event_index,
            pit_mode="historical",
            live_state_path=live_state_path,
        )
        elapsed = (datetime.now() - t0).total_seconds()

        if attribution:
            pd = attribution.get("primary_driver", {})
            fb = attribution.get("feedback", {})
            pc = fb.get("prediction_comparison", {})
            results.append({
                "quarter": ql,
                "status": "ok",
                "outcome": outcome,  # "succeeded" | "recovered"
                "elapsed_s": round(elapsed, 1),
                "direction_correct": pc.get("direction_correct"),
                "primary_driver": pd.get("summary", "?")[:60],
                "category": pd.get("category", "?"),
                "predictor_lessons": len(fb.get("predictor_lessons", [])),
                "data_lessons": len(fb.get("data_lessons", [])),
            })
            log.info("OK [%s] (%.1fs) — %s | correct=%s", outcome, elapsed,
                     pd.get("category"), pc.get("direction_correct"))
        elif outcome in LearnerOutcome.SKIPPED:
            # Environmental skip (no prediction / no daily_stock). Not a
            # failure — label it correctly and stop per the sequential
            # policy (subsequent quarters likely have the same gap).
            results.append({"quarter": ql, "status": "skipped",
                            "outcome": outcome, "elapsed_s": round(elapsed, 1)})
            log.warning("SKIPPED for %s %s [%s] (%.1fs) — stopping sequential scan",
                        ticker, ql, outcome, elapsed)
            break
        else:
            # Pipeline-level failure. Outcome string IS the diagnostic.
            results.append({"quarter": ql, "status": "failed",
                            "outcome": outcome, "elapsed_s": round(elapsed, 1)})
            log.error("FAILED for %s %s [%s] (%.1fs) — stopping per historical failure policy",
                      ticker, ql, outcome, elapsed)
            break  # Historical failure policy: stop ticker's sequence

    # Summary
    print(f"\n{'='*60}")
    print(f"Calibration Summary: {ticker}")
    print(f"{'='*60}")
    for r in results:
        if r["status"] == "ok":
            print(f"  {r['quarter']}: OK [{r.get('outcome','?')}] ({r['elapsed_s']}s) — {r['category']} | correct={r['direction_correct']} | lessons={r['predictor_lessons']}+{r['data_lessons']}")
        elif r["status"] == "skipped":
            print(f"  {r['quarter']}: SKIPPED [{r.get('outcome','?')}] ({r['elapsed_s']}s)")
        else:
            print(f"  {r['quarter']}: FAILED [{r.get('outcome','?')}] ({r['elapsed_s']}s)")
    ok = sum(1 for r in results if r["status"] == "ok")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    failed = sum(1 for r in results if r["status"] == "failed")
    print(f"\n{ok} ok / {skipped} skipped / {failed} failed (total={len(results)})")

    # Write summary
    summary_path = Path(f"earnings-analysis/test-outputs/calibration_{ticker}.json")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w") as f:
        json.dump({"ticker": ticker, "results": results, "completed_at": datetime.now().isoformat()}, f, indent=2)
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
