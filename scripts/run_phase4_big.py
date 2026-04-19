#!/usr/bin/env python3
"""Phase 4 big run — 3 quarters sequentially, exercising guards end-to-end:

  Q3_FY2023: learner only (prediction already exists, finalized, Opus 4.7)
  Q4_FY2023: learner only (prediction already exists, Opus 4.6 — fine, it's frozen)
  Q1_FY2024: FULL pipeline (fresh bundle + predictor + learner)

All three SDK calls exercise:
  - _assert_claude_code_oauth_ready() (strips ANTHROPIC_API_KEY from env)
  - cli_path = /home/faisal/.local/bin/claude (system CLI)
  - env override (empty ANTHROPIC_API_KEY in subprocess)
  - Opus 4.7 + adaptive thinking

Expected duration: ~30 min total.
"""
import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "earnings"))

from earnings_orchestrator import COMPANIES_DIR, run_learner_for_quarter

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger("phase4")

TICKER = "AVGO"


def _load_events():
    return json.loads((COMPANIES_DIR / TICKER / "events" / "event.json").read_text())["events"]


def _find_idx(events, accession):
    for i, e in enumerate(events):
        if e.get("accession_8k") == accession:
            return i, e
    raise RuntimeError(f"{accession} not in event.json")


def _qi(events, i):
    e = events[i]
    return {
        "accession_8k": e["accession_8k"],
        "filed_8k": e["filed_8k"],
        "market_session": e.get("market_session_8k"),
        "period_of_report": None,
        "prev_8k_ts": events[i - 1]["filed_8k"] if i > 0 else None,
        "quarter_label": e["quarter_label"],
    }


def learner_only(accession, label):
    events = _load_events()
    i, e = _find_idx(events, accession)
    qi = _qi(events, i)
    log.info("[%s] Running learner-only (prediction already finalized)", label)
    t0 = datetime.now()
    result, _outcome = run_learner_for_quarter(
        ticker=TICKER,
        quarter_info=qi,
        events=events,
        current_index=i,
        pit_mode="historical",
        live_state_path=COMPANIES_DIR / TICKER / "events" / "live_state.json",
    )
    dt = (datetime.now() - t0).total_seconds()
    if not result:
        raise RuntimeError(f"[{label}] Learner failed")
    pc = result["feedback"]["prediction_comparison"]
    log.info(
        "[%s] DONE in %.1fs | model=%s | category=%s | correct=%s | mag_err=%s",
        label, dt, result["model_version"],
        result["primary_driver"]["category"],
        pc["direction_correct"], pc["magnitude_error_pct"],
    )
    return result


def full_pipeline(accession, label):
    log.info("[%s] Running FULL pipeline (bundle + predict + learn) via CLI", label)
    t0 = datetime.now()
    r = subprocess.run(
        [
            "python3", "scripts/earnings/earnings_orchestrator.py",
            TICKER, accession, "--save", "--predict", "--learn",
        ],
        capture_output=True, text=True,
    )
    dt = (datetime.now() - t0).total_seconds()
    log.info("[%s] CLI exit=%d in %.1fs", label, r.returncode, dt)
    if r.returncode != 0:
        log.error("[%s] stdout tail:\n%s", label, r.stdout[-2000:])
        log.error("[%s] stderr tail:\n%s", label, r.stderr[-2000:])
        raise RuntimeError(f"[{label}] full pipeline failed")
    # print last 30 lines for visibility
    log.info("[%s] stdout tail:\n%s", label, "\n".join(r.stdout.splitlines()[-30:]))


def main():
    log.info("=== Phase 4 big run START %s ===", datetime.now().isoformat())
    try:
        learner_only("0001730168-23-000074", "Q3_FY2023")
        learner_only("0001730168-23-000093", "Q4_FY2023")
        full_pipeline("0001730168-24-000012", "Q1_FY2024")
    except Exception as e:
        log.error("STOPPED per historical failure policy: %s", e)
        sys.exit(1)
    log.info("=== Phase 4 big run DONE %s ===", datetime.now().isoformat())


if __name__ == "__main__":
    main()
