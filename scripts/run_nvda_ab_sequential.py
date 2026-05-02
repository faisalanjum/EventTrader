#!/usr/bin/env python3
"""NVDA sequential calibration with per-quarter A/B (WITH vs WITHOUT lessons).

For each of 5 NVDA quarters in chronological order:
  1. Full pipeline via CLI: --save --predict --learn
     (produces prediction/result.json WITH lessons + learning/result.json)
  2. Strip learning_context from the bundle, re-predict
     (produces experiments/prediction_no_lessons/result.json)
  3. Compare WITH vs WITHOUT on the same bundle

Lessons flow: AVGO's accumulated global.json + (NVDA Q1, Q2, ...) ticker.json
feed each successive NVDA quarter's WITH-lessons run.
"""
import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "earnings"))

from earnings_orchestrator import (
    COMPANIES_DIR,
    PREDICTOR_MODEL_ID,
    _render_learning_context,
    finalize_prediction_result,
    render_bundle_text,
    run_predictor_via_sdk,
    validate_prediction_result,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger("nvda_ab")

TICKER = "NVDA"


def _load_events():
    return json.loads((COMPANIES_DIR / TICKER / "events" / "event.json").read_text())["events"]


def _actual_direction(daily_pct: float) -> str:
    if daily_pct > 0:
        return "long"
    if daily_pct < 0:
        return "short"
    return "flat"


def _correct(direction: str, actual: str) -> bool:
    if direction == "no_call":
        return actual == "flat"
    return direction == actual


def strip_learning_context(src: Path, bundle_out: Path, rendered_out: Path) -> None:
    bundle = json.loads(src.read_text(encoding="utf-8"))
    bundle["learning_context"] = {
        "ticker_lessons": [],
        "global_lessons": [],
        "ticker_ref": None,
        "global_ref": None,
    }
    bundle_out.write_text(json.dumps(bundle, indent=2, default=str), encoding="utf-8")
    rendered_out.write_text(render_bundle_text(bundle), encoding="utf-8")


def run_full_pipeline(accession: str, label: str) -> None:
    log.info("[%s] === Full pipeline (predict + learn) starting ===", label)
    t0 = datetime.now()
    r = subprocess.run(
        [
            "python3", "scripts/earnings/earnings_orchestrator.py",
            TICKER, accession, "--save", "--predict", "--learn",
        ],
        capture_output=True, text=True,
    )
    dt = (datetime.now() - t0).total_seconds()
    log.info("[%s] Full pipeline CLI exit=%d in %.1fs", label, r.returncode, dt)
    if r.returncode != 0:
        log.error("[%s] stdout tail:\n%s", label, r.stdout[-1500:])
        log.error("[%s] stderr tail:\n%s", label, r.stderr[-1500:])
        raise RuntimeError(f"Full pipeline failed for {label}")


def run_baseline(accession: str, label: str, quarter_info: dict) -> None:
    log.info("[%s] === Baseline (predict WITHOUT lessons) starting ===", label)
    ev_dir = COMPANIES_DIR / TICKER / "events" / label
    baseline_dir = ev_dir / "experiments" / "prediction_no_lessons"
    baseline_dir.mkdir(parents=True, exist_ok=True)
    stripped_bundle = baseline_dir / "context_bundle.json"
    stripped_rendered = baseline_dir / "context_bundle_rendered.txt"
    # Context bundle is at QUARTER ROOT per obsidian_thinking.md (2026-04-17).
    strip_learning_context(ev_dir / "context_bundle.json", stripped_bundle, stripped_rendered)
    test_result_path = baseline_dir / "result.json"
    section_audit_path = baseline_dir / "section_audit.json"
    if test_result_path.exists():
        test_result_path.unlink()
    if section_audit_path.exists():
        section_audit_path.unlink()
    t0 = datetime.now()
    _pred_result, baseline_session_id = run_predictor_via_sdk(
        stripped_bundle, stripped_rendered, section_audit_path, test_result_path
    )
    dt = (datetime.now() - t0).total_seconds()
    log.info("[%s] Baseline predictor done in %.1fs", label, dt)
    finalize_prediction_result(
        result_path=test_result_path,
        ticker=TICKER,
        quarter_info=quarter_info,
        model=PREDICTOR_MODEL_ID,
        sdk_session_id=baseline_session_id,
        experiment_name="prediction_no_lessons",
    )
    # T1: load stripped bundle to derive expected lesson list (=[] for A/B)
    bundle = json.loads(stripped_bundle.read_text(encoding="utf-8"))
    _, _expected_lessons = _render_learning_context((bundle or {}).get("learning_context") or {})
    # U67 legacy/offline — A/B harness intentionally skips evidence_source_catalog
    # enforcement (predictions here can predate the catalog and are dev-only).
    validate_prediction_result(json.loads(test_result_path.read_text()), TICKER, label,
                               expected_lesson_texts=_expected_lessons,
                               expected_source_ids=None)


def compare(label: str) -> dict:
    attr = json.loads((COMPANIES_DIR / TICKER / "events" / label / "learning" / "result.json").read_text())
    with_pred = json.loads((COMPANIES_DIR / TICKER / "events" / label / "prediction" / "result.json").read_text())
    without_pred = json.loads((COMPANIES_DIR / TICKER / "events" / label / "experiments" / "prediction_no_lessons" / "result.json").read_text())

    actual = attr["actual_return"]["daily_stock_pct"]
    actual_dir = _actual_direction(actual)
    w_ok = _correct(with_pred["direction"], actual_dir)
    wo_ok = _correct(without_pred["direction"], actual_dir)

    log.info(
        "[%s] COMPARE | actual=%+.2f%% (%s) | WITH: %s(%d) %s | WITHOUT: %s(%d) %s | %s",
        label, actual, actual_dir,
        with_pred["direction"], with_pred["confidence_score"], "CORRECT" if w_ok else "WRONG",
        without_pred["direction"], without_pred["confidence_score"], "CORRECT" if wo_ok else "WRONG",
        "SAME" if with_pred["direction"] == without_pred["direction"] else "DIFF",
    )
    return {
        "quarter": label,
        "actual_pct": actual,
        "actual_dir": actual_dir,
        "with": {"direction": with_pred["direction"], "confidence": with_pred["confidence_score"], "correct": w_ok},
        "without": {"direction": without_pred["direction"], "confidence": without_pred["confidence_score"], "correct": wo_ok},
    }


def main():
    events = _load_events()
    targets = [(e["accession_8k"], e["quarter_label"]) for e in events[:5]]
    log.info("=== NVDA sequential calibration (5 quarters with A/B) ===")
    for acc, lbl in targets:
        log.info("  %s (%s)", lbl, acc)

    results = []
    for idx, (accession, label) in enumerate(targets):
        log.info("\n===== NVDA %s (%d/5) =====", label, idx + 1)
        qi = {
            "accession_8k": accession,
            "filed_8k": events[idx]["filed_8k"],
            "market_session": events[idx].get("market_session_8k"),
            "period_of_report": None,
            "prev_8k_ts": events[idx - 1]["filed_8k"] if idx > 0 else None,
            "quarter_label": label,
        }
        try:
            run_full_pipeline(accession, label)
            run_baseline(accession, label, qi)
            results.append(compare(label))
        except Exception as e:
            log.error("[%s] FAILED: %s — stopping ticker bootstrap per policy", label, e)
            break

    # Final summary
    log.info("\n============================================================")
    log.info("NVDA A/B FINAL on %d quarters:", len(results))
    w_correct = sum(1 for r in results if r["with"]["correct"])
    wo_correct = sum(1 for r in results if r["without"]["correct"])
    n = len(results)
    log.info("  WITH lessons:    %d/%d correct (%.0f%%)", w_correct, n, 100 * w_correct / n if n else 0)
    log.info("  WITHOUT lessons: %d/%d correct (%.0f%%)", wo_correct, n, 100 * wo_correct / n if n else 0)
    log.info("  Delta: %+d", w_correct - wo_correct)
    log.info("============================================================")

    summary_path = Path("earnings-analysis/test-outputs/ab_NVDA.json")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    log.info("Summary written to %s", summary_path)


if __name__ == "__main__":
    main()
