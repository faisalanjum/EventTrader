#!/usr/bin/env python3
"""A/B baseline: re-predict AVGO Q1-Q5 with learning_context stripped.

Saves all baseline artifacts to experiments/prediction_no_lessons/ so the
no-lessons variant has one canonical home per quarter.
Compares WITH-lessons (current prediction/result.json) vs WITHOUT-lessons (fresh).
"""
import json
import shutil
import sys
import logging
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
log = logging.getLogger("ab_baseline")

QUARTERS = [
    ("0001730168-23-000004", "Q1_FY2023"),
    ("0001730168-23-000062", "Q2_FY2023"),
    ("0001730168-23-000074", "Q3_FY2023"),
    ("0001730168-23-000093", "Q4_FY2023"),
    ("0001730168-24-000012", "Q1_FY2024"),
]


def strip_learning_context(bundle_in: Path, bundle_out: Path, rendered_out: Path) -> None:
    """Blank the learning_context in the bundle and re-render without the Prior Lessons section."""
    bundle = json.loads(bundle_in.read_text(encoding="utf-8"))
    bundle["learning_context"] = {
        "ticker_lessons": [],
        "global_lessons": [],
        "ticker_ref": None,
        "global_ref": None,
    }
    bundle_out.write_text(json.dumps(bundle, indent=2, default=str), encoding="utf-8")
    # Renderer skips the section when both ticker and global lessons are empty
    rendered_out.write_text(render_bundle_text(bundle), encoding="utf-8")


def _actual_direction(daily_pct: float) -> str:
    if daily_pct > 0:
        return "long"
    if daily_pct < 0:
        return "short"
    return "flat"


def main():
    results = []
    for accession, ql in QUARTERS:
        log.info("=== %s (%s) ===", ql, accession)
        ev_dir = COMPANIES_DIR / "AVGO" / "events" / ql
        pred_dir = ev_dir / "prediction"
        baseline_dir = ev_dir / "experiments" / "prediction_no_lessons"
        baseline_dir.mkdir(parents=True, exist_ok=True)

        # Current (WITH-lessons) prediction — already on disk
        original = pred_dir / "result.json"
        if not original.exists():
            log.error("  Missing %s — skipping", original)
            continue
        with_lessons = json.loads(original.read_text(encoding="utf-8"))

        # Actual return (from learning/result.json — renamed from attribution/ per obsidian_thinking.md)
        attr_path = ev_dir / "learning" / "result.json"
        if not attr_path.exists():
            # Backward compat: during the migration window, some quarters may still
            # be at the old attribution/ path before the migration runs.
            legacy = ev_dir / "attribution" / "result.json"
            if legacy.exists():
                attr_path = legacy
        if attr_path.exists():
            attr = json.loads(attr_path.read_text(encoding="utf-8"))
            actual_daily = attr["actual_return"]["daily_stock_pct"]
            actual_dir = _actual_direction(actual_daily)
        else:
            actual_daily, actual_dir = None, "unknown"

        # Strip learning context — context_bundle is at QUARTER ROOT (ev_dir),
        # not under prediction/, per obsidian_thinking.md (2026-04-17).
        stripped_bundle = baseline_dir / "context_bundle.json"
        stripped_rendered = baseline_dir / "context_bundle_rendered.txt"
        source_bundle = ev_dir / "context_bundle.json"
        if not source_bundle.exists():
            # Pre-migration fallback
            source_bundle = pred_dir / "context_bundle.json"
        strip_learning_context(source_bundle, stripped_bundle, stripped_rendered)
        log.info("  Stripped bundle written: %s", stripped_bundle)

        # Run predictor on stripped bundle (reuse existing if present — resume support)
        test_result_path = baseline_dir / "result.json"
        baseline_session_id = None
        if test_result_path.exists():
            log.info("  Reusing existing NO_LESSONS prediction (resume): %s", test_result_path)
        else:
            t0 = datetime.now()
            try:
                _pred_result, baseline_session_id = run_predictor_via_sdk(
                    stripped_bundle, stripped_rendered, test_result_path
                )
            except Exception as e:
                log.error("  Predictor SDK call failed: %s", e)
                continue
            dt = (datetime.now() - t0).total_seconds()
            log.info("  Predictor done in %.1fs", dt)

        if not test_result_path.exists():
            log.error("  No result written — skipping")
            continue

        # Finalize (add metadata fields + stamp sdk_session_id + render + harvest)
        quarter_info = {"quarter_label": ql, "accession_8k": accession}
        finalize_prediction_result(
            result_path=test_result_path,
            ticker="AVGO",
            quarter_info=quarter_info,
            model=PREDICTOR_MODEL_ID,
            sdk_session_id=baseline_session_id,
            experiment_name="prediction_no_lessons",
        )
        no_lessons = json.loads(test_result_path.read_text(encoding="utf-8"))
        # T1: load stripped bundle to derive expected lesson list (=[] for A/B)
        bundle = json.loads(stripped_bundle.read_text(encoding="utf-8"))
        _, _expected_lessons = _render_learning_context((bundle or {}).get("learning_context") or {})
        # U67 legacy/offline — A/B harness intentionally skips evidence_source_catalog
        # enforcement (predictions here can predate the catalog and are dev-only).
        validate_prediction_result(no_lessons, "AVGO", ql,
                                   expected_lesson_texts=_expected_lessons,
                                   expected_source_ids=None)

        def _correct(pred_dir, actual_dir):
            if pred_dir == "no_call":
                return actual_dir == "flat"
            return pred_dir == actual_dir

        r = {
            "quarter": ql,
            "actual_daily_pct": actual_daily,
            "actual_direction": actual_dir,
            "with_lessons": {
                "direction": with_lessons.get("direction"),
                "confidence": with_lessons.get("confidence_score"),
                "bucket": with_lessons.get("confidence_bucket"),
                "range": with_lessons.get("expected_move_range_pct"),
                "magnitude_bucket": with_lessons.get("magnitude_bucket"),
                "correct": _correct(with_lessons.get("direction"), actual_dir),
            },
            "without_lessons": {
                "direction": no_lessons.get("direction"),
                "confidence": no_lessons.get("confidence_score"),
                "bucket": no_lessons.get("confidence_bucket"),
                "range": no_lessons.get("expected_move_range_pct"),
                "magnitude_bucket": no_lessons.get("magnitude_bucket"),
                "correct": _correct(no_lessons.get("direction"), actual_dir),
            },
        }
        results.append(r)
        log.info(
            "  actual=%+.2f%% (%s) | WITH: %s(%d) correct=%s | WITHOUT: %s(%d) correct=%s",
            actual_daily if actual_daily is not None else 0, actual_dir,
            r["with_lessons"]["direction"], r["with_lessons"]["confidence"], r["with_lessons"]["correct"],
            r["without_lessons"]["direction"], r["without_lessons"]["confidence"], r["without_lessons"]["correct"],
        )

    # Save summary
    summary_path = Path("earnings-analysis/test-outputs/ab_baseline_AVGO.json")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    log.info("Summary written to %s", summary_path)

    # Headline
    with_correct = sum(1 for r in results if r["with_lessons"]["correct"])
    without_correct = sum(1 for r in results if r["without_lessons"]["correct"])
    n = len(results)
    log.info("=" * 60)
    log.info("A/B RESULT on %d AVGO quarters:", n)
    log.info("  WITH lessons:    %d/%d correct (%.0f%%)", with_correct, n, 100 * with_correct / n if n else 0)
    log.info("  WITHOUT lessons: %d/%d correct (%.0f%%)", without_correct, n, 100 * without_correct / n if n else 0)
    log.info("  Delta: %+d", with_correct - without_correct)
    log.info("=" * 60)
    for r in results:
        same = r["with_lessons"]["direction"] == r["without_lessons"]["direction"]
        marker = "SAME" if same else "DIFF"
        print(f"  {r['quarter']:10s} | actual {r['actual_daily_pct']:+6.2f}% ({r['actual_direction']:5s}) | "
              f"WITH {r['with_lessons']['direction']:6s}({r['with_lessons']['confidence']:3d}) "
              f"{'✓' if r['with_lessons']['correct'] else '✗'}  |  "
              f"WITHOUT {r['without_lessons']['direction']:6s}({r['without_lessons']['confidence']:3d}) "
              f"{'✓' if r['without_lessons']['correct'] else '✗'}  [{marker}]")


if __name__ == "__main__":
    main()
