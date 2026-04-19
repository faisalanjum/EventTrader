#!/usr/bin/env python3
"""Sequential calibration: finalize Q3 prediction, run Q3 learner, then Q4, then Q1_FY2024.
Uses existing bundles where available to avoid AV rate-limit."""
import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "earnings"))

from earnings_orchestrator import (
    COMPANIES_DIR,
    LearnerOutcome,
    finalize_prediction_result,
    get_attribution_paths,
    get_prediction_paths,
    PREDICTOR_MODEL_ID,
    run_learner_for_quarter,
    validate_prediction_result,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger("calibration")

TICKER = "AVGO"
TARGETS = [
    ("0001730168-23-000074", "Q3_FY2023", "finalize_and_learn"),   # prediction written, needs finalize + learn
    ("0001730168-23-000093", "Q4_FY2023", "full"),                 # full pipeline via CLI
    ("0001730168-24-000012", "Q1_FY2024", "full"),                 # full pipeline via CLI
]


def _load_events():
    return json.loads((COMPANIES_DIR / TICKER / "events" / "event.json").read_text())["events"]


def _find_index(events, accession):
    for i, e in enumerate(events):
        if e.get("accession_8k") == accession:
            return i
    raise RuntimeError(f"{accession} not in event.json")


def _build_quarter_info(events, i):
    e = events[i]
    return {
        "accession_8k": e["accession_8k"],
        "filed_8k": e["filed_8k"],
        "market_session": e.get("market_session_8k"),
        "period_of_report": None,
        "prev_8k_ts": events[i - 1]["filed_8k"] if i > 0 else None,
        "quarter_label": e["quarter_label"],
    }


def finalize_and_learn(accession, quarter_label):
    """Q3 path: prediction exists from diagnostic, finalize + run learner."""
    events = _load_events()
    idx = _find_index(events, accession)
    qi = _build_quarter_info(events, idx)
    paths = get_prediction_paths(TICKER, qi)

    log.info("[%s] Finalizing existing prediction", quarter_label)
    finalize_prediction_result(
        result_path=paths["result_path"],
        ticker=TICKER,
        quarter_info=qi,
        model=PREDICTOR_MODEL_ID,
    )
    prediction = json.loads(paths["result_path"].read_text())
    validate_prediction_result(prediction, TICKER, quarter_label)
    log.info("[%s] Prediction: %s | %s | %s",
             quarter_label, prediction["direction"],
             prediction["confidence_bucket"], prediction["magnitude_bucket"])

    log.info("[%s] Running learner ...", quarter_label)
    live_state = COMPANIES_DIR / TICKER / "events" / "live_state.json"
    t0 = datetime.now()
    result, outcome = run_learner_for_quarter(
        ticker=TICKER,
        quarter_info=qi,
        events=events,
        current_index=idx,
        pit_mode="historical",
        live_state_path=live_state,
    )
    log.info("[%s] Learner done in %.1fs", quarter_label, (datetime.now() - t0).total_seconds())
    if outcome in LearnerOutcome.SKIPPED:
        raise RuntimeError(f"Learner skipped for {quarter_label}: {outcome}")
    if result is None:
        raise RuntimeError(f"Learner failed for {quarter_label}: {outcome}")
    pc = result["feedback"]["prediction_comparison"]
    log.info("[%s] Attribution: category=%s | correct=%s | mag_err=%s",
             quarter_label, result["primary_driver"]["category"],
             pc["direction_correct"], pc["magnitude_error_pct"])


def full_pipeline(accession, quarter_label):
    """Q4, Q1_FY2024 path: shell out to the CLI for full --save --predict --learn."""
    log.info("[%s] Running full CLI pipeline", quarter_label)
    t0 = datetime.now()
    result = subprocess.run(
        ["python3", "scripts/earnings/earnings_orchestrator.py",
         TICKER, accession, "--save", "--predict", "--learn"],
        capture_output=True,
        text=True,
    )
    elapsed = (datetime.now() - t0).total_seconds()
    log.info("[%s] CLI exited %d in %.1fs", quarter_label, result.returncode, elapsed)
    if result.returncode != 0:
        log.error("[%s] stdout tail:\n%s", quarter_label, result.stdout[-2000:])
        log.error("[%s] stderr tail:\n%s", quarter_label, result.stderr[-2000:])
        raise RuntimeError(f"Full pipeline failed for {quarter_label}")
    # Print last lines of stdout for visibility
    log.info("[%s] stdout tail:\n%s", quarter_label, result.stdout[-1500:])


def main():
    log.info("=== Calibration start: %s ===", datetime.now().isoformat())
    for accession, quarter_label, mode in TARGETS:
        log.info("--- Processing %s (%s, mode=%s) ---", quarter_label, accession, mode)
        try:
            if mode == "finalize_and_learn":
                finalize_and_learn(accession, quarter_label)
            elif mode == "full":
                full_pipeline(accession, quarter_label)
        except Exception as e:
            log.error("[%s] FAILED: %s", quarter_label, e)
            log.error("Stopping per historical failure policy (ticker bootstrap stops)")
            break
    log.info("=== Calibration done: %s ===", datetime.now().isoformat())


if __name__ == "__main__":
    main()
