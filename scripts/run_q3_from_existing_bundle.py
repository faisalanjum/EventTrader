#!/usr/bin/env python3
"""One-off: run predictor + learner on AVGO Q3_FY2023 using the existing bundle.
Skips bundle rebuild to avoid AlphaVantage daily rate limit.
"""
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "earnings"))

from earnings_orchestrator import (
    COMPANIES_DIR,
    finalize_prediction_result,
    get_attribution_paths,
    get_prediction_paths,
    PREDICTOR_MODEL_ID,
    run_learner_for_quarter,
    run_predictor_via_sdk,
    validate_prediction_result,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)

TICKER = "AVGO"
ACCESSION = "0001730168-23-000074"  # Q3_FY2023


def main():
    event_path = COMPANIES_DIR / TICKER / "events" / "event.json"
    events = json.loads(event_path.read_text())["events"]

    # Find Q3_FY2023
    current_idx = None
    quarter_info = None
    for i, e in enumerate(events):
        if e.get("accession_8k") == ACCESSION:
            current_idx = i
            quarter_info = {
                "accession_8k": e["accession_8k"],
                "filed_8k": e["filed_8k"],
                "market_session": e.get("market_session_8k"),
                "period_of_report": None,
                "prev_8k_ts": events[i - 1]["filed_8k"] if i > 0 else None,
                "quarter_label": e["quarter_label"],
            }
            break
    if quarter_info is None:
        raise RuntimeError(f"{ACCESSION} not in event.json")

    log.info("Ticker: %s | Quarter: %s | Accession: %s",
             TICKER, quarter_info["quarter_label"], ACCESSION)

    paths = get_prediction_paths(TICKER, quarter_info)
    if not paths["bundle_path"].exists():
        raise RuntimeError(f"Bundle missing: {paths['bundle_path']}")
    if not paths["rendered_path"].exists():
        raise RuntimeError(f"Rendered bundle missing: {paths['rendered_path']}")

    # ── Step 1: Predictor via SDK (reuses existing bundle) ──
    if paths["result_path"].exists():
        log.info("Deleting stale prediction/result.json")
        paths["result_path"].unlink()

    log.info("Running predictor via SDK on existing bundle ...")
    t0 = datetime.now()
    run_predictor_via_sdk(paths["bundle_path"], paths["rendered_path"], paths["result_path"])
    log.info("Predictor done in %.1fs", (datetime.now() - t0).total_seconds())

    if not paths["result_path"].exists():
        raise RuntimeError("Predictor did not write result.json")

    finalize_prediction_result(
        result_path=paths["result_path"],
        ticker=TICKER,
        quarter_info=quarter_info,
        model=PREDICTOR_MODEL_ID,
    )

    prediction = json.loads(paths["result_path"].read_text())
    validate_prediction_result(prediction, TICKER, quarter_info["quarter_label"])
    log.info("Prediction: %s | confidence=%s (%s) | magnitude=%s",
             prediction["direction"], prediction["confidence_score"],
             prediction["confidence_bucket"], prediction["magnitude_bucket"])

    # ── Step 2: Learner via SDK ──
    log.info("Running learner via SDK ...")
    live_state_path = COMPANIES_DIR / TICKER / "events" / "live_state.json"
    t1 = datetime.now()
    attribution, _outcome = run_learner_for_quarter(
        ticker=TICKER,
        quarter_info=quarter_info,
        events=events,
        current_index=current_idx,
        pit_mode="historical",
        live_state_path=live_state_path,
    )
    log.info("Learner done in %.1fs", (datetime.now() - t1).total_seconds())

    if attribution:
        pd = attribution.get("primary_driver", {})
        fb = attribution.get("feedback", {})
        pc = fb.get("prediction_comparison", {})
        log.info("Attribution: primary_driver=%s | correct=%s | mag_error=%s",
                 pd.get("category"), pc.get("direction_correct"), pc.get("magnitude_error_pct"))
    else:
        log.error("Learner failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
